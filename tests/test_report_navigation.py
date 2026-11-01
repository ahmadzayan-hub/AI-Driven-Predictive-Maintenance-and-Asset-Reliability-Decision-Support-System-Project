"""Shared report destinations and bounded summary; no Office/model dependency."""
from io import BytesIO
import copy
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from server.executive_export import render_html, render_docx, render_sections_html, report_sections, Section, STYLE, W
from tests import test_executive_exports as fixtures
from tests.test_executive_exports import HtmlDocument, NS


class ReportNavigationTests(unittest.TestCase):
    def test_contents_follows_present_evidence_and_does_not_promise_analysis(self):
        brief = fixtures.ExecutiveDocumentTests().brief('en')
        brief['models'] = []
        brief['findings'] = []
        sections = report_sections(brief)[1]
        titles = [section.title for section in sections]
        self.assertEqual(titles[:3], ['Executive summary', 'Decision context', 'Decision questions'])
        for before, after in [('Scope and filters', 'Controlled KPIs'),
                              ('Controlled KPIs', 'Review priorities'),
                              ('Review priorities', 'Decision boundaries and unresolved issues')]:
            self.assertLess(titles.index(before), titles.index(after))
        self.assertTrue(all(s.paragraphs or s.after_paragraphs or any(t.rows for t in s.tables) for s in sections))
        # Sections with nothing to report carry no heading; the decision
        # context names them once, with their statement, so absence stays
        # explicit (ADR 2026-10-27-interactive-dashboard).
        self.assertNotIn('Whole-run findings', titles)
        self.assertNotIn('Recorded model evidence and limitations', titles)
        context = sections[1]
        self.assertEqual(context.title, 'Decision context')
        self.assertIn('Left out because there is nothing to report: Whole-run findings (No verified findings are available in this briefing.); '
                      'Recorded model evidence and limitations (No model evaluation is available; predictive performance is not claimed.)',
                      context.paragraphs)
        html = render_html(brief).decode()
        self.assertIn('No model evaluation is available; predictive performance is not claimed.', html)
        self.assertNotIn('Whole-run findings</bdi></h2>', html)
        self.assertNotIn('Recorded model evidence and limitations</bdi></h2>', html)
        self.assertNotIn('Technical appendix and source audit', html)
        for index, section in enumerate(sections):
            self.assertIn(section.title if index == 0 else f'{index}. {section.title}', html)
        self.assertNotIn('<h2><bdi dir="auto">1. Executive summary</bdi></h2>', html)
        self.assertNotIn('Imaginary predictive validation', render_sections_html(
            'Test', [sections[0], Section('Imaginary predictive validation'), sections[1]], 'en').decode())

    def test_sections_with_content_keep_their_statement_and_arabic_names_the_absent_ones(self):
        brief = fixtures.ExecutiveDocumentTests().brief('ar')
        brief['models'] = []
        sections = report_sections(brief)[1]
        titles = [section.title for section in sections]
        self.assertNotIn('أدلة النماذج المسجلة وحدودها', titles)
        self.assertIn('نتائج التشغيل الكامل', titles)
        self.assertTrue(any(p.startswith('أُسقطت الأقسام التالية لعدم وجود ما يُبلَّغ عنه: أدلة النماذج المسجلة وحدودها')
                            for p in sections[1].paragraphs))
        # A section with real content beside a missing part keeps the statement in place.
        english = fixtures.ExecutiveDocumentTests().brief('en')
        english['kpis']['measures'] = []
        english['kpis']['unavailable'] = {'first_time_fix': 'no outcome column'}
        kpis = next(s for s in report_sections(english)[1] if s.title == 'Controlled KPIs')
        self.assertIn('No controlled KPI is computable for this scope.', kpis.paragraphs)
        self.assertTrue(kpis.tables[-1].rows)

    def test_every_html_contents_link_has_one_destination_and_no_self_entry(self):
        for language in ('en', 'ar'):
            brief = fixtures.ExecutiveDocumentTests().brief(language)
            parsed = HtmlDocument(render_html(brief).decode())
            ids = [attrs['id'] for _, attrs in parsed.tags if 'id' in attrs]
            self.assertEqual(len(ids), len(set(ids)))
            links = [attrs['href'] for tag, attrs in parsed.tags if tag == 'a']
            self.assertTrue(links)
            self.assertTrue(all(link.startswith('#') and ids.count(link[1:]) == 1 for link in links))
            self.assertEqual(len([link for link in links if link.startswith('#section-')]), len(report_sections(brief)[1]))
            self.assertEqual(render_html(brief).decode().count('id="contents"'), 1)

    def test_word_bookmarks_page_fields_and_headings_agree_without_fake_pages(self):
        for language in ('en', 'ar'):
            brief = fixtures.ExecutiveDocumentTests().brief(language)
            with ZipFile(BytesIO(render_docx(brief))) as archive:
                root = ET.fromstring(archive.read('word/document.xml'))
                starts = root.findall('.//w:bookmarkStart', NS)
                ends = root.findall('.//w:bookmarkEnd', NS)
                names = [item.get(f'{{{W}}}name') for item in starts]
                self.assertEqual(len(names), len(set(names)))
                self.assertEqual({x.get(f'{{{W}}}id') for x in starts}, {x.get(f'{{{W}}}id') for x in ends})
                self.assertEqual(len(names), len(report_sections(brief)[1]) + 2 + len(root.findall('.//w:tbl', NS)))
                for link in root.findall('.//w:hyperlink', NS):
                    self.assertIn(link.get(f'{{{W}}}anchor'), names)
                for field in root.findall('.//w:fldSimple', NS):
                    self.assertIn(field.get(f'{{{W}}}instr').split()[1], names)
                    self.assertEqual(field.get(f'{{{W}}}dirty'), 'true')
                    self.assertFalse(any(c.isdigit() for c in ''.join(field.itertext())))
                self.assertEqual(len(root.findall('.//w:fldSimple', NS)), len(names))
                settings = ET.fromstring(archive.read('word/settings.xml'))
                self.assertEqual(settings.find('w:updateFields', NS).get(f'{{{W}}}val'), 'true')
                styles = ET.fromstring(archive.read('word/styles.xml'))
                self.assertIsNone(styles.find("w:style[@w:styleId='ContentsTitle']/w:pPr/w:outlineLvl", NS))

    def test_frontmatter_indexes_real_captions_and_summary_is_unnumbered(self):
        for language in ('en', 'ar'):
            brief = fixtures.ExecutiveDocumentTests().brief(language)
            html = render_html(brief).decode()
            parsed = HtmlDocument(html)
            links = [attrs['href'] for tag, attrs in parsed.tags if tag == 'a']
            # The summary's back-link is outside the contents. The TOC starts with LOT/LOF.
            self.assertEqual(links[1:4], ['#list-of-tables', '#list-of-figures', '#section-0'])
            captions = [attrs['id'] for tag, attrs in parsed.tags if tag == 'table']
            self.assertEqual([x[1:] for x in links if x.startswith('#table-')], captions)
            self.assertEqual(html.count('<caption>'), len(captions))
            with ZipFile(BytesIO(render_docx(brief))) as archive:
                root = ET.fromstring(archive.read('word/document.xml'))
                links = root.findall('.//w:hyperlink', NS)
                self.assertEqual([x.get(f'{{{W}}}anchor') for x in links[:3]],
                                 ['list_of_tables', 'list_of_figures', 'section_0'])
                headings = [p for p in root.findall('w:body/w:p', NS)
                            if p.find("w:pPr/w:pStyle[@w:val='Heading1']", NS) is not None]
                self.assertEqual(''.join(headings[0].itertext()), report_sections(brief)[1][0].title)
                self.assertIn('1. ' + report_sections(brief)[1][1].title, [''.join(p.itertext()) for p in headings])
            self.assertIn('لا توجد أشكال' if language == 'ar' else 'No figures are included', html)

    def test_long_scope_and_limitations_do_not_grow_or_clip_front_page(self):
        brief = fixtures.ExecutiveDocumentTests().brief()
        brief['run']['dataset_name'] = 'Long source name ' * 100
        brief['readiness']['limitations'] = ['Caution ' * 200] * 25
        original = copy.deepcopy(brief)
        sections = report_sections(brief)[1]
        front = sections[0]
        self.assertTrue(front.compact)
        self.assertLess(sum(len(p) for p in front.paragraphs + front.after_paragraphs), 1000)
        html = render_html(brief).decode()
        self.assertIn(brief['readiness']['limitations'][0], html)
        self.assertNotIn('overflow: hidden', STYLE)
        self.assertNotIn('word-break: break-word', STYLE)
        self.assertIn('widows: 3', STYLE)
        self.assertEqual(brief, original)

    def test_tables_keep_repeat_headers_no_row_splits_and_readable_type(self):
        with ZipFile(BytesIO(render_docx(fixtures.ExecutiveDocumentTests().brief('ar')))) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            for row in root.findall('.//w:tr', NS):
                self.assertIsNotNone(row.find('w:trPr/w:cantSplit', NS))
            for table in root.findall('.//w:tbl', NS):
                self.assertIsNotNone(table.find('w:tr/w:trPr/w:tblHeader', NS))
            styles = ET.fromstring(archive.read('word/styles.xml'))
            self.assertTrue(all(int(size.get(f'{{{W}}}val')) >= 22 for size in styles.findall('.//w:sz', NS)))


if __name__ == '__main__':
    unittest.main()
