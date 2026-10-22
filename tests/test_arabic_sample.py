"""Arabic demo labels are source data, with the same fictional sales figures."""
import csv
import io
import unittest

from server import analytics
from tests.test_report_language import run_pipeline


class ArabicSampleTests(unittest.TestCase):
    def test_sample_labels_are_arabic_and_every_numeric_cell_is_unchanged(self):
        english = list(csv.reader(io.StringIO(analytics.sample_dataset())))
        arabic = list(csv.reader(io.StringIO(analytics.sample_dataset("ar"))))
        self.assertEqual(arabic[0], ["الشهر", "المنطقة", "الفئة", "الإيرادات", "الوحدات"])
        self.assertEqual(len(english), len(arabic))
        for en, ar in zip(english[1:], arabic[1:]):
            self.assertEqual(en[0], ar[0])
            self.assertEqual(en[3:], ar[3:])
            self.assertIn(ar[1], ("الشمال", "الجنوب"))
            self.assertIn(ar[2], ("الأجهزة", "البرمجيات", "الخدمات"))

    def test_arabic_source_keeps_totals_trends_forecasts_and_scenario_values(self):
        english, en = run_pipeline(analytics.sample_dataset(), "en")
        arabic, ar = run_pipeline(analytics.sample_dataset("ar"), "ar")
        self.assertEqual(ar["preparer"]["total"], en["preparer"]["total"])
        self.assertEqual(ar["preparer"]["trend"], en["preparer"]["trend"])
        self.assertEqual(sorted(ar["preparer"]["groups"].values()), sorted(en["preparer"]["groups"].values()))
        self.assertEqual(ar["predictive"]["forecast"], en["predictive"]["forecast"])
        self.assertEqual(ar["preparer"]["date_col"], "الشهر")
        self.assertEqual(ar["preparer"]["measure"], "الإيرادات")
        for stage in ("prescriptive", "sensitivity"):
            self.assertEqual([c["value"] for c in arabic[stage]["calculations"]],
                             [c["value"] for c in english[stage]["calculations"]])
        self.assertTrue(ar["validator"]["passed"])
        for chart in ar["visuals"]["charts"]:
            self.assertNotIn("revenue", chart["title"])
            self.assertNotIn("North", chart["labels"])
        self.assertIn("الشمال", ar["reporter"]["report_markdown"])


if __name__ == "__main__":
    unittest.main()
