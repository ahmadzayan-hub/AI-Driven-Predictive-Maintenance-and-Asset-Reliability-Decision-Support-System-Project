"""Private, deterministic evidence extraction. No model or network API is used.

The caller owns authorization, persistence and original-byte retention. ``metadata``
is JSON-safe; binary derivatives appear only in ``artifacts`` and must never be
included in an ordinary metadata/API response. Source text is evidence, not an
instruction. Header/role and digest suggestions require a person's review.
"""

import hashlib
import io
import mimetypes
import os
import platform
import posixpath
import re
import shutil
import signal
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.parsers import expat

from server import datasets


EXTRACTION_VERSION = "evidence-extraction/1"
MAX_EXPANDED_BYTES = 64_000_000
MAX_PARTS = 2048
MAX_SHEETS = 32
MAX_TOTAL_ROWS = 100_000
MAX_CELLS = 250_000
MAX_DOCUMENT_CHARS = 1_000_000
CONVERSION_TIMEOUT = 60
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class IngestionError(datasets.DatasetError):
    """A controlled refusal, compatible with the existing bilingual API errors."""


def _error(en, ar="تعذّر استخراج هذا المصدر بأمان. راجع الملف والقيود.", status=422):
    return IngestionError(status, en, ar)


def _warning(code, en, ar):
    return {"code": code, "en": en, "ar": ar}


class _Budget:
    def __init__(self):
        self.used = 0
        self.rows = 0
        self.cells = 0

    def take(self, count):
        self.used += count
        if self.used > MAX_EXPANDED_BYTES:
            raise _error("The package exceeds the extraction expansion limit.",
                         "تجاوزت الحزمة حد الحجم المسموح بعد فك الضغط.")


def _open_package(data):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError, ValueError):
        raise _error("The source is not a valid Office package.", "المصدر ليس حزمة Office صالحة.")
    infos = archive.infolist()
    if len(infos) > MAX_PARTS:
        archive.close()
        raise _error("The package contains too many parts.", "تحتوي الحزمة على أجزاء أكثر من الحد المسموح.")
    names = set()
    declared = 0
    for info in infos:
        name = info.filename
        parts = name.split("/")
        if (name.startswith("/") or "\\" in name or ".." in parts
                or ":" in parts[0] or any(ord(c) < 32 or ord(c) == 127 for c in name)
                or name in names or info.flag_bits & 1
                or (info.external_attr >> 16) & 0o170000 == 0o120000):
            archive.close()
            raise _error("The package contains an unsafe, duplicate or encrypted part.",
                         "تحتوي الحزمة على جزء غير آمن أو مكرر أو مشفّر.")
        names.add(name)
        declared += info.file_size
        if declared > MAX_EXPANDED_BYTES:
            archive.close()
            raise _error("The package exceeds the extraction expansion limit.",
                         "تجاوزت الحزمة حد الحجم المسموح بعد فك الضغط.")
    return archive


def _tree(archive, part, budget):
    stack, roots = [], []

    def start(tag, attrs):
        node = ET.Element(tag, attrs)
        if stack:
            stack[-1].append(node)
        else:
            roots.append(node)
        stack.append(node)

    def end(_tag):
        stack.pop()

    def text(value):
        if stack:
            stack[-1].text = (stack[-1].text or "") + value

    datasets._parse_part(archive, part, budget, start=start, end=end, text=text)
    if len(roots) != 1:
        raise _error("The source XML has no single document root.")
    return roots[0]


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _attr(node, name, default=None):
    return next((value for key, value in node.attrib.items() if _local(key) == name), default)


def _children(node, name):
    return [child for child in node if _local(child.tag) == name]


def _first(node, name):
    return next((child for child in node if _local(child.tag) == name), None)


def _value(node, name, default=""):
    found = _first(node, name)
    return default if found is None else found.text or ""


def _read_bytes(archive, name, budget):
    chunks = []
    try:
        with archive.open(name) as stream:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                budget.take(len(chunk))
                chunks.append(chunk)
    except (zipfile.BadZipFile, KeyError, RuntimeError, OSError, EOFError):
        raise _error("A package part could not be read safely.")
    return b"".join(chunks)


def _letters(index):
    value, out = index + 1, ""
    while value:
        value, rem = divmod(value - 1, 26)
        out = chr(65 + rem) + out
    return out


def _cell_locator(sheet, ref):
    return "'" + sheet.replace("'", "''") + "'!" + ref


