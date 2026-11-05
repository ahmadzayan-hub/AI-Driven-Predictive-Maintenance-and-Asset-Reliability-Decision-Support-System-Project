"""Regression tests for the gaps the synthetic stress run found (ADR 2026-11-05-stress-findings).

Each test holds one fix on invented rows. The full run is
`python scripts/stress_datasets.py`; its results are in docs/STRESS_TEST_RESULTS.md.
"""
import unittest

from server import analytics, query
from server.maintenance import kpis
from scripts.generate_synthetic_dataset import generate


class ClaimFigures(unittest.TestCase):
    def test_a_period_label_is_not_read_as_a_figure(self):
        claim = {"text": "The largest is 2025, which came in 283,521 above the trend.",
                 "evidence": ["c"], "labels": ["2025"]}
        self.assertTrue(analytics.claim_figures_match(claim, {"c": {"value": 283521.46}}))
        claim.pop("labels")
        self.assertFalse(analytics.claim_figures_match(claim, {"c": {"value": 283521.46}}))

    def test_a_label_with_a_month_is_removed_whole(self):
        claim = {"text": "Downtime for 2025-03 is around 5.96.", "evidence": ["c"], "labels": ["2025-03"]}
        self.assertTrue(analytics.claim_figures_match(claim, {"c": {"value": 5.96}}))


class Numbers(unittest.TestCase):
    def test_formatted_numbers_read_as_numbers(self):
        for text, value in (("85%", 85.0), ("AED 12,000", 12000.0), ("(300)", -300.0), ("٣٤٥", 345.0),
                            ("1,234", 1234.0)):
            self.assertEqual(analytics._to_number(text), value, text)

    def test_text_and_ambiguous_decimals_stay_unread(self):
        for text in ("ASSET-001", "2025-07-01", "12,34", "Good"):
            self.assertIsNone(analytics._to_number(text), text)

    def test_not_applicable_is_a_missing_marker(self):
        for text in ("Not applicable", "N/A", "-", "غير منطبق"):
            self.assertIn(text.lower(), analytics.MISSING_MARKERS)


class Dates(unittest.TestCase):
    def test_a_timestamp_column_is_the_time_axis(self):
        self.assertEqual(analytics._date_like_column(["Asset", "Timestamp", "Vibration_mm_s"]), "Timestamp")

    def test_sensor_readings_are_averaged(self):
        for name in ("Vibration_mm_s", "Pressure_Bar", "Sensor_001_Reading", "Supply_Voltage"):
            self.assertFalse(query.additive(name), name)


class TextGrades(unittest.TestCase):
    def test_share_graded_poor_or_worse(self):
        rows = [{"Condition_Grade": g} for g in ("Good", "Fair", "Poor", "Very poor", "Not applicable", "", "حرج")]
        out = {r["key"]: r for r in kpis.compute_all(["Condition_Grade"], rows)["results"]}
        share = out["condition_poor_grade_share"]
        self.assertEqual((share["records"], share["records_unmeasured"]), (5, 2))
        self.assertAlmostEqual(share["value"], 60.0)     # Poor, Very poor, حرج of 5 graded


class Generator(unittest.TestCase):
    def test_large_files_stay_in_two_years_and_add_fleets(self):
        rows = generate(10_000, seed=3)
        periods = {r[3] for r in rows}
        self.assertEqual((min(periods), max(periods)), ("2025-01-01", "2026-12-01"))
        self.assertGreater(len({r[1] for r in rows}), 94)
        self.assertEqual(len({r[0] for r in rows}), 10_000)


if __name__ == "__main__":
    unittest.main()
