"""Synthetic selected-report and live media authorization regressions. No encoder/model."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from server.app import create_app
from server.assistant import Assistant
from server.auth import Principal
from server.model_gateway import ModelGateway
from server.motion_local import LocalMotion
from server.motion_storyboard import from_evidence_run, from_run, MotionStoryRefused
from server.operations import Operations
from server.rmd_workflow import create_review_run
from tests.support import closing, scoped_token
from tests.test_assistant import FakeSession, make_agent, engine_in, finish
from tests.test_rmd_ingestion import workbook
from tests.test_rmd_service import MMS_MAPPING

SECRET = "report-motion-synthetic-test-secret-not-a-credential"


class SelectedReportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.engine = engine_in(temp.name, self)
        self.assistant = Assistant(ModelGateway(env={}), self.engine)
        self.session = FakeSession(make_agent(), owner="alice")
        self.old = finish(self.engine, self.engine.create_run("Older A", owner="alice")["id"])
        self.new = finish(self.engine, self.engine.create_run("Newer B", owner="alice")["id"])

    def execute(self, name, run_id, principal=None):
        token = self.assistant._requester.set(principal)
        try:
            return self.assistant._execute(name, {"run_id": run_id}, self.session, "")
        finally:
            self.assistant._requester.reset(token)

    def test_explicit_older_report_and_status_never_select_latest(self):
        for action in ("explain_report", "run_status"):
            answer = self.execute(action, self.old["id"], Principal("alice", "owner", "test"))
            self.assertEqual(answer["result"]["run_id"], self.old["id"])
            self.assertNotIn("Newer B", answer["text"])

    def test_missing_and_other_owner_are_indistinguishable_without_fallback(self):
        foreign = self.engine.create_run("Private foreign report", owner="bob")
        for action in ("explain_report", "run_status"):
            missing = self.execute(action, "missing", Principal("alice", "owner", "test"))
            denied = self.execute(action, foreign["id"], Principal("alice", "owner", "test"))
            self.assertEqual(missing, denied)
            self.assertIsNone(denied["result"])

    def test_actual_requester_not_session_creator_controls_access(self):
        answer = self.execute("explain_report", self.old["id"], Principal("bob", "owner", "test"))
        self.assertIsNone(answer["result"])
        self.assistant.identity_mode = "managed"
        self.assertIsNone(self.execute("explain_report", self.old["id"])["result"])

    def test_full_content_hash_changes_with_unchanged_headline(self):
        first = from_run(self.old)
        changed = deepcopy(self.old); changed["report"]["content"] += "\nDifferent finding"
        second = from_run(changed)
        self.assertNotEqual(first["source_context"]["report_sha256"], second["source_context"]["report_sha256"])
        self.assertEqual(first["scenes"], second["scenes"])


class MotionAccessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.env_patch = patch.dict("os.environ", {"AGENTIC_MOTION_ROOT": str(self.root / "media")})
        self.env_patch.start(); self.addCleanup(self.env_patch.stop)
        self.motion = LocalMotion()
        config = self.root / "config.json"
        config.write_text(json.dumps({"database_file": str(self.root / "test.db"),
            "memory_file": str(self.root / "memory.json"), "vault_dir": str(self.root / "vault")}))
        with patch("server.motion_local.LocalMotion", return_value=self.motion):
            self.app = closing(self, create_app(config, env={
                "AGENTIC_OS_JWT_SECRET": SECRET, "SUPABASE_URL": "https://test.supabase.invalid",
                "AGENTIC_OS_ROLE_ASSIGNMENTS": "operator:admin", "AGENTIC_MOTION_LOCAL_ENABLED": "1"}))
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.store, self.engine, self.service = self.app.state.store, self.app.state.engine, self.app.state.rmd
        self.alice = Principal("alice", "owner", "test")
        self.ops = Operations(self.store)
        self.org = self.ops.create_organization(self.alice, {"name": "Synthetic depot", "idempotency_key": "org"})
        self.ops.set_member(self.alice, self.org["id"], {"subject": "bob", "role": "manager",
            "expected_version": self.org["version"], "idempotency_key": "member"})
        self.checks = dict(outcome="approve", watched_full_video=True, checked_audio_alignment=True,
            checked_arabic=True, checked_evidence=True, checked_brand_and_rights=True)

    def headers(self, who):
        return {"Authorization": "Bearer " + scoped_token(SECRET, who, "owner")}

    def fixture(self, private=False):
        pack = self.service.create_pack(self.alice, {"title": "Synthetic evidence", **({} if private else {"organization_id": self.org["id"]})})
        source = self.service.import_source(self.alice, pack["id"], "synthetic.xlsx", workbook(), "workbook")
        self.service.save_mapping(self.alice, pack["id"], source["id"], {"sheets": deepcopy(MMS_MAPPING)})
        analysis = self.service.create_analysis(self.alice, pack["id"], {"filters": {}, "language": "en"})
        run_id = create_review_run(self.service, self.engine, self.alice, pack["id"], analysis["id"], {"idempotency_key": "review"})["run_id"]
        run = self.engine.get_run(run_id)
        story = from_evidence_run(self.service, self.alice, run)
        with patch("server.motion_local.WORKERS.submit"):
            job = self.motion.create("alice", run_id, run, None, storyboard=story)
        # Synthetic bytes test guarded delivery/hash only, not MP4 encoding.
        media = self.motion.base / (job["id"] + ".mp4"); media.write_bytes(b"synthetic-media-not-a-real-video")
        self.motion._update(job["id"], "RENDERED_DRAFT", video_name=media.name,
            video_sha=hashlib.sha256(media.read_bytes()).hexdigest())
        self.motion.submit(job["id"], "alice")
        return pack, analysis, run, job["id"], source

    def get(self, job, who, suffix=""):
        return self.client.get(f"/api/motion/jobs/{job}{suffix}", headers=self.headers(who))

    def decide(self, job, who):
        return self.client.post(f"/api/motion/jobs/{job}/decision", headers=self.headers(who), json=self.checks)

    def test_rmd_adapter_replays_snapshot_and_binds_hash(self):
        pack, analysis, run, job, source = self.fixture()
        response = self.client.get(f"/api/runs/{run['id']}/motion-storyboard", headers=self.headers("alice"))
        self.assertEqual(response.status_code, 200, response.text)
        context = response.json()["source_context"]
        self.assertEqual(response.headers["cache-control"], "private, no-store, max-age=0")
        self.assertEqual(context["fingerprint"], analysis["fingerprint"])
        self.assertEqual(context["report_sha256"], hashlib.sha256(run["report"]["content"].encode()).hexdigest())
        mismatched = deepcopy(run); mismatched["report_language"] = "ar"
        with self.assertRaises(MotionStoryRefused): from_evidence_run(self.service, self.alice, mismatched)
        bad = deepcopy(run); bad["tasks"][1]["quality_checks"][0]["passed"] = False
        with self.assertRaises(MotionStoryRefused): from_evidence_run(self.service, self.alice, bad)
        # Private evidence never flows to ordinary retained assistant messages.
        assistant = Assistant(ModelGateway(env={}), self.engine)
        self.assertIsNone(assistant._explain({"run_id": run["id"]}, FakeSession(make_agent(), "alice"))["result"])

    def test_existing_org_reviewer_can_preview_and_approve_but_author_cannot(self):
        _, _, _, job, _ = self.fixture()
        self.assertEqual(self.get(job, "bob", "/preview").status_code, 200)
        self.assertEqual(self.get(job, "bob").status_code, 200)
        self.assertEqual(self.decide(job, "alice").status_code, 409)
        answer = self.decide(job, "bob")
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertEqual(answer.json()["status"], "INTERNAL_APPROVED")
        self.assertFalse(answer.json()["publication_allowed"])

    def test_outsider_and_admin_without_membership_cannot_read_or_review(self):
        _, _, _, job, _ = self.fixture()
        for who in ("outsider", "operator"):
            self.assertEqual(self.get(job, who).status_code, 404)
            self.assertEqual(self.get(job, who, "/preview").status_code, 404)
            self.assertEqual(self.decide(job, who).status_code, 404)

    def test_private_pack_does_not_gain_a_reviewer_grant(self):
        _, _, _, job, _ = self.fixture(private=True)
        for who in ("bob", "operator"):
            self.assertEqual(self.get(job, who, "/preview").status_code, 404)
            self.assertEqual(self.decide(job, who).status_code, 404)

    def test_revocation_including_original_author_is_checked_live(self):
        _, _, _, job, _ = self.fixture()
        for who in ("alice", "bob"):
            self.store._exec("DELETE FROM organization_members WHERE org_id = ? AND subject = ?", (self.org["id"], who))
            self.assertEqual(self.get(job, who).status_code, 404)
            self.assertEqual(self.get(job, who, "/preview").status_code, 404)
            self.assertEqual(self.decide(job, who).status_code, 404)

    def test_source_deletion_blocks_existing_media(self):
        _, _, _, job, source = self.fixture()
        self.store._exec("DELETE FROM rmd_sources WHERE id = ?", (source["id"],))
        self.assertEqual(self.get(job, "alice", "/preview").status_code, 404)
        self.assertEqual(self.decide(job, "bob").status_code, 404)

    def test_report_changes_and_snapshot_tampering_are_refused(self):
        _, analysis, run, job, _ = self.fixture()
        self.store.update("artifacts", run["report"]["id"], {"content": run["report"]["content"] + "\nChanged"})
        self.assertEqual(self.get(job, "alice", "/preview").status_code, 409)
        self.assertEqual(self.decide(job, "bob").status_code, 409)
        self.store.update("artifacts", run["report"]["id"], {"content": run["report"]["content"]})
        row = self.store._exec("SELECT result_json FROM rmd_analyses WHERE id = ?", (analysis["id"],))[0]
        result = json.loads(row["result_json"]); result["counts_by_grain"]["mms_work_order"] += 1
        self.store.update("rmd_analyses", analysis["id"], {"result_json": json.dumps(result)})
        self.assertTrue(self.get(job, "alice").json()["needs_update"])

    def test_removed_run_cannot_authorize_stored_media(self):
        pack, _, _, job, _ = self.fixture()
        self.service.delete_pack(self.alice, pack["id"])
        self.assertEqual(self.get(job, "alice").status_code, 404)

    def test_unsubmitted_draft_not_visible_to_reviewer(self):
        _, _, _, job, _ = self.fixture()
        self.motion._update(job, "RENDERED_DRAFT")
        self.assertEqual(self.get(job, "bob", "/preview").status_code, 404)
        self.assertEqual(self.get(job, "alice", "/preview").status_code, 200)


    def test_generic_storyboard_http_and_legacy_hashless_job_fail_closed(self):
        run = finish(self.engine, self.engine.create_run("Synthetic generic", owner="alice")["id"])
        url = f"/api/runs/{run['id']}/motion-storyboard"
        response = self.client.get(url, headers=self.headers("alice"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("report_sha256", response.json()["source_context"])
        self.assertEqual(self.client.get(url, headers=self.headers("outsider")).status_code, 404)
        with patch("server.motion_local.WORKERS.submit"):
            job = self.motion.create("alice", run["id"], run, None)["id"]
        row = self.motion.record(job, "alice")
        story = json.loads(row["storyboard"]); del story["source_context"]["report_sha256"]
        raw = json.dumps(story, ensure_ascii=False, sort_keys=True)
        self.motion._update(job, "RENDERED_DRAFT", storyboard=raw, storyboard_sha=hashlib.sha256(raw.encode()).hexdigest())
        response = self.get(job, "alice")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["needs_update"])

    def test_invalid_report_content_is_refused_not_a_type_error(self):
        from tests.test_motion_storyboard import run as fixture
        for invalid in (None, {}, 42):
            run = fixture(); run["report"]["content"] = invalid
            with self.assertRaises(MotionStoryRefused): from_run(run)


    def test_source_hash_change_with_unchanged_report_refuses_derivative(self):
        _, _, run, job, source = self.fixture()
        self.store.update("rmd_sources", source["id"], {"sha256": "0" * 64})
        self.assertEqual(self.engine.get_run(run["id"])["report"], run["report"])
        self.assertTrue(self.get(job, "alice").json()["needs_update"])
        self.assertEqual(self.get(job, "bob", "/preview").status_code, 409)
        self.assertEqual(self.decide(job, "bob").status_code, 409)


    def test_submit_rechecks_organization_write_not_just_read(self):
        _, _, _, job, _ = self.fixture()
        self.motion._update(job, "RENDERED_DRAFT")
        self.store._exec("UPDATE organization_members SET role = 'viewer' WHERE org_id = ? AND subject = ?", (self.org["id"], "alice"))
        self.assertEqual(self.get(job, "alice", "/preview").status_code, 200)
        response = self.client.post(f"/api/motion/jobs/{job}/submit", headers=self.headers("alice"))
        self.assertEqual(response.status_code, 404)

    def test_render_and_storyboard_check_source_before_accepting_audio(self):
        _, _, run, _, _ = self.fixture()
        for who in ("outsider", "operator"):
            response = self.client.get(f"/api/runs/{run['id']}/motion-storyboard", headers=self.headers(who))
            self.assertEqual(response.status_code, 404)
            with patch("server.motion_local.WORKERS.submit") as worker:
                response = self.client.post(f"/api/motion/runs/{run['id']}/render",
                    headers={**self.headers(who), "Content-Length": "24000001"}, content=b"synthetic")
                self.assertEqual(response.status_code, 404)
                worker.assert_not_called()

    def test_missing_and_inaccessible_jobs_are_indistinguishable(self):
        _, _, _, job, _ = self.fixture()
        for who in ("outsider", "operator"):
            for suffix in ("", "/preview"):
                missing = self.get("MOT-missing", who, suffix)
                denied = self.get(job, who, suffix)
                self.assertEqual(missing.status_code, 404)
                self.assertEqual(denied.status_code, 404)
                self.assertEqual(missing.json().get("detail"), denied.json().get("detail"))
                self.assertEqual(missing.json()["error"]["code"], denied.json()["error"]["code"])
            missing = self.decide("MOT-missing", who)
            denied = self.decide(job, who)
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(denied.status_code, 404)
            self.assertEqual(missing.json().get("detail"), denied.json().get("detail"))

    def test_concurrent_final_decisions_have_one_winner_across_connections(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from server.motion_local import MotionError
        _, _, _, job, _ = self.fixture()
        other = LocalMotion()
        barrier = Barrier(2)
        checks = {key: value for key, value in self.checks.items() if key != "outcome"}
        def decide(pair):
            instance, outcome = pair
            barrier.wait()
            try:
                return instance.decide(job, "bob", outcome, "Human review", checks, approval_allowed=True)
            except MotionError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(decide, [(self.motion, "approve"), (other, "return")]))
        winners = [result for result in results if result]
        self.assertEqual(len(winners), 1)
        self.assertFalse(winners[0]["publication_allowed"])
        self.assertEqual(self.motion.record(job, "alice")["status"], winners[0]["status"])