def _sheet_role(name, labels):
    text = (name + " " + " ".join(labels)).lower()
    # A suggestion, never an authoritative mapping or record-grain assignment.
    if any(word in name.lower() for word in ("summary", "ملخص", "إجمالي")):
        return "summary"
    if any(word in name.lower() for word in ("reconcil", "مطابقة")):
        return "sr_reconciliation"
    if any(word in text for word in ("work order", "wo status", "mms", "أمر عمل")):
        return "mms_work_order"
    if any(word in text for word in ("occ", "event id", "رقم الحدث")):
        return "occ_event"
    return "other"


def _header_row(rows):
    candidates = []
    terms = ("status", "date", "description", "location", "work", "event", "sr", "wo",
             "الحالة", "التاريخ", "الموقع", "الوصف")
    for row in rows[:40]:
        cells = [str(c["value"]).strip() for c in row["cells"].values()
                 if c["value"] is not None and str(c["value"]).strip()]
        if not cells:
            continue
        words = sum(1 for value in cells if not re.fullmatch(r"[-+\d.,:/ ]+", value))
        signals = sum(1 for value in cells if any(t in value.lower() for t in terms))
        long = sum(len(value) > 100 for value in cells)
        score = min(words, 15) + 2 * signals - long * 2
        candidates.append((score, -row["source_row"], row["source_row"]))
    return max(candidates)[2] if candidates else None


