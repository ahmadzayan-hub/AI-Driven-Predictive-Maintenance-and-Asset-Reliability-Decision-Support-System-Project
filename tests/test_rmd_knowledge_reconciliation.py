"""Reconcile the figures in the Analytics knowledge pack to its source workbook.

Two layers, kept apart on purpose:

* `WorkbookReconciliation` needs the original synthetic workbook (SRC-29). It
  is skipped unless the file is present AND its SHA-256 equals the manifest
  value, so a different version can never be passed off as the documented one.
  Point `RMD_ANALYTICS_WORKBOOK` at it, or leave it under `private/`.
* `EngineDefinitions` always runs on a tiny invented table. It proves the
  repository's KPI engine uses the definitions the pack states (ratio of sums,
  not average of rates), independent of any real file.

All data here is synthetic and educational. A match shows the pack quotes what
the workbook computes; it does not make the figures operational RMD values.
"""
import hashlib
import os
import unittest
from collections import Counter
from pathlib import Path

from server import datasets
from server.maintenance import kpis

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "knowledge" / "rmd-v2-analytics-9226"
SRC_29_SHA256 = "08b9625b0b1e6d158ad58ab87a449e23e47a4a327e331bdce3385f0b0a2f252d"


def find_workbook():
    candidates = [os.environ.get("RMD_ANALYTICS_WORKBOOK", "")]
    candidates += [str(p) for p in (ROOT / "private").glob("**/*Analytics_Workbook*.xlsx")]
    for candidate in candidates:
        path = Path(candidate) if candidate else None
        if path and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == SRC_29_SHA256:
            return path
    return None


def pack_text():
    return "\n".join(p.read_text(encoding="utf-8") for p in PACK.glob("*.md"))


@unittest.skipUnless(find_workbook(), "SRC-29 workbook with the documented SHA-256 is not available")
class WorkbookReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        table = datasets.read(find_workbook().read_bytes(), "workbook.xlsx", sheet="Dataset")
        cls.columns = [c.lstrip("﻿") for c in table.columns]
        cls.rows = [dict(zip(cls.columns, row)) for row in table.rows]
        cls.text = pack_text()

    def num(self, key):
        return [float(r[key]) for r in self.rows]

    def total(self, key):
        return sum(self.num(key))

    def mean(self, key):
        return self.total(key) / len(self.rows)

    def stated(self, figure):
        self.assertIn(figure, self.text, f"{figure} is not stated in the pack")

    def test_shape_matches_the_documented_dataset(self):
        self.assertEqual(len(self.rows), 5000)
        self.assertEqual(len(self.columns), 60)

    def test_sla_two_definitions(self):
        met = sum(a <= t for a, t in zip(self.num("SLA_Actual_Hours"), self.num("SLA_Target_Hours")))
        self.assertEqual(met, 2306)
        self.assertAlmostEqual(met / 5000 * 100, 46.12, places=2)
        self.assertAlmostEqual(self.mean("SLA_Compliance_Score"), 0.75782986, places=8)
        self.stated("46.12")

    def test_availability_row_mean_versus_aggregate(self):
        self.assertAlmostEqual(self.mean("Availability_Pct") * 100, 96.779802, places=6)
        aggregate = 100 * (1 - self.total("Downtime_Hours") / self.total("Planned_Operating_Hours"))
        self.assertAlmostEqual(aggregate, 96.962530, places=6)
        self.stated("96.779802")
        self.stated("96.962530")

    def test_mtbf_and_mttr_two_definitions(self):
        failures = self.total("Failure_Count")
        self.assertAlmostEqual(self.mean("MTBF_Hours"), 342.541096, places=5)
        self.assertAlmostEqual(self.total("Operating_Hours") / failures, 313.320570, places=5)
        self.assertAlmostEqual(self.mean("MTTR_Hours"), 11.708741, places=5)
        self.assertAlmostEqual(self.total("Downtime_Hours") / failures, 11.988112, places=5)
        for figure in ("342.541096", "313.320570", "11.708741", "11.988112"):
            self.stated(figure)

    def test_rows_are_not_assets(self):
        high = [r for r in self.rows if r["Risk_Category"] == "High"]
        self.assertEqual(len(high), 289)
        self.assertEqual(sum(float(r["Overdue_WO_Count"]) > 0 for r in self.rows), 3950)
        self.assertEqual(self.total("Overdue_WO_Count"), 5940)
        self.assertLess(len({r["Asset_ID"] for r in high}), 289 + 1)
        self.stated("5,940")

    def test_first_time_fix_weighted_versus_row_mean(self):
        fixed, corrective = self.total("First_Time_Fix_Count"), self.total("Corrective_WO_Count")
        self.assertEqual((fixed, corrective), (7984, 10428))
        self.assertAlmostEqual(fixed / corrective * 100, 76.563099, places=5)
        self.assertAlmostEqual(self.mean("First_Time_Fix_Rate") * 100, 64.716888, places=5)
        self.stated("76.563099")
        self.stated("64.716888")

    def test_cost_ratio_is_not_roi(self):
        spend, loss = self.total("Maintenance_Cost_USD"), self.total("Production_Loss_USD")
        self.assertAlmostEqual(spend, 50430446.2805, places=3)
        self.assertAlmostEqual(loss, 228881052.0055, places=3)
        self.assertAlmostEqual(loss / spend, 4.538549, places=6)
        self.stated("4.538549")

    def test_rows_by_year_are_unequal(self):
        years = Counter(r["Record_Date"][:4] for r in self.rows)
        self.assertEqual((years["2024"], years["2025"], years["2026"]), (2004, 2000, 996))
        self.stated("2,004")

    def test_repository_engine_reproduces_the_aggregates(self):
        by_key = {r["key"]: r["value"] for r in kpis.compute_all(self.columns, self.rows)["results"]}
        self.assertAlmostEqual(by_key["availability"], 96.962530, places=5)
        self.assertAlmostEqual(by_key["mtbf"], 313.320570, places=5)
        self.assertAlmostEqual(by_key["mttr"], 11.988112, places=5)
        self.assertAlmostEqual(by_key["sla_attainment"], 46.12, places=2)
        self.assertAlmostEqual(by_key["first_time_fix"], 76.563099, places=5)
        self.assertAlmostEqual(by_key["loss_to_maintenance_ratio"], 4.538549, places=6)


class EngineDefinitions(unittest.TestCase):
    """Synthetic fixture, always run: ratio of sums, not an average of rates."""

    COLUMNS = ["Planned_Operating_Hours", "Operating_Hours", "Downtime_Hours", "Failure_Count",
               "First_Time_Fix_Count", "Corrective_WO_Count"]
    ROWS = [
        dict(zip(COLUMNS, ("100", "90", "10", "1", "1", "1"))),
        dict(zip(COLUMNS, ("900", "800", "100", "9", "9", "99"))),
    ]

    def test_availability_weights_by_planned_hours(self):
        by_key = {r["key"]: r["value"] for r in kpis.compute_all(self.COLUMNS, self.ROWS)["results"]}
        # Rows are 90% and 88.9%: a row mean would be about 89.44. The ratio of sums is 89.0.
        self.assertAlmostEqual(by_key["availability"], 89.0, places=6)

    def test_first_time_fix_weights_by_corrective_work(self):
        by_key = {r["key"]: r["value"] for r in kpis.compute_all(self.COLUMNS, self.ROWS)["results"]}
        # Row rates are 100% and 9.09%: a mean would be 54.55. The weighted rate is 10/100.
        self.assertAlmostEqual(by_key["first_time_fix"], 10.0, places=6)


if __name__ == "__main__":
    unittest.main()
