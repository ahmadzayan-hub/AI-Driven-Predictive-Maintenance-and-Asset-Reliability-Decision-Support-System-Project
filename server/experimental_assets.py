"""Safe, read-only asset type inspection in a quarantined ingestion worker.

Never executes Power BI content or claims that PBIX == an analyzable dataset.
No OCR, text extraction, DAX evaluation or external services.
"""
from __future__ import annotations
import hashlib
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

class UnsupportedAsset(ValueError):
    pass

MAX_PACKAGE_ENTRIES=4000
MAX_UNCOMPRESSED_BYTES=700_000_000
MAX_MEMBER_EXPANSION_RATIO=1000

def identify(path):
    path=Path(path)
    with path.open("rb") as source:
        signature=source.read(12)
    ext=path.suffix.lower()
    if ext==".pdf" and signature.startswith(b"%PDF-"):
        return {"kind":"pdf","status":"requires_isolated_extraction_and_human_review"}
    if ext in (".png",".jpg",".jpeg",".webp",".tif",".tiff"):
        signatures = {
            ".png": signature.startswith(bytes.fromhex("89504e470d0a1a0a")),
            ".jpg": signature.startswith(bytes.fromhex("ffd8ff")),
            ".jpeg": signature.startswith(bytes.fromhex("ffd8ff")),
            ".webp": signature[:4] == b"RIFF" and signature[8:12] == b"WEBP",
            ".tif": signature[:4] in (bytes.fromhex("49492a00"), bytes.fromhex("4d4d002a")),
            ".tiff": signature[:4] in (bytes.fromhex("49492a00"), bytes.fromhex("4d4d002a")),
        }
        valid=signatures[ext]
        if not valid:
            raise UnsupportedAsset("File extension does not match recognizable image signature")
        return {"kind":"image","status":"requires_isolated_image_parser_and_human_review"}
    if ext==".pbix":
        if not zipfile.is_zipfile(path):
            raise UnsupportedAsset("Not a ZIP-based PBIX package; unknown layout")
        with zipfile.ZipFile(path) as archive:
            entries=archive.infolist()
            total=0
            if len(entries)>MAX_PACKAGE_ENTRIES:
                raise UnsupportedAsset("Too many PBIX archive entries")
            for info in entries:
                n=info.filename.replace("\\","/")
                segments=PurePosixPath(n).parts
                if n.startswith("/") or ".." in segments or ":" in n.split("/")[0]:
                    raise UnsupportedAsset("Unsafe archive member path")
                if info.flag_bits & 1:
                    raise UnsupportedAsset("Encrypted archive entries require a separate approved reader")
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise UnsupportedAsset("Unsupported archive compression method")
                if info.create_system == 3 and stat.S_ISLNK(info.external_attr >> 16):
                    raise UnsupportedAsset("Archive symbolic links are not allowed")
                if info.file_size > 1024 * 1024 and (
                    info.compress_size == 0 or
                    info.file_size > MAX_MEMBER_EXPANSION_RATIO * info.compress_size
                ):
                    raise UnsupportedAsset("Suspicious archive compression ratio")
                total+=info.file_size
                if total>MAX_UNCOMPRESSED_BYTES:
                    raise UnsupportedAsset("Potential decompression bomb")
            names={x.filename for x in entries}
        return {"kind":"pbix","entries":len(entries),
                "has_report_layout":any("Report/Layout" in n for n in names),
                "has_data_model":any(n.endswith("DataModel") for n in names),
                "status":"metadata_only_no_semantic_model_or_data_import"}
    raise UnsupportedAsset("Format not recognized by isolated inspector")