def _worksheet(archive, part, budget, name, strings, styles, date1904):
    root = _tree(archive, part, budget)
    hidden_columns, column_specs = set(), []
    for node in root.iter():
        if _local(node.tag) != "col":
            continue
        try:
            start, end = int(_attr(node, "min", "0")), int(_attr(node, "max", "0"))
        except ValueError:
            raise _error("A column range is invalid.")
        if start < 1 or end < start or end > datasets.MAX_COLUMNS:
            raise _error("A sheet column range exceeds the supported bounds.")
        hidden = _attr(node, "hidden", "0").lower() in ("1", "true")
        if hidden:
            hidden_columns.update(range(start - 1, end))
        column_specs.append({"min": start, "max": end, "hidden": hidden,
                             "attributes": dict(node.attrib)})
    rows, seen_rows, hidden_rows, width, count = [], set(), [], 0, 0
    shared_formulas, errors, uncached = 0, 0, 0
    for node in root.iter():
        if _local(node.tag) != "row":
            continue
        try:
            number = int(_attr(node, "r", str(len(rows) + 1)))
        except ValueError:
            raise _error("A worksheet source-row number is invalid.")
        if number < 1 or number > 1_048_576 or number in seen_rows:
            raise _error("A worksheet source row is repeated or outside Excel bounds.")
        if len(rows) >= datasets.MAX_ROWS + 40:
            raise _error("A worksheet exceeds the extraction row limit.")
        budget.rows += 1
        if budget.rows > MAX_TOTAL_ROWS:
            raise _error("The workbook exceeds the total extraction row limit.")
        seen_rows.add(number)
        hidden = _attr(node, "hidden", "0").lower() in ("1", "true")
        if hidden:
            hidden_rows.append(number)
        cells, previous = {}, -1
        for cell in _children(node, "c"):
            ref = _attr(cell, "r", "")
            index = datasets._column_index(ref)
            index = previous + 1 if index is None else index
            if index >= datasets.MAX_COLUMNS:
                raise _error("The sheet exceeds the supported column limit.")
            letter = _letters(index)
            if letter in cells:
                raise _error("A worksheet row contains a repeated cell address.")
            if ref and not re.fullmatch(r"[A-Za-z]+" + str(number), ref):
                raise _error("A cell address disagrees with its source row.")
            ref = letter + str(number)
            previous, width, count = index, max(width, index + 1), count + 1
            budget.cells += 1
            if count > MAX_CELLS or budget.cells > MAX_CELLS:
                raise _error("The worksheet exceeds the extraction cell limit.")
            kind, raw = _attr(cell, "t", "n"), _value(cell, "v")
            formula_node = _first(cell, "f")
            formula_raw = None if formula_node is None else formula_node.text or ""
            try:
                style = int(_attr(cell, "s", "0"))
            except ValueError:
                raise _error("A worksheet cell-style index is invalid.")
            if style < 0:
                raise _error("A worksheet cell-style index is invalid.")
            value = raw
            if kind == "s":
                try:
                    string_index = int(raw)
                    if string_index < 0:
                        raise ValueError()
                    value = strings[string_index]
                except (ValueError, IndexError):
                    raise _error("A shared-string reference is invalid.")
            elif kind == "inlineStr":
                value = "".join(t.text or "" for t in cell.iter() if _local(t.tag) == "t")
            elif kind == "b":
                value = "TRUE" if raw == "1" else "FALSE" if raw == "0" else raw
            elif kind == "e":
                errors += 1  # Retain the actual error token; never coerce it to zero/blank.
            elif kind not in ("str", "d") and raw and style < len(styles):
                if styles[style] != (False, False):
                    try:
                        value = datasets._serial_to_text(float(raw), styles[style], date1904) or raw
                    except (ValueError, OverflowError):
                        value = raw
            source_value = value if kind in ("s", "inlineStr") else raw
            cached = _first(cell, "v") is not None and (bool(raw) or kind == "str")
            if formula_node is not None and not cached:
                uncached += 1
            if formula_node is not None and _attr(formula_node, "t") == "shared":
                shared_formulas += 1
            cells[letter] = {
                "ref": ref, "locator": _cell_locator(name, ref), "column": letter,
                "type": kind, "style_index": style, "raw_value": source_value,
                "xml_value": raw,
                "value": value, "formula": None if formula_raw is None else "=" + formula_raw,
                "formula_raw": formula_raw,
                "formula_attributes": {} if formula_node is None else dict(formula_node.attrib),
                "has_cached_result": cached if formula_node is not None else None,
                "cached_raw": raw if formula_node is not None and cached else None,
                "cached_value": value if formula_node is not None and cached else None,
                "hidden_column": index in hidden_columns,
            }
        rows.append({"source_row": number, "hidden": hidden,
                     "locator": _cell_locator(name, str(number) + ":" + str(number)),
                     "cells": cells})
    header = _header_row(rows)
    header_cells = next((r["cells"] for r in rows if r["source_row"] == header), {})
    columns = [{"id": _letters(i), "letter": _letters(i),
                "label": str(header_cells.get(_letters(i), {}).get("value", "")),
                "hidden": i in hidden_columns,
                "header_locator": None if header is None else _cell_locator(name, _letters(i) + str(header))}
               for i in range(width)]
    filter_node = next((n for n in root.iter() if _local(n.tag) == "autoFilter"), None)
    filter_ref = _attr(filter_node, "ref") if filter_node is not None else None
    dimension = next((n for n in root.iter() if _local(n.tag) == "dimension"), None)
    data_rows = [r for r in rows if header is not None and r["source_row"] > header
                 and any(str(c["value"]).strip() for c in r["cells"].values())]
    beyond = []
    if filter_ref:
        ends = re.findall(r"[A-Za-z]+(\d+)", filter_ref)
        if ends:
            stop = max(int(value) for value in ends)
            beyond = [r["source_row"] for r in data_rows if r["source_row"] > stop]
    return {
        "name": name, "part": part, "header_row_proposed": header,
        "mapping_status": "requires_confirmation", "columns": columns, "rows": rows,
        "source_row_count": len(rows), "data_row_count_proposed": len(data_rows),
        "suggested_role": _sheet_role(name, [c["label"] for c in columns]),
        "hidden_columns": [_letters(i) for i in sorted(hidden_columns)],
        "hidden_rows": hidden_rows, "column_specs": column_specs,
        "auto_filter_ref": filter_ref, "rows_beyond_filter": beyond,
        "dimension_ref": _attr(dimension, "ref") if dimension is not None else None,
        "merged_cells": [_attr(n, "ref") for n in root.iter() if _local(n.tag) == "mergeCell"],
        "formula_count": sum(c["formula"] is not None for r in rows for c in r["cells"].values()),
        "uncached_formula_count": uncached, "shared_formula_count": shared_formulas,
        "error_cell_count": errors, "cell_count": count,
    }


