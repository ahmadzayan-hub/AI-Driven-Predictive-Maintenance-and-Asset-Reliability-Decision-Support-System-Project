"""Synthetic evidence → immutable report → actual approval/publish lifecycle."""

from copy import deepcopy
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from server.auth import Principal
from server.erasure import erase, survey
from server.model_gateway import ModelGateway
from server.operations import Operations, require_org_access
from server.rmd_assistant import aggregate_facts, explain
from server.rmd_service import RmdError, RmdService
from server.rmd_workflow import authorize_run, create_review_run
from server.runs import RunEngine
from server.storage import open_store
from tests.test_rmd_ingestion import workbook, document
from tests.test_rmd_service import MMS_MAPPING, RECON_MAPPING, RECON_SHEET


class EvidenceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = open_store(None, self.root / "evidence.db")
        self.addCleanup(self.store.close)
        self.service = RmdService(self.store)
        self.engine = RunEngine(self.store, self.root / "vault", ModelGateway(env={}))
        self.alice = Principal("alice", "owner", "test")
        self.bob = Principal("bob", "owner", "test")
        self.admin = Principal("operator", "admin", "test")
        self.pack = self.service.create_pack(self.alice, {"title": "Synthetic evidence"})
        self.pid = self.pack["id"]

    def populate(self, pack=None):
        pid = pack or self.pid
        source = self.service.import_source(self.alice, pid, "synthetic.xlsx", workbook(), "workbook")
        self.service.save_mapping(self.alice, pid, source["id"], {"sheets": deepcopy(MMS_MAPPING)})
        return self.service.create_analysis(self.alice, pid, {"filters": {}, "language": "en"})

    def review(self, analysis, pack=None):
        return create_review_run(self.service, self.engine, self.alice, pack or self.pid,
                                 analysis["id"], {"idempotency_key": "review-" + analysis["id"]})["run_id"]

    def test_genuine_report_is_hash_bound_and_published_only_after_approval(self):
        analysis = self.populate()
        run_id = self.review(analysis)
        run = self.engine.get_run(run_id)
        self.assertEqual(run["state"], "queued")
        self.assertEqual(run["tasks"][1]["quality_checks"][0]["name"], "immutable_snapshot_replay")
        self.assertEqual(self.store.get_run(run_id)["dataset_text"], "")
        self.assertIsNone(self.store.get_run(run_id)["dataset_id"])
        self.assertIsNone(run["dataset_id"])
        self.assertFalse((self.root / "vault" / "Reports").exists())
        self.assertEqual(self.review(analysis), run_id)
        run = self.engine.advance(run_id)
        self.assertEqual(run["state"], "awaiting_approval")
        approval_id = run["approvals"][0]["id"]
        self.assertIn(analysis["fingerprint"], run["report"]["content"])
        run = self.engine.decide_approval(run_id, approval_id, "approve", approver="alice")
        self.assertEqual(run["state"], "completed")
        self.assertTrue((self.engine.vault_dir / run["report"]["published_path"]).is_file())
        self.assertEqual(run["approvals"][0]["decided_by"], "alice")
        overlay = self.service.get_analysis(self.alice, self.pid, analysis["id"])
        self.assertEqual(overlay["publication_state"], "published")
        self.assertEqual(overlay["published_path"], run["report"]["published_path"])

    def test_changed_artifact_refuses_old_approval(self):
        run_id = self.review(self.populate())
        run = self.engine.advance(run_id)
        self.store.update("artifacts", run["report"]["id"], {"content": "Changed synthetic artifact"})
        with self.assertRaisesRegex(ValueError, "Artifact changed"):
            self.engine.decide_approval(run_id, run["approvals"][0]["id"], "approve")
        self.assertFalse((self.root / "vault" / "Reports").exists())

    def test_pack_deletion_also_removes_local_publications(self):
        run_id = self.review(self.populate())
        run = self.engine.advance(run_id)
        run = self.engine.decide_approval(run_id, run["approvals"][0]["id"], "approve", "alice")
        path = self.engine.vault_dir / run["report"]["published_path"]
        self.assertTrue(path.exists())
        result = self.service.delete_pack(self.alice, self.pid)
        self.assertFalse(path.exists())
        self.assertEqual(len(result["vault_files_deleted"]), 2)
        self.assertIsNone(self.store.get_run(run_id))

    def test_tampered_snapshot_cannot_become_a_review_run(self):
        analysis = self.populate()
        row = self.store._exec("SELECT result_json FROM rmd_analyses WHERE id = ?", (analysis["id"],))[0]
        result = json.loads(row["result_json"])
        result["counts_by_grain"]["mms_work_order"] += 1
        self.store.update("rmd_analyses", analysis["id"], {"result_json": json.dumps(result)})
        with self.assertRaises(RmdError) as caught:
            self.review(analysis)
        self.assertEqual(caught.exception.code, "snapshot_validation_failed")
        self.assertEqual(self.engine.list_runs(), [])

    def test_bound_report_never_grants_admin_access(self):
        run_id = self.review(self.populate())
        self.assertTrue(authorize_run(self.service, self.alice, run_id))
        self.assertFalse(authorize_run(self.service, self.bob, run_id))
        self.assertFalse(authorize_run(self.service, self.admin, run_id))
        self.assertIsNone(authorize_run(self.service, self.alice, "unrelated"))

    def test_shared_evidence_and_bound_run_survive_creator_erasure(self):
        ops = Operations(self.store)
        org = ops.create_organization(self.alice, {"name": "Synthetic depot", "idempotency_key": "org"})
        ops.set_member(self.alice, org["id"], {"subject": "bob", "role": "owner", "expected_version": org["version"], "idempotency_key": "bob"})
        pack = self.service.create_pack(self.alice, {"title": "Shared", "organization_id": org["id"]})
        run_id = self.review(self.populate(pack["id"]), pack["id"])
        result = erase(self.store, "alice")
        self.assertEqual(result["deleted"]["runs"], 0)
        self.assertIsNotNone(self.store.get_run(run_id))
        self.assertFalse(authorize_run(self.service, self.alice, run_id))
        self.assertTrue(authorize_run(self.service, self.bob, run_id))
        before = survey(self.store, "bob")
        self.assertEqual(before["rows"]["runs"], 1)
        result = erase(self.store, "bob")
        self.assertEqual(result["deleted"]["runs"], 1)
        self.assertIsNone(self.store.get_run(run_id))
        self.assertEqual(self.store._exec("SELECT * FROM rmd_runs"), [])

    def test_aggregate_projection_excludes_private_source_values_and_prompts(self):
        analysis = self.populate()
        analysis["records"] = [{"location": "PRIVATE_CANARY", "sr": "PRIVATE_IDENTIFIER"}]
        analysis["source_versions"].append({"filename": "PRIVATE_FILENAME"})
        self.assertNotIn("PRIVATE_", json.dumps(aggregate_facts(analysis)))
        gateway = Mock()
        gateway.narrate.return_value = {"source": "model", "text": "There are 999999 incidents."}
        assistant = SimpleNamespace(gateway=gateway)
        answer = explain(assistant, self.service, self.alice, self.pid, {
            "question": "PRIVATE_USER_QUESTION", "analysis_id": analysis["id"]})
        gateway.narrate.assert_not_called()
        self.assertTrue(answer["ephemeral"])
        self.service.env = {"AGENTIC_OS_RMD_MODEL_AGGREGATES": "1"}
        answer = explain(assistant, self.service, self.alice, self.pid, {
            "question": "PRIVATE_USER_QUESTION", "analysis_id": analysis["id"]})
        self.assertNotIn("PRIVATE_", str(gateway.narrate.call_args))
        self.assertEqual(answer["source"], "deterministic")
        self.assertNotIn("999999", answer["text"])
        gateway.narrate.return_value = {"source": "model", "text": "Bearing wear caused the failures."}
        answer = explain(assistant, self.service, self.alice, self.pid, {
            "question": "summarize", "analysis_id": analysis["id"]})
        self.assertEqual(answer["source"], "deterministic")
        self.assertNotIn("caused", answer["text"])

    def test_private_clauses_answer_authorized_person_without_gateway(self):
        source = self.service.import_source(self.alice, self.pid, "synthetic.docx", document(), "procedure")
        assistant = SimpleNamespace(gateway=Mock())
        answer = explain(assistant, self.service, self.alice, self.pid, {"question": "What does the procedure require of the manager?"})
        self.assertTrue(answer["citations"])
        self.assertEqual(answer["citations"][0]["source_id"], source["id"])
        self.assertTrue(answer["citations"][0]["locator"])
        assistant.gateway.narrate.assert_not_called()
        with self.assertRaises(RmdError):
            explain(assistant, self.service, self.bob, self.pid, {"question": "procedure"})

    def test_missing_sr_answer_uses_exact_selected_comparison_records(self):
        self.populate()
        source = self.service.import_source(self.alice, self.pid, "synthetic-reconciliation.xlsx",
            workbook(RECON_SHEET.replace("SR-0007", "SYN-NOT-IN-MMS")), "workbook")
        self.service.save_mapping(self.alice, self.pid, source["id"], {"sheets": deepcopy(RECON_MAPPING)})
        mms_id = next(s["id"] for s in self.service.get_pack(self.alice, self.pid)["sources"]
                      if s["name"] == "synthetic.xlsx")
        analysis = self.service.create_analysis(self.alice, self.pid, {
            "filters": {"comparison_source_ids": [mms_id]}, "language": "en"})
        gateway = Mock()
        answer = explain(SimpleNamespace(gateway=gateway), self.service, self.alice, self.pid, {
            "question": "Which SR identifiers are missing from the comparison?", "analysis_id": analysis["id"]})
        self.assertIn("SYN-NOT-IN-MMS", answer["text"])
        self.assertIn("only the selected comparison source", answer["text"])
        self.assertNotIn("root cause", answer["text"])
        gateway.narrate.assert_not_called()

    def test_generic_run_and_vault_routes_recheck_bound_pack_access(self):
        import httpx
        from server.app import create_app
        from server.auth import issue_local_test_token
        config = self.root / "app.json"
        config.write_text(json.dumps({
            "agent_name": "Synthetic evidence test", "memory_file": str(self.root / "memory.json"),
            "database_file": str(self.root / "evidence.db"), "vault_dir": str(self.root / "vault")}))
        env = {"AGENTIC_OS_JWT_SECRET": "synthetic-rmd-token-secret-not-a-credential",
               "AGENTIC_OS_JWT_AUDIENCE": "rmd-test", "AGENTIC_OS_JWT_ISSUER": "https://issuer.invalid/",
               "AGENTIC_OS_ROLE_ASSIGNMENTS": "alice:owner,bob:owner,operator:admin"}
        app = create_app(config, env=env)
        self.addCleanup(app.state.store.close)
        org = Operations(self.store).create_organization(self.alice, {"name": "Depot", "idempotency_key": "org"})
        Operations(self.store).set_member(self.alice, org["id"], {
            "subject": "bob", "role": "viewer", "expected_version": org["version"], "idempotency_key": "bob"})
        pack = self.service.create_pack(self.alice, {"title": "Shared", "organization_id": org["id"]})
        run_id = self.review(self.populate(pack["id"]), pack["id"])
        run = self.engine.advance(run_id)
        self.engine.decide_approval(run_id, run["approvals"][0]["id"], "approve", "alice")
        path = self.store.list_notes(owner="alice")[0]["path"]

        def headers(subject):
            return {"Authorization": "Bearer " + issue_local_test_token(
                env["AGENTIC_OS_JWT_SECRET"], subject, audience="rmd-test", issuer="https://issuer.invalid/")}

        async def check():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://evidence.test") as client:
                for subject, status in (("alice", 200), ("bob", 200), ("operator", 404)):
                    response = await client.get(f"/api/runs/{run_id}", headers=headers(subject))
                    self.assertEqual(response.status_code, status, response.text)
                    if status == 200:
                        self.assertIsNone(response.json()["dataset_id"])
                denied = await client.post(f"/api/runs/{run_id}/pause", headers=headers("bob"))
                self.assertEqual(denied.status_code, 404)
                for subject, expected in (("bob", True), ("operator", False)):
                    response = await client.get("/api/runs", headers=headers(subject))
                    self.assertEqual(run_id in {r["id"] for r in response.json()["runs"]}, expected)
                self.store._exec("DELETE FROM organization_members WHERE org_id = ? AND subject = ?", (org["id"], "alice"))
                response = await client.get(f"/api/runs/{run_id}", headers=headers("alice"))
                self.assertEqual(response.status_code, 404)
                response = await client.get("/api/vault", headers=headers("alice"))
                self.assertNotIn(run_id, str(response.json()))
                response = await client.get("/api/vault/note", params={"path": path}, headers=headers("alice"))
                self.assertEqual(response.status_code, 404)
                response = await client.get("/api/vault/note", params={"path": path}, headers=headers("bob"))
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(app.state.assistant._latest_run("alice"))

        async def inline(function, /, *args, **kwargs):
            # Same HTTP-only dispatcher adaptation as the service test. The
            # restricted local runner cannot verify AnyIO worker scheduling.
            return function(*args, **kwargs)
        with patch("fastapi.routing.run_in_threadpool", inline), patch("fastapi.dependencies.utils.run_in_threadpool", inline):
            asyncio.run(asyncio.wait_for(check(), timeout=15))


if __name__ == "__main__":
    unittest.main()
