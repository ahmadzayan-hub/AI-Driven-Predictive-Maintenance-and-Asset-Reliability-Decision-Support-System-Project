"""The brief and its documents carry the page's two-way matrix (ADR 2026-11-06-two-way-matrix).

Synthetic survey lines only."""
import unittest

from server import query
from server.executive import ExecutiveDashboardAgent
from server.executive_export import render_docx, render_html
from tests.test_executive_exports import HtmlDocument, docx_document, docx_tables

COLUMNS = ["Line_ID", "Station", "Criticality", "Condition_Score"]


def survey():
    rows = [{"Line_ID": f"L{i}", "Station": f"ST{i % 6:02d}", "Criticality": ["High", "Medium", "Low"][(i // 6) % 3],
             "Condition_Score": 5.0 + i % 4} for i in range(72)]
    return query.table_from(COLUMNS, {"Condition_Score"}, rows, {"Condition_Score": "analysed"})


def run():
    return {"id": "run-x", "dataset_name": "survey.csv", "state": "succeeded", "updated_at": "2026-11-06T10:00:00Z"}


class CrossTabTests(unittest.TestCase):

    def brief(self, filters=None, language="en", table=None):
        return ExecutiveDashboardAgent().brief(table or survey(), run(), [], filters or [], language)

    def test_cells_count_the_scope_and_are_cited(self):
        cross = self.brief()["crosstab"]
        self.assertEqual({cross["rows"], cross["columns"]}, {"Station", "Criticality"})
        self.assertEqual(cross["records"], 72)
        self.assertEqual(sum(map(sum, cross["cells"])), 72)
        self.assertLessEqual(len(cross["column_values"]), 8)
        evidence = {e["id"]: e for e in self.brief()["evidence"]}
        self.assertEqual(evidence[cross["evidence_ref"]]["value"], 72)

    def test_a_filter_narrows_the_counts_not_the_columns(self):
        whole = self.brief()["crosstab"]
        north = self.brief([{"column": "Station", "op": "in", "values": ["ST01"]}])["crosstab"]
        self.assertEqual((north["rows"], north["columns"]), (whole["rows"], whole["columns"]))
        self.assertEqual(north["records"], 12)

    def test_no_informative_pair_no_matrix(self):
        rows = [{"Line_ID": f"L{i}", "Station": f"ST{i % 6:02d}", "Criticality": ["High", "Low"][i % 6 // 3],
                 "Condition_Score": 5.0} for i in range(36)]   # each station has one criticality
        self.assertIsNone(self.brief(table=query.table_from(COLUMNS, {"Condition_Score"}, rows))["crosstab"])

    def test_both_documents_show_every_cell_in_both_languages(self):
        for language in ("en", "ar"):
            brief = self.brief(language=language)
            cross = brief["crosstab"]
            expected = [[cross["rows"], *cross["column_values"]]] + [
                [name, *map(str, counts)] for name, counts in zip(cross["row_values"], cross["cells"])]
            html = HtmlDocument(render_html(brief).decode("utf-8")).tables
            word = docx_tables(docx_document(render_docx(brief)))
            for tables in (html, word):
                self.assertIn(expected, tables, language)


if __name__ == "__main__":
    unittest.main()