def _workbook(data):
    budget = _Budget()
    with _open_package(data) as archive:
        names = set(archive.namelist())
        root_rels = datasets._relationships(archive, "", budget)
        workbook = next((target for kind, target in root_rels.values()
                         if kind.endswith("/officeDocument")), "xl/workbook.xml")
        if workbook not in names:
            raise _error("The package has no workbook part.")
        rels = datasets._relationships(archive, workbook, budget)
        tree = _tree(archive, workbook, budget)
        if _local(tree.tag) != "workbook":
            raise _error("The workbook part has an invalid root element.")
        settings = next((n for n in tree.iter() if _local(n.tag) == "workbookPr"), None)
        date1904 = settings is not None and _attr(settings, "date1904", "0").lower() in ("1", "true")
        def part(suffix):
            return next((target for kind, target in rels.values()
                         if kind.endswith(suffix) and target in names), None)
        strings = datasets._shared_strings(archive, part("/sharedStrings"), budget)
        styles = datasets._styles(archive, part("/styles"), budget)
        sheets = []
        for node in tree.iter():
            if _local(node.tag) != "sheet":
                continue
            rel = rels.get(_attr(node, "id"))
            if not rel or not rel[0].endswith("/worksheet") or rel[1] not in names:
                continue
            if len(sheets) >= MAX_SHEETS:
                raise _error("The workbook exceeds the extraction sheet limit.")
            sheet = _worksheet(archive, rel[1], budget, _attr(node, "name", ""),
                               strings, styles, date1904)
            sheet["visibility"] = _attr(node, "state", "visible")
            sheets.append(sheet)
        if not sheets:
            raise _error("The workbook has no readable worksheets.")
        if sum(s["source_row_count"] for s in sheets) > MAX_TOTAL_ROWS:
            raise _error("The workbook exceeds the total extraction row limit.")
        if sum(s["cell_count"] for s in sheets) > MAX_CELLS:
            raise _error("The workbook exceeds the total extraction cell limit.")
        external = any(name.startswith("xl/externalLinks/") for name in names)
        macros = any(name.lower().endswith("vbaproject.bin") for name in names)
    warnings = [_warning("mapping_unconfirmed", "Sheet roles and header rows are suggestions until reviewed.",
                         "أدوار الأوراق وصفوف العناوين مقترحات إلى أن تُراجع.")]
    if any(s["rows_beyond_filter"] for s in sheets):
        warnings.append(_warning("records_beyond_filter", "Records beyond a saved filter were retained.",
                                 "احتُفظ بالسجلات الواقعة بعد نطاق التصفية المحفوظ."))
    if any(s["uncached_formula_count"] for s in sheets):
        warnings.append(_warning("uncached_formulas", "Some formulas have no saved result; none were evaluated.",
                                 "لا توجد نتائج محفوظة لبعض الصيغ، ولم تُنفّذ أي صيغة."))
    if external or macros:
        warnings.append(_warning("inactive_content", "External workbook content and macros were not executed.",
                                 "لم يُنفّذ المحتوى الخارجي للمصنّف أو وحدات الماكرو."))
    return {"sheets": sheets, "warnings": warnings, "coverage": {
        "worksheets_extracted": len(sheets), "hidden_sheets_included": True,
        "hidden_rows_columns_included": True, "formulas_evaluated": False,
        "raw_and_cached_values_retained": True, "external_content_present": external,
        "macros_present": macros, "formatting_and_chart_rendering": "not_extracted",
        "record_grain": "requires_mapping_confirmation", "expanded_bytes_read": budget.used,
        "excel_date_system": "1904" if date1904 else "1900",
    }}


def _paragraph_text(node):
    parts = []
    def visit(current):
        for child in current:
            local = _local(child.tag)
            if local == "p":
                continue  # Text boxes' nested paragraphs get their own locators.
            if local in ("t", "delText"):
                parts.append(child.text or "")
            elif local == "tab":
                parts.append("\t")
            elif local in ("br", "cr"):
                parts.append("\n")
            else:
                visit(child)
    visit(node)
    return "".join(parts).strip()


def _style_levels(archive, budget):
    if "word/styles.xml" not in archive.namelist():
        return {}
    root = _tree(archive, "word/styles.xml", budget)
    levels = {}
    for node in root:
        if _local(node.tag) != "style":
            continue
        style_id = _attr(node, "styleId", "")
        outline = next((n for n in node.iter() if _local(n.tag) == "outlineLvl"), None)
        if outline is not None:
            try:
                level = int(_attr(outline, "val", "9")) + 1
            except ValueError:
                continue
            if 1 <= level <= 6:
                levels[style_id] = level
    return levels


