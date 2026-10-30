"""Understanding and cleaning the data (30 October 2026).

The Data Profiling Agent now says what a reader should check before trusting
a figure: each measure's range, values far outside it, negative values, mostly
empty and single-value columns. The cleaner reads missing-value markers as
empty and names categories spelled more than one way. Nothing here changes a
value: unusual values are kept and spellings are not merged, so every total
is what the data says.
"""

import unittest

from server import analytics
from tests.test_analytics import run_pipeline


def claims(results, role):
    return {c["id"]: c for c in results[role]["claims"]}


def calcs(results, role):
    return {c["id"]: c["value"] for c in results[role]["calculations"]}


# Twelve months of repair costs with one value far above the rest (row 8)
# and one credit note (row 10).
COSTS = [12, 14, 13, 15, 12, 16, 14, 13, 9000, 15, -40, 14]
COST_CSV = "month,site,cost,note\n" + "\n".join(
    f"2025-{i + 1:02d},Depot,{c}," for i, c in enumerate(COSTS)) + "\n"


class UnderstandingTests(unittest.TestCase):

    def test_each_measure_gets_its_range_and_unusual_values(self):
        ctx, results = run_pipeline(COST_CSV)
        measure = ctx["profiler"]["profile"]["cost"]["measure"]
        self.assertEqual((measure["count"], measure["min"], measure["max"]), (12, -40, 9000))
        self.assertEqual(measure["median"], 14)
        self.assertEqual((measure["outliers"], measure["negatives"]), (2, 1))
        self.assertEqual(measure["outlier_rows"], [8, 10])
        self.assertEqual(len(measure["fences"]), 2)

    def test_unusual_and_negative_values_are_claims_tied_to_calculations(self):
        ctx, results = run_pipeline(COST_CSV)
        found = claims(results, "profiler")
        self.assertEqual(found["cl_outliers"]["type"], "limitation")
        self.assertIn("cost 2", found["cl_outliers"]["text"])
        self.assertIn("kept, not removed or changed", found["cl_outliers"]["text"])
        self.assertEqual(found["cl_outliers"]["evidence"], ["c_outliers"])
        self.assertIn("cost 1", found["cl_negatives"]["text"])
        self.assertEqual(calcs(results, "profiler")["c_outliers"], 2)
        # Kept: the total still includes the unusual value and the credit.
        self.assertEqual(sum(row["cost"] for row in ctx["cleaner"]["rows"]), sum(COSTS))

    def test_mostly_empty_and_single_value_columns_are_named(self):
        ctx, results = run_pipeline(COST_CSV)
        profile = ctx["profiler"]["profile"]
        self.assertEqual(profile["note"]["missing_share"], 1.0)
        self.assertTrue(profile["site"]["constant"])
        found = claims(results, "profiler")
        self.assertIn("note (100%)", found["cl_sparse_columns"]["text"])
        self.assertIn("site", found["cl_constant_columns"]["text"])
        self.assertEqual(found["cl_constant_columns"]["type"], "fact")

    def test_a_tidy_dataset_makes_none_of_these_claims(self):
        text = "month,region,cost\n" + "\n".join(
            f"2025-{m:02d},{'North' if m % 2 else 'South'},{100 + m}" for m in range(1, 13)) + "\n"
        ctx, results = run_pipeline(text)
        made = set(claims(results, "profiler")) | set(claims(results, "cleaner"))
        for absent in ("cl_outliers", "cl_negatives", "cl_sparse_columns", "cl_constant_columns",
                       "cl_missing_markers", "cl_spelling_variants"):
            self.assertNotIn(absent, made)

    def test_both_languages_pass_the_validator(self):
        for language in ("en", "ar"):
            with self.subTest(language=language):
                ctx, results = run_pipeline(COST_CSV, language=language)
                failed = [c["name"] for c in results["validator"]["quality_checks"] if not c["passed"]]
                self.assertEqual(failed, [])
        ctx, results = run_pipeline(COST_CSV, language="ar")
        self.assertIn("أُبقيت كما هي", claims(results, "profiler")["cl_outliers"]["text_ar"])


class CleaningTests(unittest.TestCase):

    def test_categories_spelled_more_than_one_way_are_named_not_merged(self):
        regions = ["North"] * 5 + ["north"] * 2 + ["North  "] + ["South"] * 4
        text = "region,cost\n" + "\n".join(f"{r},{10 + i}" for i, r in enumerate(regions)) + "\n"
        ctx, results = run_pipeline(text)
        variants = ctx["cleaner"]["spelling_variants"]
        self.assertEqual(variants, {"region": [[["North", 6], ["north", 2]]]})
        claim = claims(results, "cleaner")["cl_spelling_variants"]
        self.assertEqual(claim["type"], "limitation")
        self.assertIn("“North” (6), “north” (2)", claim["text"])
        self.assertEqual(calcs(results, "cleaner")["c_spelling_variants"], 1)
        # Not merged: both spellings remain in the rows the analysis reads.
        self.assertEqual({row["region"] for row in ctx["cleaner"]["rows"]}, {"North", "north", "South"})

    def test_markers_make_a_mostly_numeric_column_numeric(self):
        text = "asset,hours\n" + "\n".join(
            f"A{i},{'N/A' if i % 4 == 0 else i}" for i in range(1, 21)) + "\n"
        ctx, results = run_pipeline(text)
        self.assertIn("hours", ctx["profiler"]["numeric_columns"])
        self.assertEqual(ctx["cleaner"]["missing_markers"], 5)
        self.assertEqual(calcs(results, "cleaner")["c_coercion"], 0)

    def test_marker_words_are_not_read_as_missing_in_a_text_column(self):
        text = "failure_mode,hours\n" + "\n".join(
            f"{'None' if i % 2 else 'Seal'},{i}" for i in range(1, 9)) + "\n"
        ctx, results = run_pipeline(text)
        self.assertEqual({row["failure_mode"] for row in ctx["cleaner"]["rows"]}, {"None", "Seal"})
        self.assertEqual(ctx["profiler"]["profile"]["failure_mode"]["missing"], 0)

    def test_the_markers_include_arabic(self):
        self.assertIn("غير متوفر", analytics.MISSING_MARKERS)
        self.assertIn("#n/a", analytics.MISSING_MARKERS)



class ArabicDisplayTests(unittest.TestCase):

    def test_every_new_calculation_reads_in_arabic(self):
        from server import report_display
        regions = ["North"] * 5 + ["north"] * 2 + ["South"] * 4
        marked = "region,cost,note\n" + "\n".join(
            f"{r},{'n/a' if i == 3 else 10 + i}," for i, r in enumerate(regions)) + "\n"
        found = {}
        for text in (COST_CSV, marked):
            _, results = run_pipeline(text, language="ar")
            for role in ("profiler", "cleaner"):
                found.update({c["id"]: c for c in results[role]["calculations"]})
        for key in ("c_sparse_columns", "c_constant_columns", "c_outliers", "c_negatives",
                    "c_missing_markers", "c_spelling_variants", "c_coercion"):
            with self.subTest(calculation=key):
                name, _, method = report_display.calculation(found[key], "ar")
                self.assertFalse(name.startswith("الاسم الأصلي"), name)
                self.assertFalse(method.startswith("الطريقة الأصلية"), method)



if __name__ == "__main__":
    unittest.main()
