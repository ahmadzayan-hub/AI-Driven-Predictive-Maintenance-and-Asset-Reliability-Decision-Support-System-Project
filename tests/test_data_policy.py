"""The owner's data policy, points 2 to 4 (31 October 2026).

2. Unusual values are judged within each group of the breakdown, and by
   ratio (a log scale) for positive measures leaning high; when leaving them
   out moves a measure's average by 10% or more, both averages are reported.
3. A gap in a column the association model reads beside the measure is
   filled for that model alone, with the group's median, flagged, and the
   result compared without the fill. The measure is never filled, nor a
   column missing more than 30% of its values.
4. The report states the policy and what it did on the run.
"""

import unittest

from server import analytics, report_display
from tests.test_analytics import run_pipeline
from tests.test_data_understanding import COST_CSV, COSTS


def claims(results, role):
    return {c["id"]: c for c in results[role]["claims"]}


def calcs(results, role):
    return {c["id"]: c for c in results[role]["calculations"]}


# Two fleets of very different size: 40 is ordinary overall but unusual
# among the small fleet's values near 10.
FLEET = [("Large", v) for v in (1000, 1010, 990, 1005, 995, 1002)] + \
        [("Small", v) for v in (10, 11, 9, 10, 12, 40)]
FLEET_CSV = "fleet,cost\n" + "\n".join(f"{f},{v}" for f, v in FLEET) + "\n"

# Repair costs that lean far to the high side: by difference the largest is
# unusual, by ratio none is.
SKEWED = [10, 12, 15, 20, 30, 50, 80, 150, 300, 600]


def assoc_csv(age_gaps, hours_gap=False):
    """Twelve months, two sites; age missing in the given row numbers."""
    lines = ["month,site,hours,age"]
    for i in range(12):
        age = "" if i in age_gaps else str(2 + i)
        hours = "" if hours_gap and i == 5 else str(100 + 10 * i + (5 if i % 2 else 0))
        lines.append(f"2025-{i + 1:02d},{'North' if i % 2 else 'South'},{hours},{age}")
    return "\n".join(lines) + "\n"


class UnusualValueTests(unittest.TestCase):

    def test_values_are_judged_within_each_group(self):
        groups = {i: f for i, (f, _) in enumerate(FLEET)}
        numbers = [(i, v) for i, (_, v) in enumerate(FLEET)]
        self.assertEqual(analytics._measure_profile(numbers)["outliers"], 0)
        grouped = analytics._measure_profile(numbers, groups)
        self.assertTrue(grouped["grouped"])
        self.assertEqual((grouped["outliers"], grouped["outlier_rows"]), (1, [11]))

    def test_the_pipeline_groups_by_the_breakdown(self):
        ctx, results = run_pipeline(FLEET_CSV)
        measure = ctx["profiler"]["profile"]["cost"]["measure"]
        self.assertTrue(measure["grouped"])
        self.assertEqual(measure["outlier_rows"], [11])
        self.assertIn("within each group of fleet", claims(results, "profiler")["cl_outliers"]["text"])

    def test_positive_measures_leaning_high_are_judged_by_ratio(self):
        numbers = list(enumerate(SKEWED))
        profile = analytics._measure_profile(numbers)
        self.assertEqual((profile["scale"], profile["outliers"]), ("log", 0))
        # The same values by difference would flag the largest.
        low, high = analytics._fences(sorted(SKEWED))
        self.assertEqual([v for v in SKEWED if v < low or v > high], [600])

    def test_negative_values_keep_the_plain_scale(self):
        ctx, _ = run_pipeline(COST_CSV)
        self.assertEqual(ctx["profiler"]["profile"]["cost"]["measure"]["scale"], "linear")

    def test_a_material_effect_shows_the_average_with_and_without(self):
        ctx, results = run_pipeline(COST_CSV)
        measure = ctx["profiler"]["profile"]["cost"]["measure"]
        kept = [c for i, c in enumerate(COSTS) if i not in (8, 10)]
        self.assertAlmostEqual(measure["mean"], sum(COSTS) / 12, places=4)
        self.assertAlmostEqual(measure["mean_without_outliers"], sum(kept) / 10, places=4)
        claim = claims(results, "profiler")["cl_outlier_effect"]
        self.assertEqual(claim["type"], "limitation")
        expected = f"{sum(COSTS) / 12:,.2f} with, {sum(kept) / 10:,.2f} without"
        self.assertIn(expected, claim["text"])
        self.assertIn(expected, calcs(results, "profiler")["c_outlier_effect"]["value"])

    def test_a_small_effect_is_not_reported(self):
        _, results = run_pipeline(FLEET_CSV)
        self.assertNotIn("cl_outlier_effect", claims(results, "profiler"))


