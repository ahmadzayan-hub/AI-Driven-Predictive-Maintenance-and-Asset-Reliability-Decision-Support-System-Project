"""The period a set of records covers, read from the run's own date column.

Only the column the pipeline marked as the date role is used, and only values
that read as ISO dates (YYYY-MM or YYYY-MM-DD). Nothing is inferred from other
columns: with no date role, or no readable value, the period is None and the
interface says so.
"""

from __future__ import annotations

import re

_ISO = re.compile(r"^(\d{4})-(\d{2})(?:-(\d{2}))?")


def period_of(table, rows) -> dict | None:
    """{"column", "from", "to", "dated"}: the earliest and latest date in `rows`."""
    column = next((c for c, role in (table.roles or {}).items() if role == "date"), None)
    if column is None or column not in table.columns:
        return None
    at = table.columns.index(column)
    seen = []
    for row in rows:
        value = row[at] if at < len(row) else None
        match = _ISO.match(str(value).strip()) if value not in (None, "") else None
        if match:
            seen.append(match.group(0))
    if not seen:
        return None
    return {"column": column, "from": min(seen), "to": max(seen), "dated": len(seen)}
