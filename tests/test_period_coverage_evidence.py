"""Coverage evidence regressions use fabricated counts, never uploaded rows."""
import unittest
from server import analytics
from tests.test_analytics import run_pipeline, explicit_grouping

class PeriodCoverageEvidenceTests(unittest.TestCase):
    def test_every_comparison_count_is_cited_and_tampering_still_fails(self):
        dropped = {'period': '2025-12', 'records': 83, 'most': 167}
        for language in ('en', 'ar'):
            claim = analytics._incomplete_period_claim(
                {'report_language': language}, 'test', dropped, 'the check', 'الفحص')
            calcs = {c['id']: c for c in analytics._incomplete_period_calcs(dropped)}
            self.assertTrue(analytics.claim_figures_match(claim, calcs))
            self.assertEqual(calcs['c_earlier_period_max_records']['value'], 167)
            claim['text'] += ' Compared with 999 records.'
            self.assertFalse(analytics.claim_figures_match(claim, calcs))

    def test_sustained_lower_density_does_not_make_last_month_incomplete(self):
        labels = [f'{year}-{month:02d}' for year in (2025, 2026) for month in range(1, 13)]
        counts = {p: 167 if p.startswith('2025') else 83 for p in labels}
        prep = {'trend': {p: counts[p] * 10 for p in labels}, 'trend_counts': counts}
        kept, _, dropped = analytics._complete_periods(prep)
        self.assertEqual(kept, labels)
        self.assertIsNone(dropped)

    def test_sharp_tail_drop_is_coverage_precaution_not_calendar_proof(self):
        prep = {'trend': {'2025-01': 1670, '2025-02': 1670, '2025-03': 830},
                'trend_counts': {'2025-01': 167, '2025-02': 167, '2025-03': 83}}
        _, _, dropped = analytics._complete_periods(prep)
        self.assertIsNotNone(dropped)
        claim = analytics._incomplete_period_claim({}, 'test', dropped, 'the check', 'الفحص')
        self.assertIn('counts alone do not establish calendar incompleteness', claim['text'])

    def test_uneven_coverage_blocks_total_forecast_but_keeps_report(self):
        lines = ['month,team,sales']
        for month in range(1, 13):
            for n in range(8 if month <= 6 else 4):
                lines.append(f'2025-{month:02d},T{n%2},{100+month+n}')
        for language in ('en', 'ar'):
            ctx, results = run_pipeline('\n'.join(lines), language=language, mapping=explicit_grouping())
            self.assertEqual(list(ctx['preparer']['trend_counts'].values()), [8]*6 + [4]*6)
            self.assertEqual(ctx['predictive']['forecast'], [])
            self.assertIn('cl_forecast_coverage', [c['id'] for c in results['predictive']['claims']])
            self.assertEqual(results['validator']['status'], 'succeeded')
            self.assertEqual(results['reporter']['status'], 'succeeded')
            self.assertIn('Period record coverage differs' if language=='en' else 'تختلف تغطية الفترات',
                          ctx['prescriptive']['exec_summary'])
            from server.model_gateway import ModelGateway
            fallback = analytics.prescriptive(ctx, gateway=ModelGateway(env={}))
            self.assertIn('Period record coverage differs' if language=='en' else 'تختلف تغطية الفترات',
                          fallback['output']['exec_summary'])
            self.assertIn('Scenario screening only' if language == 'en' else 'مقارنة سيناريوهات فقط',
                          ctx['prescriptive']['headline'])
            self.assertFalse(any(c['type']=='recommendation' for c in results['prescriptive']['claims']))

    def test_partially_stated_inputs_do_not_promote_default_option_to_validated_action(self):
        from tests.test_analytics import linear_dataset
        for assumptions in ({'costs': {'Beta': 1}}, {'uplift': {'Beta': .30}}):
            for language in ('en', 'ar'):
                ctx, _ = run_pipeline(linear_dataset(), language=language, mapping=explicit_grouping())
                ctx['assumptions'] = assumptions
                result = analytics.prescriptive(ctx)
                self.assertFalse(any(c['type']=='recommendation' for c in result['claims']))
                self.assertTrue(result['output']['headline'].startswith(
                    'Scenario screening only' if language=='en' else 'مقارنة سيناريوهات فقط'))
                self.assertNotIn('same 10%', result['output']['report_markdown'])
                self.assertNotIn('**Recommendation:', result['output']['report_markdown'])

    def test_new_coverage_calculations_have_arabic_display_without_changing_evidence(self):
        from server import report_display
        calcs = analytics._incomplete_period_calcs({'period':'2025-12','records':83,'most':167})
        calcs += [{'id':'c_forecast_coverage_min','name':'minimum_period_records','value':83,
                   'method':'minimum count over retained periods'},
                  {'id':'c_forecast_coverage_max','name':'maximum_period_records','value':167,
                   'method':'maximum count over retained periods'}]
        for calc in calcs:
            original = dict(calc)
            name, value, method = report_display.calculation(calc, 'ar')
            self.assertNotIn('الاسم الأصلي', name)
            self.assertNotIn('الطريقة الأصلية', method)
            self.assertEqual(value, calc['value'])
            self.assertEqual(calc, original)

    def test_unknown_counts_preserve_existing_behavior(self):
        prep = {'trend': {'2025-01':100,'2025-02':200,'2025-03':50}}
        labels, values, dropped = analytics._complete_periods(prep)
        self.assertEqual(labels,list(prep['trend']))
        self.assertEqual(values,list(prep['trend'].values()))
        self.assertIsNone(dropped)

    def test_largest_anomaly_cites_its_own_calculation_not_the_first_period(self):
        from tests.test_mapping import SHOP_CSV, SHOP_MAPPING
        _, results = run_pipeline(SHOP_CSV, mapping=SHOP_MAPPING)
        result = results['anomaly']
        claim = next(c for c in result['claims'] if c['id']=='cl_anom')
        calcs = {c['id']:c for c in result['calculations']}
        self.assertIn('c_anom_1',claim['evidence'])
        self.assertTrue(analytics.claim_figures_match(claim,calcs))
        self.assertEqual(results['validator']['status'],'succeeded')

    def test_long_group_labels_keep_builtin_note_grounded_within_existing_bound(self):
        from tests.test_analytics import linear_dataset
        from server.orchestration import built_in_agent_note, grounded
        for width in (45,50,60):
            _, results = run_pipeline(linear_dataset().replace('Alpha','A'*width), mapping=explicit_grouping())
            facts = [c['text'] for c in results['prescriptive']['claims']]
            self.assertIsNotNone(grounded(built_in_agent_note('prescriptive',facts),facts))


