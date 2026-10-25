"""Business files preserve scoped evidence, identity and snapshot boundaries."""

import copy
from html.parser import HTMLParser
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from server.executive import ExecutiveDashboardAgent, MAX_FILTER_CHARS
from server.executive_export import (render_html, render_docx, attachment_name, W,
                                     CONTENT_POLICY, DOCX_MIME)
from tests import test_executive as fixtures


NS = {"w": W}
FILTERS = [{"column": "Site", "op": "in", "values": ["North"]}]
STAMP = "2026-10-19T17:00:00+00:00"


class HtmlDocument(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.tags, self.text, self.tables = [], [], []
        self.row = self.cell = None
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append("\n")

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"}:
            self.row.append("".join(self.cell))
            self.cell = None
        elif tag == "tr":
            self.tables[-1].append(self.row)
            self.row = None


def docx_document(content):
    with ZipFile(BytesIO(content)) as archive:
        return ET.fromstring(archive.read("word/document.xml"))


def docx_tables(root):
    return [[["".join(cell.itertext()) for cell in row.findall("w:tc", NS)]
             for row in table.findall("w:tr", NS)]
            for table in root.findall(".//w:tbl", NS)]


def property_table(tables, key, value):
    return next(dict(row for row in table if len(row) == 2)
                for table in tables if [key, value] in table)


class ExecutiveDocumentTests(unittest.TestCase):
    def brief(self, language="en"):
        run = fixtures.run()
        run["updated_at"] = STAMP
        return ExecutiveDashboardAgent().brief(fixtures.table(), run,
            [fixtures.stage(models=[{"kind": "maintenance_risk", "target": "synthetic target",
                "fitted": False, "details": {"verdict": "not_supported", "reason": "Not enough dated evidence",
                "decision": "Qualified engineering review", "raw_rows": ["NEVER_EXPORT_THIS_ROW"]}}])],
            FILTERS, language)

    def test_html_and_docx_preserve_kpi_arithmetic_coverage_and_every_evidence_reference(self):
        brief = self.brief()
        original = copy.deepcopy(brief)
        html = HtmlDocument(render_html(brief).decode("utf-8"))
        word = docx_document(render_docx(brief))
        text = "".join(word.itertext())
        for tables in (html.tables, docx_tables(word)):
            kpi = property_table(tables, "Evidence ID", "executive.kpi.first_time_fix")
            self.assertEqual(kpi["Numerator"], "14")
            self.assertEqual(kpi["Denominator"], "20")
            self.assertEqual(kpi["Population"], "all records")
            self.assertEqual(kpi["Measured records"], "2")
            self.assertEqual(kpi["Excluded records"], "0")
            self.assertEqual(kpi["Unmeasured records"], "0")
            missing = property_table(tables, "Evidence ID", "executive.kpi.downtime_per_record")
            self.assertEqual(missing["Unmeasured records"], "1")
            self.assertEqual(missing["Measured records"], "1")
            self.assertEqual(property_table(tables, "Selected records", "2")["Total records"], "3")
        html_text = "".join(html.text)
        for item in brief["evidence"]:
            for content in (html_text, text):
                self.assertIn(item["id"], content)
                self.assertIn(item["method"], content)
        for content in (html_text, text):
            self.assertIn(STAMP, content)
            self.assertIn("Not fitted / unsupported", content)
            self.assertIn("not establish future failure", content)
            self.assertNotIn("PRIVATE_ROW_", content)
            self.assertNotIn("NEVER_EXPORT_THIS_ROW", content)
        self.assertEqual(brief, original)

    def test_html_escapes_untrusted_text_and_has_no_active_or_external_content(self):
        brief = self.brief()
        payload = '<script src="https://example.invalid/leak">alert(1)</script>&'
        brief["run"]["dataset_name"] = payload
        brief["headline"] = payload
        brief["evidence"][0]["method"] = payload
        content = render_html(brief).decode("utf-8")
        parsed = HtmlDocument(content)
        self.assertIn(payload, "".join(parsed.text))
        self.assertNotIn("<script", content)
        self.assertFalse(any(tag in {"script", "iframe", "img", "object", "link"} for tag, _ in parsed.tags))
        self.assertTrue(any(tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"
                            and "default-src 'none'" in attrs["content"] for tag, attrs in parsed.tags))
        word = docx_document(render_docx(brief))
        self.assertIn(payload, "".join(word.itertext()))
        # Navigation is internal only; untrusted prose cannot create links.
        links = word.findall(".//w:hyperlink", NS)
        self.assertTrue(links)
        bookmarks = {x.get(f"{{{W}}}name") for x in word.findall('.//w:bookmarkStart', NS)}
        self.assertTrue(all(link.get(f"{{{W}}}anchor") in bookmarks for link in links))

    def test_docx_is_deterministic_real_ooxml_with_internal_relationships_and_print_layout(self):
        brief = self.brief()
        output = render_docx(brief)
        self.assertTrue(output.startswith(b"PK\x03\x04"))
        self.assertEqual(output, render_docx(brief))
        with ZipFile(BytesIO(output)) as archive:
            self.assertIn("[Content_Types].xml", archive.namelist())
            self.assertIn("word/styles.xml", archive.namelist())
            self.assertFalse(any("macro" in name.lower() or "vba" in name.lower() for name in archive.namelist()))
            for name in archive.namelist():
                if name == "word/fonts/Dubai-Regular.odttf":
                    from server.report_fonts import obfuscate_font, FONT_SHA256
                    from hashlib import sha256
                    self.assertEqual(sha256(obfuscate_font(archive.read(name))).hexdigest(), FONT_SHA256)
                    continue
                root = ET.fromstring(archive.read(name))
                if name.endswith(".rels"):
                    self.assertFalse(any(item.get("TargetMode") == "External" for item in root))
        root = docx_document(output)
        size = root.find(".//w:pgSz", NS)
        self.assertEqual((size.get(f"{{{W}}}w"), size.get(f"{{{W}}}h")), ("12240", "15840"))
        for table in root.findall(".//w:tbl", NS):
            self.assertIsNotNone(table.find("w:tr/w:trPr/w:tblHeader", NS))
            self.assertEqual(sum(int(c.get(f"{{{W}}}w")) for c in table.findall("w:tblGrid/w:gridCol", NS)), 9360)

    def test_arabic_uses_rtl_paragraphs_runs_and_tables_while_identifiers_remain_ltr(self):
        brief = self.brief("ar")
        parsed = HtmlDocument(render_html(brief).decode("utf-8"))
        self.assertIn(("html", {"lang": "ar", "dir": "rtl"}), parsed.tags)
        self.assertIn("ملحق الأدلة", "".join(parsed.text))
        root = docx_document(render_docx(brief))
        self.assertTrue(root.findall(".//w:pPr/w:bidi", NS))
        # Every paragraph is explicit, so office-profile defaults cannot alter
        # it. Technical cells follow their text; Arabic document prose stays RTL.
        for paragraph in root.findall(".//w:p", NS):
            self.assertIn(paragraph.find("w:pPr/w:bidi", NS).get(f"{{{W}}}val"), {"0", "1"})
            self.assertIn(paragraph.find("w:pPr/w:jc", NS).get(f"{{{W}}}val"), {"start", "end"})
        for paragraph in root.findall("w:body/w:p", NS):
            self.assertEqual(paragraph.find("w:pPr/w:bidi", NS).get(f"{{{W}}}val"), "1")
            self.assertEqual(paragraph.find("w:pPr/w:jc", NS).get(f"{{{W}}}val"), "start")
        measure = next(item for item in brief["kpis"]["measures"] if item["key"] == "first_time_fix")
        for value in ("executive.kpi.first_time_fix", measure["formula"], STAMP):
            paragraph = next(item for item in root.findall(".//w:tc/w:p", NS) if "".join(item.itertext()) == value)
            self.assertEqual(paragraph.find("w:pPr/w:bidi", NS).get(f"{{{W}}}val"), "0")
            self.assertEqual(paragraph.find("w:pPr/w:jc", NS).get(f"{{{W}}}val"), "start")
        for value in ("14", "20"):
            paragraph = next(item for item in root.findall(".//w:tc/w:p", NS) if "".join(item.itertext()) == value)
            self.assertEqual(paragraph.find("w:pPr/w:bidi", NS).get(f"{{{W}}}val"), "0")
            self.assertEqual(paragraph.find("w:pPr/w:jc", NS).get(f"{{{W}}}val"), "end")
        self.assertTrue(root.findall(".//w:rPr/w:rtl[@w:val='1']", NS))
        self.assertTrue(root.findall(".//w:rPr/w:rtl[@w:val='0']", NS))
        self.assertEqual(len(root.findall(".//w:tbl", NS)), len(root.findall(".//w:tblPr/w:bidiVisual", NS)))
        self.assertTrue(all(node.get(f"{{{W}}}val") == "1" for node in root.findall(".//w:tblPr/w:bidiVisual", NS)))
        self.assertEqual(root.find(".//w:sectPr/w:bidi", NS).get(f"{{{W}}}val"), "1")
        kpi = property_table(docx_tables(root), "معرّف الدليل", "executive.kpi.first_time_fix")
        self.assertEqual(kpi["البسط"], "14")
        self.assertEqual(kpi["المقام"], "20")
        self.assertIn("ملحق الأدلة", "".join(root.itertext()))

    def test_english_explicitly_disables_rtl_instead_of_inheriting_office_profile(self):
        root = docx_document(render_docx(self.brief()))
        for paragraph in root.findall(".//w:p", NS):
            self.assertEqual(paragraph.find("w:pPr/w:bidi", NS).get(f"{{{W}}}val"), "0")
            self.assertEqual(paragraph.find("w:pPr/w:jc", NS).get(f"{{{W}}}val"), "start")
        for run in root.findall(".//w:r", NS):
            self.assertEqual(run.find("w:rPr/w:rtl", NS).get(f"{{{W}}}val"), "0")
        for table in root.findall(".//w:tbl", NS):
            self.assertEqual(table.find("w:tblPr/w:bidiVisual", NS).get(f"{{{W}}}val"), "0")
        self.assertEqual(root.find(".//w:sectPr/w:bidi", NS).get(f"{{{W}}}val"), "0")

    def test_empty_scope_keeps_missing_values_and_does_not_invent_performance(self):
        brief = ExecutiveDashboardAgent().brief(fixtures.table(), fixtures.run(), [],
            [{"column": "Site", "op": "in", "values": ["Unknown"]}])
        for tables in (HtmlDocument(render_html(brief).decode()).tables, docx_tables(docx_document(render_docx(brief)))):
            kpi = property_table(tables, "Evidence ID", "executive.kpi.first_time_fix")
            self.assertEqual(kpi["Value"], "Not available")
            self.assertEqual(kpi["Measured records"], "0")
            self.assertIn("zero", kpi["Undefined value reason"])
        name = attachment_name('../../a"\r\n', "ar", "docx")
        self.assertRegex(name, r"^miyaar-executive-[A-Za-z0-9_-]+-ar\.docx$")

    def test_compact_summary_precedes_audits_and_preserves_values_in_both_formats(self):
        brief = self.brief()
        for tables in (HtmlDocument(render_html(brief).decode()).tables, docx_tables(docx_document(render_docx(brief)))):
            summary = next(table for table in tables if table[0] == ["Measure", "Value", "Scale", "Measured records"])
            self.assertEqual(len(summary) - 1, len(brief["kpis"]["measures"]))
            for measure, row in zip(brief["kpis"]["measures"], summary[1:]):
                audit = property_table(tables, "Evidence ID", "executive.kpi." + measure["key"])
                self.assertEqual(row, [measure["title"], audit["Value"], audit["Scale"], audit["Measured records"]])
            first_audit = next(table for table in tables if ["Evidence ID", "executive.kpi." + brief["kpis"]["measures"][0]["key"]] in table)
            self.assertLess(tables.index(summary), tables.index(first_audit))

    def test_known_codes_have_readable_arabic_labels_and_unknown_codes_remain_exact(self):
        brief = self.brief("ar")
        for tables in (HtmlDocument(render_html(brief).decode()).tables, docx_tables(docx_document(render_docx(brief)))):
            state = property_table(tables, "معرّف التشغيل", "r1")["حالة التشغيل"]
            self.assertIn("بانتظار الاعتماد", state)
            self.assertIn("awaiting_approval", state)
            kpi = property_table(tables, "معرّف الدليل", "executive.kpi.first_time_fix")
            self.assertIn("جميع السجلات", kpi["مجموعة القياس"])
            self.assertIn("all records", kpi["مجموعة القياس"])
            self.assertIn("استبعاد", kpi["سياسة القيم المفقودة"])
            self.assertIn("نسبة مئوية", kpi["مقياس القيمة"])
        brief["run"]["state"] = "custom_operator_state"
        brief["kpis"]["measures"][0].update(scale="custom_unit", population="custom_population", missing_policy="custom_policy")
        for tables in (HtmlDocument(render_html(brief).decode()).tables, docx_tables(docx_document(render_docx(brief)))):
            self.assertEqual(property_table(tables, "معرّف التشغيل", "r1")["حالة التشغيل"], "custom_operator_state")
            kpi = property_table(tables, "معرّف الدليل", "executive.kpi." + brief["kpis"]["measures"][0]["key"])
            self.assertEqual((kpi["مقياس القيمة"], kpi["مجموعة القياس"], kpi["سياسة القيم المفقودة"]),
                             ("custom_unit", "custom_population", "custom_policy"))


@unittest.skipUnless(fixtures.FASTAPI_AVAILABLE, "fastapi is not installed")
class ExecutiveExportApiTests(unittest.TestCase):
    setUp = fixtures.ExecutiveApiTests.setUp
    auth = fixtures.ExecutiveApiTests.auth
    make_run = fixtures.ExecutiveApiTests.make_run

    def export(self, run, format="html", **params):
        if "expected_snapshot_id" not in params:
            prepared = self.client.get(f"/api/runs/{run['id']}/executive", headers=self.auth(),
                params={k: params[k] for k in ("language", "filters") if k in params})
            params["expected_snapshot_id"] = prepared.json()["snapshot_id"] if prepared.status_code == 200 else "0" * 64
        return self.client.get(f"/api/runs/{run['id']}/executive/export", headers=self.auth(),
            params={"format": format, "expected_updated_at": run["updated_at"], **params})

    def test_authorized_filtered_downloads_are_business_files_and_leave_approvals_unchanged(self):
        run = self.make_run()
        store = self.app.state.store
        before = (store.get_run(run["id"]), store.get_tasks(run["id"]), store.approvals_for_run(run["id"]))
        with patch.object(self.app.state.engine.gateway, "narrate", side_effect=AssertionError("No model calls")):
            html = self.export(run, filters=json.dumps(FILTERS))
            word = self.export(run, "docx", filters=json.dumps(FILTERS), language="ar")
        self.assertEqual(html.status_code, 200, html.text)
        self.assertEqual(word.status_code, 200, word.text)
        self.assertTrue(html.headers["content-type"].startswith("text/html"))
        self.assertEqual(word.headers["content-type"], DOCX_MIME)
        self.assertIn("attachment;", html.headers["content-disposition"])
        self.assertIn("-ar.docx", word.headers["content-disposition"])
        for response in (html, word):
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertEqual(response.headers["content-security-policy"], CONTENT_POLICY)
        properties = property_table(HtmlDocument(html.text).tables, "Selected records", "2")
        self.assertEqual(properties["Total records"], "3")
        self.assertTrue(word.content.startswith(b"PK\x03\x04"))
        self.assertEqual(before, (store.get_run(run["id"]), store.get_tasks(run["id"]), store.approvals_for_run(run["id"])))

    def test_timestamp_mismatch_requires_refresh_in_both_languages(self):
        run = self.make_run()
        for language in ("en", "ar"):
            response = self.export(run, language=language, expected_updated_at="stale")
            self.assertEqual(response.status_code, 409, response.text)
            self.assertIn("حدّث" if language == "ar" else "Refresh", response.json()["detail"])
        original = self.app.state.engine.load_table

        def progress(*args):
            loaded = original(*args)
            self.app.state.store.update("runs", run["id"], {"updated_at": STAMP})
            return loaded

        with patch.object(self.app.state.engine, "load_table", side_effect=progress):
            self.assertEqual(self.export(run).status_code, 409)
        refreshed = self.client.get(f"/api/runs/{run['id']}/executive", headers=self.auth()).json()
        response = self.export(run, expected_updated_at=refreshed["run"]["updated_at"])
        self.assertEqual(response.status_code, 200, response.text)

    def test_identity_ownership_readiness_and_required_snapshot_guard(self):
        run = self.make_run(finish=False)
        path = f"/api/runs/{run['id']}/executive/export"
        params = {"expected_updated_at": run["updated_at"], "expected_snapshot_id": "0" * 64, "filters": "invalid"}
        self.assertEqual(self.client.get(path, params=params).status_code, 401)
        self.assertEqual(self.client.get(path, headers=self.auth("mallory"), params=params).status_code, 404)
        self.assertEqual(self.client.get(path, headers=self.auth(), params=params).status_code, 409)
        self.assertEqual(self.client.get("/api/runs/absent/executive/export", headers=self.auth(), params=params).status_code, 404)
        self.assertEqual(self.client.get(path, headers=self.auth()).status_code, 422)

    def test_content_change_without_timestamp_change_rejects_stale_snapshot(self):
        run = self.make_run()
        path = f"/api/runs/{run['id']}/executive"
        prepared = self.client.get(path, headers=self.auth()).json()
        repeated = self.client.get(path, headers=self.auth()).json()
        self.assertEqual(prepared["snapshot_id"], repeated["snapshot_id"])
        self.assertEqual(self.export(run, expected_snapshot_id=prepared["snapshot_id"]).status_code, 200)
        store = self.app.state.store
        task = next(task for task in store.get_tasks(run["id"])
                    if task["role"] == "validator" and task["state"] == "succeeded")
        result = json.loads(task["result_json"])
        result["quality_checks"].append({"name": "synthetic_concurrent_result_change", "passed": False})
        store.update("tasks", task["id"], {"result_json": json.dumps(result)})
        self.assertEqual(store.get_run(run["id"])["updated_at"], prepared["run"]["updated_at"])
        changed = self.client.get(path, headers=self.auth()).json()
        self.assertNotEqual(prepared["snapshot_id"], changed["snapshot_id"])
        self.assertEqual(self.export(run, expected_snapshot_id=prepared["snapshot_id"]).status_code, 409)
        self.assertEqual(self.export(run, expected_snapshot_id=changed["snapshot_id"]).status_code, 200)

    def test_filter_limits_and_format_validation_match_the_brief_boundary(self):
        run = self.make_run()
        cases = ["{}", "x" * (MAX_FILTER_CHARS + 1),
                 json.dumps(FILTERS * 13),
                 json.dumps([{"column": "Site", "op": "in", "values": ["North"] * 201}]),
                 json.dumps([{"column": "absent", "op": "eq", "value": 1}])]
        for filters in cases:
            response = self.export(run, language="ar", filters=filters)
            self.assertEqual(response.status_code, 422, response.text[:200])
        self.assertEqual(self.export(run, "pdf").status_code, 422)
        self.assertEqual(self.export(run, language="fr").status_code, 422)
        self.assertEqual(self.export(run, expected_updated_at="").status_code, 422)
        self.assertEqual(self.export(run, expected_snapshot_id="x" * 64).status_code, 422)
        path = f"/api/runs/{run['id']}/executive/export"
        self.assertEqual(self.client.get(path, headers=self.auth(),
            params={"expected_updated_at": run["updated_at"]}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
