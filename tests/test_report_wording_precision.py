"""Bilingual report wording follows the actual planning and forecast state."""
import math
import statistics
import unittest

from server import analytics
from tests.test_analytics import explicit_grouping, linear_dataset, run_pipeline


class ReportWordingPrecisionTests(unittest.TestCase):
    def test_planning_threshold_does_not_make_smaller_effects_impossible(self):
        for language in ('en', 'ar'):
            with self.subTest(language=language):
                ctx, results = run_pipeline(analytics.sample_dataset(), language=language)
                values = [row[ctx['preparer']['measure']] for row in ctx['cleaner']['rows']]
                z_sum = statistics.NormalDist().inv_cdf(.975) + statistics.NormalDist().inv_cdf(.80)
                expected = z_sum * math.sqrt(2 * statistics.variance(values) / (len(values) / 2)) / abs(statistics.fmean(values))
                calculation = next(item for item in results['experiment']['calculations'] if item['id'] == 'c_exp_mde')
                self.assertEqual(calculation['value'], round(expected, 4))
                report = ctx['experiment']['report_markdown']
                self.assertIn('four times in five' if language == 'en' else 'أربع من كل خمس', report)
                self.assertIn('Smaller effects can still be detected' if language == 'en' else 'قد تُرصد تغيرات أصغر', report)
                self.assertIn('lower probability' if language == 'en' else 'باحتمال أقل', report)
                self.assertNotIn('invisible' if language == 'en' else 'لن يظهر', report)
                self.assertTrue(ctx['validator']['passed'])

    def assert_forecast_limit(self, dataset, produced):
        for language in ('en', 'ar'):
            with self.subTest(language=language):
                ctx, results = run_pipeline(dataset, language=language, mapping=explicit_grouping())
                self.assertEqual(bool(ctx['predictive']['forecast']), produced)
                limits = results['reporter']['output']['report_markdown'].rsplit(
                    analytics.REPORT_TEXT[language]['limits'], 1)[1]
                forecast_text = 'The forecast extends' if language == 'en' else 'يمدّ التوقع النمط التاريخي'
                refusal_text = 'No forecast was produced' if language == 'en' else 'لم يُنتج أي توقع'
                self.assertIn(forecast_text if produced else refusal_text, limits)
                self.assertNotIn(refusal_text if produced else forecast_text, limits)
                self.assertTrue(ctx['validator']['passed'])

    def test_insufficient_history_report_does_not_imply_a_forecast(self):
        self.assert_forecast_limit('month,team,sales\n2025-01,A,10\n2025-02,A,20\n2025-03,A,30\n', False)

    def test_unequal_coverage_report_does_not_imply_a_forecast(self):
        rows = ['month,team,sales']
        for month in range(1, 13):
            for index in range(8 if month <= 6 else 4):
                rows.append(f'2025-{month:02d},T{index % 2},{100 + month + index}')
        self.assert_forecast_limit('\n'.join(rows), False)

    def test_produced_forecast_keeps_its_assumptions(self):
        self.assert_forecast_limit(linear_dataset(), True)


if __name__ == '__main__':
    unittest.main()