_DIGEST_TERMS = {
    "purpose": ("purpose", "objective", "الغرض", "الهدف"),
    "scope": ("scope", "النطاق"),
    "recorded_approvals": ("approved", "approval", "authorised", "authorized", "اعتماد", "موافقة"),
    "roles_responsibilities": ("responsib", "role", "manager", "shall ensure", "مسؤول", "مدير", "دور"),
    "workflow_decisions": ("process", "procedure", "decision", "review", "approve", "خطوات", "إجراء", "قرار"),
    "requirements_deadlines": ("shall", "must", "within", "deadline", "يجب", "يتعين", "خلال", "موعد"),
    "required_records": ("record", "retain", "evidence", "form", "register", "سجل", "نموذج", "دليل"),
    "referenced_documents": ("reference", "refer to", "manual", "مرجع", "مراجع", "دليل"),
    "applicability": ("appl", "metro", "tram", "department", "نطاق", "مترو", "ترام", "إدارة"),
}


def _digest(clauses, filename):
    result = {}
    for field, terms in _DIGEST_TERMS.items():
        items = [{"text": c["text"], "locator": c["locator"], "clause_id": c["id"]}
                 for c in clauses if any(term in (c["section"] + " " + c["text"]).lower() for term in terms)]
        result[field] = {"status": "extracted_candidates" if items else "not_identified",
                         "review_required": True, "items": items}
    patterns = {
        "document_code": re.compile(r"\b[A-Z][A-Z0-9]{1,12}-\d{2,5}-[A-Z0-9-]+\b", re.I),
        "revision": re.compile(r"\b(?:rev(?:ision)?\s*[.:\-]?\s*\d{1,4}|Rev\d{1,4})\b", re.I),
        "dates": re.compile(r"\b(?:\d{1,2}[ /-](?:\d{1,2}|[A-Za-z]{3,9})[ /-]\d{4}|\d{1,2}[A-Za-z]{3}\d{4}|\d{4}-\d{2}-\d{2})\b"),
    }
    for field, pattern in patterns.items():
        items = [{"text": m.group(0), "locator": c["locator"], "clause_id": c["id"]}
                 for c in clauses for m in pattern.finditer(c["text"])]
        result[field] = {"status": "extracted_candidates" if items else "not_identified",
                         "review_required": True, "items": items}
    result["source_identifier"] = {"text": filename, "basis": "supplied_filename", "verified": False}
    result["current_applicability"] = {"status": "unverified", "decision": None,
                                      "basis": "supplied_reference_copy"}
    questions = [{"code": "current_applicability", "review_required": True},
                 {"code": "referenced_sources_not_automatically_available", "review_required": True}]
    name_dates = re.findall(r"(\d{1,2})([A-Za-z]{3})(\d{4})", filename)
    for c in clauses:
        in_history = "histor" in c["section"].lower() or "change" in c["section"].lower()
        for day, month, year in re.findall(r"(\d{1,2})[ -]?([A-Za-z]{3})[ -]?(\d{4})", c["text"]):
            for nd, nm, ny in name_dates:
                if day.lstrip("0") == nd.lstrip("0") and month.lower() == nm.lower() and year != ny:
                    questions.append({"code": "identifier_change_history_date_conflict" if in_history else "identifier_recorded_date_conflict",
                                      "source_identifier_date": nd + nm + ny,
                                      "recorded_date": day + month + year,
                                      "locator": c["locator"], "clause_id": c["id"],
                                      "context": "change_history" if in_history else "unclassified_source_date",
                                      "review_required": True})
    result["questions"] = questions
    result["practical_implications"] = {"status": "requires_analyst_review", "items": []}
    return result


def _artifact(name, data, content_type=None):
    return {"name": name, "content_type": content_type or mimetypes.guess_type(name)[0] or "application/octet-stream",
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "data": data}


