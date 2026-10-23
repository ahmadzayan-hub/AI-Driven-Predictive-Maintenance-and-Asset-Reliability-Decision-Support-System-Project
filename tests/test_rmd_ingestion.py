"""Synthetic evidence packages only; no operational source documents."""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from server import rmd_ingestion as ingestion


def package(parts):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return out.getvalue()


def workbook(sheet_xml=None):
    worksheet = sheet_xml or '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
      <dimension ref="A1:J7"/><cols><col min="3" max="3" hidden="1"/></cols>
      <sheetData>
        <row r="1"><c r="A1" t="inlineStr"><is><t>Synthetic operational extract</t></is></c></row>
        <row r="3">
          <c r="A3" t="inlineStr"><is><t>SR</t></is></c>
          <c r="B3" t="inlineStr"><is><t>WO</t></is></c>
          <c r="C3" t="inlineStr"><is><t>WO Status</t></is></c>
          <c r="D3" t="inlineStr"><is><t>Work Group</t></is></c>
          <c r="E3" t="inlineStr"><is><t>Work Group</t></is></c>
          <c r="F3" t="inlineStr"><is><t>Event Date</t></is></c>
          <c r="G3" t="inlineStr"><is><t>Result</t></is></c>
          <c r="H3" t="inlineStr"><is><t>Note</t></is></c>
          <c r="I3" t="inlineStr"><is><t>Indicator</t></is></c>
          <c r="J3" t="inlineStr"><is><t>Error</t></is></c>
        </row>
        <row r="4">
          <c r="A4" t="inlineStr"><is><t>SR-0007</t></is></c>
          <c r="B4" t="inlineStr"><is><t>WO-001</t></is></c>
          <c r="C4" t="inlineStr"><is><t>CLOSE</t></is></c>
          <c r="D4" t="inlineStr"><is><t>Group alpha</t></is></c>
          <c r="E4" t="inlineStr"><is><t>Group beta</t></is></c>
          <c r="F4" s="1"><v>45000</v></c>
          <c r="G4"><f>SUM(1,2)</f><v>3</v></c>
          <c r="H4" t="inlineStr"><is><t>NA</t></is></c>
          <c r="I4" t="inlineStr"><is><t>TBD</t></is></c>
          <c r="J4" t="e"><v>#N/A</v></c>
        </row>
        <row r="5" hidden="1">
          <c r="A5" t="inlineStr"><is><t>SR-0007</t></is></c>
          <c r="B5" t="inlineStr"><is><t>WO-002</t></is></c>
          <c r="C5"/><c r="F5" t="inlineStr"><is><t>03/04/2024</t></is></c>
          <c r="G5"><f t="shared" si="0"/></c>
        </row>
        <row r="7"><c r="A7" t="inlineStr"><is><t>SR-0008</t></is></c>
          <c r="B7" t="inlineStr"><is><t>WO-003</t></is></c>
          <c r="C7" t="inlineStr"><is><t>COMP</t></is></c>
          <c r="H7" t="inlineStr"><is><t>EMPTY</t></is></c></row>
      </sheetData><autoFilter ref="A3:J5"/><mergeCells count="1"><mergeCell ref="A1:D1"/></mergeCells>
    </worksheet>'''
    return package({
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><workbookPr date1904="0"/><sheets><sheet name="Working sheet" sheetId="1" r:id="s1"/><sheet name="Summary" sheetId="2" state="hidden" r:id="s2"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="s1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/one.xml"/><Relationship Id="s2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/two.xml"/><Relationship Id="style" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml": '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>',
        "xl/worksheets/one.xml": worksheet,
        "xl/worksheets/two.xml": '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Metric</t></is></c><c r="B1" t="inlineStr"><is><t>Value</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Source rows</t></is></c><c r="B2"><v>3</v></c></row></sheetData></worksheet>',
    })


def document(with_media=True):
    body = '''<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Purpose</w:t></w:r></w:p>
      <w:p><w:r><w:t>Review the supplied synthetic operational evidence.</w:t></w:r></w:p>
      <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Scope</w:t></w:r></w:p>
      <w:p><w:r><w:t>This reference applies to the fictional test network only.</w:t></w:r></w:p>
      <w:p><w:r><w:t>Document code SYN-001-GEN; Revision Rev00.</w:t></w:r></w:p>
      <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Change history</w:t></w:r></w:p>
      <w:p><w:r><w:t>11Jan2099 — source entry retained without correction.</w:t></w:r></w:p>
      <w:p><w:r><w:t>The review manager shall retain the evidence within five working days. Refer to the separate operations manual.</w:t></w:r></w:p>
      <w:tbl><w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>Recorded approval</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:tcPr><w:vMerge w:val="restart"/></w:tcPr><w:p><w:r><w:t>Test role</w:t></w:r></w:p></w:tc>
          <w:tc><w:p><w:r><w:t>Signature not independently verified</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'''
    if with_media:
        body += '<w:p><w:r><w:drawing><a:graphic/></w:drawing></w:r></w:p>'
    parts = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><w:body>' + body + '<w:sectPr/></w:body></w:document>',
        "word/header1.xml": '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Supplied reference copy — synthetic header</w:t></w:r></w:p></w:hdr>',
    }
    if with_media:
        parts["word/media/schematic.png"] = b"synthetic-image-placeholder-not-a-real-procedure"
        parts["word/diagrams/data1.xml"] = '<drawing xmlns="urn:synthetic">Uninterpreted synthetic flowchart</drawing>'
    return package(parts)


class WorkbookEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.result = ingestion.ingest_source("synthetic-evidence.xlsx", workbook(), "workbook")
        self.metadata = self.result["metadata"]
        self.sheet = self.metadata["sheets"][0]

    def test_all_sheets_and_physical_rows_are_preserved(self):
        self.assertEqual([s["name"] for s in self.metadata["sheets"]], ["Working sheet", "Summary"])
        self.assertEqual(self.metadata["sheets"][1]["visibility"], "hidden")
        self.assertEqual(self.metadata["sheets"][1]["suggested_role"], "summary")
        self.assertEqual([r["source_row"] for r in self.sheet["rows"]], [1, 3, 4, 5, 7])
        self.assertEqual(self.sheet["data_row_count_proposed"], 3)
        self.assertEqual(self.sheet["header_row_proposed"], 3)
        self.assertEqual(self.sheet["mapping_status"], "requires_confirmation")

    def test_duplicate_column_names_never_overwrite_source_columns(self):
        columns = self.sheet["columns"]
        self.assertEqual(columns[3]["label"], columns[4]["label"])
        self.assertEqual((columns[3]["id"], columns[4]["id"]), ("D", "E"))
        row = self.sheet["rows"][2]["cells"]
        self.assertEqual(row["D"]["value"], "Group alpha")
        self.assertEqual(row["D"]["raw_value"], "Group alpha")
        self.assertEqual(row["D"]["xml_value"], "")
        self.assertEqual(row["E"]["value"], "Group beta")

    def test_hidden_status_and_rows_past_filter_remain_addressable(self):
        self.assertEqual(self.sheet["hidden_columns"], ["C"])
        self.assertEqual(self.sheet["hidden_rows"], [5])
        self.assertEqual(self.sheet["auto_filter_ref"], "A3:J5")
        self.assertEqual(self.sheet["rows_beyond_filter"], [7])
        cell = self.sheet["rows"][-1]["cells"]["C"]
        self.assertEqual(cell["locator"], "'Working sheet'!C7")
        self.assertEqual(cell["value"], "COMP")
        self.assertTrue(cell["hidden_column"])

    def test_formulas_and_cache_are_retained_without_execution(self):
        cells = self.sheet["rows"][2]["cells"]
        self.assertEqual(cells["G"]["formula"], "=SUM(1,2)")
        self.assertEqual(cells["G"]["cached_value"], "3")
        uncached = self.sheet["rows"][3]["cells"]["G"]
        self.assertEqual(uncached["formula_attributes"]["t"], "shared")
        self.assertFalse(uncached["has_cached_result"])
        self.assertIsNone(uncached["cached_value"])
        self.assertEqual(self.sheet["uncached_formula_count"], 1)
        self.assertFalse(self.metadata["coverage"]["formulas_evaluated"])

    def test_repeated_identifiers_and_field_specific_missing_tokens_are_not_merged(self):
        a, b, c = [r["cells"] for r in self.sheet["rows"][2:]]
        self.assertEqual(a["A"]["value"], b["A"]["value"])
        self.assertNotEqual(a["B"]["value"], b["B"]["value"])
        self.assertEqual(a["H"]["value"], "NA")
        self.assertEqual(a["I"]["value"], "TBD")
        self.assertEqual(c["H"]["value"], "EMPTY")
        self.assertEqual(b["C"]["value"], "")
        self.assertEqual(a["J"]["value"], "#N/A")

    def test_dates_keep_raw_serial_and_ambiguous_source_text(self):
        serial = self.sheet["rows"][2]["cells"]["F"]
        self.assertEqual(serial["raw_value"], "45000")
        self.assertEqual(serial["value"], "2023-03-15")
        self.assertEqual(self.sheet["rows"][3]["cells"]["F"]["value"], "03/04/2024")

    def test_metadata_has_no_binary_artifact_payload(self):
        json.dumps(self.metadata)
        self.assertEqual(self.result["artifacts"], [])
        self.assertEqual(self.metadata["coverage"]["excel_date_system"], "1900")

    def test_repeated_cell_address_is_refused_instead_of_overwritten(self):
        bad = '<worksheet><sheetData><row r="1"><c r="A1"><v>1</v></c><c r="A1"><v>2</v></c></row></sheetData></worksheet>'
        with self.assertRaises(ingestion.IngestionError):
            ingestion.ingest_source("synthetic.xlsx", workbook(bad), "workbook")

    def test_empty_numeric_formula_cache_is_reported_unavailable(self):
        sheet = '<worksheet><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Formula</t></is></c></row><row r="2"><c r="A2"><f>1+2</f><v/></c></row></sheetData></worksheet>'
        result = ingestion.ingest_source("synthetic.xlsx", workbook(sheet), "workbook")
        cells = result["metadata"]["sheets"][0]["rows"][1]["cells"]
        self.assertFalse(cells["A"]["has_cached_result"])
        self.assertIsNone(cells["A"]["cached_value"])
        self.assertEqual(result["metadata"]["sheets"][0]["uncached_formula_count"], 1)


class ProcedureEvidenceTests(unittest.TestCase):
    def test_paragraph_table_and_header_locators_are_stable(self):
        first = ingestion.ingest_source("SYN-001-GEN-11Jan2001.docx", document(), "procedure")
        second = ingestion.ingest_source("SYN-001-GEN-11Jan2001.docx", document(), "procedure")
        doc = first["metadata"]["document"]
        self.assertEqual(doc["clauses"], second["metadata"]["document"]["clauses"])
        self.assertEqual(doc["tables"][0]["rows"][0]["cells"][0]["column_span"], "2")
        self.assertEqual(doc["tables"][0]["rows"][1]["cells"][0]["vertical_merge"], "restart")
        self.assertTrue(any(p["source_part"] == "word/header1.xml" for p in doc["paragraphs"]))
        self.assertTrue(all(c["locator"].startswith("word/") for c in doc["clauses"]))
        self.assertTrue(any(c["kind"] == "table_row" and "Recorded approval" in c["text"] for c in doc["clauses"]))

    def test_tracked_deletion_is_exposed_for_review_not_silently_accepted(self):
        original = document(False)
        with zipfile.ZipFile(io.BytesIO(original)) as source:
            parts = {name: source.read(name) for name in source.namelist()}
        parts["word/document.xml"] = parts["word/document.xml"].replace(
            b"<w:sectPr/>", b'<w:p><w:del><w:r><w:delText>Removed synthetic requirement</w:delText></w:r></w:del></w:p><w:sectPr/>')
        metadata = ingestion.ingest_source("synthetic.docx", package(parts), "procedure")["metadata"]
        deleted = next(c for c in metadata["document"]["clauses"] if "Removed synthetic" in c["text"])
        self.assertTrue(deleted["tracked_changes"]["deleted_text_present"])
        self.assertEqual(deleted["review_status"], "unreviewed")
        self.assertEqual(metadata["coverage"]["tracked_change_paragraphs"], 1)

    def test_digest_preserves_revision_and_identifier_date_conflict_without_deciding_authority(self):
        metadata = ingestion.ingest_source("SYN-001-GEN-11Jan2001.docx", document(), "procedure")["metadata"]
        digest = metadata["document"]["digest"]
        self.assertEqual(digest["current_applicability"]["status"], "unverified")
        self.assertIn("Rev00", [v["text"] for v in digest["revision"]["items"]])
        conflict = next(q for q in digest["questions"] if q["code"] == "identifier_change_history_date_conflict")
        self.assertEqual(conflict["recorded_date"], "11Jan2099")
        self.assertTrue(digest["purpose"]["review_required"])
        self.assertEqual(digest["practical_implications"]["status"], "requires_analyst_review")

    def test_visual_appendices_are_preserved_and_never_declared_verified(self):
        result = ingestion.ingest_source("synthetic.docx", document(), "procedure")
        metadata = result["metadata"]
        coverage = metadata["coverage"]
        self.assertEqual(coverage["embedded_image_parts"], 1)
        self.assertEqual(coverage["diagram_parts"], 1)
        self.assertEqual(coverage["visual_review"], "required")
        self.assertFalse(coverage["complete_document_review"])
        self.assertEqual(coverage["image_ocr"], "not_performed")
        self.assertEqual(result["artifacts"][0]["name"], "word/media/schematic.png")
        self.assertIsInstance(result["artifacts"][0]["data"], bytes)
        self.assertNotIn("data", metadata["artifacts"][0])
        json.dumps(metadata)

    def test_legacy_extension_does_not_turn_html_or_docx_into_binary_word(self):
        for fake in (b"<html><body>not binary Word</body></html>", document(False)):
            with self.subTest(signature=fake[:8]):
                with self.assertRaises(ingestion.IngestionError):
                    ingestion.ingest_source("synthetic.doc", fake, "procedure")

    def test_missing_converter_is_an_explicit_recoverable_error(self):
        with patch.object(ingestion.shutil, "which", return_value=None):
            with self.assertRaises(ingestion.IngestionError) as context:
                ingestion.ingest_source("synthetic.doc", ingestion.OLE_SIGNATURE + b"test", "procedure")
        self.assertEqual(context.exception.status, 503)

    @unittest.skipUnless(shutil.which("soffice") or shutil.which("libreoffice"), "LibreOffice is optional")
    def test_real_legacy_conversion_retains_docx_pdf_and_provenance(self):
        program = shutil.which("soffice") or shutil.which("libreoffice")
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "fixture.docx"
            source.write_bytes(document(False))
            output = base / "binary"
            output.mkdir()
            profile = base / "profile"
            command = [program, "-env:UserInstallation=" + profile.as_uri(), "--headless",
                       "--convert-to", "doc:MS Word 97", "--outdir", str(output), str(source)]
            # A genuine Word binary is produced, never an extension-renamed fixture.
            made = subprocess.run(command, capture_output=True, timeout=60)
            target = output / "fixture.doc"
            self.assertEqual(made.returncode, 0, made.stderr.decode("utf-8", "replace"))
            self.assertTrue(target.is_file(), made.stdout.decode("utf-8", "replace"))
            data = target.read_bytes()
            self.assertTrue(data.startswith(ingestion.OLE_SIGNATURE))
            result = ingestion.ingest_source("synthetic.doc", data, "procedure", converter=program)
        conversion = result["metadata"]["extraction"]["conversion"]
        self.assertTrue(conversion["isolated_profile"])
        self.assertTrue(conversion["macros_disabled"])
        self.assertTrue(conversion["external_link_updates_disabled"])
        self.assertTrue(conversion["version"])
        self.assertEqual({a["name"] for a in result["artifacts"] if a["name"].startswith("converted.")},
                         {"converted.docx", "converted.pdf"})
        self.assertTrue(any(a["data"].startswith(b"%PDF-") for a in result["artifacts"]))
        self.assertIn("Review the supplied synthetic", " ".join(c["text"] for c in result["metadata"]["document"]["clauses"]))


class ExtractionSafetyTests(unittest.TestCase):
    def test_converter_child_does_not_receive_application_credentials(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-secret", "DATABASE_URL": "synthetic-db"}):
            code, out, _ = ingestion._command([sys.executable, "-c",
                "import os; assert 'OPENAI_API_KEY' not in os.environ; assert 'DATABASE_URL' not in os.environ; print('isolated')"], 10)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), b"isolated")

    def test_path_traversal_and_duplicate_parts_are_refused(self):
        bad = package({"../escape.xml": "outside"})
        with self.assertRaises(ingestion.IngestionError):
            ingestion.ingest_source("synthetic.docx", bad, "procedure")
        out = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(out, "w") as z:
                z.writestr("word/document.xml", "<document/>")
                z.writestr("word/document.xml", "<document/>")
        with self.assertRaises(ingestion.IngestionError):
            ingestion.ingest_source("synthetic.docx", out.getvalue(), "procedure")

    def test_entity_declarations_and_expansion_bombs_are_refused(self):
        bad = package({"word/document.xml": '<!DOCTYPE x [<!ENTITY x "payload">]><document>&x;</document>'})
        with self.assertRaises(ingestion.datasets.DatasetError):
            ingestion.ingest_source("synthetic.docx", bad, "procedure")
        bomb = package({"word/document.xml": "<document>" + "x" * 5000 + "</document>"})
        with patch.object(ingestion, "MAX_EXPANDED_BYTES", 1000):
            with self.assertRaises(ingestion.IngestionError):
                ingestion.ingest_source("synthetic.docx", bomb, "procedure")

    def test_workbook_cell_budget_is_global_across_sheets(self):
        # The first sheet fits, but the hidden summary pushes the combined
        # budget over its ceiling. Refuse during parsing, before all allocation.
        result = ingestion.ingest_source("synthetic.xlsx", workbook(), "workbook")
        first_count = result["metadata"]["sheets"][0]["cell_count"]
        with patch.object(ingestion, "MAX_CELLS", first_count + 1):
            with self.assertRaises(ingestion.IngestionError):
                ingestion.ingest_source("synthetic.xlsx", workbook(), "workbook")

    def test_empty_oversized_unknown_kind_and_unsafe_filename_are_refused(self):
        cases = [("synthetic.docx", b"", "procedure"),
                 ("../synthetic.docx", b"x", "procedure"),
                 ("unsafe\nfilename.docx", b"x", "procedure"),
                 ("synthetic.docx", b"x", "unknown"),
                 ("synthetic.xlsx", b"x" * (ingestion.datasets.MAX_UPLOAD_BYTES + 1), "workbook")]
        for name, data, kind in cases:
            with self.subTest(name=name, kind=kind):
                with self.assertRaises(ingestion.datasets.DatasetError):
                    ingestion.ingest_source(name, data, kind)


if __name__ == "__main__":
    unittest.main()
