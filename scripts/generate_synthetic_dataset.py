#!/usr/bin/env python3
"""Generate a synthetic fleet-maintenance dataset for testing the database and the pipeline.

Every value is invented by a seeded random generator. Nothing here is, or
resembles, an operator's data. The same seed always gives the same file, so a
test can check a total by hand.

    python scripts/generate_synthetic_dataset.py --rows 5000 --out fleet.csv
    python scripts/generate_synthetic_dataset.py --rows 2000 --defects --out messy.csv

The file name starts with SYNTHETIC so it is never mistaken for real data.
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import sys
from pathlib import Path

MAX_ROWS = 50_000  # the pipeline's own limit (server.analytics.MAX_ROWS)
COLUMNS = ["Record_ID", "Asset_ID", "Asset_Class", "Period", "Maintenance_Cost_USD",
           "Operating_Hours", "Planned_Operating_Hours", "Downtime_Hours", "Failure_Count"]
# class: (assets, failure rate per month, mean repair cost, planned hours per month)
CLASSES = {"Pumps": (14, 0.55, 2_400, 600), "Doors": (30, 0.35, 900, 540),
           "Signals": (22, 0.20, 3_100, 720), "Track": (18, 0.12, 5_200, 720),
           "Power": (10, 0.28, 4_000, 720)}
FIRST_YEAR, MONTHS = 2025, 24


def generate(rows: int = 5_000, seed: int = 2026, defects: bool = False) -> list[list]:
    """Return `rows` records, one per asset and month, oldest month first."""
    if not 1 <= rows <= MAX_ROWS:
        raise ValueError(f"rows must be between 1 and {MAX_ROWS}")
    rng = random.Random(seed)
    assets = [(f"{name[:3].upper()}-{n + 1:03d}", name, spec) for name, spec in CLASSES.items()
              for n in range(spec[0])]
    # A weak asset fails more often: a few per class, so the data has a story to find.
    weak = {asset_id for asset_id, _, _ in assets if rng.random() < 0.12}
    out: list[list] = []
    for month in range(MONTHS):
        year, m = FIRST_YEAR + month // 12, month % 12 + 1
        for asset_id, name, (_, rate, repair, planned) in assets:
            if len(out) >= rows:
                break
            lam = rate * (3 if asset_id in weak else 1) * (1 + 0.25 * (month / MONTHS))
            failures = sum(rng.random() < lam / 4 for _ in range(4))
            downtime = round(sum(rng.uniform(1.5, 14) for _ in range(failures)), 1)
            planned_hours = planned * rng.choice([1, 1, 1, 0.95])
            operating = round(max(0.0, planned_hours - downtime - rng.uniform(0, 12)), 1)
            cost = round(40 + failures * rng.gauss(repair, repair * 0.25) + rng.uniform(0, 160), 2)
            out.append([f"SYN-{len(out) + 1:06d}", asset_id, name, f"{year}-{m:02d}-01", max(cost, 0),
                        operating, round(planned_hours, 1), downtime, failures])
    if len(out) < rows:  # more rows than 24 months of the fleet: repeat the months with new draws
        month = 0
        while len(out) < rows:
            year, m = FIRST_YEAR + (MONTHS + month) // 12, (MONTHS + month) % 12 + 1
            for asset_id, name, (_, rate, repair, planned) in assets:
                if len(out) >= rows:
                    break
                failures = int(rng.random() < rate * (3 if asset_id in weak else 1))
                downtime = round(failures * rng.uniform(1.5, 14), 1)
                out.append([f"SYN-{len(out) + 1:06d}", asset_id, name, f"{year}-{m:02d}-01",
                            round(40 + failures * repair * rng.uniform(0.6, 1.4), 2),
                            round(max(0.0, planned - downtime - rng.uniform(0, 12)), 1), planned,
                            downtime, failures])
            month += 1
    if defects:  # the dirt a real export carries: blanks, a duplicate, a text cell, a negative
        for i in rng.sample(range(len(out)), max(1, rows // 100)):
            out[i][4] = ""
        for i in rng.sample(range(len(out)), max(1, rows // 200)):
            out[i][5] = "n/a"
        out[len(out) // 2][8] = -1
        out[-1] = list(out[0])
    return out


def to_csv(records: list[list]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(records)
    return buffer.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rows", type=int, default=5_000, help=f"1 to {MAX_ROWS} (default 5000)")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--defects", action="store_true", help="add blanks, text cells, a negative and a duplicate row")
    parser.add_argument("--out", type=Path, default=Path("SYNTHETIC_fleet.csv"))
    args = parser.parse_args(argv)
    try:
        records = generate(args.rows, args.seed, args.defects)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    args.out.write_text(to_csv(records), encoding="utf-8")
    print(f"wrote {len(records)} synthetic records to {args.out} (seed {args.seed}"
          f"{', with defects' if args.defects else ''})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
