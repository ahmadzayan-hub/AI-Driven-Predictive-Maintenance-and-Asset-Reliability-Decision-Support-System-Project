"""Private synthetic ingestion → snapshot → evidence → review/export acceptance."""

import asyncio
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from server.auth import Principal
from server.operations import Operations, require_org_access
from server.rmd_schema import RMD_TABLES, erase_org_rmd, erase_owner_rmd, rmd_counts
from server.rmd_service import RmdError, RmdService, uid
from server.storage import open_store
from tests.test_rmd_ingestion import document, workbook


MMS_MAPPING = [
    {"name": "Working sheet", "role": "mms_work_order", "header_row": 3,
     "columns": {"sr_id": "A", "wo_id": "B", "wo_status": "C", "event_date": "F",
                 "location": "D", "category": "E", "symptom": "H"}},
    {"name": "Summary", "role": "summary", "header_row": 1, "columns": {}},
]
RECON_SHEET = '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
<row r="1"><c r="A1" t="inlineStr"><is><t>SR</t></is></c><c r="B1" t="inlineStr"><is><t>Source label</t></is></c><c r="C1" t="inlineStr"><is><t>Event Date</t></is></c><c r="D1" t="inlineStr"><is><t>Junction</t></is></c></row>
<row r="2"><c r="A2" t="inlineStr"><is><t>SR-0007</t></is></c><c r="B2" t="inlineStr"><is><t>Absent from original comparison</t></is></c><c r="C2" t="inlineStr"><is><t>2026-01-06</t></is></c><c r="D2" t="inlineStr"><is><t>=FICTIONAL_JUNCTION()</t></is></c></row>
</sheetData></worksheet>'''
RECON_MAPPING = [
    {"name": "Working sheet", "role": "sr_reconciliation", "header_row": 1,
     "columns": {"sr_id": "A", "source_reconciliation_label": "B", "event_date": "C", "location": "D"}},
    {"name": "Summary", "role": "summary", "header_row": 1, "columns": {}},
]


class RmdServiceTests(unittest.TestCase):
    database_url = None

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "private-evidence.db"
        self.store = open_store(self.database_url, self.db)
        if self.database_url:
            from server.storage import RESTORE_ORDER
            for table in reversed(RESTORE_ORDER):
                self.store._exec(f"DELETE FROM {table}")
        self.addCleanup(lambda: self.store.close())
        self.service = RmdService(self.store, identity_mode="local")
        self.alice = Principal("evidence-alice", "owner", "test")
        self.bob = Principal("evidence-bob", "owner", "test")
        self.admin = Principal("evidence-operator", "admin", "test")
        self.viewer = Principal("evidence-viewer", "viewer", "test")
        self.pack = self.service.create_pack(self.alice, {"title": "Synthetic evidence", "idempotency_key": "pack"})
        self.pid = self.pack["id"]

    def error(self, code, method, *args, **kwargs):
        with self.assertRaises(RmdError) as caught:
            method(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def import_workbooks(self):
        first = self.service.import_source(self.alice, self.pid, "synthetic-operations.xlsx", workbook(), "workbook")
        self.service.save_mapping(self.alice, self.pid, first["id"], {"sheets": deepcopy(MMS_MAPPING)})
        second = self.service.import_source(self.alice, self.pid, "synthetic-reconciliation.xlsx", workbook(RECON_SHEET), "workbook")
        self.service.save_mapping(self.alice, self.pid, second["id"], {"sheets": deepcopy(RECON_MAPPING)})
        return first, second

    def analyse(self, filters=None, key="analysis"):
        return self.service.create_analysis(self.alice, self.pid,
            {"filters": filters or {}, "language": "en", "idempotency_key": key})

    def organization(self, principal, key="org"):
        return Operations(self.store).create_organization(principal, {"name": "Synthetic depot", "idempotency_key": key})

    def member(self, org, subject, role):
        current = require_org_access(self.store, self.alice, org["id"])
        return Operations(self.store).set_member(self.alice, org["id"], {
            "subject": subject, "role": role, "expected_version": current["version"],
            "idempotency_key": f"membership-{subject}-{current['version']}"})

    def test_pack_owner_is_derived_and_admin_cannot_guess_private_pack(self):
        for other in (self.bob, self.admin, self.viewer):
            self.assertEqual(self.error("pack_not_found", self.service.get_pack, other, self.pid).status, 404)
            self.assertEqual(self.service.list_packs(other), {"packs": []})
        self.error("invalid_owner", self.service.create_pack, self.alice,
                   {"title": "Forged", "owner": self.bob.subject})
        self.error("invalid_owner", self.service.create_pack, self.alice,
                   {"title": "Forged", "owner_id": self.bob.subject})

    def test_idempotent_pack_replay_and_payload_conflict(self):
        body = {"title": "Synthetic evidence", "idempotency_key": "pack"}
        self.assertEqual(self.service.create_pack(self.alice, body)["id"], self.pid)
        self.error("idempotency_conflict", self.service.create_pack, self.alice, {**body, "title": "Changed"})
        self.assertEqual(len(self.service.list_packs(self.alice)["packs"]), 1)

    def test_organization_membership_and_platform_permissions_intersect(self):
        org = self.organization(self.alice)
        other_org = self.organization(self.bob)
        body = {"title": "Shared evidence", "organization_id": org["id"]}
        shared = self.service.create_pack(self.alice, body)
        for other in (self.bob, self.admin):
            self.error("pack_not_found", self.service.get_pack, other, shared["id"])
        self.error("organization_not_found", self.service.create_pack, self.alice,
                   {"title": "Wrong organization", "organization_id": other_org["id"]})
        self.member(org, self.viewer.subject, "viewer")
        visible = self.service.get_pack(self.viewer, shared["id"])
        self.assertEqual(visible["permissions"], {"read": True, "write": False, "review": False})
        self.error("permission_denied", self.service.import_source, self.viewer, shared["id"], "x.xlsx", workbook(), "workbook")

    def test_warm_org_access_is_revoked_for_all_evidence_surfaces(self):
        org = self.organization(self.alice)
        shared = self.service.create_pack(self.alice, {"title": "Shared", "organization_id": org["id"]})
        pid = shared["id"]
        source = self.service.import_source(self.alice, pid, "synthetic-procedure.docx", document(), "procedure")
        self.member(org, self.bob.subject, "manager")
        self.assertTrue(self.service.search_knowledge(self.bob, pid, "review")["hits"])
        self.assertTrue(self.service.download_source(self.bob, pid, source["id"])[0])
        self.member(org, self.bob.subject, "removed")
        for method, args in (
            (self.service.get_pack, (pid,)), (self.service.get_source, (pid, source["id"])),
            (self.service.search_knowledge, (pid, "review")),
            (self.service.download_source, (pid, source["id"])),
            (self.service.list_actions, (pid,)), (self.service.list_links, (pid,)),
            (self.service.audit, (pid,))):
            self.assertEqual(self.error("pack_not_found", method, self.bob, *args).status, 404)
        self.assertEqual(self.service.list_packs(self.bob), {"packs": []})

    def test_original_bytes_source_hash_and_private_metadata_are_retained(self):
        data = document()
        source = self.service.import_source(self.alice, self.pid, "synthetic-procedure.docx", data, "procedure")
        repeated = self.service.import_source(self.alice, self.pid, "synthetic-procedure.docx", data, "procedure")
        self.assertEqual(source["id"], repeated["id"])
        self.assertEqual(self.service.download_source(self.alice, self.pid, source["id"])[0], data)
        public = json.dumps(source)
        self.assertNotIn("original_base64", public)
        self.assertNotIn("data_base64", public)
        self.assertNotIn(self.temp.name, public)
        self.assertTrue(source["document"]["digest"])
        self.assertEqual(source["applicability"]["state"], "unverified")
        self.assertIsInstance(source["document_code"], str)
        artifact = source["artifacts"][0]
        binary, _, _ = self.service.download_source(self.alice, self.pid, source["id"], artifact["id"])
        self.assertTrue(binary)
        self.error("artifact_not_found", self.service.download_source, self.alice, self.pid, source["id"], "unknown")

    def test_sources_from_another_pack_cannot_be_substituted(self):
        source = self.service.import_source(self.alice, self.pid, "synthetic.docx", document(), "procedure")
        other = self.service.create_pack(self.alice, {"title": "Separate"})
        self.error("source_not_found", self.service.get_source, self.alice, other["id"], source["id"])
        self.error("source_not_found", self.service.search_knowledge, self.alice, other["id"], "", source["id"])
        self.error("invalid_filename", self.service.import_source, self.alice, self.pid, "../private.docx", document(), "procedure")

    def test_analysis_requires_authoritative_mapping_of_every_sheet(self):
        source = self.service.import_source(self.alice, self.pid, "synthetic.xlsx", workbook(), "workbook")
        self.error("mapping_required", self.analyse)
        self.error("unmapped_sheets", self.service.save_mapping, self.alice, self.pid, source["id"], {"sheets": MMS_MAPPING[:1]})
        invalid = deepcopy(MMS_MAPPING); invalid[0]["columns"]["sr_id"] = "SR"
        self.error("invalid_mapping", self.service.save_mapping, self.alice, self.pid, source["id"], {"sheets": invalid})
        mapped = self.service.save_mapping(self.alice, self.pid, source["id"], {"sheets": MMS_MAPPING})
        self.assertEqual(mapped["mapping_status"], "confirmed")
        self.error("stale_revision", self.service.save_mapping, self.alice, self.pid, source["id"], {"sheets": MMS_MAPPING})

    def test_ingest_calculate_query_and_preserve_distinct_record_grains(self):
        self.import_workbooks()
        result = self.analyse()
        self.assertEqual(result["counts_by_grain"]["mms_work_order"], 3)
        self.assertEqual(result["counts_by_grain"]["sr_reconciliation"], 1)
        self.assertEqual(result["counts_by_grain"]["summary"], 2)
        self.assertIsNone(result["relationships"]["canonical_incident_count"])
        match = result["reconciliation"]["records"][0]
        self.assertEqual(match["source_label"], "Absent from original comparison")
        self.assertEqual(match["calculated_match"], "matched_in_uploaded_mms")
        self.assertEqual(len(match["matched_record_ids"]), 2)
        rows = self.service.records(self.alice, self.pid, result["id"], {"grain": "mms_work_order"})
        self.assertEqual([r["source_row"] for r in rows["records"]], [4, 5, 7])
        self.assertEqual({r["fields"]["wo_id"] for r in rows["records"]}, {"WO-001", "WO-002", "WO-003"})
        self.assertTrue(rows["records"][0]["raw_fields"]["C"]["hidden_column"])
        selected = rows["records"][0]["id"]
        self.assertEqual(self.service.records(self.alice, self.pid, result["id"], {"record_ids": [selected]})["total"], 1)
        self.error("record_not_found", self.service.records, self.alice, self.pid, result["id"], {"record_ids": ["invented"]})
        self.error("invalid_record_query", self.service.records, self.alice, self.pid, result["id"], {"limit": 201})
        self.assertFalse(any(x["available"] for x in result["readiness"]))

    def test_period_filters_keep_cited_comparison_evidence_accessible(self):
        self.import_workbooks()
        result = self.analyse({"from": "2026-01-01", "to": "2026-01-31"})
        self.assertEqual(result["coverage"]["selected_records"], 1)
        refs = result["reconciliation"]["records"][0]["matched_record_ids"]
        self.assertEqual(self.service.records(self.alice, self.pid, result["id"], {"record_ids": refs})["total"], 2)
        self.assertEqual(result["counts_by_grain"]["mms_work_order"], 0)
        self.assertEqual(result["period"]["from"], "2026-01-01")

    def test_snapshot_retains_exact_mapping_after_live_source_remap(self):
        first, _ = self.import_workbooks()
        result = self.analyse()
        mapped = self.service.get_source(self.alice, self.pid, first["id"])
        changed = deepcopy(MMS_MAPPING); changed[0]["columns"]["wo_id"] = "A"
        self.service.save_mapping(self.alice, self.pid, first["id"], {"sheets": changed, "expected_revision": mapped["revision"]})
        same = self.service.get_analysis(self.alice, self.pid, result["id"])
        self.assertEqual(result, same)
        private = json.loads(self.store._exec("SELECT sources_json FROM rmd_analysis_sources WHERE id = ?", (result["id"],))[0]["sources_json"])
        snapshot = next(x for x in private if x["source_id"] == first["id"])
        self.assertEqual(snapshot["mapping"]["sheets"][0]["columns"]["wo_id"], "B")
        self.assertEqual(snapshot["mapping"]["revision"], mapped["revision"])
        self.assertNotIn("sources_json", json.dumps(same))
        rows = self.service.records(self.alice, self.pid, result["id"], {"grain": "mms_work_order"})["records"]
        self.assertEqual(rows[0]["fields"]["wo_id"], "WO-001")

    def test_idempotent_analysis_has_one_snapshot_and_reports_payload_conflict(self):
        self.import_workbooks()
        result = self.analyse()
        self.assertEqual(self.analyse()["id"], result["id"])
        self.error("idempotency_conflict", self.analyse, {"location": "Other"})
        self.assertEqual(len(self.service.get_pack(self.alice, self.pid)["analyses"]), 1)

    def test_link_reviews_are_optimistic_durable_and_do_not_merge_incidents(self):
        self.import_workbooks(); result = self.analyse()
        link = result["proposed_links"][0]
        decision = {"decision": "confirmed", "note": "Reviewed synthetic identifiers, sources remain separate.", "expected_revision": 1}
        reviewed = self.service.review_link(self.alice, self.pid, link["id"], decision)
        self.assertEqual(reviewed["state"], "confirmed")
        self.assertEqual(reviewed["revision"], 2)
        self.error("stale_revision", self.service.review_link, self.alice, self.pid, link["id"], decision)
        reload = self.service.get_analysis(self.alice, self.pid, result["id"])
        self.assertEqual(next(x for x in reload["proposed_links"] if x["id"] == link["id"])["state"], "confirmed")
        self.assertEqual(self.store._exec("SELECT COUNT(*) AS n FROM rmd_incidents")[0]["n"], 0)
        self.assertEqual(reload["counts_by_grain"], result["counts_by_grain"])
        self.assertIn("link_confirmed", [e["action"] for e in self.service.audit(self.alice, self.pid)["events"]])

    def test_actions_are_derived_from_snapshot_priority_and_require_closure_evidence(self):
        self.import_workbooks(); result = self.analyse()
        priority = result["priorities"][0]
        body = {"analysis_id": result["id"], "priority_id": priority["id"], "idempotency_key": "action",
                "owner_role": "Invented", "due_date": "1900-01-01", "proposed_action": "Invented"}
        action = self.service.create_action(self.alice, self.pid, body)
        self.assertEqual(action["proposed_action"], priority["proposed_action"])
        self.assertEqual(action["owner_role"], priority["owner_role"])
        self.assertIsNone(action["due_date"])
        self.assertFalse(action["maintenance_authorization"])
        self.assertEqual(self.service.create_action(self.alice, self.pid, body)["id"], action["id"])
        self.error("closure_evidence_required", self.service.update_action, self.alice, self.pid, action["id"], {"state": "closed", "expected_revision": 1})
        closed = self.service.update_action(self.alice, self.pid, action["id"], {"state": "closed", "expected_revision": 1, "closure_evidence": ["Authorized review reference SYN-REVIEW-1"]})
        self.assertEqual(closed["state"], "closed")
        self.error("stale_revision", self.service.update_action, self.alice, self.pid, action["id"], {"state": "accepted", "expected_revision": 1})
        self.error("priority_not_found", self.service.create_action, self.alice, self.pid, {"analysis_id": result["id"], "priority_id": "fake"})

    def test_knowledge_search_has_clause_locations_hashes_and_unverified_authority(self):
        source = self.service.import_source(self.alice, self.pid, "synthetic-reference.docx", document(), "procedure")
        result = self.service.search_knowledge(self.alice, self.pid, "manager", source["id"])
        self.assertTrue(result["hits"])
        hit = result["hits"][0]
        self.assertIn("manager", hit["text"])
        self.assertTrue(hit["locator"])
        self.assertEqual(len(hit["passage_sha256"]), 64)
        self.assertEqual(hit["classification"], "private_reference")
        self.assertEqual(hit["model_use"], "not_permitted_by_default")
        self.assertEqual(hit["applicability"]["state"], "unverified")
        self.assertEqual(self.service.search_knowledge(self.alice, self.pid, "unmatchedword")["hits"], [])

    def test_exports_preserve_snapshot_values_chart_tables_and_csv_security(self):
        self.import_workbooks(); result = self.analyse({"from": "2026-01-01", "to": "2026-01-31"})
        binary, mime, _ = self.service.export(self.alice, self.pid, result["id"], "csv")
        self.assertIn("text/csv", mime)
        rows = list(csv.DictReader(io.StringIO(binary.decode("utf-8-sig"))))
        for kpi in result["kpis"]:
            exported = next(r for r in rows if r["calculation_id"] == kpi["calculation_id"])
            self.assertEqual(int(exported["value"]), kpi["value"])
            self.assertEqual(exported["formula"], kpi["formula"])
            self.assertEqual(json.loads(exported["filters"]), result["filters"])
            self.assertEqual(json.loads(exported["record_ids"]), kpi["evidence_record_ids"])
        points = [p for chart in result["charts"] for p in chart["table"]]
        exported_points = [r for r in rows if r["kind"] == "chart_value"]
        self.assertEqual(len(points), len(exported_points))
        self.assertTrue(any(r["label"].startswith("'=FICTIONAL") for r in exported_points))
        html, _, _ = self.service.export(self.alice, self.pid, result["id"], language="ar")
        page = html.decode()
        self.assertIn('lang="ar" dir="rtl"', page)
        self.assertIn(result["fingerprint"], page)
        self.assertIn("=FICTIONAL_JUNCTION()", page)
        self.assertIn("default-src", page)
        self.assertIn('id="contents"', page)
        self.assertIn('miyaar-export-font" content="Dubai"', page)
        from tests.test_executive_exports import HtmlDocument
        parsed = HtmlDocument(page)
        ids = [attrs['id'] for _, attrs in parsed.tags if 'id' in attrs]
        links = [attrs['href'][1:] for tag, attrs in parsed.tags if tag == 'a']
        self.assertTrue(links)
        self.assertTrue(all(ids.count(destination) == 1 for destination in links))
        self.assertIn('الملخص التنفيذي', page)
        self.error("stale_snapshot", self.service.export, self.alice, self.pid, result["id"], fingerprint="other")
        self.error("pack_not_found", self.service.export, self.bob, self.pid, result["id"])

    def test_every_private_record_snapshot_is_durable_after_database_reopen(self):
        self.import_workbooks(); result = self.analyse()
        self.store.close()
        self.store = open_store(self.database_url, self.db)
        self.service = RmdService(self.store)
        restored = self.service.get_analysis(self.alice, self.pid, result["id"])
        self.assertEqual(restored, result)
        self.assertEqual(self.service.records(self.alice, self.pid, result["id"])["total"], 6)
        self.error("pack_not_found", self.service.get_analysis, self.bob, self.pid, result["id"])

    def test_erasure_removes_personal_data_but_preserves_shared_organization_evidence(self):
        self.import_workbooks(); self.analyse()
        org = self.organization(self.alice)
        shared = self.service.create_pack(self.alice, {"title": "Shared retained", "organization_id": org["id"], "idempotency_key": "shared"})
        self.member(org, self.bob.subject, "manager")
        before = rmd_counts(self.store, owner=self.alice.subject)
        self.assertEqual(before["rmd_packs"], 1)
        self.assertEqual(before["rmd_analyses"], 1)
        with self.store.atomic("erase-test"):
            erase_owner_rmd(self.store, self.alice.subject)
        self.error("pack_not_found", self.service.get_pack, self.alice, self.pid)
        self.assertEqual(self.service.get_pack(self.bob, shared["id"])["owner"], self.alice.subject)
        self.assertTrue(self.service.audit(self.bob, shared["id"])["events"])
        self.assertEqual(rmd_counts(self.store, org_ids=[org["id"]])["rmd_packs"], 1)
        with self.store.atomic("erase-org-test"):
            erase_org_rmd(self.store, org["id"])
        for table in RMD_TABLES:
            self.assertEqual(self.store._exec(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"], 0)

    def test_pack_deletion_removes_bound_reports_before_authorization_binding(self):
        from server.rmd_workflow import create_review_run
        self.import_workbooks(); result = self.analyse()
        engine = SimpleNamespace(new_id=uid, limits=None)
        review = create_review_run(self.service, engine, self.alice, self.pid, result["id"], {"idempotency_key": "review"})
        run_id = review["run_id"]
        self.assertEqual(self.service.get_analysis(self.alice, self.pid, result["id"])["run_id"], run_id)
        self.assertTrue(self.store._exec("SELECT id FROM artifacts WHERE run_id = ?", (run_id,)))
        self.service.delete_pack(self.alice, self.pid)
        for table in ("tasks", "approvals", "artifacts", "vault_notes", "kpi_policies"):
            self.assertEqual(self.store._exec(f"SELECT * FROM {table} WHERE run_id = ?", (run_id,)), [])
        self.assertEqual(self.store._exec("SELECT id FROM runs WHERE id = ?", (run_id,)), [])
        self.assertEqual(self.store._exec("SELECT id FROM rmd_runs WHERE id = ?", (run_id,)), [])

    def test_http_boundary_no_store_upload_citations_download_and_separate_user(self):
        try:
            import httpx
            from fastapi import FastAPI, Header
            from server.rmd_api import install_rmd_api
        except ImportError as error:
            self.skipTest(str(error))
        app = FastAPI()
        principals = {"alice": self.alice, "bob": self.bob}
        async def current_principal(x_user: str = Header("alice")):
            return principals[x_user]
        install_rmd_api(app, self.store, current_principal, "local", engine=SimpleNamespace(new_id=uid, limits=None))

        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://evidence.test") as client:
                prefix = f"/api/rmd/packs/{self.pid}"
                original_bytes = document()
                upload = await client.post(prefix + "/sources?kind=procedure&filename=synthetic.docx", content=original_bytes, headers={"Content-Type": "application/octet-stream"})
                self.assertEqual(upload.status_code, 200, upload.text)
                self.assertIn("no-store", upload.headers["cache-control"])
                sid = upload.json()["id"]
                search = await client.get(prefix + "/knowledge?q=manager")
                self.assertTrue(search.json()["hits"])
                original = await client.get(prefix + f"/sources/{sid}/download")
                self.assertEqual(original.content, original_bytes)
                self.assertIn("attachment", original.headers["content-disposition"])
                denied = await client.get(prefix + f"/sources/{sid}", headers={"X-User": "bob"})
                self.assertEqual(denied.status_code, 404)
                self.assertIn("no-store", denied.headers["cache-control"])
                invalid = await client.get(prefix + "/knowledge?limit=1000")
                self.assertEqual(invalid.status_code, 422)
                self.assertIn("no-store", invalid.headers["cache-control"])
                malformed = await client.post(prefix + "/sources?kind=procedure&filename=not-office.txt", content=b"not an office source")
                self.assertEqual(malformed.status_code, 415, malformed.text)
                self.assertIn("no-store", malformed.headers["cache-control"])
                explanation = await client.post(prefix + "/assistant", json={"question": "What does the manager require?"})
                self.assertEqual(explanation.status_code, 200, explanation.text)
                self.assertTrue(explanation.json()["ephemeral"])
                self.assertTrue(explanation.json()["citations"])
                self.import_workbooks(); result = self.analyse()
                export = await client.get(prefix + f"/analyses/{result['id']}/export?format=html&language=ar")
                self.assertEqual(export.status_code, 200, export.text)
                self.assertIn('dir="rtl"', export.text)
                page = await client.post(prefix + f"/analyses/{result['id']}/records/query", json={"record_ids": result["scope"]["record_ids"][:1]})
                self.assertEqual(page.status_code, 200, page.text)
                self.assertEqual(page.json()["total"], 1)
                review_path = prefix + f"/analyses/{result['id']}/review-run"
                forged = await client.post(review_path, json={"idempotency_key": "review", "owner": "someone-else"})
                self.assertEqual(forged.status_code, 422)
                review = await client.post(review_path, json={"idempotency_key": "review"})
                self.assertEqual(review.status_code, 200, review.text)
                self.assertTrue(review.json()["run_id"])
                forbidden = await client.post(review_path, json={"idempotency_key": "review"}, headers={"X-User": "bob"})
                self.assertEqual(forbidden.status_code, 404)
        async def inline_dispatch(function, /, *args, **kwargs):
            # HTTP semantics can be checked inside the restricted runner where
            # AnyIO worker wakeups stall. Production thread scheduling is not
            # verified by this in-process boundary test.
            return function(*args, **kwargs)
        with patch("fastapi.routing.run_in_threadpool", inline_dispatch), patch("server.rmd_api.run_in_threadpool", inline_dispatch):
            asyncio.run(asyncio.wait_for(run(), timeout=15))


if __name__ == "__main__":
    unittest.main()
