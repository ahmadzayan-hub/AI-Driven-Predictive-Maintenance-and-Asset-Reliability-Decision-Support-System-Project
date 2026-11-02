"""Validity limits per measure (31 October 2026, owner policy item 1).

A mapping may declare the lowest and highest value a measure can hold
(hours worked: 0 to 24). A value outside its limit is a data error: the
cleaner leaves it out of every figure, records the row, value and limit so
it can be reversed, and says so in a claim tied to a calculation. Without
declared limits nothing changes.
"""

import unittest

from server import mapping as colmap
from server import report_display
from tests.test_analytics import run_pipeline
from tests import test_mapping
from tests.test_mapping import mapping_for

HOURS = [8, 9, -3, 7, 30, 8, 10, 6, 9, 8]
HOURS_CSV = "month,asset,hours\n" + "\n".join(
    f"2025-{i + 1:02d},A{i % 3},{h}" for i, h in enumerate(HOURS)) + "\n"
COLUMNS = ["month", "asset", "hours"]
ROWS = [{"month": f"2025-{i + 1:02d}", "asset": f"A{i % 3}", "hours": str(h)}
        for i, h in enumerate(HOURS)]


def hours_mapping(limits=None):
    mapping = mapping_for({"month": "date", "asset": "dimension", "hours": "measure"},
                          measure="hours", dimension="asset", grain="month")
    if limits is not None:
        mapping["limits"] = limits
    return mapping


def problems_of(mapping):
    with self_raises() as caught:
        colmap.validate(mapping, COLUMNS, ROWS)
    return caught


class self_raises:
    def __enter__(self):
        return self

    def __exit__(self, kind, error, _):
        if kind is None:
            raise AssertionError("the mapping was accepted")
        if not issubclass(kind, colmap.MappingError):
            return False
        self.problems = error.problems
        return True


class ValidationTests(unittest.TestCase):

    def test_limits_are_saved_only_when_given(self):
        saved = colmap.validate(hours_mapping({"hours": {"min": 0, "max": 24}}), COLUMNS, ROWS)
        self.assertEqual(saved["limits"], {"hours": {"min": 0, "max": 24}})
        self.assertNotIn("limits", colmap.validate(hours_mapping(), COLUMNS, ROWS))
        self.assertNotIn("limits", colmap.validate(hours_mapping({}), COLUMNS, ROWS))

    def test_one_side_is_enough(self):
        saved = colmap.validate(hours_mapping({"hours": {"min": 0}}), COLUMNS, ROWS)
        self.assertEqual(saved["limits"], {"hours": {"min": 0}})

    def test_bad_limits_are_refused_in_both_languages(self):
        cases = {
            "not a measure": {"asset": {"min": 0}},
            "not a number": {"hours": {"min": "zero"}},
            "a boolean": {"hours": {"max": True}},
            "min above max": {"hours": {"min": 25, "max": 24}},
        }
        for label, limits in cases.items():
            with self.subTest(case=label):
                caught = problems_of(hours_mapping(limits))
                self.assertEqual([p.field for p in caught.problems], ["limits"])
                self.assertTrue(all(p.en and p.ar for p in caught.problems))

    def test_breaks_limit_names_the_side(self):
        limit = {"min": 0, "max": 24}
        self.assertEqual(colmap.breaks_limit(-1, limit), "min")
        self.assertEqual(colmap.breaks_limit(25, limit), "max")
        self.assertIsNone(colmap.breaks_limit(0, limit))
        self.assertIsNone(colmap.breaks_limit(24, limit))
        self.assertIsNone(colmap.breaks_limit(None, limit))
        self.assertIsNone(colmap.breaks_limit(-1, None))


