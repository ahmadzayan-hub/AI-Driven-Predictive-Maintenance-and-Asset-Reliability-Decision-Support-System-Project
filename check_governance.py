#!/usr/bin/env python3
"""Re-verify the five data traps recorded in Memory.md.

    python -I tools/check_governance.py

Each check prints the evidence and a verdict. The traps are properties of
the supplied master, so every check should hold; a FAIL means the master
changed, or the trap was recorded wrongly, and Memory.md needs correcting
before any figure built on it is trusted.
"""

import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dataset import load, num, total

results = []


def check(name, passed, evidence):
    results.append(passed)
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    for line in evidence:
        print(f"        {line}")
    print()


def main():
    rows = load()
    corrective = [r for r in rows if r["Work_Order_Type"] == "Corrective"]

    # Trap 1 -------------------------------------------------------------
    by_asset = defaultdict(list)
    for r in rows:
        by_asset[r["Asset_ID"]].append(r)
    one_date = sum(1 for rs in by_asset.values()
                   if len({r["Record_Date"] for r in rs}) == 1)
    mixed = sum(1 for rs in by_asset.values()
                if len({r["Asset_Class"] for r in rs}) > 1)
    ages = [(min(num(r["Asset_Age_Years"]) for r in rs),
             max(num(r["Asset_Age_Years"]) for r in rs)) for rs in by_asset.values()]
    widest = max(hi - lo for lo, hi in ages)
    check("Trap 1: Asset_ID is a date bucket, not an asset identity",
          one_date == len(by_asset) and mixed == len(by_asset),
          [f"{len(by_asset)} distinct Asset_ID values",
           f"{one_date} of {len(by_asset)} map to exactly one Record_Date",
           f"{mixed} of {len(by_asset)} mix more than one Asset_Class",
           f"widest age span inside one Asset_ID: {widest:.1f} years",
           "=> no asset panel: no per-asset history and no per-asset MTBF trend"])

    # Trap 2 -------------------------------------------------------------
    placeholder = [r for r in rows if r["Work_Order_Type"] == "Preventive"]
    row_mean_ftf = statistics.fmean(num(r["First_Time_Fix_Rate"]) for r in rows)
    weighted_ftf = total(corrective, "First_Time_Fix_Count") / total(corrective, "Corrective_WO_Count")
    check("Trap 2: row-rate averages are not the KPI",
          abs(row_mean_ftf - weighted_ftf) > 0.05
          and all(num(r["First_Time_Fix_Rate"]) == 0 for r in placeholder),
          [f"{len(placeholder)} preventive records store placeholder rates (first-time fix 0)",
           f"row mean over all records {row_mean_ftf:.1%} vs weighted on corrective {weighted_ftf:.1%}",
           f"gap {abs(row_mean_ftf - weighted_ftf) * 100:.1f} points",
           "=> quote ratios of sums, and say which population a rate covers"])

    # Trap 3 -------------------------------------------------------------
    identity = sum(1 for r in rows if abs(
        num(r["Availability_Pct"])
        - (num(r["Planned_Operating_Hours"]) - num(r["Downtime_Hours"]))
        / num(r["Planned_Operating_Hours"])) < 0.005)
    col_mean = statistics.fmean(num(r["Availability_Pct"]) for r in rows)
    op_over_planned = total(rows, "Operating_Hours") / total(rows, "Planned_Operating_Hours")
    met = sum(1 for r in rows if num(r["SLA_Actual_Hours"]) <= num(r["SLA_Target_Hours"]))
    check("Trap 3: two different availabilities, and two different SLA measures",
          identity == len(rows) and abs(col_mean - op_over_planned) > 0.1,
          [f"Availability_Pct == (Planned - Downtime)/Planned in {identity} of {len(rows)} rows",
           f"its mean is {col_mean:.1%} (a 0-1 fraction despite the _Pct name)",
           f"sum(Operating)/sum(Planned) is {op_over_planned:.1%} -- a different measure",
           f"SLA_Compliance_Score mean {statistics.fmean(num(r['SLA_Compliance_Score']) for r in rows):.1%} "
           f"(capped ratio) vs {met / len(rows):.1%} of records that met their target"])

    # Trap 4 -------------------------------------------------------------
    pairs = Counter((r["Work_Order_Type"], num(r["Failure_Count"]) > 0) for r in rows)
    leaks = (pairs[("Corrective", False)] == 0 and pairs[("Preventive", True)] == 0)
    no_failure = sum(1 for r in rows if r["Failure_Mode"] == "No Failure")
    check("Trap 4: failure is perfectly determined by the work-order type",
          leaks,
          [f"corrective with a failure {pairs[('Corrective', True)]:,}, without {pairs[('Corrective', False)]}",
           f"preventive with a failure {pairs[('Preventive', True)]}, without {pairs[('Preventive', False)]:,}",
           f"Failure_Mode == 'No Failure' marks exactly {no_failure:,} records",
           "=> Work_Order_Type and Failure_Mode leak the target; model corrective records only"])

    # Trap 5 -------------------------------------------------------------
    per_year = defaultdict(list)
    for r in rows:
        per_year[r["Record_Date"][:4]].append(r)
    lines, per_record = [], []
    for y in sorted(per_year):
        rs = per_year[y]
        lpr = total(rs, "Production_Loss_USD") / len(rs)
        per_record.append(lpr)
        lines.append(f"{y}: {len(rs):>5,} records, loss ${total(rs, 'Production_Loss_USD'):>13,.0f}, "
                     f"per record ${lpr:>8,.0f}")
    spread = (max(per_record) - min(per_record)) / statistics.fmean(per_record)
    check("Trap 5: uneven periods -- totals fall, per-record figures are flat",
          len(per_year["2026"]) < len(per_year["2025"]) * 0.75 and spread < 0.10,
          lines + [f"per-record spread across years {spread:.1%}",
                   "=> compare per record, never raw totals by year"])

    # Extra: the cost columns are not an accounting identity ------------
    residual = [num(r["Maintenance_Cost_USD"]) - num(r["Spare_Parts_Cost_USD"])
                - num(r["Labor_Cost_USD"]) for r in rows]
    off = sum(1 for d in residual if abs(d) > 0.01)
    check("Extra: Maintenance_Cost is not Spare_Parts + Labor",
          off == len(rows),
          [f"{off} of {len(rows)} rows carry a residual",
           f"total residual ${sum(residual):,.0f}, median ${statistics.median(residual):,.0f} a row",
           "=> do not present the cost columns as an accounting identity"])

    print(f"{sum(results)} of {len(results)} checks pass.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
