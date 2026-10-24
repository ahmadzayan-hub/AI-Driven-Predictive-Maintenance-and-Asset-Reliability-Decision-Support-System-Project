"""Only existing evidence may populate the reference-informed report contract."""
import copy
import hashlib
import json
import unittest
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from server.executive import ExecutiveDashboardAgent
from server.executive_export import render_docx, render_html
from server.report_contract import model_audit
from tests import test_executive as fixtures


class ReportContractTests(unittest.TestCase):
    def card(self):
        return {'kind': 'maintenance_risk', 'target': 'synthetic future target', 'version': 2,
                'fitted_at': '2026-10-20T10:00:00Z', 'snapshot': 'sha256:synthetic-training-source',
                'training_window': {'first': '2025-01', 'last': '2025-12', 'raw_rows': 'NEVER_COPY_ROWS'},
                'excluded_inputs': {'Failure_Count': 'Defines the outcome, not known before decision'},
                'train_records': 100, 'test_records': 40, 'beats_baseline': False,
                'metric': {'name': 'balanced accuracy', 'model': .52, 'baseline': .5},
                'split': {'kind': 'time', 'first_held_out': '2026-01'},
                'details': {'verdict': 'weak', 'balanced_accuracy_lower_bound': .37,
                            'held_out_records': 40, 'held_out_positives': 8,
                            'train_records_unmeasured': 2, 'test_records_unmeasured': 3,
                            'raw_rows': [{'secret': 'NEVER_COPY_ROWS'}],
                            'probabilities': {'brier': .24, 'baseline_brier': .20,
                                              'base_rate': .2, 'better_than_base_rate': False,
                                              'raw_rows': 'NEVER_COPY_ROWS'}}}

    def brief(self, language='en'):
        return ExecutiveDashboardAgent().brief(fixtures.table(), fixtures.run(),
            [fixtures.stage(models=[self.card()])], [{'column':'Site','op':'in','values':['North']}], language)

    def test_persisted_model_provenance_and_uncertainty_survive_both_formats(self):
        for language in ('ar', 'en'):
            brief = self.brief(language)
            before = copy.deepcopy(brief)
            html = render_html(brief).decode()
            with ZipFile(BytesIO(render_docx(brief))) as archive:
                word = ''.join(ET.fromstring(archive.read('word/document.xml')).itertext())
            for output in (html, word):
                for value in ('2025-01','2025-12','sha256:synthetic-training-source','2026-10-20T10:00:00Z',
                              'Defines the outcome, not known before decision', '0.37', '0.24'):
                    self.assertIn(value, output)
                self.assertNotIn('NEVER_COPY_ROWS', output)
                self.assertIn('ضعيف' if language == 'ar' else 'Weak', output)
            self.assertEqual(before, brief)

    def test_contract_is_unapproved_bound_to_snapshot_and_preserves_scope(self):
        brief = self.brief()
        contract = brief['report_contract']
        self.assertEqual(contract['status'], 'unapproved_evidence_projection')
        self.assertFalse(contract['analytical_claims_added'])
        self.assertEqual(contract['dataset']['records'], 2)
        self.assertIsNone(contract['dataset']['period'])
        self.assertIsNone(contract['dataset']['grain'])
        canonical = {key: value for key, value in brief.items() if key != 'snapshot_id'}
        self.assertEqual(brief['snapshot_id'], hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(',',':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest())
        for decision in contract['decisions']:
            self.assertIsNone(decision['approval'])
            self.assertIsNone(decision['impact_estimate'])
            self.assertIsNone(decision['schedule'])
            self.assertEqual(decision['assignment_status'], 'unassigned')
            self.assertTrue(all(ref.startswith('executive.kpi.') for ref in decision['controlled_kpis']))
            self.assertEqual(decision['evidence_limits'], brief['readiness']['limitations'])
        self.assertTrue(any(d['controlled_kpis'] for d in contract['decisions']))
        self.assertEqual(contract, self.brief()['report_contract'])

    def test_source_provenance_change_invalidates_prepared_snapshot(self):
        old = self.brief()
        changed = self.card()
        changed['training_window']['last'] = '2026-02'
        with patch.object(self, 'card', return_value=changed):
            new = self.brief()
        self.assertNotEqual(old['snapshot_id'], new['snapshot_id'])
        self.assertEqual(old['headline'], new['headline'])

    def test_classification_aggregates_are_bounded_known_schema(self):
        card = self.card()
        card['details'].update(classes=['A', 'B'], hit_rates={'A': .8, 'B': .6},
                               confusion={'A': {'A': 8, 'B': 2, 'raw_rows': ['SECRET']}, 'B': {'A': 4, 'B': 6}})
        card['details']['probabilities']['positive_class'] = 'B'
        card['details']['probabilities']['bins'] = [{'range': [0, .2], 'records': 10, 'mean_predicted': .1, 'observed': .2, 'raw_rows': 'SECRET'}]
        rows = model_audit(card)
        values = {item['label_en']: item['value'] for item in rows}
        self.assertEqual(values['Calibration event (positive class)'], 'B')
        self.assertEqual(values['Class hit rate: A'], .8)
        self.assertEqual(values['Confusion actual A → predicted B'], 2)
        self.assertEqual(values['Calibration bin 1: mean predicted'], .1)
        self.assertNotIn('SECRET', str(rows))

    def test_unsupported_sections_and_incomplete_metadata_are_explicit(self):
        brief = self.brief()
        coverage = {item['section']: item['status'] for item in brief['report_contract']['coverage']}
        self.assertEqual(coverage['financial_scenarios'], 'not_evaluated_in_this_brief')
        self.assertEqual(coverage['implementation_plan'], 'not_recorded')
        self.assertEqual(coverage['ai_participation'], 'expert_review_not_demonstrated_by_this_view')
        rows = model_audit({'details': ['raw'], 'training_window': ['raw'], 'snapshot': {'raw':'SECRET'}})
        self.assertTrue(all(item['value'] is None for item in rows))
        self.assertNotIn('SECRET', str(rows))

    def test_known_schema_is_bounded_and_rejects_numeric_type_confusion(self):
        card = self.card()
        card['details']['balanced_accuracy_lower_bound'] = True
        card['details']['held_out_records'] = -1
        card['details']['probabilities']['positive_class'] = 'X' * 161
        card['excluded_inputs'] = {str(index): 'reason' for index in range(100)}
        card['excluded_inputs']['raw_rows'] = ['SECRET']
        rows = model_audit(card)
        values = {row['label_en']: row['value'] for row in rows}
        self.assertIsNone(values['Mean per-class one-sided 95% Wilson lower bound'])
        self.assertIsNone(values['Held-out records'])
        self.assertIsNone(values['Calibration event (positive class)'])
        self.assertTrue(values['Excluded-input details omitted by export bounds'])
        self.assertLess(len(rows), 55)
        self.assertNotIn('SECRET', str(rows))