def _document(data, filename):
    budget, artifacts = _Budget(), []
    with _open_package(data) as archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            raise _error("The package has no Word document part.")
        style_levels = _style_levels(archive, budget)
        parts = ["word/document.xml"] + sorted(name for name in names if
            re.fullmatch(r"word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml", name))
        paragraphs, tables, clauses, total_chars, drawings = [], [], [], 0, 0
        for part in parts:
            root = _tree(archive, part, budget)
            if part == "word/document.xml" and _local(root.tag) != "document":
                raise _error("The Word document part has an invalid root element.")
            headings, paragraph_index, table_index = [], 0, 0
            paragraph_by_node = {}
            for node in root.iter():
                local = _local(node.tag)
                if local in ("drawing", "pict", "object"):
                    drawings += 1
                if local != "p":
                    continue
                paragraph_index += 1
                text = _paragraph_text(node)
                total_chars += len(text)
                if total_chars > MAX_DOCUMENT_CHARS:
                    raise _error("The document exceeds the extracted-text limit.")
                properties = _first(node, "pPr")
                style_node = _first(properties, "pStyle") if properties is not None else None
                style = _attr(style_node, "val", "") if style_node is not None else ""
                outline = _first(properties, "outlineLvl") if properties is not None else None
                level = style_levels.get(style)
                match = re.fullmatch(r"heading\s*([1-6])", style, re.I)
                if match:
                    level = int(match.group(1))
                if outline is not None:
                    try:
                        own = int(_attr(outline, "val", "9")) + 1
                        level = own if 1 <= own <= 6 else level
                    except ValueError:
                        pass
                if level and text:
                    headings = [x for x in headings if x[0] < level] + [(level, text)]
                locator = part + "#p:" + str(paragraph_index)
                tracked = {"deleted_text_present": any(_local(n.tag) in ("del", "delText") for n in node.iter()),
                           "inserted_text_present": any(_local(n.tag) == "ins" for n in node.iter())}
                paragraph = {"source_part": part, "ordinal": paragraph_index, "locator": locator,
                             "text": text, "style": style, "heading_level": level,
                             "section": " / ".join(title for _, title in headings),
                             "tracked_changes": tracked}
                paragraphs.append(paragraph)
                paragraph_by_node[id(node)] = paragraph
                if text:
                    clauses.append({"id": hashlib.sha256((locator + "\0" + text).encode()).hexdigest()[:24],
                                    "text": text, "locator": locator, "section": paragraph["section"],
                                    "kind": "paragraph", "review_status": "unreviewed",
                                    "tracked_changes": tracked})
            for node in root.iter():
                if _local(node.tag) != "tbl":
                    continue
                table_index += 1
                locator = part + "#table:" + str(table_index)
                table = {"locator": locator, "source_part": part, "ordinal": table_index, "rows": []}
                for ri, row in enumerate(_children(node, "tr"), 1):
                    cells = []
                    for ci, cell in enumerate(_children(row, "tc"), 1):
                        properties = _first(cell, "tcPr")
                        span = _first(properties, "gridSpan") if properties is not None else None
                        merge = _first(properties, "vMerge") if properties is not None else None
                        paras = [paragraph_by_node[id(p)] for p in cell.iter()
                                 if id(p) in paragraph_by_node]
                        cloc = locator + "/row:" + str(ri) + "/cell:" + str(ci)
                        cells.append({"locator": cloc, "cell": ci,
                                      "text": "\n".join(p["text"] for p in paras if p["text"]),
                                      "column_span": _attr(span, "val", "1") if span is not None else "1",
                                      "vertical_merge": _attr(merge, "val", "continue") if merge is not None else None,
                                      "paragraph_locators": [p["locator"] for p in paras],
                                      "section": next((p["section"] for p in paras if p["section"]), "")})
                    row_locator = locator + "/row:" + str(ri)
                    table["rows"].append({"row": ri, "locator": row_locator, "cells": cells})
                    row_text = "\t".join(cell["text"] for cell in cells)
                    if row_text.strip():
                        clauses.append({"id": hashlib.sha256((row_locator + "\0" + row_text).encode()).hexdigest()[:24],
                                        "text": row_text, "locator": row_locator,
                                        "section": next((cell["section"] for cell in cells if cell["section"]), ""),
                                        "kind": "table_row", "review_status": "unreviewed",
                                        "source_cell_locators": [cell["locator"] for cell in cells]})
                tables.append(table)
        for name in sorted(names):
            if not name.endswith("/") and (name.startswith("word/media/") or name.startswith("word/embeddings/")):
                blob = _read_bytes(archive, name, budget)
                artifacts.append(_artifact(name, blob))
        media = [name for name in names if name.startswith("word/media/") and not name.endswith("/")]
        diagrams = [name for name in names if name.startswith("word/diagrams/") and not name.endswith("/")]
        embeddings = [name for name in names if name.startswith("word/embeddings/") and not name.endswith("/")]
        comments = [name for name in names if name.startswith("word/comments") and name.endswith(".xml")]
    warnings = [_warning("reference_authority_unverified", "This is a supplied reference copy; current applicability needs review.",
                         "هذه نسخة مرجعية مقدّمة؛ يلزم التحقق من سريانها الحالي."),
                _warning("digest_requires_review", "Digest fields are source-text candidates, not an approved interpretation.",
                         "حقول الملخص مقتطفات مرشحة من المصدر وليست تفسيرًا معتمدًا.")]
    visual_required = bool(media or diagrams or drawings or embeddings)
    if visual_required:
        warnings.append(_warning("visual_appendices_unverified", "Images, drawings or embedded content require visual review; text extraction does not verify them.",
                                 "تتطلب الصور والرسوم والمحتويات المضمّنة مراجعة بصرية؛ استخراج النص لا يثبت تغطيتها."))
    if comments:
        warnings.append(_warning("annotations_not_extracted", "Document comments were retained in the original but not interpreted.",
                                 "حُفظت تعليقات المستند في الأصل ولم تُفسّر."))
    document = {"paragraphs": paragraphs, "tables": tables, "clauses": clauses,
                "digest": _digest(clauses, filename)}
    return {"document": document, "warnings": warnings, "coverage": {
        "text_parts_extracted": parts, "paragraphs": len(paragraphs), "tables": len(tables),
        "characters": total_chars, "embedded_image_parts": len(media),
        "drawing_elements": drawings, "diagram_parts": len(diagrams),
        "embedded_objects": len(embeddings), "comments_interpreted": False,
        "visual_review": "required" if visual_required else "not_established_by_text_extraction",
        "image_ocr": "not_performed", "page_mapping": "not_inferred",
        "tracked_change_paragraphs": sum(any(p["tracked_changes"].values()) for p in paragraphs),
        "complete_document_review": False, "expanded_bytes_read": budget.used,
    }}, artifacts


