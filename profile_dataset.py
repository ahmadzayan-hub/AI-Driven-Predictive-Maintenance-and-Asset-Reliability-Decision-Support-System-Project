#!/usr/bin/env python3
"""Profile the master CSV: shape, coverage, dimensions and the headline totals.

    python -I tools/profile_dataset.py

Run this before quoting any figure. The four headline totals it prints are
the ones the report, the deck and the dashboard must all agree on.
"""

import sys
from collections import Counter
from pathlib import Path

# `python -I` keeps the script's own directory off sys.path, so add it back
# explicitly rather than dropping the isolation flag.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dataset import load, num, total, ratio

HEADLINE = ["Failure_Count", "Downtime_Hours", "Maintenance_Cost_USD", "Production_Loss_USD"]
OTHER_TOTALS = ["Operating_Hours", "Planned_Operating_Hours", "Preventive_WO_Count",
                "Corrective_WO_Count", "Completed_WO_Count", "Overdue_WO_Count",
                "First_Time_Fix_Count", "Repeat_Repair_Count", "Inventory_Stockout_Count",
                "Safety_Incident_Count", "Spare_Parts_Cost_USD", "Labor_Cost_USD"]


def main():
    rows = load()
    cols = list(rows[0].keys())

    print(f"Shape            {len(rows):,} rows x {len(cols)} columns")
    blank = {c: sum(1 for r in rows if not r[c].strip()) for c in cols}
    blank = {c: n for c, n in blank.items() if n}
    print(f"Blank cells      {blank or 'none'}")
    print(f"Record_ID        {len(set(r['Record_ID'] for r in rows)):,} distinct "
          f"({'unique' if len(set(r['Record_ID'] for r in rows)) == len(rows) else 'NOT UNIQUE'})")

    dates = sorted(r["Record_Date"] for r in rows)
    print(f"Coverage         {dates[0]} to {dates[-1]}")
    years = Counter(r["Record_Date"][:4] for r in rows)
    print("Records by year  " + ", ".join(f"{y}: {n:,}" for y, n in sorted(years.items())))
    print(f"                 (uneven: compare per record, never raw totals by year)")

    print("\nDimensions")
    for c in cols:
        values = Counter(r[c] for r in rows)
        if 2 <= len(values) <= 26 and not c.endswith(("_Count", "_Hours", "_USD")):
            top = ", ".join(f"{k} {v:,}" for k, v in values.most_common(6))
            more = f", +{len(values) - 6} more" if len(values) > 6 else ""
            print(f"  {c:24s} {len(values):>3} | {top}{more}")

    print("\nThe four headline totals (must agree in report, deck and dashboard)")
    for c in HEADLINE:
        print(f"  {c:28s} {total(rows, c):>18,.1f}")

    print("\nOther totals")
    for c in OTHER_TOTALS:
        print(f"  {c:28s} {total(rows, c):>18,.1f}")

    print("\nWeighted KPIs (ratios of sums)")
    corrective = [r for r in rows if r["Work_Order_Type"] == "Corrective"]
    pm = total(rows, "Preventive_WO_Count") / (total(rows, "Preventive_WO_Count")
                                               + total(rows, "Corrective_WO_Count"))
    print(f"  Preventive ratio             {pm:>8.2%}")
    print(f"  First-time fix (corrective)  {ratio(corrective, 'First_Time_Fix_Count', 'Corrective_WO_Count'):>8.2%}")
    print(f"  Repeat repair (corrective)   {ratio(corrective, 'Repeat_Repair_Count', 'Corrective_WO_Count'):>8.2%}")
    met = sum(1 for r in rows if num(r["SLA_Actual_Hours"]) <= num(r["SLA_Target_Hours"]))
    print(f"  SLA target met               {met / len(rows):>8.2%}  ({met:,} of {len(rows):,} records)")
    print(f"  Loss per downtime hour       {total(rows, 'Production_Loss_USD') / total(rows, 'Downtime_Hours'):>8,.0f} USD")
    print(f"  Cost per operating hour      {total(rows, 'Maintenance_Cost_USD') / total(rows, 'Operating_Hours'):>8,.2f} USD")


if __name__ == "__main__":
    main()