class FillForModelTests(unittest.TestCase):

    def test_a_short_gap_is_filled_for_the_model_and_checked_both_ways(self):
        ctx, results = run_pipeline(assoc_csv({3, 8}))
        filled = ctx["diagnostic"]["filled_for_model"]
        self.assertEqual(len(filled), 1)
        record = filled[0]
        self.assertEqual((record["column"], record["filled"], record["flag_column"]),
                         ("age", 2, "age_filled"))
        self.assertEqual(record["method"], "group median")
        found = calcs(results, "diagnostic")
        self.assertEqual(found["c_fill_0"]["value"], 2)
        self.assertEqual(found["c_fill_observed_0"]["value"], record["correlation_observed"])
        self.assertEqual(found["c_assoc_0"]["value"], record["correlation_filled"])
        self.assertEqual(found["c_assoc_n_0"]["value"], 12)
        claim = claims(results, "diagnostic")["cl_fill_0"]
        self.assertEqual(claim["type"], "limitation")
        self.assertIn("no stored value changed", claim["text"])

    def test_no_stored_value_changes(self):
        ctx, _ = run_pipeline(assoc_csv({3, 8}))
        self.assertEqual(sum(1 for r in ctx["cleaner"]["rows"] if r["age"] is None), 2)

    def test_the_measure_is_never_filled(self):
        ctx, results = run_pipeline(assoc_csv(set(), hours_gap=True))
        self.assertEqual(ctx["diagnostic"]["filled_for_model"], [])
        self.assertEqual(calcs(results, "diagnostic")["c_assoc_n_0"]["value"], 11)

    def test_a_column_missing_more_than_the_ceiling_is_not_filled(self):
        ctx, results = run_pipeline(assoc_csv({0, 2, 4, 6}))
        self.assertGreater(4 / 12, analytics.FILL_MAX_SHARE)
        self.assertEqual(ctx["diagnostic"]["filled_for_model"], [])
        self.assertNotIn("cl_fill_0", claims(results, "diagnostic"))


class PolicyInReportTests(unittest.TestCase):

    def report(self, text, language="en"):
        _, results = run_pipeline(text, language=language)
        return results["reporter"]["output"]["report_markdown"]

    def test_the_report_states_the_policy_and_what_it_did(self):
        report = self.report(assoc_csv({3, 8}))
        self.assertIn("## Data policy applied", report)
        self.assertIn("Validity limits: none declared", report)
        self.assertIn("in the association model only, for age (2)", report)
        self.assertIn("The measure is never filled", report)

    def test_the_arabic_report_states_it_too(self):
        report = self.report(COST_CSV, "ar")
        self.assertIn("## سياسة البيانات المطبقة", report)
        self.assertIn("ويُعرض المتوسط معها ودونها لـcost", report)


class BothLanguagesTests(unittest.TestCase):

    def test_the_validator_passes_and_arabic_labels_exist(self):
        found = {}
        for text in (COST_CSV, FLEET_CSV, assoc_csv({3, 8})):
            for language in ("en", "ar"):
                with self.subTest(language=language):
                    _, results = run_pipeline(text, language=language)
                    failed = [c["name"] for c in results["validator"]["quality_checks"]
                              if not c["passed"]]
                    self.assertEqual(failed, [])
                    for role in ("profiler", "diagnostic"):
                        found.update({c["id"]: c for c in results[role]["calculations"]})
        for key in ("c_outliers", "c_outlier_effect", "c_fill_0", "c_fill_observed_0"):
            with self.subTest(calculation=key):
                name, _, method = report_display.calculation(found[key], "ar")
                self.assertFalse(name.startswith("الاسم الأصلي"), name)
                self.assertFalse(method.startswith("الطريقة الأصلية"), method)


if __name__ == "__main__":
    unittest.main()