def _converter_environment():
    # An Office parser does not need model, database, application or identity
    # credentials. Preserve runtime paths/proxy/CA policy, never repurpose HOME.
    allowed = {"PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP",
               "LD_LIBRARY_PATH", "XDG_RUNTIME_DIR", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
               "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy",
               "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE"}
    return {key: value for key, value in os.environ.items() if key in allowed}


def _command(argv, timeout):
    """A bounded process group, never a shell command or user-supplied path."""
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=(os.name == "posix"),
                                   env=_converter_environment())
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                pass
            process.communicate()
            raise _error("Document conversion exceeded its time limit.", "تجاوز تحويل المستند المهلة المحددة.")
    except OSError:
        raise _error("The configured document converter could not run.", "تعذّر تشغيل محوّل المستندات المحدد.", status=503)
    return process.returncode, out, err


def _convert_doc(data, converter=None):
    program = converter or shutil.which("soffice") or shutil.which("libreoffice")
    if not program:
        raise _error("Legacy .doc extraction requires an installed LibreOffice converter.",
                     "يتطلب استخراج ملفات ‎.doc‎ القديمة تثبيت محوّل LibreOffice.", status=503)
    code, version, _ = _command([str(program), "--version"], 10)
    if code or b"LibreOffice" not in version:
        raise _error("The document converter version could not be verified.", status=503)
    with tempfile.TemporaryDirectory(prefix="evidence-convert-") as temporary:
        base = Path(temporary)
        source = base / "source.doc"
        source.write_bytes(data)
        profile = base / "profile"
        user = profile / "user"
        user.mkdir(parents=True)
        # A new profile prevents shared state/lock reuse. Macros are disabled.
        (user / "registrymodifications.xcu").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
            '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>'
            '<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop>'
            '<prop oor:name="BlockUntrustedRefererLinks" oor:op="fuse"><value>true</value></prop>'
            '</item><item oor:path="/org.openoffice.Office.Writer/Content/Update">'
            '<prop oor:name="Link" oor:op="fuse"><value>0</value></prop>'
            '</item><item oor:path="/org.openoffice.Office.Calc/Content/Update">'
            '<prop oor:name="Link" oor:op="fuse"><value>0</value></prop>'
            '</item></oor:items>', encoding="utf-8")
        common = [str(program), "-env:UserInstallation=" + profile.as_uri(), "--headless",
                  "--invisible", "--nodefault", "--norestore", "--nofirststartwizard"]
        outputs = {}
        for extension, export_filter in (("docx", "Office Open XML Text"), ("pdf", "writer_pdf_Export")):
            destination = base / extension
            destination.mkdir()
            argv = common + ["--convert-to", extension + ":" + export_filter,
                             "--outdir", str(destination), str(source)]
            returncode, _, _ = _command(argv, CONVERSION_TIMEOUT)
            output = destination / ("source." + extension)
            if returncode or not output.is_file() or output.stat().st_size == 0:
                raise _error("LibreOffice did not produce the expected converted document.",
                             "لم يُنتج LibreOffice المستند المحوّل المتوقع.")
            if output.stat().st_size > MAX_EXPANDED_BYTES:
                raise _error("The converted document exceeds the extraction limit.")
            outputs[extension] = output.read_bytes()
    provenance = {
        "tool": "LibreOffice", "version": version.decode("utf-8", "replace").strip()[:240],
        "isolated_profile": True, "macros_disabled": True,
        "external_link_updates_disabled": True,
        "application_credentials_forwarded": False,
        "network_isolation": "not_guaranteed_by_process_wrapper",
        "timeout_seconds_per_conversion": CONVERSION_TIMEOUT,
        "docx_sha256": hashlib.sha256(outputs["docx"]).hexdigest(),
        "pdf_sha256": hashlib.sha256(outputs["pdf"]).hexdigest(),
    }
    return outputs, provenance


