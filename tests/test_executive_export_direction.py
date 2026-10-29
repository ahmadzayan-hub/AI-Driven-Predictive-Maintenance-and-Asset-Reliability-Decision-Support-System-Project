"""Technical values keep their mathematical reading inside bilingual tables."""

from io import BytesIO
from pathlib import Path
import re
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from server.executive_export import PERFORMANCE_COLORS, render_docx


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": W[1:-1]}


def document(language, methods):
    brief = {
        "language": language,
        "run": {"id": "fictional-direction-qa", "dataset_name": "FICTIONAL QA",
                "state": "completed", "updated_at": "2026-10-20T00:00:00Z"},
        "scope": {"records": 0, "total_records": 0, "filters": []},
        "headline": "اختبار اتجاه النص" if language == "ar" else "Text direction verification",
        "readiness": {"status": "empty", "limitations": []},
        "kpis": {"measures": [], "unavailable": {}},
        "priorities": [], "questions": [], "findings": [], "models": [],
        "evidence": [{"id": f"qa.{index}", "label": "Direction QA", "value": 0,
                      "method": method, "scope": "whole_run"}
                     for index, method in enumerate(methods)],
    }
    with ZipFile(BytesIO(render_docx(brief))) as archive:
        return ET.fromstring(archive.read("word/document.xml"))


def text(paragraph):
    return "".join(paragraph.itertext())


def paragraph_with(root, value):
    return next(p for p in root.findall(".//w:p", NS) if text(p) == value)


class ExecutiveExportDirectionTests(unittest.TestCase):
    def test_numeric_signs_percent_and_ranges_stay_ltr_with_document_alignment(self):
        methods = ["-12.5", "-12.5%", "−12.5", "−12.5%", "-12.5 – -2.5",
                   "(-12.5)", "+12.5", "0", "95.5", "12.5%"]
        for language in ("en", "ar"):
            root = document(language, methods)
            for method in methods:
                with self.subTest(language=language, method=method):
                    paragraph = paragraph_with(root, method)
                    self.assertEqual(paragraph.find("w:pPr/w:bidi", NS).get(W + "val"), "0")
                    self.assertEqual(paragraph.find("w:pPr/w:jc", NS).get(W + "val"),
                                     "end" if language == "ar" else "start")
                    runs = paragraph.findall("w:r", NS)
                    self.assertEqual(len(runs), 1)
                    self.assertEqual(runs[0].find("w:rPr/w:rtl", NS).get(W + "val"), "0")
                    self.assertEqual(text(runs[0]), method)

    def test_negative_scientific_values_keep_sign_and_exponent_in_one_ltr_run(self):
        methods = ["-1.25e-3", "−1.25E−3", "-1.25e-3 – -2.5e-4"]
        root = document("ar", methods)
        for method in methods:
            with self.subTest(method=method):
                paragraph = paragraph_with(root, method)
                self.assertEqual(paragraph.find("w:pPr/w:bidi", NS).get(W + "val"), "0")
                self.assertEqual(paragraph.find("w:pPr/w:jc", NS).get(W + "val"), "start")
                runs = paragraph.findall("w:r", NS)
                self.assertEqual(len(runs), 1)
                self.assertEqual(runs[0].find("w:rPr/w:rtl", NS).get(W + "val"), "0")
                self.assertEqual(text(runs[0]), method)

    def test_latin_formulas_stay_one_ltr_run_inside_arabic_tables(self):
        methods = [
            "(model - baseline) / baseline on the same held-out records",
            "(last period - first period) / first period",
            "1 − (unexplained variation / total variation) for the fitted line",
            "2·(1.96+0.84)²·variance/(0.10·mean)² — two-sided 5%, 80% power",
        ]
        root = document("ar", methods)
        for method in methods:
            with self.subTest(method=method):
                paragraph = paragraph_with(root, method)
                self.assertEqual(paragraph.find("w:pPr/w:bidi", NS).get(W + "val"), "0")
                runs = paragraph.findall("w:r", NS)
                self.assertEqual(len(runs), 1)
                self.assertEqual(runs[0].find("w:rPr/w:rtl", NS).get(W + "val"), "0")
                self.assertEqual(text(runs[0]), method)

    def test_arabic_titles_labels_and_table_order_remain_explicitly_rtl(self):
        method = "(95.5) الجاهزية مقارنة بالهدف Availability_Pct"
        root = document("ar", [method])
        # Section numbers follow the sections actually present (empty ones are
        # left out), so the heading is found by its title, not its number.
        heading = next(p for p in root.findall(".//w:p", NS) if text(p).endswith("مصدر البيانات وتتبع اللقطة"))
        self.assertEqual(heading.find("w:pPr/w:bidi", NS).get(W + "val"), "1")
        for value in ("معيار | Miyaar", "الطريقة", method):
            with self.subTest(value=value):
                self.assertEqual(paragraph_with(root, value).find("w:pPr/w:bidi", NS).get(W + "val"), "1")
        self.assertTrue(all(table.find("w:tblPr/w:bidiVisual", NS).get(W + "val") == "1"
                            for table in root.findall(".//w:tbl", NS)))
        self.assertEqual(root.find("w:body/w:sectPr/w:bidi", NS).get(W + "val"), "1")
        for value in ("95.5", "0", "2026-10-20T00:00:00Z"):
            self.assertIn(value, text(root))

    def test_latin_first_mixed_method_keeps_operators_and_arabic_values(self):
        method = "model: weak; meets_floor: لا; baseline: 0.5"
        root = document("ar", [method])
        paragraph = paragraph_with(root, method)
        self.assertEqual(paragraph.find("w:pPr/w:bidi", NS).get(W + "val"), "0")
        self.assertEqual(len(paragraph.findall("w:r", NS)), 1)
        self.assertEqual(text(paragraph), method)

    def test_arabic_cell_values_can_be_rtl_in_an_english_document(self):
        method = "القياس الفعلي قبل التقريب 95.5"
        root = document("en", [method])
        self.assertEqual(paragraph_with(root, method).find("w:pPr/w:bidi", NS).get(W + "val"), "1")
        self.assertEqual(paragraph_with(root, "معيار | Miyaar").find("w:pPr/w:bidi", NS).get(W + "val"), "0")
        self.assertTrue(all(table.find("w:tblPr/w:bidiVisual", NS).get(W + "val") == "0"
                            for table in root.findall(".//w:tbl", NS)))
        self.assertEqual(root.find("w:body/w:sectPr/w:bidi", NS).get(W + "val"), "0")


class ExportSemanticPaletteTests(unittest.TestCase):
    def test_assessed_document_colors_match_the_actual_frontend_light_tokens(self):
        path = Path(__file__).resolve().parents[1] / "frontend/src/shared/styles/tokens.css"
        light = path.read_text(encoding="utf-8").split("[data-theme='dark']", 1)[0]
        for status, token in {"good": "success", "okay": "metric-okay", "bad": "danger"}.items():
            with self.subTest(status=status):
                color = re.search(r"--" + re.escape(token) + r":\s*#([0-9a-fA-F]{6})\s*;", light)
                self.assertIsNotNone(color, f"Missing light token {token}")
                self.assertEqual(PERFORMANCE_COLORS[status].upper(), color.group(1).upper())


if __name__ == "__main__":
    unittest.main()
