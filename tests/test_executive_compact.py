"""Presentation selection never becomes a new analytical or approval decision."""
import copy
from io import BytesIO
import unittest
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from server import executive_export as export
from tests import test_executive_exports as fixtures


class CompactExecutiveTests(unittest.TestCase):
    def test_source_order_scope_and_every_warning_survive_without_mutation(self):
        for language in ('ar', 'en'):
            brief = fixtures.ExecutiveDocumentTests().brief(language)
            original = copy.deepcopy(brief)
            title, sections = export.report_sections(brief)
            front = sections[0]
            self.assertEqual(title, 'معيار | Miyaar')
            self.assertEqual([row[0] for row in front.tables[0].rows], [item['title'] for item in brief['advisory']['decisions'][:3]])
            self.assertIn('North', ' '.join(front.paragraphs))
            self.assertNotIn(brief['run']['updated_at'], ' '.join(front.paragraphs))
            self.assertIn('فترة البيانات غير محددة' if language == 'ar' else 'Data period not specified', front.paragraphs)
            self.assertEqual(front.after_title, 'حدود القراءة' if language == 'ar' else 'Reading limits')
            self.assertTrue(all(item in front.after_paragraphs for item in brief['readiness']['limitations']))
            expected = [item['value'] for item in brief['advisory']['domains'] if item['value'] is not None][:3]
            self.assertEqual(len(front.tables[1].rows), len(expected))
            for value, row in zip(expected, front.tables[1].rows):
                self.assertTrue(row[1].startswith(format(value, ".12g")))
            self.assertTrue(sections[1].page_break_before)
            full = ' '.join(str(section) for section in sections[2:])
            for item in brief['evidence']:
                self.assertIn(item['id'], full)
            self.assertEqual(brief, original)
            self.assertEqual(export.render_docx(brief), export.render_docx(brief))

    def test_no_new_financial_prediction_or_assignment_claims_and_appendix_navigation(self):
        brief = fixtures.ExecutiveDocumentTests().brief('en')
        front = export.report_sections(brief)[1][0]
        text = str(front)
        self.assertIn('Proposed role, not assigned', text)
        self.assertIn('no intervention, forecast or savings is approved', text)
        self.assertNotIn('predicted savings', text.lower())
        html = export.render_html(brief).decode()
        self.assertIn('href="#section-1"', html)
        self.assertIn('id="section-1" style="break-before:page"', html)
        with ZipFile(BytesIO(export.render_docx(brief))) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            self.assertIsNotNone(root.find('.//w:pageBreakBefore', {'w': export.W}))
            styles = ET.fromstring(archive.read('word/styles.xml'))
            self.assertIsNotNone(styles.find('.//w:outlineLvl', {'w': export.W}))