def ingest_source(filename: str, data: bytes, kind: str, *, converter: str | None = None) -> dict:
    """Extract an authorized upload without changing it or evaluating formulas.

    Return ``{'metadata': <JSON-safe>, 'artifacts': <private byte records>}``.
    Supplying ``converter`` is a trusted deployment/test option, not request data.
    """
    if not isinstance(filename, str) or not filename or len(filename) > 240 \
            or "/" in filename or "\\" in filename \
            or any(ord(c) < 32 or ord(c) == 127 for c in filename):
        raise _error("A safe source filename is required.", "يلزم اسم ملف مصدر آمن.")
    if kind not in ("procedure", "workbook"):
        raise _error("Choose procedure or workbook as the source kind.", "اختر إجراءً أو مصنّفًا كنوع للمصدر.")
    if not isinstance(data, bytes) or not data:
        raise _error("The source file is empty.", "ملف المصدر فارغ.")
    if len(data) > datasets.MAX_UPLOAD_BYTES:
        raise datasets.too_large()
    extension = posixpath.splitext(filename)[1].lower()
    metadata = {"source_name": filename, "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data), "kind": kind, "format": extension.lstrip("."),
                "extraction_version": EXTRACTION_VERSION,
                "source_authority": "supplied_reference_copy" if kind == "procedure" else "supplied_operational_extract",
                "current_applicability": "unverified" if kind == "procedure" else "not_applicable",
                "extraction": {"tool": "stdlib OOXML parser", "version": EXTRACTION_VERSION,
                               "python_version": platform.python_version(),
                               "xml_parser_version": expat.EXPAT_VERSION,
                               "original_preserved_by": "authorized_persistence_caller"}}
    artifacts = []
    try:
        if kind == "workbook":
            if extension not in (".xlsx", ".xlsm"):
                raise _error("Evidence workbooks must be supplied as .xlsx or .xlsm.",
                             "يجب تقديم مصنّفات الأدلة بصيغة ‎.xlsx‎ أو ‎.xlsm‎.", status=415)
            metadata.update(_workbook(data))
        else:
            if extension == ".doc":
                if not data.startswith(OLE_SIGNATURE):
                    raise _error("The .doc source is not a genuine binary Word document.",
                                 "المصدر ‎.doc‎ ليس مستند Word ثنائيًا أصليًا.")
                outputs, provenance = _convert_doc(data, converter)
                parsed, embedded = _document(outputs["docx"], filename)
                metadata["extraction"]["conversion"] = provenance
                artifacts.extend([_artifact("converted.docx", outputs["docx"]),
                                  _artifact("converted.pdf", outputs["pdf"], "application/pdf")])
                parsed["warnings"].append(_warning("converter_network_boundary",
                    "Conversion used an isolated profile; operating-system network isolation requires deployment controls.",
                    "استُخدم ملف تعريف معزول للتحويل؛ يتطلب عزل الشبكة على مستوى النظام ضوابط نشر مستقلة."))
            elif extension == ".docx":
                parsed, embedded = _document(data, filename)
            else:
                raise _error("Procedure sources must be genuine .doc or .docx documents.",
                             "يجب أن تكون مصادر الإجراءات مستندات أصلية بصيغة ‎.doc‎ أو ‎.docx‎.", status=415)
            metadata.update(parsed)
            artifacts.extend(embedded)
    except datasets.DatasetError:
        raise
    except (ValueError, OverflowError, IndexError, KeyError, zipfile.BadZipFile, OSError):
        raise _error("The source package could not be extracted safely.", "تعذّر استخراج حزمة المصدر بأمان.")
    metadata["artifacts"] = [{k: v for k, v in item.items() if k != "data"} for item in artifacts]
    return {"metadata": metadata, "artifacts": artifacts}