class CleanerTests(unittest.TestCase):

    def run_with_limits(self, language="en"):
        mapping = colmap.validate(hours_mapping({"hours": {"min": 0, "max": 24}}), COLUMNS, ROWS)
        return run_pipeline(HOURS_CSV, mapping=mapping, language=language)

    def test_values_outside_the_limits_are_left_out_and_recorded(self):
        ctx, results = self.run_with_limits()
        cleaner = ctx["cleaner"]
        self.assertEqual(cleaner["invalid_count"], 2)
        recorded = {(v["value"], v["broke"], v["limit"]) for v in cleaner["invalid_values"]}
        self.assertEqual(recorded, {(-3, "min", 0), (30, "max", 24)})
        self.assertTrue(all("row" in v and v["column"] == "hours" for v in cleaner["invalid_values"]))
        kept = [row["hours"] for row in cleaner["rows"] if row["hours"] is not None]
        self.assertEqual(sum(kept), sum(h for h in HOURS if 0 <= h <= 24))

    def test_a_claim_ties_the_exclusion_to_a_calculation(self):
        ctx, results = self.run_with_limits()
        calcs = {c["id"]: c["value"] for c in results["cleaner"]["calculations"]}
        self.assertEqual(calcs["c_invalid_values"], 2)
        claim = {c["id"]: c for c in results["cleaner"]["claims"]}["cl_invalid_values"]
        self.assertEqual(claim["type"], "limitation")
        self.assertEqual(claim["evidence"], ["c_invalid_values"])
        _, arabic = self.run_with_limits("ar")
        claim_ar = {c["id"]: c for c in arabic["cleaner"]["claims"]}["cl_invalid_values"]
        self.assertIn("استُبعدت", claim_ar.get("text_ar") or claim_ar["text"])

    def test_the_profile_no_longer_counts_them(self):
        ctx, _ = self.run_with_limits()
        measure = ctx["profiler"]["profile"]["hours"]["measure"]
        self.assertEqual(measure["negatives"], 0)
        self.assertEqual((measure["min"], measure["max"]), (6, 10))

    def test_without_limits_nothing_changes(self):
        mapping = colmap.validate(hours_mapping(), COLUMNS, ROWS)
        ctx, results = run_pipeline(HOURS_CSV, mapping=mapping)
        self.assertEqual(ctx["cleaner"]["invalid_count"], 0)
        self.assertNotIn("cl_invalid_values", {c["id"] for c in results["cleaner"]["claims"]})
        self.assertEqual(sum(row["hours"] for row in ctx["cleaner"]["rows"]), sum(HOURS))

    def test_both_languages_pass_the_validator_and_read_in_arabic(self):
        for language in ("en", "ar"):
            with self.subTest(language=language):
                _, results = self.run_with_limits(language)
                failed = [c["name"] for c in results["validator"]["quality_checks"] if not c["passed"]]
                self.assertEqual(failed, [])
        _, results = self.run_with_limits("ar")
        calc = {c["id"]: c for c in results["cleaner"]["calculations"]}["c_invalid_values"]
        name, _, method = report_display.calculation(calc, "ar")
        self.assertFalse(name.startswith("الاسم الأصلي"), name)
        self.assertFalse(method.startswith("الطريقة الأصلية"), method)


class ApiTests(unittest.TestCase):
    # The mapping API helpers, borrowed without inheriting that file's tests.
    _base = test_mapping.MappingApiTestCase
    database_config, setUp = _base.database_config, _base.setUp
    upload, run_to_gate, result = _base.upload, _base.run_to_gate, _base.result
    output, claim_ids = _base.output, _base.claim_ids

    def test_a_saved_mapping_with_limits_is_applied_to_a_run(self):
        dataset_id = self.upload(HOURS_CSV, "hours.csv")
        body = hours_mapping({"hours": {"min": 0, "max": 24}})
        response = self.client.put(f"/api/datasets/{dataset_id}/mapping", json=body)
        self.assertEqual(response.status_code, 200, response.text)
        run = self.run_to_gate(dataset_id=dataset_id, goal="Hours by asset")
        self.assertEqual(self.output(run, "cleaner")["invalid_count"], 2)
        self.assertIn("cl_invalid_values", self.claim_ids(run))

    def test_bad_limits_are_refused_by_the_api(self):
        dataset_id = self.upload(HOURS_CSV, "hours.csv")
        body = hours_mapping({"asset": {"min": 0}})
        response = self.client.put(f"/api/datasets/{dataset_id}/mapping", json=body)
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
