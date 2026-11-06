"""Readable download names (owner's naming rules, 6 November 2026).

Plain words with spaces, the language as a word, no run identifiers: the
run, language and snapshot are recorded inside each file. See
docs/adr/2026-11-06-readable-download-names.md.
"""
from urllib.parse import quote

LANGUAGE = {"en": "English", "ar": "Arabic"}


def executive(language, format):
    """The executive brief as HTML or Word, or its slides."""
    word = LANGUAGE.get(language, "English")
    if format == "slides":
        return f"Executive Slides {word}.html"
    return f"Executive Brief {word}.{format}"


def film(language, name):
    """A rendered executive film or one of its companion files."""
    word = LANGUAGE.get(language, "English")
    return {"video.mp4": f"Executive Film {word}.mp4",
            "subtitles.vtt": f"Executive Film {word}.vtt",
            "subtitles.srt": f"Executive Film {word}.srt",
            "manifest.json": f"Executive Film {word} Manifest.json"}[name]


CLEANED_DATA = "Cleaned Data.csv"
SESSION_EXPORT = "Session Export.json"
DRAFT_PREVIEW = "Internal Draft.mp4"


def disposition(name, inline=False):
    """A Content-Disposition header that keeps the spaces in every browser:
    the quoted plain name, and the RFC 5987 encoded one beside it."""
    plain = name.encode("ascii", "ignore").decode().replace('"', "") or "download"
    return f'{"inline" if inline else "attachment"}; filename="{plain}"; filename*=UTF-8\'\'{quote(name)}'
