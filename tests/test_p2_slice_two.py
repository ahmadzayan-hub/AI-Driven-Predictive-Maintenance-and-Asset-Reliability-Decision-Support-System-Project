"""The second P2 slice (assessment B9, B12, B13, B14, B16, G11): the
database as publish target, logged failures with 503 on outages, one error
envelope and the contract behind sign-in, a required connector allowlist
in production, recorded schema migrations and a loud optional-runtime job."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from server import connectors, storage
from server.app import create_app
from server.connectors import ConnectorError
from server.model_gateway import ModelGateway
from server.runs import RunEngine
from server.storage import open_store
from tests.support import closing, closing_store

ROOT = Path(__file__).resolve().parent.parent


class PublishTargetTest(unittest.TestCase):
    """B13: the store is the publish target; the vault folder is a courtesy."""

    def engine(self, vault):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = open_store(None, Path(tmp.name) / "agentic.db")
        closing_store(self, store)
        return RunEngine(store, vault, ModelGateway(env={})), store

    def approve(self, engine):
        run = engine.create_run("Analyze the sample sales dataset")
        for _ in range(40):
            run = engine.advance(run["id"])
            if run["state"] == "awaiting_approval":
                break
        self.assertEqual(run["state"], "awaiting_approval")
        approval = next(a for a in run["approvals"] if a["state"] == "pending")
        return engine.decide_approval(run["id"], approval["id"], "approve", approver="owner")

    def test_an_unwritable_vault_still_publishes_to_the_store(self):
        blocker = tempfile.NamedTemporaryFile(delete=False)
        self.addCleanup(os.unlink, blocker.name)
        blocker.close()
        # A file where the vault folder should be: every mkdir fails.
        engine, store = self.engine(Path(blocker.name))
        run = self.approve(engine)
        self.assertEqual(run["state"], "completed")
        self.assertTrue(run["report"]["published_path"].startswith("store:Reports/"))
        publish = next(t for t in run["tasks"] if t["role"] == "publish")
        self.assertIn("database store", publish["summary"])
        paths = {n["path"] for n in store.list_notes()}
        self.assertIn(f"Runs/{run['id']}.md", paths)
        self.assertTrue(any(p.startswith("Reports/") for p in paths))

    def test_a_writable_vault_gets_both_notes_and_the_store_too(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        engine, store = self.engine(Path(tmp.name) / "vault")
        run = self.approve(engine)
        self.assertEqual(len(list((Path(tmp.name) / "vault" / "Reports").glob("*.md"))), 1)
        self.assertEqual(len(list((Path(tmp.name) / "vault" / "Runs").glob("*.md"))), 1)
        self.assertEqual(len(store.list_notes()), 2)
        self.assertNotIn("store:", run["report"]["published_path"])

    def test_the_model_timeout_is_clamped_on_vercel(self):
        self.assertEqual(ModelGateway(env={"AGENTIC_OS_MODEL_TIMEOUT_SECONDS": "60"}).timeout, 60)
        self.assertEqual(ModelGateway(env={"AGENTIC_OS_MODEL_TIMEOUT_SECONDS": "60", "VERCEL": "1"}).timeout, 12)


class FailingMemoryStore:
    def __init__(self, error):
        self.error = error

    def memory_load(self, owner):
        raise self.error


class NarrowExceptTest(unittest.TestCase):
    """B9: an outage reads as empty memory, a bug surfaces."""

    def test_a_database_error_reads_as_empty_and_anything_else_raises(self):
        backend = storage.DbMemoryBackend(FailingMemoryStore(sqlite3.OperationalError("locked")))
        with self.assertLogs("agentic.storage", level="WARNING"):
            self.assertEqual(backend.load(), {})
        with self.assertRaises(KeyError):
            storage.DbMemoryBackend(FailingMemoryStore(KeyError("bug"))).load()

    def test_is_database_error_knows_the_drivers(self):
        self.assertTrue(storage.is_database_error(sqlite3.OperationalError()))
        self.assertFalse(storage.is_database_error(ValueError()))


class ApiEnvelopeTest(unittest.TestCase):
    """B14 and B9 at the API: one error shape, 503 on an outage, the
    contract behind sign-in."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Slice Two", "memory_file": str(root / "memory.json"),
                                      "vault_dir": str(root / "vault")}), encoding="utf-8")
        self.app = create_app(config)
        self.client = TestClient(closing(self, self.app), raise_server_exceptions=False)

    def test_a_404_carries_detail_and_the_error_object(self):
        response = self.client.get("/api/vault/note", params={"path": "nope.md"})
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["detail"], "Note not found.")
        self.assertEqual(body["error"]["code"], "not_found")
        self.assertEqual(body["error"]["message"], "Note not found.")
        self.assertEqual(body["error"]["request_id"], response.headers["X-Request-ID"])
        self.assertTrue(response.headers.get("X-Request-ID"))

    def test_a_422_from_validation_has_the_same_shape(self):
        response = self.client.post("/api/runs", json={"goal": 7})
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertIsInstance(body["detail"], list)
        self.assertEqual(body["error"]["code"], "validation_failed")
        self.assertTrue(body["error"]["problems"])

    def test_a_database_outage_is_a_503_and_is_logged_with_the_request_id(self):
        def outage(*args, **kwargs):
            raise sqlite3.OperationalError("database is locked")
        original = storage.SqlStore.list_runs
        storage.SqlStore.list_runs = outage
        self.addCleanup(setattr, storage.SqlStore, "list_runs", original)
        with self.assertLogs("agentic_os.errors", level="ERROR") as logs:
            response = self.client.get("/api/runs", headers={"X-Request-ID": "req-slice-two"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "database_unavailable")
        self.assertTrue(any("req-slice-two" in line for line in logs.output))

    def test_the_contract_is_served_to_a_reader_and_not_at_the_public_path(self):
        # The public paths are not the contract: with a built interface the
        # SPA fallback answers them with the app page, otherwise the JSON
        # 404 envelope. Neither carries the contract's paths.
        for path in ("/openapi.json", "/docs"):
            public = self.client.get(path)
            is_json = public.headers.get("content-type", "").split(";")[0] == "application/json"
            body = public.json() if is_json else {}
            self.assertNotIn("paths", body, path)
            if is_json:
                self.assertEqual(public.status_code, 404, path)
        response = self.client.get("/api/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/runs", response.json()["paths"])


class ConnectorAllowlistTest(unittest.TestCase):
    """B16: production without an allowlist refuses every live source."""

    def test_production_without_an_allowlist_refuses_and_a_list_admits(self):
        with self.assertRaises(ConnectorError) as refused:
            connectors._parts("https://data.example.org/feed.csv", {"AGENTIC_OS_ENV": "production"})
        self.assertIn("AGENTIC_OS_CONNECTOR_HOSTS", refused.exception.args[0])
        host, _, _ = connectors._parts("https://data.example.org/feed.csv",
                                       {"VERCEL": "1", "AGENTIC_OS_CONNECTOR_HOSTS": "data.example.org"})
        self.assertEqual(host, "data.example.org")
        host, _, _ = connectors._parts("https://data.example.org/feed.csv", {})
        self.assertEqual(host, "data.example.org", "local mode stays open")

    def test_is_production_reads_the_hosted_signals(self):
        self.assertTrue(connectors.is_production({"VERCEL": "1"}))
        self.assertTrue(connectors.is_production({"AGENTIC_OS_JWKS_URL": "https://x/jwks"}))
        self.assertFalse(connectors.is_production({}))


class SchemaVersionTest(unittest.TestCase):
    """B12: the migration pass runs once and is recorded."""

    def test_the_version_is_recorded_and_the_pass_is_skipped_next_time(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "a.db"
        first = open_store(None, path)
        self.assertEqual(first._schema_version(), storage.SCHEMA_VERSION)
        first.close()
        calls = []
        original = storage.SqlStore._migrate
        storage.SqlStore._migrate = lambda self: calls.append(1)
        try:
            second = open_store(None, path)
            closing_store(self, second)
        finally:
            storage.SqlStore._migrate = original
        self.assertEqual(calls, [], "a database at the current version skips the migration pass")


class OptionalRuntimeGuardTest(unittest.TestCase):
    """G11: with the flag set, a missing runtime fails the module."""

    def test_the_flag_turns_a_skip_into_a_failure(self):
        try:
            import langgraph  # noqa: F401
            import pydantic_ai  # noqa: F401
            self.skipTest("the optional runtimes are installed here, so the guard admits them")
        except ImportError:
            pass
        env = dict(os.environ, REQUIRE_OPTIONAL_RUNTIMES="1")
        result = subprocess.run([sys.executable, "-m", "unittest", "tests.test_frameworks"],
                                cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REQUIRE_OPTIONAL_RUNTIMES", result.stderr)


if __name__ == "__main__":
    unittest.main()
