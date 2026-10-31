"""Drift between two snapshots of a live source (owner slice R5, 31 October 2026).

When a live source brings a new snapshot, it is compared with the previous
one before the analysis is read. Four plain rules, each with a stated
threshold, so a reader can recompute any alert:

1. Columns added or removed.
2. Row count changed by half or more (down) or doubled (up).
3. A numeric column's median moved by at least half of its previous
   interquartile spread (any move at all when that spread was zero).
4. A column's share of empty cells rose or fell by 10 percentage points or more.

A column is numeric when at least 90% of its filled cells read as numbers in
both snapshots. Nothing is changed or blocked: the alert is stated with the
snapshot, and the analysis runs as before.
"""
import statistics

from server.analytics import _to_number

ROWS_DOWN = 0.5        # new rows / old rows at or below this
ROWS_UP = 2.0          # new rows / old rows at or above this
MEDIAN_SHIFT = 0.5     # median move / previous interquartile spread
MISSING_POINTS = 0.10  # change in the share of empty cells
NUMERIC_SHARE = 0.9
MAX_LISTED = 5


def _numbers(rows, column):
    filled = [str(r.get(column) or "").strip() for r in rows]
    filled = [v for v in filled if v]
    numbers = [n for n in (_to_number(v) for v in filled) if n is not None]
    return numbers if filled and len(numbers) >= NUMERIC_SHARE * len(filled) else None


def _empty_share(rows, column):
    if not rows:
        return 0.0
    return sum(1 for r in rows if not str(r.get(column) or "").strip()) / len(rows)


def _quartiles(values):
    if len(values) < 4:
        return None
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q1, q3


def compare(old_columns, old_rows, new_columns, new_rows):
    """Findings, each a dict with a `kind` and its figures. Empty when stable."""
    findings = []
    added = [c for c in new_columns if c not in old_columns]
    removed = [c for c in old_columns if c not in new_columns]
    if added or removed:
        findings.append({"kind": "columns", "added": added, "removed": removed})
    if old_rows:
        ratio = len(new_rows) / len(old_rows)
        if ratio <= ROWS_DOWN or ratio >= ROWS_UP:
            findings.append({"kind": "rows", "old": len(old_rows), "new": len(new_rows)})
    shared = [c for c in new_columns if c in old_columns]
    for column in shared:
        before, after = _numbers(old_rows, column), _numbers(new_rows, column)
        if before and after:
            quartiles = _quartiles(before)
            if quartiles:
                spread = quartiles[1] - quartiles[0]
                old_median, new_median = statistics.median(before), statistics.median(after)
                moved = abs(new_median - old_median)
                if (spread > 0 and moved >= MEDIAN_SHIFT * spread) or (spread == 0 and moved > 0):
                    findings.append({"kind": "median", "column": column,
                                     "old": round(old_median, 4), "new": round(new_median, 4),
                                     "spread": round(spread, 4)})
        old_empty, new_empty = _empty_share(old_rows, column), _empty_share(new_rows, column)
        if abs(new_empty - old_empty) >= MISSING_POINTS:
            findings.append({"kind": "missing", "column": column,
                             "old": round(old_empty, 4), "new": round(new_empty, 4)})
    return findings


def _g(value):
    return f"{value:,.4g}" if abs(value) < 1e4 else f"{value:,.0f}"


def describe(findings, language="en"):
    """One note for the connector, in its language. None when stable."""
    if not findings:
        return None
    arabic = language == "ar"
    parts = []
    for f in findings[:MAX_LISTED]:
        kind = f["kind"]
        if kind == "columns":
            if arabic:
                bits = ([f"أُضيفت {', '.join(f['added'])}"] if f["added"] else []) + \
                       ([f"حُذفت {', '.join(f['removed'])}"] if f["removed"] else [])
                parts.append("الأعمدة: " + "، ".join(bits))
            else:
                bits = ([f"added {', '.join(f['added'])}"] if f["added"] else []) + \
                       ([f"removed {', '.join(f['removed'])}"] if f["removed"] else [])
                parts.append("columns " + "; ".join(bits))
        elif kind == "rows":
            parts.append(f"عدد الصفوف من {f['old']:,} إلى {f['new']:,}" if arabic else
                         f"rows from {f['old']:,} to {f['new']:,}")
        elif kind == "median":
            parts.append(f"الوسيط في {f['column']} من {_g(f['old'])} إلى {_g(f['new'])}" if arabic
                         else f"{f['column']} median from {_g(f['old'])} to {_g(f['new'])}")
        else:
            parts.append(f"الخلايا الفارغة في {f['column']} من {f['old']:.0%} إلى {f['new']:.0%}"
                         if arabic else
                         f"{f['column']} empty cells from {f['old']:.0%} to {f['new']:.0%}")
    more = len(findings) - MAX_LISTED
    if arabic:
        return ("تغيّرت اللقطة الجديدة عن السابقة بشكل ملحوظ: " + "؛ ".join(parts)
                + (f"؛ و{more} تغيّرات أخرى" if more > 0 else "")
                + ". حُلّلت كالمعتاد؛ راجع المصدر قبل اعتماد النتائج.")
    return ("The new snapshot differs materially from the previous one: " + "; ".join(parts)
            + (f"; and {more} more" if more > 0 else "")
            + ". It was analysed as usual; check the source before approving the results.")