class DiagnosticContributionEvidenceTests(unittest.TestCase):
    def test_counter_direction_group_outside_top_five_retains_cited_value(self):
        names = ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta")
        for deltas, expected_index in (((1000, 900, 800, 700, 600, -123), 5),
                                       ((1000, 900, 800, 700, 600, -723), 3)):
            lines = ["month,team,sales"]
            for month in range(6):
                for name, delta in zip(names, deltas):
                    lines.append(f"2025-{month + 1:02d},{name},{2000 + delta * month / 5}")
            for language in ("en", "ar"):
                with self.subTest(index=expected_index, language=language):
                    ctx, results = run_pipeline("\n".join(lines), language=language,
                                                mapping=explicit_grouping())
                    diag = results["diagnostic"]
                    claim = next(c for c in diag["claims"] if c["id"] == "cl_decline")
                    calcs = {c["id"]: c for c in diag["calculations"]}
                    selected = f"c_contrib_{expected_index}"
                    self.assertEqual(claim["evidence"], [selected, "c_totalchange"])
                    self.assertEqual(calcs[selected]["value"], deltas[-1])
                    self.assertTrue(analytics.claim_figures_match(claim, calcs))
                    self.assertEqual(results["validator"]["status"], "succeeded")
                    self.assertEqual(results["reporter"]["status"], "succeeded")
                    contribution_ids = [c["id"] for c in diag["calculations"]
                                        if c["id"].startswith("c_contrib_")]
                    self.assertEqual(len(contribution_ids), 6 if expected_index == 5 else 5)
                    self.assertEqual(len(contribution_ids), len(set(contribution_ids)))
                    tampered = {**calcs, selected: {**calcs[selected], "value": 42}}
                    self.assertFalse(analytics.claim_figures_match(claim, tampered))
