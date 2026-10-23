"""No copyrighted binary fixture: synthetic bytes exercise package contracts."""
import copy
import base64
import re
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from server import executive_export as export, report_fonts as fonts
from tests import test_executive_exports as fixtures


class ReportFontTests(unittest.TestCase):
    def test_missing_and_invalid_font_are_honest_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'font.ttf'
            with patch.object(fonts, 'FONT_PATH', path):
                self.assertFalse(fonts.font_readiness()['dubai_available'])
                path.write_bytes(b'bad font')
                self.assertIsNone(fonts.verified_font())
                self.assertEqual(fonts.font_readiness()['family'], 'Arial')
                self.assertFalse(fonts.font_readiness()['pdf'])

    def test_resource_is_size_and_hash_pinned(self):
        data = b'a' * 139928
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'font.ttf'
            path.write_bytes(data)
            with patch.object(fonts, 'FONT_PATH', path), patch.object(fonts, 'FONT_SHA256', sha256(data).hexdigest()):
                self.assertEqual(fonts.verified_font(), data)
                path.write_bytes(data + b'a')
                self.assertIsNone(fonts.verified_font())

    def test_full_font_roundtrip_and_same_evidence_in_both_languages(self):
        data = bytes(range(256)) * 20
        for language in ('ar', 'en'):
            brief = fixtures.ExecutiveDocumentTests().brief(language)
            original = copy.deepcopy(brief)
            with patch.object(export, 'verified_font', return_value=data):
                html = export.render_html(brief).decode()
                first = export.render_docx(brief)
                self.assertEqual(first, export.render_docx(brief))
            self.assertIn('font-src data:', html)
            self.assertIn('font-family: Dubai', html)
            self.assertEqual(base64.b64decode(re.search(r'data:font/ttf;base64,([A-Za-z0-9+/=]+)', html).group(1)), data)
            with ZipFile(BytesIO(first)) as archive:
                embedded = archive.read('word/fonts/Dubai-Regular.odttf')
                self.assertEqual(fonts.obfuscate_font(embedded), data)
                self.assertEqual(embedded[32:], data[32:])
                root = ET.fromstring(archive.read('word/document.xml'))
                for node in root.findall('.//w:rFonts', {'w': export.W}):
                    self.assertEqual(node.get('{'+export.W+'}cs'), 'Dubai')
                self.assertNotIn(b'TargetMode="External"', archive.read('word/_rels/fontTable.xml.rels'))
                self.assertIn(b'subsetted="0"', archive.read('word/fontTable.xml'))
            self.assertEqual(original, brief)
