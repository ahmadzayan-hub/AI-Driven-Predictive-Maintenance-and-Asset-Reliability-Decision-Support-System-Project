"""The comprehensive report leaves out headings with nothing under them
(ADR 2026-10-28-stage-report-sections). Key metrics, every claim and charts
are each printed only when a stage produced one; the limitations name what
was left out, once, in the reader's language.
"""
import unittest

from server import analytics
from server.analytics import _chart_lines, _claim_lines, _metric_lines, REPORT_TEXT


def empty_ctx(**extra):
    ctx = {"visuals": {"charts": []}}
    ctx.update(extra)
    return ctx


CALC = {"name": "Revenue", "value": 120, "method": "sum of sales", "scale": "money"}
CLAIM = {"text": "Revenue rose", "type": "descriptive", "evidence": ["ev1"], "status": "supported"}


class StageReportSectionTests(unittest.TestCase):
    def test_empty_run_produces_no_metric_claim_or_chart_lines(self):
        for language in ("en", "ar"):
            text = REPORT_TEXT[language]
            ctx = empty_ctx(descriptive_result={"calculations": [], "claims": []})
            with self.subTest(language=language):
                self.assertEqual(_metric_lines(ctx, language, text), [])
                self.assertEqual(_claim_lines(ctx, language, text), [])
                self.assertEqual(_chart_lines(ctx, language, text), [])

    def test_populated_sections_keep_their_heading_and_rows(self):
        text = REPORT_TEXT["en"]
        ctx = empty_ctx(descriptive_result={"calculations": [CALC], "claims": [CLAIM]},
                        visuals={"charts": [{"title": "Sales", "type": "bar", "alt": "Bars of sales"}]})
        metrics = _metric_lines(ctx, "en", text)
        self.assertIn(text["metrics"], metrics)
        self.assertTrue(any("Revenue" in line for line in metrics))
        claims = _claim_lines(ctx, "en", text)
        self.assertEqual(claims[3], text["claims"])
        self.assertIn("| Revenue rose | descriptive | ev1 | supported |", claims)
        charts = _chart_lines(ctx, "en", text)
        self.assertEqual(charts[1], text["charts"])
        self.assertIn("Bars of sales", charts[2])

    def test_a_section_with_nothing_is_named_in_the_limitations_in_both_languages(self):
        for language in ("en", "ar"):
            text = REPORT_TEXT[language]
            titles = [text["metrics"].lstrip("# "), text["claims"].lstrip("# "), text["charts"].lstrip("# ")]
            line = text["left_out"].format(sections=text["separator"].join(titles))
            with self.subTest(language=language):
                for title in titles:
                    self.assertIn(title, line)
                self.assertTrue(line.startswith("- "))

    def test_the_headings_are_the_same_titles_the_report_has_always_used(self):
        self.assertEqual(REPORT_TEXT["en"]["metrics"], "## Key metrics")
        self.assertEqual(REPORT_TEXT["en"]["claims"], "## Every claim in this report")
        self.assertEqual(REPORT_TEXT["en"]["charts"], "## Charts")
        self.assertIsNotNone(analytics.reporter)


if __name__ == "__main__":
    unittest.main()
