"""Shared loading for the Team 3 master CSV.

The master is never written to. Every tool here opens it read-only and
derives its figures from scratch, so a number in the documents can always
be checked against the file rather than against another document.
"""

import csv
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
MASTER = WORKSPACE / "course" / "Group_9226_Team_3_Enterprise_Dataset.csv"


def load(path=None):
    """Every row of the master as dicts, with the byte-order mark stripped."""
    p = Path(path) if path else MASTER
    if not p.is_file():
        raise SystemExit(f"master CSV not found: {p}")
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(value):
    """The value as a float, or None when it is not a number."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def total(rows, column):
    """Sum of a column, treating non-numbers as zero."""
    return sum(num(r[column]) or 0 for r in rows)


def ratio(rows, numerator, denominator):
    """A KPI as a ratio of sums, never an average of row rates."""
    den = total(rows, denominator)
    return total(rows, numerator) / den if den else None
