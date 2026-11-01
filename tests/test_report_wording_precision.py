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

    def test_planning_power_is_a_curve_not_a_cutoff(self):
        normal = statistics.NormalDist()
        critical = normal.inv_cdf(.975)
        for variance, count in ((1, 4), (25, 21), (100, 200)):
            with self.subTest(variance=variance, count=count):
                standard_error = math.sqrt(2 * variance / (count / 2))
                threshold = analytics._smallest_detectable_change(variance, count)
                def power(effect):
                    shift = effect / standard_error
                    return normal.cdf(-critical - shift) + 1 - normal.cdf(critical - shift)
                self.assertAlmostEqual(power(0), .05, places=12)
                self.assertAlmostEqual(power(threshold), .80, places=5)
                self.assertGreater(power(threshold / 2), .05)
                self.assertLess(power(threshold / 2), .80)
                self.assertGreater(power(threshold * 1.5), .80)
                self.assertAlmostEqual(power(-threshold), power(threshold), places=12)

    def test_planning_threshold_requires_spread_and_two_observations_per_arm(self):
        for variance, count in ((0, 20), (-1, 20), (1, 3), (1, 0)):
            with self.subTest(variance=variance, count=count):
                self.assertIsNone(analytics._smallest_detectable_change(variance, count))

    def test_forecast_and_backtest_minima_are_different(self):
        # Four/five periods produce a projection, but do not validate its accuracy.
        for periods in (3, 4, 5, 6):
            source = 'month,team,sales\n' + ''.join(
                f'2025-{month:02d},A,{10 * month}\n' for month in range(1, periods + 1))
            for language in ('en', 'ar'):
                with self.subTest(periods=periods, language=language):
                    ctx, _ = run_pipeline(source, language=language, mapping=explicit_grouping())
                    forecast = ctx['predictive']
                    self.assertEqual(bool(forecast['forecast']), periods >= 4)
                    self.assertEqual(forecast.get('backtest_error') is not None, periods >= 6)
                    key = ('no_forecast_limit' if periods < 4 else
                           'unmeasured_forecast_limit' if periods < 6 else 'forecast_limit')
                    self.assertIn(analytics.REPORT_TEXT[language][key], ctx['reporter']['report_markdown'])
                    self.assertTrue(ctx['validator']['passed'])

    def test_zero_backtest_error_is_measured_not_missing(self):
        for language in ('en', 'ar'):
            ctx, _ = run_pipeline(linear_dataset(), language=language, mapping=explicit_grouping())
            self.assertEqual(ctx['predictive']['backtest_error'], 0)
            report = ctx['reporter']['report_markdown']
            self.assertIn(analytics.REPORT_TEXT[language]['forecast_limit'], report)
            self.assertNotIn(analytics.REPORT_TEXT[language]['unmeasured_forecast_limit'], report)

    def test_zero_holdout_values_leave_accuracy_unmeasured(self):
        source = 'month,team,sales\n' + ''.join(
            f'2025-{month:02d},A,{0 if month == 6 else 10 * month}\n'
            for month in range(1, 7))
        for language in ('en', 'ar'):
            ctx, _ = run_pipeline(source, language=language, mapping=explicit_grouping())
            self.assertTrue(ctx['predictive']['forecast'])
            self.assertIsNone(ctx['predictive']['backtest_error'])
            self.assertIn('zero actual values' if language == 'en' else 'تساوي صفراً',
                          ctx['predictive']['report_markdown'])
            self.assertIn(analytics.REPORT_TEXT[language]['unmeasured_forecast_limit'],
                          ctx['reporter']['report_markdown'])

    def test_no_dates_does_not_imply_a_forecast(self):
        for language in ('en', 'ar'):
            ctx, _ = run_pipeline('team,sales\nA,10\nB,20\nA,30\nB,40\n', language=language)
            self.assertFalse(ctx['predictive']['forecast'])
            self.assertIn(analytics.REPORT_TEXT[language]['no_forecast_limit'],
                          ctx['reporter']['report_markdown'])
            self.assertTrue(ctx['validator']['passed'])

    def test_rate_totals_are_not_forecast_in_either_language(self):
        source = 'month,team,availability_rate\n' + ''.join(
            f'2025-{month:02d},A,0.9\n' for month in range(1, 7))
        for language in ('en', 'ar'):
            ctx, results = run_pipeline(source, language=language,
                                       mapping=explicit_grouping(measure='availability_rate'))
            self.assertFalse(ctx['predictive']['forecast'])
            self.assertIn('c_rate', [c['id'] for c in results['predictive']['calculations']])
            self.assertIn(analytics.REPORT_TEXT[language]['no_forecast_limit'],
                          ctx['reporter']['report_markdown'])
            self.assertTrue(ctx['validator']['passed'])

    def test_low_coverage_tail_is_excluded_before_counting_forecast_periods(self):
        source = 'month,team,sales\n' + ''.join(
            f'2025-{month:02d},A,{10 * month + index}\n'
            for month in range(1, 5) for index in range(1 if month == 4 else 4))
        for language in ('en', 'ar'):
            ctx, results = run_pipeline(source, language=language, mapping=explicit_grouping())
            self.assertEqual(len(ctx['preparer']['trend']), 4)
            calculations = {c['id']: c['value'] for c in results['predictive']['calculations']}
            self.assertEqual(calculations['c_periods'], 3)
            self.assertFalse(ctx['predictive']['forecast'])
            self.assertIn(analytics.REPORT_TEXT[language]['no_forecast_limit'],
                          ctx['reporter']['report_markdown'])
            self.assertTrue(ctx['validator']['passed'])


if __name__ == '__main__':
    unittest.main()
