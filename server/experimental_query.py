"""Read-only, opt-in queries over the experimental CSV index, not a public API.

The trusted backend caller must authorize the database path. This module provides
no tenant authentication and does not change legacy ingestion or paging. Records
remain JSON arrays: even a projection decodes a complete, byte-bounded row. Memory
is bounded by metadata, one decoded row, and (for paging) the projected result;
SQLite native allocations and OS caching are not measured by Python heap tests.

Budgets count UTF-8 bytes stored in SQLite; page output uses compact, ASCII-escaped
JSON bytes. Summary scanning has explicit row/byte limits, not an unlimited-data
claim. Decimal arithmetic uses bounded integer coefficients, never float or the
ambient Decimal context. Numeric syntax is ASCII [+-]?(digits[.digits]?|.digits),
with surrounding whitespace ignored. Exponents, currency, grouping, NaN and
infinity are invalid. Syntactically valid numbers exceeding the bounds fail the
whole request. Results use canonical plain decimal strings (including "0").
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3

from server.experimental_ingest import LargeIntakeError

MAX_SELECTED_COLUMNS = 32
MAX_INDEX_COLUMNS = 100_000
MAX_PAGE_SIZE = 1_000
MAX_CURSOR = (1 << 63) - 1
DEFAULT_METADATA_BYTES = 1_048_576
HARD_METADATA_BYTES = 4_194_304
DEFAULT_RECORD_BYTES = 4_194_304
HARD_RECORD_BYTES = 16_777_216
DEFAULT_SELECTION_BYTES = 65_536
HARD_SELECTION_BYTES = 262_144
DEFAULT_OUTPUT_BYTES = 8_388_608
HARD_OUTPUT_BYTES = 33_554_432
DEFAULT_PAGE_SCAN_BYTES = 67_108_864
HARD_PAGE_SCAN_BYTES = 536_870_912
DEFAULT_SCAN_ROWS = 10_000_000
HARD_SCAN_ROWS = 100_000_000
DEFAULT_SCAN_BYTES = 2_000_000_000
HARD_SCAN_BYTES = 4_000_000_000
MAX_NUMERIC_TOKEN_CHARS = 1_024
MAX_NUMERIC_DIGITS = 1_000
MAX_NUMERIC_SCALE = 500
# At most 1,000 coefficient digits + 500 scale-alignment digits + 8 carry
# digits for 100,000,000 rows: bounded below Python's default int-string limit.
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")


def _integer(value, name, maximum, minimum=1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise LargeIntakeError(f"Invalid {name}")
    return value


def _selection(columns, max_selection_bytes):
    _integer(max_selection_bytes, "selection byte budget", HARD_SELECTION_BYTES)
    if not isinstance(columns, (list, tuple)) or not 1 <= len(columns) <= MAX_SELECTED_COLUMNS:
        raise LargeIntakeError("Select 1 to 32 unique named columns")
    remaining = max_selection_bytes
    seen = set()
    for name in columns:
        if not isinstance(name, str) or not name or len(name) > remaining:
            raise LargeIntakeError("Invalid column selection or selection byte budget")
        try:
            remaining -= len(name.encode("utf-8"))
        except UnicodeError:
            raise LargeIntakeError("Invalid column selection") from None
        if remaining < 0 or name in seen:
            raise LargeIntakeError("Invalid column selection or selection byte budget")
        seen.add(name)
    return list(columns)


@contextmanager
def _snapshot(database):
    db = None
    try:
        # as_uri escapes '?' and '#' in filenames. Callers cannot inject URI
        # modes, and mode=ro cannot create a missing database.
        uri = Path(database).resolve(strict=True).as_uri() + "?mode=ro"
        db = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=1.0)
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        yield db
    except LargeIntakeError:
        raise
    except (sqlite3.Error, OSError, ValueError, TypeError, UnicodeError, RecursionError):
        # No SQL exception, filename, header or raw cell is included in errors.
        raise LargeIntakeError("Invalid or unreadable experimental index") from None
    finally:
        if db is not None:
            db.close()  # Also ends the read transaction on every exit path.


def _columns(db, selected, max_metadata_bytes):
    tables = dict(db.execute(
        "SELECT name,type FROM main.sqlite_schema WHERE name IN ('wide_meta','wide_records')"
    ))
    if tables != {"wide_meta": "table", "wide_records": "table"}:
        raise LargeIntakeError("Invalid index schema")
    expected = {
        "wide_meta": [("name", "TEXT", 0, 1), ("value", "TEXT", 1, 0)],
        "wide_records": [("ordinal", "INTEGER", 0, 1), ("payload", "TEXT", 1, 0)],
    }
    for table, shape in expected.items():
        actual = [(r[1], r[2].upper(), r[3], r[5])
                  for r in db.execute(f"PRAGMA main.table_info({table})")]
        if actual != shape:
            raise LargeIntakeError("Invalid index schema")
    info = db.execute(
        "SELECT typeof(value),length(CAST(value AS BLOB)) "
        "FROM main.wide_meta WHERE name='columns'"
    ).fetchone()
    if info is None or info[0] != "text" or not 0 < info[1] <= max_metadata_bytes:
        raise LargeIntakeError("Invalid metadata or metadata byte budget exceeded")
    raw = db.execute("SELECT value FROM main.wide_meta WHERE name='columns'").fetchone()[0]
    try:
        columns = json.loads(raw)
    except (ValueError, RecursionError):
        raise LargeIntakeError("Invalid index metadata JSON") from None
    if (not isinstance(columns, list) or not 1 <= len(columns) <= MAX_INDEX_COLUMNS
            or not all(isinstance(c, str) and c for c in columns)
            or len(set(columns)) != len(columns)):
        raise LargeIntakeError("Invalid index columns")
    positions = {name: n for n, name in enumerate(columns)}
    if any(name not in positions for name in selected):
        raise LargeIntakeError("Unknown selected column")
    first = db.execute("SELECT ordinal FROM main.wide_records ORDER BY ordinal LIMIT 1").fetchone()
    if first is not None and (type(first[0]) is not int or first[0] <= 0):
        raise LargeIntakeError("Invalid record ordinal")
    return len(columns), [positions[name] for name in selected]


def _decode_row(payload, width):
    try:
        values = json.loads(payload)
    except (ValueError, TypeError, RecursionError):
        raise LargeIntakeError("Invalid record JSON") from None
    if (not isinstance(values, list) or len(values) != width
            or not all(isinstance(value, str) for value in values)):
        raise LargeIntakeError("Invalid record width or cell type")
    return values


def _records(db, *, width, after, limit, max_record_bytes, max_scan_bytes,
             require_complete=False):
    # Probe only sizes/ordinals first. Neither an oversized payload nor the
    # row-limit sentinel crosses into Python. The point lookup uses the same
    # snapshot, so the checked size cannot change between these two reads.
    # BLOB length counts UTF-8 and embedded NUL bytes correctly.
    cursor = db.execute(
        "SELECT ordinal,typeof(payload),length(CAST(payload AS BLOB)) "
        "FROM main.wide_records WHERE ordinal>? ORDER BY ordinal LIMIT ?",
        (after, limit + int(require_complete)),
    )
    scanned_bytes = 0
    scanned_rows = 0
    previous = after
    try:
        while True:
            entry = cursor.fetchone()
            if entry is None:
                break
            if scanned_rows >= limit:
                raise LargeIntakeError("Scan row budget exceeded")
            ordinal, kind, byte_count = entry
            if type(ordinal) is not int or ordinal <= previous:
                raise LargeIntakeError("Invalid record ordinal")
            if kind != "text" or not 0 < byte_count <= max_record_bytes:
                raise LargeIntakeError("Invalid record or record byte budget exceeded")
            scanned_bytes += byte_count
            if scanned_bytes > max_scan_bytes:
                raise LargeIntakeError("Scan byte budget exceeded")
            payload_cursor = db.execute(
                "SELECT payload FROM main.wide_records WHERE ordinal=?", (ordinal,))
            try:
                payload = payload_cursor.fetchone()[0]
            finally:
                payload_cursor.close()
            values = _decode_row(payload, width)
            yield ordinal, values
            previous = ordinal
            scanned_rows += 1
            del values, entry, payload
    finally:
        cursor.close()


def _json_size(value):
    return len(json.dumps(value, ensure_ascii=True, separators=(",", ":")))


def page(database, *, columns, after=0, size=100,
         max_metadata_bytes=DEFAULT_METADATA_BYTES,
         max_record_bytes=DEFAULT_RECORD_BYTES,
         max_selection_bytes=DEFAULT_SELECTION_BYTES,
         max_output_bytes=DEFAULT_OUTPUT_BYTES,
         max_scan_bytes=DEFAULT_PAGE_SCAN_BYTES):
    """Project selected columns in caller order; keep original ordinal cursors.

    Return the legacy shape {columns, rows: [{ordinal, values}], next}. `next` is
    the last returned ordinal, or None on an empty page; it does not promise a
    subsequent row. Output budget counts compact ensure_ascii=True JSON bytes.
    """
    selected = _selection(columns, max_selection_bytes)
    _integer(after, "cursor", MAX_CURSOR, minimum=0)
    _integer(size, "page size", MAX_PAGE_SIZE)
    _integer(max_metadata_bytes, "metadata byte budget", HARD_METADATA_BYTES)
    _integer(max_record_bytes, "record byte budget", HARD_RECORD_BYTES)
    _integer(max_output_bytes, "output byte budget", HARD_OUTPUT_BYTES)
    _integer(max_scan_bytes, "scan byte budget", HARD_PAGE_SCAN_BYTES)
    result = {"columns": selected, "rows": [], "next": None}
    base_bytes = _json_size(result)
    if base_bytes > max_output_bytes:
        raise LargeIntakeError("Page output byte budget exceeded")
    rows_bytes = 0
    with _snapshot(database) as db:
        width, positions = _columns(db, selected, max_metadata_bytes)
        records = _records(db, width=width, after=after, limit=size,
                           max_record_bytes=max_record_bytes, max_scan_bytes=max_scan_bytes)
        try:
            for ordinal, values in records:
                record = {"ordinal": ordinal, "values": [values[p] for p in positions]}
                rows_bytes += _json_size(record) + bool(result["rows"])
                if base_bytes + rows_bytes + len(str(ordinal)) - len("null") > max_output_bytes:
                    raise LargeIntakeError("Page output byte budget exceeded")
                result["rows"].append(record)
                result["next"] = ordinal
                del values
        finally:
            records.close()
    return result


def _number(token):
    token = token.strip()
    if not token:
        return "blank", None
    if _DECIMAL.fullmatch(token) is None:
        return "invalid", None
    if len(token) > MAX_NUMERIC_TOKEN_CHARS:
        raise LargeIntakeError("Numeric token budget exceeded")
    negative = token.startswith("-")
    unsigned = token.lstrip("+-")
    whole, _, fraction = unsigned.partition(".")
    digits = whole + fraction
    if len(digits) > MAX_NUMERIC_DIGITS or len(fraction) > MAX_NUMERIC_SCALE:
        raise LargeIntakeError("Numeric digit or scale budget exceeded")
    coefficient = int(digits)
    return "numeric", (-coefficient if negative else coefficient, len(fraction))


def _decimal_string(coefficient, scale):
    if coefficient == 0:
        return "0"
    digits = str(abs(coefficient))
    if scale:
        digits = digits.zfill(scale + 1)
        digits = (digits[:-scale] + "." + digits[-scale:]).rstrip("0").rstrip(".")
    return ("-" if coefficient < 0 else "") + digits


@dataclass
class _Summary:
    numeric: int = 0
    blank: int = 0
    invalid: int = 0
    scale: int = 0
    total: int = 0
    minimum: int | None = None
    maximum: int | None = None

    def add(self, value):
        kind, number = _number(value)
        if kind != "numeric":
            setattr(self, kind, getattr(self, kind) + 1)
            return
        coefficient, scale = number
        if scale > self.scale:
            factor = 10 ** (scale - self.scale)
            self.total *= factor
            if self.minimum is not None:
                self.minimum *= factor
                self.maximum *= factor
            self.scale = scale
        else:
            coefficient *= 10 ** (self.scale - scale)
        self.total += coefficient
        self.minimum = coefficient if self.minimum is None else min(self.minimum, coefficient)
        self.maximum = coefficient if self.maximum is None else max(self.maximum, coefficient)
        self.numeric += 1

    def result(self):
        return {"numeric": self.numeric, "blank": self.blank, "invalid": self.invalid,
                "sum": _decimal_string(self.total, self.scale) if self.numeric else None,
                "min": _decimal_string(self.minimum, self.scale) if self.numeric else None,
                "max": _decimal_string(self.maximum, self.scale) if self.numeric else None}


def summarize(database, *, columns, max_metadata_bytes=DEFAULT_METADATA_BYTES,
              max_record_bytes=DEFAULT_RECORD_BYTES,
              max_selection_bytes=DEFAULT_SELECTION_BYTES,
              max_scan_rows=DEFAULT_SCAN_ROWS, max_scan_bytes=DEFAULT_SCAN_BYTES):
    """Scan the complete snapshot or raise; never return a partial summary.

    Return {rows_scanned, columns: {name: {numeric, blank, invalid, sum, min, max}}}.
    All three counts are explicit. Without any numeric cells, sum/min/max are
    None, not zero. Only the requested columns are summarized.
    """
    selected = _selection(columns, max_selection_bytes)
    _integer(max_metadata_bytes, "metadata byte budget", HARD_METADATA_BYTES)
    _integer(max_record_bytes, "record byte budget", HARD_RECORD_BYTES)
    _integer(max_scan_rows, "scan row budget", HARD_SCAN_ROWS)
    _integer(max_scan_bytes, "scan byte budget", HARD_SCAN_BYTES)
    summaries = [_Summary() for _ in selected]
    rows_scanned = 0
    with _snapshot(database) as db:
        width, positions = _columns(db, selected, max_metadata_bytes)
        records = _records(db, width=width, after=0, limit=max_scan_rows,
                           max_record_bytes=max_record_bytes, max_scan_bytes=max_scan_bytes,
                           require_complete=True)
        try:
            for _, values in records:
                for summary, position in zip(summaries, positions):
                    summary.add(values[position])
                rows_scanned += 1
                del values
        finally:
            records.close()
    return {"rows_scanned": rows_scanned,
            "columns": {name: summary.result() for name, summary in zip(selected, summaries)}}
