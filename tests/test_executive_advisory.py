"""Decision framing preserves scope, evidence, source uncertainty and source rows."""
import copy
import json
import unittest

from server import query
from server.executive import ExecutiveDashboardAgent
from server.executive_export import render_html, render_docx
from tests.test_executive import table, run
from tests.test_executive_exports import docx_document


class AdvisoryTests(unittest.TestCase):
    def test_five_domains_use_scoped_totals_and_never_invent_source_verification(self):
        source = table()
        before = copy.deepcopy(source)
        brief = ExecutiveDashboardAgent().brief(source, run(), filters=[{'column':'Site','op':'eq','value':'North'}])
        domains = {d['id']: d for d in brief['advisory']['domains']}
        self.assertEqual(set(domains), {'condition','failures','work_orders','downtime','economic'})
        self.assertEqual(domains['downtime']['value'], 10)
        self.assertEqual(domains['downtime']['records'], 1)
        self.assertEqual(domains['downtime']['unmeasured'], 1)
        self.assertEqual(domains['economic']['value'], 1000)
        self.assertEqual(domains['condition']['status'], 'unavailable')
        self.assertEqual(domains['downtime']['status'], 'unassessed')
        self.assertTrue(all(s['status']=='unassessed' for s in brief['advisory']['sources']))
        self.assertIn('consult the instructors', brief['advisory']['escalation'])
        self.assertEqual(source, before)
        self.assertNotIn('PRIVATE_ROW_', json.dumps(brief))
        for item in brief['advisory']['domains'] + brief['advisory']['decisions']:
            self.assertTrue(set(item['evidence_refs']) <= {e['id'] for e in brief['evidence']})

    def test_condition_mean_excludes_missing_readings_and_is_not_a_health_verdict(self):
        source = query.Table(['Site','Condition_Score'], {'Condition_Score'}, [['N',80.],['N',None],['S',20.]])
        brief = ExecutiveDashboardAgent().brief(source,run(),filters=[{'column':'Site','op':'eq','value':'N'}])
        condition = brief['advisory']['domains'][0]
        self.assertEqual((condition['value'],condition['records'],condition['unmeasured']), (80.,1,1))
        self.assertEqual(condition['status'],'unassessed')
        ref = next(e for e in brief['evidence'] if e['id']==condition['evidence_refs'][0])
        self.assertEqual(ref['value'],80.)
        self.assertEqual(ref['scope'],'filtered')

    def test_empty_scope_has_no_proposed_interventions_or_zero_totals(self):
        brief = ExecutiveDashboardAgent().brief(table(),run(),filters=[{'column':'Site','op':'eq','value':'absent'}])
        self.assertFalse(brief['advisory']['decisions'])
        self.assertTrue(all(d['value'] is None for d in brief['advisory']['domains']))
        self.assertIn('No decision recommendation',brief['advisory']['recommendation'])

    def test_both_languages_and_document_formats_lead_with_advice_before_audits(self):
        agent=ExecutiveDashboardAgent()
        en=agent.brief(table(),run())
        ar=agent.brief(table(),run(),language='ar')
        self.assertEqual([d['value'] for d in en['advisory']['domains']], [d['value'] for d in ar['advisory']['domains']])
        self.assertNotEqual(en['advisory']['recommendation'],ar['advisory']['recommendation'])
        for brief in (en,ar):
            html=render_html(brief).decode('utf-8')
            word=''.join(docx_document(render_docx(brief)).itertext())
            for content in (html,word):
                self.assertIn(brief['advisory']['title'],content)
                self.assertIn(brief['advisory']['preservation'],content)
                self.assertIn(brief['advisory']['prediction'],content)
                self.assertLess(content.index(brief['advisory']['recommendation']),content.index('executive.kpi.first_time_fix'))


if __name__ == '__main__': unittest.main()
