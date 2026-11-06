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


class DecimalComma(unittest.TestCase):
    """Open gap 2 of the first stress run, closed on 5 November."""

    def test_the_comma_is_read_only_when_the_mapping_says_so(self):
        from server import mapping
        self.assertIsNone(mapping.parse_number("12,34"))
        self.assertEqual(mapping.parse_number("12,34", "comma"), 12.34)
        self.assertEqual(mapping.parse_number("1.234,5", "comma"), 1234.5)
        self.assertEqual(mapping.parse_number("(7,5)", "comma"), -7.5)
        self.assertIsNone(mapping.parse_number("12.34.5", "comma"))

    def test_a_semicolon_file_with_decimal_commas_splits_on_the_semicolon(self):
        from server import datasets
        table = datasets.read(b"Station;Downtime_Hours\nST01;12,50\nST02;3,75\nST03;8,05\n", "eu.csv")
        self.assertEqual(table.columns, ["Station", "Downtime_Hours"])

    def test_the_comma_is_suggested_and_declared_values_validate(self):
        from server import mapping
        rows = [{"Station": f"ST{i:02d}", "Downtime_Hours": f"{i},{i * 7 % 100:02d}"} for i in range(1, 9)]
        suggestion = mapping.suggest(["Station", "Downtime_Hours"], rows)
        self.assertEqual(suggestion.get("decimal"), "comma")
        self.assertEqual(suggestion["roles"]["Downtime_Hours"], "measure")
        saved = mapping.validate({**suggestion, "measure": "Downtime_Hours"}, ["Station", "Downtime_Hours"], rows)
        self.assertEqual(saved["decimal"], "comma")

    def test_thousands_with_three_digits_are_not_suggested_as_decimals(self):
        from server import mapping
        rows = [{"Cost": v} for v in ("1,250", "2,400", "3,100", "9,999")]
        self.assertIsNone(mapping.suggest(["Cost"], rows).get("decimal"))


class Direction(unittest.TestCase):
    """Open gap 1: a 1-is-best grade ranks weakest first once the owner says so."""

    def plan(self, better=None):
        from server import layout_plan as L
        rows = [{"Assessment_Date": "2025-06-01", "Station": f"ST{i % 4}", "Condition_Rating": 1 + i % 5}
                for i in range(40)]
        table = query.table_from(["Assessment_Date", "Station", "Condition_Rating"], ["Condition_Rating"], rows,
                                 {"Station": "breakdown", "Condition_Rating": "analysed"})
        prof = L.profile(table)
        plan = L.rule_plan(prof, L.capabilities(prof), "", better)
        return next(s for s in plan["sections"] if s["component"] == "priorities")

    def test_lower_is_better_puts_the_highest_rating_first(self):
        self.assertIs(self.plan({"Condition_Rating": "lower"})["binding"]["sort"]["desc"], True)
        self.assertIs(self.plan({"Condition_Rating": "higher"})["binding"]["sort"]["desc"], False)

    def test_a_direction_must_name_a_measure(self):
        from server import mapping
        rows = [{"Station": "ST01", "Condition_Rating": "2"}, {"Station": "ST02", "Condition_Rating": "4"}]
        with self.assertRaises(mapping.MappingError):
            mapping.validate({"roles": {"Station": "dimension", "Condition_Rating": "measure"},
                              "measure": "Condition_Rating", "better": {"Station": "lower"}},
                             ["Station", "Condition_Rating"], rows)


class KnowledgeWithoutModel(unittest.TestCase):
    """Open gap 4: a real question is answered from the knowledge base without a model."""

    def gate(self, text):
        from server.assistant import Assistant
        assistant = Assistant.__new__(Assistant)
        assistant.env = {}
        return Assistant._knowledge_answers(assistant, text)

    def test_subject_questions_reach_the_knowledge_base(self):
        for text in ("What are the G02 P75 values?", "هل قيم P75 الحالية لحالة G02 معتمدة؟",
                     "Is the synthetic Failure_Probability a validated prediction?"):
            self.assertTrue(self.gate(text), text)

    def test_conversation_does_not(self):
        # A general question names nothing specific, so it gets the honest no-model reply.
        for text in ("How are you today?", "Can you write me a poem?", "Tell me a joke please?", "hello",
                     "What is the weather in Dubai?", "What is preventive maintenance?"):
            self.assertFalse(self.gate(text), text)


class ChatFigures(unittest.TestCase):
    """Open gap 3: figures keep every digit and gain thousands separators."""

    def test_grouped_and_exact(self):
        self.assertEqual(format(382031.46, ",.12g"), "382,031.46")
        self.assertEqual(format(99.996, ",.12g"), "99.996")
        source = open("server/data_chat.py", encoding="utf-8").read()
        self.assertNotIn('format(item["value"], ".12g")', source)


if __name__ == "__main__":
    unittest.main()
