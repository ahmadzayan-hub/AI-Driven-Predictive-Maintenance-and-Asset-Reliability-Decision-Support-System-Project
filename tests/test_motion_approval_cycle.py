"""Synthetic HTTP workflow tests: no real media/model/provider calls."""
import hashlib
import json
import unittest
from unittest.mock import patch
from tests import test_report_motion_guards as fixtures


class MotionApprovalCycleTests(unittest.TestCase):
    setUp = fixtures.MotionAccessTests.setUp
    fixture = fixtures.MotionAccessTests.fixture
    headers = fixtures.MotionAccessTests.headers
    get = fixtures.MotionAccessTests.get

    def draft(self, run, **params):
        with patch("server.motion_local.WORKERS.submit") as worker:
            result = self.client.post(f"/api/motion/runs/{run['id']}/draft", headers=self.headers("alice"), params=params)
            worker.assert_not_called()
        return result

    def approve(self, job, who="bob", **overrides):
        story = self.get(job, who, "/script")
        body = dict(binding=story.json().get("workflow", {}).get("binding", "0" * 64), reviewed_script=True,
                    checked_evidence=True, checked_audience_format=True, checked_narration_rights=True)
        body.update(overrides)
        return self.client.post(f"/api/motion/jobs/{job}/script-approval", headers=self.headers(who), json=body)

    def render(self, job):
        return self.client.post(f"/api/motion/jobs/{job}/render-approved", headers=self.headers("alice"))

    def test_explicit_approval_then_single_render_and_no_auto_publish(self):
        _, _, run, _, _ = self.fixture()
        response = self.draft(run, audience="maintenance", video_format="vertical")
        self.assertEqual(response.status_code, 201, response.text)
        job = response.json()["id"]
        self.assertEqual(response.json()["status"], "SCRIPT_REVIEW_REQUESTED")
        with patch("server.motion_local.WORKERS.submit") as worker:
            self.assertEqual(self.render(job).status_code, 409)
            worker.assert_not_called()
            self.assertEqual(self.approve(job, "alice").status_code, 409)
            self.assertEqual(self.approve(job, checked_evidence=False).status_code, 409)
            self.assertEqual(self.approve(job, binding="0" * 64).status_code, 409)
            self.assertEqual(self.approve(job).status_code, 200)
            self.assertEqual(self.render(job).status_code, 202)
            worker.assert_called_once()
            self.assertEqual(self.render(job).status_code, 409)
        self.assertFalse(self.get(job, "alice").json()["publication_allowed"])

    def test_revocation_and_private_pack_remain_closed(self):
        _, _, run, _, _ = self.fixture(private=True)
        job = self.draft(run).json()["id"]
        for who in ("bob", "operator", "outsider"):
            self.assertEqual(self.get(job, who, "/script").status_code, 404)
            self.assertEqual(self.approve(job, who).status_code, 404)
        _, _, run, _, _ = self.fixture()
        job = self.draft(run).json()["id"]
        self.store._exec("DELETE FROM organization_members WHERE org_id=? AND subject=?", (self.org["id"], "bob"))
        self.assertEqual(self.approve(job).status_code, 404)

    def test_two_immutable_repair_children_then_human_escalation(self):
        _, _, run, _, _ = self.fixture()
        first = self.draft(run).json()["id"]
        self.motion._update(first, "FAILED", error="Synthetic QA failure")
        before = self.motion.record(first, "alice")
        child = self.draft(run, parent_id=first, repair_note="Correct approved narration timing")
        self.assertEqual(child.status_code, 201, child.text)
        second = child.json()["id"]
        self.assertEqual(self.motion.record(first, "alice"), before)
        self.assertEqual(self.draft(run, parent_id=first, repair_note="Duplicate retry").status_code, 409)
        self.assertEqual(self.render(second).status_code, 409)
        self.motion._update(second, "RETURNED")
        third = self.draft(run, parent_id=second, repair_note="Resolve human visual review")
        self.assertEqual(third.status_code, 201, third.text)
        self.motion._update(third.json()["id"], "FAILED")
        self.assertEqual(self.draft(run, parent_id=third.json()["id"], repair_note="Again").status_code, 409)

    def test_changed_approval_fields_and_audio_refuse_encoding(self):
        _, _, run, _, _ = self.fixture()
        response = self.client.post(f"/api/motion/runs/{run['id']}/draft", headers=self.headers("alice"), content=b"synthetic-audio")
        job = response.json()["id"]
        self.assertEqual(self.get(job, "bob", "/narration").content, b"synthetic-audio")
        self.assertEqual(self.approve(job).status_code, 200)
        row = self.motion.record(job, "alice")
        flow = json.loads(row["review_checks"]); flow["workflow"]["audience"] = "leadership"
        self.motion._update(job, "SCRIPT_APPROVED", review_checks=json.dumps(flow))
        with patch("server.motion_local.WORKERS.submit") as worker:
            self.assertEqual(self.render(job).status_code, 409)
            worker.assert_not_called()
        self.motion._update(job, "SCRIPT_APPROVED", review_checks=row["review_checks"])
        (self.motion.base / row["audio_name"]).write_bytes(b"changed")
        self.assertEqual(self.get(job, "bob", "/narration").status_code, 404)
        # Encoder checks stored narration hash before any render calls.
        self.motion._encode(job)
        self.assertIn("Narration has changed", self.motion.record(job, "alice")["error"])
        self.assertEqual(self.motion.record(job, "alice")["status"], "FAILED")

    def test_stale_metadata_has_no_content_and_revocation_has_no_metadata(self):
        _, _, run, _, source = self.fixture()
        job = self.draft(run).json()["id"]
        self.store.update("rmd_sources", source["id"], {"sha256": "0" * 64})
        response = self.get(job, "alice")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"id", "needs_update", "status", "next_action", "publication_allowed"})
        self.assertEqual(self.get(job, "bob", "/script").status_code, 409)
        self.assertEqual(self.approve(job).status_code, 409)
        self.store._exec("DELETE FROM organization_members WHERE org_id=? AND subject=?", (self.org["id"], "alice"))
        self.assertEqual(self.get(job, "alice").status_code, 404)

    def test_unfinished_or_cross_run_repairs_and_unsupported_format_denied(self):
        _, _, run, _, _ = self.fixture()
        job = self.draft(run).json()["id"]
        self.assertEqual(self.draft(run, parent_id=job, repair_note="Not failed").status_code, 409)
        self.assertEqual(self.draft(run, video_format="square").status_code, 422)

    def test_invalid_rmd_report_shape_fails_closed(self):
        from copy import deepcopy
        from server.motion_storyboard import from_evidence_run, MotionStoryRefused
        _, _, run, _, _ = self.fixture()
        for report in ("invalid", 42, None, {"content": {}}):
            changed = deepcopy(run); changed["report"] = report
            with self.assertRaises(MotionStoryRefused):
                from_evidence_run(self.service, self.alice, changed)

    def test_changed_audio_blocks_approval_and_approved_queue(self):
        _, _, run, _, _ = self.fixture()
        response = self.client.post(f"/api/motion/runs/{run['id']}/draft", headers=self.headers("alice"), content=b"synthetic-audio")
        job = response.json()["id"]
        story = self.get(job, "bob", "/script").json()
        row = self.motion.record(job, "alice")
        path = self.motion.base / row["audio_name"]
        path.write_bytes(b"tampered")
        body = dict(binding=story["workflow"]["binding"], reviewed_script=True,
                    checked_evidence=True, checked_audience_format=True, checked_narration_rights=True)
        self.assertEqual(self.client.post(f"/api/motion/jobs/{job}/script-approval", headers=self.headers("bob"), json=body).status_code, 409)
        path.write_bytes(b"synthetic-audio")
        self.assertEqual(self.approve(job).status_code, 200)
        path.write_bytes(b"tampered again")
        with patch("server.motion_local.WORKERS.submit") as worker:
            self.assertEqual(self.render(job).status_code, 409)
            worker.assert_not_called()

    def test_storyboard_tampering_is_not_the_reviewed_binding(self):
        _, _, run, _, _ = self.fixture()
        job = self.draft(run).json()["id"]
        row = self.motion.record(job, "alice")
        story = json.loads(row["storyboard"]); story["scenes"][0]["text"] = "Unverified claim"
        self.motion._update(job, "SCRIPT_REVIEW_REQUESTED", storyboard=json.dumps(story))
        self.assertEqual(self.get(job, "bob", "/script").status_code, 409)
        self.assertTrue(self.get(job, "alice").json()["needs_update"])

    def test_arabic_draft_requires_narration_and_never_enqueues(self):
        from copy import deepcopy
        from server.motion_local import MotionError
        from server.motion_storyboard import from_evidence_run
        _, _, run, _, _ = self.fixture()
        story = deepcopy(from_evidence_run(self.service, self.alice, run)); story["language"] = "ar"
        flow = {"audience": "internal", "format": "wide", "repair_attempt": 0}
        with patch("server.motion_local.WORKERS.submit") as worker:
            with self.assertRaises(MotionError):
                self.motion.create("alice", run["id"], run, None, storyboard=story, workflow=flow)
            job = self.motion.create("alice", run["id"], run, b"synthetic-arabic-audio", storyboard=story, workflow=flow)
            self.assertEqual(job["status"], "SCRIPT_REVIEW_REQUESTED")
            worker.assert_not_called()

    def test_concurrent_repair_claims_create_only_one_child(self):
        from concurrent.futures import ThreadPoolExecutor
        from server.motion_local import MotionError
        _, _, run, _, _ = self.fixture()
        job = self.draft(run).json()["id"]
        row = self.motion.record(job, "alice")
        self.motion._update(job, "FAILED")
        flow = dict(self.motion.workflow(row), parent_id=job, repair_attempt=1, repair_note="Synthetic correction")
        def create():
            try:
                return self.motion.create("alice", run["id"], run, None,
                    storyboard=json.loads(row["storyboard"]), workflow=flow)["id"]
            except MotionError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(sum(value is not None for value in results), 1)

    def test_concurrent_render_submits_once_and_queue_failure_is_recorded(self):
        from concurrent.futures import ThreadPoolExecutor
        from server.motion_local import MotionError
        _, _, run, _, _ = self.fixture()
        job = self.draft(run).json()["id"]
        self.assertEqual(self.approve(job).status_code, 200)
        def render():
            try:
                return self.motion.render_approved(job, "alice")["status"]
            except MotionError:
                return "refused"
        with patch("server.motion_local.WORKERS.submit") as worker:
            with ThreadPoolExecutor(max_workers=2) as pool:
                answers = list(pool.map(lambda _: render(), range(2)))
            self.assertEqual(sorted(answers), ["QUEUED", "refused"])
            worker.assert_called_once()
        other = self.draft(run).json()["id"]
        self.assertEqual(self.approve(other).status_code, 200)
        with patch("server.motion_local.WORKERS.submit", side_effect=RuntimeError("sensitive internal error")):
            response = self.render(other)
        self.assertEqual(response.status_code, 409)
        record = self.motion.record(other, "alice")
        self.assertEqual(record["status"], "FAILED")
        self.assertNotIn("sensitive", record["error"])

    def test_database_rollback_removes_only_its_new_audio(self):
        from server.motion_storyboard import from_evidence_run
        _, _, run, _, _ = self.fixture()
        story = from_evidence_run(self.service, self.alice, run)
        before = {path.name for path in self.motion.base.iterdir()}
        # Binding happens after insertion/audio write inside the same transaction.
        with patch.object(self.motion, "script_binding", side_effect=RuntimeError("synthetic database transaction failure")):
            with self.assertRaises(RuntimeError):
                self.motion.create("alice", run["id"], run, b"temporary-audio",
                    storyboard=story, workflow={"audience": "internal", "format": "wide", "repair_attempt": 0})
        self.assertEqual({path.name for path in self.motion.base.iterdir()}, before)

    def test_script_changed_after_approval_never_queues(self):
        _, _, run, _, _ = self.fixture()
        job = self.draft(run).json()["id"]
        self.assertEqual(self.approve(job).status_code, 200)
        row = self.motion.record(job, "alice")
        self.motion._update(job, "SCRIPT_APPROVED", storyboard=row["storyboard"] + " ")
        with patch("server.motion_local.WORKERS.submit") as worker:
            self.assertEqual(self.render(job).status_code, 409)
            worker.assert_not_called()

    def test_missing_workflow_cannot_impersonate_script_approval(self):
        _, _, run, _, _ = self.fixture()
        job = self.draft(run).json()["id"]
        self.motion._update(job, "SCRIPT_APPROVED", review_checks="{}")
        with patch("server.motion_local.WORKERS.submit") as worker:
            self.assertEqual(self.render(job).status_code, 409)
            worker.assert_not_called()
