"""Separation of duties (6 November 2026 review, Phase 3).

With AGENTIC_OS_SEPARATE_APPROVER on, the person who started an analysis
cannot approve its report; another person with the approve permission must.
Rejecting stays open to the starter. Off by default, so a one-person
workspace keeps working.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.model_gateway import ModelGateway
from server.runs import RunEngine, SelfApprovalRefused, separate_approver_from_env
from server.storage import open_store

try:
    from fastapi.testclient import TestClient
    from server.app import create_app
    from tests.support import closing, scoped_token
    HAVE_API = True
except ImportError:  # pragma: no cover - optional server dependencies
    HAVE_API = False

SECRET = "test-signing-secret-not-a-real-credential"


class EngineTests(unittest.TestCase):

    def engine(self, separate):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = open_store(None, Path(tmp.name) / "test.db")
        self.addCleanup(store.close)
        return RunEngine(store, Path(tmp.name) / "vault", ModelGateway(env={}),
                         publish_target="database", separate_approver=separate)

    def ready(self, engine, language="en"):
        run = engine.create_run("Synthetic separation of duties", owner="alice", language=language)
        for _ in range(40):
            if run["state"] == "awaiting_approval":
                return run
            run = engine.advance(run["id"])
        self.fail("The synthetic run did not reach its human gate")

    def test_off_by_default_the_starter_may_still_approve(self):
        engine = self.engine(None)
        self.assertFalse(engine.separate_approver)
        run = self.ready(engine)
        done = engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "alice")
        self.assertEqual(done["approvals"][0]["state"], "approved_once")

    def test_on_the_starter_is_refused_and_nothing_changes(self):
        engine = self.engine(True)
        run = self.ready(engine)
        with self.assertRaises(SelfApprovalRefused):
            engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "alice")
        after = engine.get_run(run["id"])
        self.assertEqual(after["state"], "awaiting_approval")
        self.assertEqual(after["approvals"][0]["state"], "pending")
        self.assertIsNone(after["report"]["published_path"])

    def test_an_unnamed_approver_is_refused(self):
        engine = self.engine(True)
        run = self.ready(engine)
        with self.assertRaises(SelfApprovalRefused):
            engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", None)

    def test_another_person_approves_and_is_recorded(self):
        engine = self.engine(True)
        run = self.ready(engine)
        done = engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "bob")
        self.assertEqual(done["approvals"][0]["state"], "approved_once")
        self.assertEqual(done["approvals"][0]["decided_by"], "bob")

    def test_the_starter_may_still_reject(self):
        engine = self.engine(True)
        run = self.ready(engine)
        done = engine.decide_approval(run["id"], run["approvals"][0]["id"], "reject", "alice")
        self.assertEqual(done["approvals"][0]["state"], "rejected")

    def test_the_refusal_speaks_the_report_language(self):
        engine = self.engine(True)
        run = self.ready(engine, language="ar")
        with self.assertRaises(SelfApprovalRefused) as caught:
            engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "alice")
        self.assertIn("شخص آخر", caught.exception.message)

    def test_the_setting_reads_only_explicit_yes_values(self):
        for value, expected in (("1", True), ("true", True), ("on", True),
                                ("", False), ("0", False), ("no", False)):
            with self.subTest(value=value), patch.dict(os.environ, {"AGENTIC_OS_SEPARATE_APPROVER": value}):
                self.assertEqual(separate_approver_from_env(), expected)


@unittest.skipUnless(HAVE_API, "server dependencies not installed")
class ApiTests(unittest.TestCase):

    def client(self, separate):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Separation Test",
                                      "memory_file": str(root / "memory.json"),
                                      "database_file": str(root / "agentic.db"),
                                      "vault_dir": str(root / "vault")}))
        env = {"AGENTIC_OS_JWT_SECRET": SECRET, "SUPABASE_URL": "https://test.supabase.invalid",
               "AGENTIC_OS_ENV": "production", "AGENTIC_OS_PUBLISH_TARGET": "database"}
        if separate:
            env["AGENTIC_OS_SEPARATE_APPROVER"] = "1"
        return TestClient(closing(self, create_app(config, env=env)), raise_server_exceptions=False)

    def auth(self, subject, role):
        return {"Authorization": "Bearer " + scoped_token(SECRET, subject=subject, role=role)}

    def pending(self, client, headers):
        run = client.post("/api/runs", json={"goal": "Separation of duties test run"},
                          headers=headers).json()
        for _ in range(40):
            if run["state"] == "awaiting_approval":
                return run
            run = client.post(f"/api/runs/{run['id']}/advance", headers=headers).json()
        self.fail("The run did not reach its human gate")

    def test_the_starter_gets_403_and_a_platform_approver_publishes(self):
        client = self.client(True)
        alice = self.auth("alice", "analyst")
        run = self.pending(client, alice)
        url = f"/api/runs/{run['id']}/approvals/{run['approvals'][0]['id']}"
        refused = client.post(url, json={"decision": "approve"}, headers=alice)
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(refused.json()["detail"]["code"], "self_approval")
        self.assertEqual(client.get(f"/api/runs/{run['id']}", headers=alice).json()["state"],
                         "awaiting_approval")
        # Runs are private to their owner; today only a platform administrator
        # can reach another person's run to approve it.
        approved = client.post(url, json={"decision": "approve"}, headers=self.auth("ops", "admin"))
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["approvals"][0]["decided_by"], "ops")

    def test_without_the_setting_the_starter_still_approves(self):
        client = self.client(False)
        alice = self.auth("alice", "analyst")
        run = self.pending(client, alice)
        url = f"/api/runs/{run['id']}/approvals/{run['approvals'][0]['id']}"
        self.assertEqual(client.post(url, json={"decision": "approve"}, headers=alice).status_code, 200)
