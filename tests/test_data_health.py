"""R4: data health (31 October 2026).

After cleaning, the share of measure values usable as recorded, with each
loss named: empty, marked missing, unreadable, outside a declared limit.
Unusual values are still used, so they are counted among the usable values.
"""
import unittest

from server import analytics, report_display
from server import mapping as colmap
from tests.test_analytics import run_pipeline
from tests.test_validity_limits import COLUMNS, HOURS_CSV, ROWS, hours_mapping

# 24 months; one blank, one marked N/A and one unreadable value.
HOURS = [str(6 + i % 4) for i in range(24)]
HOURS[3], HOURS[9], HOURS[15] = "", "N/A", "abc"
MESSY = "month,site,hours\n" + "".join(
    f"{2024 + i // 12}-{i % 12 + 1:02d},{'AB'[i % 2]},{h}\n" for i, h in enumerate(HOURS))


def claim(results, language="en"):
    found = {c["id"]: c for c in results["cleaner"]["claims"]}["cl_health"]
    return found.get("text_ar") if language == "ar" else found["text"]


class HealthTests(unittest.TestCase):

    def test_each_loss_is_counted_and_the_share_follows(self):
        ctx, results = run_pipeline(MESSY)
        health = ctx["cleaner"]["health"]
        self.assertEqual((health["cells"], health["empty"], health["marked_missing"],
                          health["unreadable"], health["outside_limits"]), (24, 1, 1, 1, 0))
        self.assertEqual(health["usable"], 21)
        self.assertEqual(health["share"], 87.5)
        self.assertIn("87.5% of measure values (21 of 24)", claim(results))
        self.assertIn("1 empty; 1 marked missing; 1 unreadable", claim(results))

    def test_values_outside_a_limit_count_against_health(self):
        mapping = colmap.validate(hours_mapping({"hours": {"min": 0, "max": 24}}), COLUMNS, ROWS)
        ctx, _ = run_pipeline(HOURS_CSV, mapping=mapping)
        health = ctx["cleaner"]["health"]
        self.assertEqual((health["outside_limits"], health["usable"], health["cells"]), (2, 8, 10))
        self.assertEqual(health["share"], 80.0)

    def test_clean_data_scores_full_and_says_so(self):
        _, results = run_pipeline("month,hours\n2025-01,8\n2025-02,9\n2025-03,7\n")
        self.assertIn("100.0%", claim(results))
        self.assertIn("none is empty, unreadable or outside a limit", claim(results))

    def test_the_report_states_it_first_in_the_policy_section(self):
        for language, heading, line in (
                ("en", "## Data policy applied", "- Data health: 87.5% of measure values (21 of 24)"),
                ("ar", "## سياسة البيانات المطبقة", "- صحة البيانات: 87.5% من قيم المقاييس (21 من 24)")):
            with self.subTest(language=language):
                _, results = run_pipeline(MESSY, language=language)
                report = results["reporter"]["output"]["report_markdown"]
                section = report.split(heading, 1)[1].strip().splitlines()
                self.assertEqual(section[0], line + (" are usable as recorded." if language == "en"
                                                     else " صالحة كما سُجّلت."))

    def test_both_languages_pass_the_validator_with_arabic_labels(self):
        for language in ("en", "ar"):
            with self.subTest(language=language):
                _, results = run_pipeline(MESSY, language=language)
                failed = [c["name"] for c in results["validator"]["quality_checks"]
                          if not c["passed"]]
                self.assertEqual(failed, [])
                calcs = {c["id"]: c for c in results["cleaner"]["calculations"]}
                cited = {c["id"]: c for c in results["cleaner"]["claims"]}["cl_health"]
                self.assertTrue(analytics.claim_figures_match(cited, calcs))
                for key in ("c_health", "c_health_cells"):
                    name, _, method = report_display.calculation(calcs[key], "ar")
                    self.assertFalse(name.startswith("الاسم الأصلي"), name)
                    self.assertFalse(method.startswith("الطريقة الأصلية"), method)


if __name__ == "__main__":
    unittest.main()
