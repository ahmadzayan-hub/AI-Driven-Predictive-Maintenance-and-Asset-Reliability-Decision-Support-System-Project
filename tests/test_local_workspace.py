"""Synthetic local-owner workflow and browser boundary, no real credentials."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from server.app import create_app
from server.auth import build_identity
from server.local_workspace import FLAG, validate
from tests.support import closing

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("local_workspace_cli", ROOT / "scripts/local_workspace.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class ProfileTest(unittest.TestCase):
    def test_opt_in_reuses_owner_not_platform_admin(self):
        identity = build_identity({FLAG: "1"})
        principal = identity.authenticate(None)
        self.assertEqual((identity.mode, principal.subject, principal.role), ("local", "local-owner", "owner"))
        self.assertFalse(principal.can("admin"))
        self.assertFalse(identity.requires_token)

    def test_hosted_auth_remains_fail_closed(self):
        for env in ({"AGENTIC_OS_REQUIRE_AUTH": "1"}, {"AGENTIC_OS_ENV": "production"}):
            with self.subTest(env=env), self.assertRaises(RuntimeError):
                build_identity(env)

    def test_refuses_hosted_credentials_cloud_and_proxies_without_echo(self):
        cases = [{key: "sensitive-do-not-echo"} for key in (
            "VERCEL", "VERCEL_URL", "K_SERVICE", "AWS_LAMBDA_FUNCTION_NAME", "DYNO",
            "DATABASE_URL", "SUPABASE_URL", "SUPABASE_JWT_SECRET", "AGENTIC_OS_JWKS_URL",
            "AGENTIC_OS_JWT_SECRET", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AI_GATEWAY_MODEL")]
        cases += [{"AGENTIC_OS_REQUIRE_AUTH": "1"}, {"AGENTIC_OS_ENV": "production"},
                  {"AGENTIC_OS_DEMO": "1"}, {"OLLAMA_HOST": "https://cloud.invalid"},
                  {"OLLAMA_HOST": "http://[::1%lo]:11434"}, {"OLLAMA_HOST": "http://[::1%25lo]:11434"},
                  {"OLLAMA_MODEL": "model:cloud"}, {"AGENTIC_OS_HERMES_MODEL": "ollama:model-cloud"},
                  {"AGENTIC_OS_AGENT_MODEL": "ollama:model:cloud"}, {"AGENTIC_OS_CONSULTANTS": "ollama,ollama:model-cloud"},
                  {"AGENTIC_OS_VAULT_DIR": "/outside"}, {"VITE_API_BASE": "https://outside.invalid"}, {"AGENTIC_OS_TASK_MODELS": "chat=openai"}]
        for env in cases:
            with self.subTest(setting=next(iter(env))):
                with self.assertRaises(RuntimeError) as result:
                    build_identity({FLAG: "1", **env})
                self.assertNotIn("sensitive-do-not-echo", str(result.exception))
                self.assertNotIn(FLAG, env)

    def test_refuses_database_config_before_opening_store(self):
        with self.assertRaises(RuntimeError):
            validate({FLAG: "1"}, {"database_url": "postgresql://synthetic.invalid"})


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.config, _ = cli.workspace_config(self.workspace)
        self.env = {FLAG: "1", "AGENTIC_OS_RATE_LIMIT_STORE": "1"}

    def client(self, host="127.0.0.1", peer="127.0.0.1", env=None):
        app = closing(self, create_app(self.config, env={**self.env, **(env or {})}))
        return TestClient(app, base_url="http://" + host, client=(peer, 50000))

    def test_same_origin_owner_entry_upload_analysis_and_restart(self):
        client = self.client()
        self.assertEqual(client.get("/api/auth/config").json(), {"mode": "local", "flows": []})
        result = client.post("/api/runs", headers={"Origin": "http://127.0.0.1", "Sec-Fetch-Site": "same-origin"}, json={
            "goal": "Analyze synthetic totals", "dataset_text": "team,sales\nA,100\nB,150\n", "dataset_name": "synthetic.csv"})
        self.assertEqual(result.status_code, 201, result.text)
        run_id = result.json()["id"]
        for _ in range(30):
            run = client.post(f"/api/runs/{run_id}/advance").json()
            if run["state"] == "awaiting_approval":
                break
        self.assertEqual(run["state"], "awaiting_approval")
        restarted = self.client()
        self.assertEqual(restarted.get(f"/api/runs/{run_id}").json()["state"], "awaiting_approval")
        self.assertEqual(len(restarted.get("/api/datasets").json()["datasets"]), 1)

    def test_browser_and_proxy_boundary(self):
        client = self.client()
        bad_headers = [
            {"Host": "attacker.invalid"}, {"Host": "127.0.0.1.attacker.invalid"},
            {"Host": "0.0.0.0"}, {"Origin": "https://attacker.invalid"}, {"Origin": "null"},
            {"Origin": "http://127.0.0.1:9999"}, {"Origin": "http://localhost"},
            {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"},
            {"Forwarded": "for=127.0.0.1"}, {"X-Forwarded-For": "127.0.0.1"},
            {"X-Forwarded-Host": "localhost"}, {"X-Forwarded-Proto": "http"},
            {"X-Real-IP": "127.0.0.1"}, [("Host", "127.0.0.1"), ("Host", "attacker.invalid")],
        ]
        for headers in bad_headers:
            with self.subTest(headers=headers):
                self.assertEqual(client.post("/api/sessions", headers=headers).status_code, 403)
                self.assertEqual(client.get("/api/identity", headers=headers).status_code, 403)
        self.assertEqual(self.client(peer="192.0.2.10").get("/api/identity").status_code, 403)
        self.assertEqual(self.client(host="0.0.0.0").get("/api/identity").status_code, 403)
        self.assertEqual(self.client(host="localhost").get("/api/identity").status_code, 200)

    def test_rate_limit_survives_restart(self):
        client = self.client(env={"AGENTIC_OS_RATE_LIMIT": "1"})
        self.assertEqual(client.post("/api/sessions").status_code, 201)
        restarted = self.client(env={"AGENTIC_OS_RATE_LIMIT": "1"})
        response = restarted.post("/api/sessions")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)

    def test_backup_restore_includes_memory_and_run_and_preserves_original(self):
        client = self.client()
        session_id = client.post("/api/sessions").json()["session_id"]
        saved = client.post(f"/api/sessions/{session_id}/memory", json={"information": "Synthetic fixture", "category": "work"})
        self.assertEqual(saved.status_code, 201, saved.text)
        run_id = client.post("/api/runs", json={"goal": "Synthetic recovery", "dataset_text": "a,b\n1,2\n3,4\n", "dataset_name": "fixture.csv"}).json()["id"]
        backup = self.root / "backup.json"
        target = self.root / "recovered"
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(cli.main(["backup", "--workspace", str(self.workspace), "--out", str(backup)]), 0)
            self.assertEqual(cli.main(["restore", "--workspace", str(target), "--from-backup", str(backup)]), 0)
            with self.assertRaises(RuntimeError):
                cli.main(["restore", "--workspace", str(self.workspace), "--from-backup", str(backup)])
            with self.assertRaises(FileExistsError):
                cli.main(["backup", "--workspace", str(self.workspace), "--out", str(backup)])
        payload = json.loads(backup.read_text())
        self.assertTrue(payload["tables"]["memory_kv"])
        recovered = TestClient(closing(self, create_app(target / "config.json", env=self.env)),
                               base_url="http://127.0.0.1", client=("127.0.0.1", 50000))
        self.assertEqual(recovered.get(f"/api/runs/{run_id}").status_code, 200)
        self.assertEqual(recovered.get(f"/api/sessions/{session_id}").status_code, 200)
        self.assertEqual(client.get(f"/api/runs/{run_id}").status_code, 200)
        # Recovery restores executable state, not only a static snapshot.
        self.assertEqual(recovered.post(f"/api/runs/{run_id}/advance").status_code, 200)

    def test_launcher_binds_loopback_and_disables_proxy_trust(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(cli.ROOT.__class__, "is_file", return_value=True), patch("uvicorn.run") as run:
            self.assertEqual(cli.main(["start", "--workspace", str(self.workspace)]), 0)
            self.assertEqual(os.environ[FLAG], "1")
            self.assertEqual(os.environ["AGENTIC_OS_RATE_LIMIT_STORE"], "1")
            self.assertEqual(run.call_args.kwargs["host"], "127.0.0.1")
            self.assertFalse(run.call_args.kwargs["proxy_headers"])
            self.assertEqual(run.call_args.kwargs["forwarded_allow_ips"], "")

    def test_unwritable_workspace_never_falls_back_to_temporary_storage(self):
        self.client()
        with patch("os.access", return_value=False), patch("tempfile.gettempdir", return_value=str(self.root / "fallback")):
            with self.assertRaises(PermissionError):
                self.client()
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(PermissionError):
                cli.main(["backup", "--workspace", str(self.workspace), "--out", str(self.root / "failed.json")])
        self.assertFalse((self.root / "fallback").exists())
        self.assertFalse((self.root / "failed.json").exists())

    def test_missing_database_cannot_be_backed_up_as_empty(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(RuntimeError):
            cli.main(["backup", "--workspace", str(self.workspace), "--out", str(self.root / "missing.json")])
        self.assertFalse((self.workspace / "agentic.db").exists())
        self.assertFalse((self.root / "missing.json").exists())

    def test_launcher_refuses_hosted_settings_without_mutation(self):
        with patch.dict(os.environ, {"AGENTIC_OS_REQUIRE_AUTH": "1"}, clear=True), patch("uvicorn.run") as run:
            with self.assertRaises(RuntimeError):
                cli.main(["start", "--workspace", str(self.workspace)])
            self.assertNotIn(FLAG, os.environ)
            self.assertEqual(os.environ["AGENTIC_OS_REQUIRE_AUTH"], "1")
            run.assert_not_called()


class ConcurrentBackupTest(unittest.TestCase):
    def test_backup_is_one_snapshot_while_another_connection_creates_a_run(self):
        from contextlib import closing as close_store
        import threading
        from server.storage import open_store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            _, config = cli.workspace_config(workspace)
            backup = root / "snapshot.json"
            with close_store(open_store(sqlite_path=config["database_file"])) as writer:
                attempted = threading.Event()
                completed = threading.Event()
                errors = []
                completed_during_snapshot = []
                # Signal at the actual transaction attempt, not merely when
                # the worker thread has been scheduled.
                writer._conn.set_trace_callback(
                    lambda sql: attempted.set() if sql == "BEGIN IMMEDIATE" else None)

                def create_run_concurrently():
                    try:
                        with writer.atomic("synthetic-concurrent-run"):
                            writer.insert("runs", {
                                "id": "synthetic-concurrent-run", "goal": "Synthetic fixture",
                                "dataset_name": "fixture.csv", "dataset_text": "a,b\n1,2\n",
                                "state": "running", "created_at": "2026-10-23",
                                "updated_at": "2026-10-23", "owner": "local-owner"})
                            writer.insert("tasks", {
                                "id": "synthetic-concurrent-task", "run_id": "synthetic-concurrent-run",
                                "idx": 0, "role": "collector", "title": "Collect", "state": "pending"})
                    except Exception as error:
                        errors.append(error)
                    finally:
                        completed.set()

                thread = threading.Thread(target=create_run_concurrently, daemon=True)
                original_backup = cli.create_backup

                def interleave_after_reading_runs(store):
                    original_exec = store._exec

                    def read_then_start_writer(sql, params=()):
                        rows = original_exec(sql, params)
                        if sql == "SELECT * FROM runs":
                            thread.start()
                            self.assertTrue(attempted.wait(5), "Concurrent writer never attempted its transaction")
                            completed_during_snapshot.append(completed.wait(0.2))
                        return rows

                    with patch.object(store, "_exec", side_effect=read_then_start_writer):
                        return original_backup(store)

                try:
                    with patch.dict(os.environ, {}, clear=True), patch.object(
                            cli, "create_backup", side_effect=interleave_after_reading_runs):
                        self.assertEqual(cli.main([
                            "backup", "--workspace", str(workspace), "--out", str(backup)]), 0)
                finally:
                    if thread.ident is not None:
                        thread.join(10)
                self.assertFalse(thread.is_alive(), "Concurrent writer did not finish after the backup")
                self.assertEqual(errors, [])
                self.assertEqual(completed_during_snapshot, [False])
                self.assertEqual(len(writer.export_all()["runs"]), 1)
                self.assertEqual(len(writer.export_all()["tasks"]), 1)
                snapshot = json.loads(backup.read_text(encoding="utf-8"))
                self.assertEqual(snapshot["tables"]["runs"], [])
                self.assertEqual(snapshot["tables"]["tasks"], [])


class LocalModelInventoryTest(unittest.TestCase):
    def test_model_inventory_rejects_remote_alias_without_generation(self):
        from unittest.mock import MagicMock
        from server.local_workspace import verify_local_model
        for entry, allowed in (({"name": "fixture-local", "size": 2_000_000}, True),
                               ({"name": "fixture-local", "size": 2_000_000, "remote_model": "remote"}, False),
                               ({"name": "fixture-local", "size": 2_000_000, "remote_host": "https://cloud.invalid"}, False)):
            with self.subTest(entry=entry):
                opener = MagicMock()
                opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({"models": [entry]}).encode()
                with patch("urllib.request.build_opener", return_value=opener):
                    if allowed:
                        verify_local_model({"OLLAMA_MODEL": "fixture-local", "OLLAMA_HOST": ""})
                    else:
                        with self.assertRaises(RuntimeError):
                            verify_local_model({"OLLAMA_MODEL": "fixture-local", "OLLAMA_HOST": ""})
                opener.open.assert_called_once_with("http://127.0.0.1:11434/api/tags", timeout=3)

    def test_direct_app_checks_inventory_before_opening_any_store(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, _ = cli.workspace_config(Path(temporary) / "workspace")
            with patch("server.local_workspace.verify_local_model", side_effect=RuntimeError("Synthetic missing local model")), patch("server.app.open_store") as store:
                with self.assertRaises(RuntimeError):
                    create_app(config, env={FLAG: "1", "OLLAMA_MODEL": "fixture-local"})
                store.assert_not_called()

    def test_absent_model_makes_no_inventory_request(self):
        from server.local_workspace import verify_local_model
        with patch("urllib.request.build_opener") as opener:
            verify_local_model({})
            opener.assert_not_called()
            with self.assertRaises(RuntimeError):
                verify_local_model({"OLLAMA_HOST": "http://127.0.0.1:11434"})
            opener.assert_not_called()
