"""Backup and restore drill.

These tests do not check that a backup file "looks right" — they destroy
the database and rebuild it from the backup, then assert that the work
inside it survived: the run, its tasks and evidence, the approval
decision, the published vault note, agent memory, the conversation
session, and the stored dataset. One case advances a restored run to
completion, because a backup that restores rows but not the ability to
continue working is not a recovery.

The whole suite runs twice: once against SQLite and once against
PostgreSQL (see RunEnginePostgresTestCase for the same pattern).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_runs import FASTAPI_AVAILABLE, PG_TEST_URL, _postgres_available

if FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient

    from server.app import create_app

from server import analytics
from tests.support import closing, closing_store
from server.backup import (BACKUP_VERSION, backup_counts, create_backup,
                           open_configured_store, restore_backup)
from server.storage import TABLES

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class BackupRestoreTestCase(unittest.TestCase):
    """Drill against the SQLite store (the local default)."""

    # Local mode keeps agent memory in data/memory.json (the original
    # file contract), so memory_kv is empty here; hosted mode keeps it in
    # the database. The drill asserts the right thing for each mode
    # instead of pretending the two are the same.
    memory_in_database = False

    def database_config(self):
        return {"database_file": str(self.root / "agentic.db")}

    def wipe_database(self):
        """Destroy the database the way an incident would.

        An incident takes the file once the processes holding it are gone,
        so every handle this test opened is released first - earlier
        clients, and the stores the test opened itself, not just the
        latest client. Windows refuses to unlink a file another handle
        still has open, and `close` is idempotent.
        """
        for store in self.handles:
            store.close()
        for suffix in ("", "-wal", "-shm"):
            Path(str(self.root / "agentic.db") + suffix).unlink(missing_ok=True)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.handles = []
        self.root = Path(self.temp_dir.name)
        self.vault = self.root / "vault"
        self.config_path = self.root / "config.json"
        config = {
            "agent_name": "Backup Test Agent",
            "memory_file": str(self.root / "memory.json"),
            "vault_dir": str(self.vault),
        }
        config.update(self.database_config())
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        self.client = self.new_client()

    def new_client(self):
        """A fresh application instance over the same database."""
        app = closing(self, create_app(self.config_path))
        store = getattr(getattr(app, "state", None), "store", None)
        if store is not None:
            self.handles.append(store)
        return TestClient(app, raise_server_exceptions=False)

    def store(self):
        store = closing_store(
            self, open_configured_store(env={}, config_path=self.config_path))
        self.handles.append(store)
        return store

    # -- helpers ----------------------------------------------------------
    def advance_until(self, run_id, stop_states, limit=None):
        # One advance per task, plus slack: a short loop would
        # 'fail' by simply not arriving.
        limit = limit or len(analytics.PIPELINE) + 5
        run = None
        for _ in range(limit):
            run = self.client.post(f"/api/runs/{run_id}/advance").json()
            if run["state"] in stop_states:
                return run
        return run

    def seed_everything(self):
        """Produce one row in every table a user's work touches."""
        session = self.client.post("/api/sessions").json()
        self.client.post(
            f"/api/sessions/{session['session_id']}/memory",
            json={"information": "Quarterly review is on Thursday",
                  "category": "work"})
        run = self.client.post("/api/runs", json={
            "goal": "Analyze team sales",
            "dataset_text": "team,quarter,sales\nA,Q1,100\nA,Q2,150\nB,Q1,90\nB,Q2,60\n",
            "dataset_name": "team-sales.csv"}).json()
        run = self.advance_until(run["id"], {"awaiting_approval"})
        self.assertEqual(run["state"], "awaiting_approval")
        approved = self.client.post(
            f"/api/runs/{run['id']}/approvals/{run['approvals'][0]['id']}",
            json={"decision": "approve"}).json()
        self.assertEqual(approved["state"], "completed")
        return session["session_id"], approved

    # -- the drill --------------------------------------------------------
    def test_a_destroyed_database_is_rebuilt_from_a_backup(self):
        session_id, original = self.seed_everything()
        notes_before = self.client.get("/api/vault").json()["notes"]
        datasets_before = self.client.get("/api/datasets").json()["datasets"]

        backup_file = self.root / "backup.json"
        taken = self.run_script("backup.py", "--out", str(backup_file))
        self.assertGreater(taken["total_rows"], 0)
        expected = ["runs", "tasks", "approvals", "artifacts", "sessions",
                    "vault_notes", "datasets"]
        if self.memory_in_database:
            expected.append("memory_kv")
        for table in expected:
            self.assertGreater(taken["rows"][table], 0, table)

        self.wipe_database()
        empty = self.new_client()
        self.assertEqual(empty.get(f"/api/runs/{original['id']}").status_code, 404)

        restored = self.run_script("restore.py", str(backup_file), "--yes")
        self.assertEqual(restored["restored_rows"], taken["total_rows"])

        recovered_client = self.new_client()
        recovered = recovered_client.get(f"/api/runs/{original['id']}").json()
        self.assertEqual(recovered["state"], "completed")
        self.assertEqual(len(recovered["tasks"]), len(original["tasks"]))
        self.assertEqual(recovered["report"]["content"],
                         original["report"]["content"])
        self.assertIn("total_sales | 400.0", recovered["report"]["content"])
        # A restored approval stays spent: recovery must not hand back a
        # second chance to publish an already-published report.
        self.assertEqual(recovered["approvals"][0]["state"], "approved_once")
        replay = recovered_client.post(
            f"/api/runs/{original['id']}/approvals/"
            f"{recovered['approvals'][0]['id']}", json={"decision": "approve"})
        self.assertEqual(replay.status_code, 409)
        # Evidence, not just rows: the validator's checks came back too.
        validator = next(t for t in recovered["tasks"] if t["role"] == "validator")
        self.assertTrue(all(c["passed"] for c in validator["quality_checks"]))

        self.assertEqual(
            [n["path"] for n in recovered_client.get("/api/vault").json()["notes"]],
            [n["path"] for n in notes_before])
        self.assertEqual(
            [d["sha256"] for d in recovered_client.get("/api/datasets").json()["datasets"]],
            [d["sha256"] for d in datasets_before])
        session = recovered_client.get(f"/api/sessions/{session_id}").json()
        self.assertIn("Quarterly review is on Thursday", session["memory"].values())

    def test_a_restored_run_can_still_be_advanced(self):
        run = self.client.post("/api/runs", json={
            "goal": "Analyze the sample sales dataset"}).json()
        for _ in range(4):
            self.client.post(f"/api/runs/{run['id']}/advance")

        payload = create_backup(self.store())
        self.wipe_database()
        self.assertEqual(restore_backup(self.store(), payload),
                         sum(backup_counts(payload).values()))

        client = self.new_client()
        resumed = client.get(f"/api/runs/{run['id']}").json()
        self.assertEqual(
            len([t for t in resumed["tasks"] if t["state"] == "succeeded"]), 4)
        # A recovered run is not a museum piece: it continues to approval.
        for _ in range(len(analytics.PIPELINE) + 5):
            state = client.post(f"/api/runs/{run['id']}/advance").json()
            if state["state"] == "awaiting_approval":
                break
        self.assertEqual(state["state"], "awaiting_approval")
        decided = client.post(
            f"/api/runs/{run['id']}/approvals/{state['approvals'][0]['id']}",
            json={"decision": "approve"}).json()
        self.assertEqual(decided["state"], "completed")

    def test_restore_replaces_the_database_rather_than_merging_into_it(self):
        keeper = self.client.post("/api/runs", json={"goal": "Before backup"}).json()
        payload = create_backup(self.store())
        stray = self.client.post("/api/runs", json={"goal": "After backup"}).json()

        restore_backup(self.store(), payload)

        client = self.new_client()
        self.assertEqual(client.get(f"/api/runs/{keeper['id']}").status_code, 200)
        self.assertEqual(client.get(f"/api/runs/{stray['id']}").status_code, 404)

    def test_an_unreadable_backup_is_refused_before_anything_is_deleted(self):
        self.client.post("/api/runs", json={"goal": "Must survive"})
        store = self.store()
        before = store.export_all()

        for bad, reason in [
            ({}, "no tables key"),
            ({"version": BACKUP_VERSION + 99, "tables": {}}, "future version"),
            ({"version": BACKUP_VERSION, "tables": {"secrets": []}}, "unknown table"),
        ]:
            with self.assertRaises(ValueError, msg=reason):
                restore_backup(store, bad)
        # The refusal happened before any DELETE ran.
        self.assertEqual(store.export_all(), before)

    def test_a_failure_part_way_through_a_restore_changes_nothing(self):
        # Assessment finding B5: deletes and inserts are one transaction,
        # so an insert that fails midway rolls the deletes back too.
        self.seed_everything()
        store = self.store()
        before = {table: len(rows) for table, rows in store.export_all().items()}
        payload = create_backup(store)
        total = sum(before.values())
        self.assertGreater(total, 5)
        halfway = total // 2
        seen = {"n": 0}
        real_insert = store.insert

        def failing_insert(table, row):
            seen["n"] += 1
            if seen["n"] == halfway:
                raise RuntimeError("simulated connection loss")
            return real_insert(table, row)

        store.insert = failing_insert
        with self.assertRaises(RuntimeError):
            restore_backup(store, payload)
        store.insert = real_insert
        after = {table: len(rows) for table, rows in store.export_all().items()}
        self.assertEqual(after, before)
        # And the store still works after the rollback.
        self.assertEqual(restore_backup(store, payload), total)

    def test_a_row_with_an_unknown_column_is_refused_before_any_delete(self):
        self.seed_everything()
        store = self.store()
        before = store.export_all()
        payload = create_backup(store)
        payload["tables"]["runs"][0] = dict(payload["tables"]["runs"][0],
                                             not_a_column="x")
        statements = []
        real_exec = store._exec

        def spying_exec(sql, params=()):
            statements.append(sql)
            return real_exec(sql, params)

        store._exec = spying_exec
        try:
            with self.assertRaises(ValueError) as refused:
                restore_backup(store, payload)
        finally:
            store._exec = real_exec
        self.assertIn("not_a_column", str(refused.exception))
        self.assertFalse([s for s in statements if s.lstrip().upper().startswith("DELETE")])
        self.assertEqual(store.export_all(), before)
        # A table whose rows are not rows is refused the same way.
        with self.assertRaises(ValueError):
            restore_backup(store, {"version": BACKUP_VERSION, "tables": {"runs": ["x"]}})
        self.assertEqual(store.export_all(), before)

    def test_agent_memory_is_backed_up_wherever_that_mode_stores_it(self):
        session = self.client.post("/api/sessions").json()
        self.client.post(f"/api/sessions/{session['session_id']}/memory",
                         json={"information": "Review is on Thursday"})
        payload = create_backup(self.store())
        memory_file = self.root / "memory.json"

        if self.memory_in_database:
            self.assertTrue(payload["tables"]["memory_kv"])
            self.assertFalse(memory_file.exists())
        else:
            # Local mode keeps the original memory.json file contract, so
            # a database backup does NOT contain memory: an operator must
            # back that file up too (documented in ADR 0005).
            self.assertEqual(payload["tables"]["memory_kv"], [])
            self.assertIn("Thursday", memory_file.read_text(encoding="utf-8"))

    def test_the_backup_covers_every_table_the_store_creates(self):
        # A new table that nobody adds to TABLES would silently not be
        # backed up; this ties the backup to the schema itself.
        payload = create_backup(self.store())
        self.assertEqual(set(payload["tables"]), set(TABLES))

    # -- CLI --------------------------------------------------------------
    @staticmethod
    def bare_environment(root=None):
        """The smallest environment the script can still run in.

        The point is that the script reads its configuration from --config and
        needs nothing from the caller's environment. On Windows that cannot be
        taken literally: Winsock initialises from SystemRoot, so a subprocess
        without it fails every socket call, and psycopg2 reports it as an
        OperationalError carrying no message at all. The SQLite drill passed and
        the PostgreSQL one failed for that reason alone. SystemRoot is the
        platform's floor, not a dependency of the script.
        """
        env = {"PATH": "/usr/bin:/bin", "HOME": str(root)}
        if os.name == "nt":
            for key in ("SystemRoot", "SYSTEMROOT"):
                if key in os.environ:
                    env[key] = os.environ[key]
        return env

    def run_script(self, name, *args):
        """Run the operator-facing script and return its JSON summary."""
        completed = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / name),
             *args, "--config", str(self.config_path)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env=self.bare_environment(self.root))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_restore_refuses_to_overwrite_without_confirmation(self):
        payload = create_backup(self.store())
        backup_file = self.root / "backup.json"
        backup_file.write_text(json.dumps(payload), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "restore.py"),
             str(backup_file), "--config", str(self.config_path)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--yes", completed.stderr)


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class BackupRestorePostgresTestCase(BackupRestoreTestCase):
    """The same drill against hosted mode, where it actually matters."""

    memory_in_database = True

    def database_config(self):
        return {"database_url": PG_TEST_URL}

    def _drop_all(self):
        import psycopg2

        conn = psycopg2.connect(PG_TEST_URL)
        conn.autocommit = True
        conn.cursor().execute(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE")
        conn.close()

    def wipe_database(self):
        self._drop_all()

    def setUp(self):
        self._drop_all()
        super().setUp()


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class CrossDialectRestoreTestCase(unittest.TestCase):
    """A backup carries no dialect, so a local database restores into a
    hosted one. That is both a disaster-recovery property and the
    supported way to move an existing local install to hosted mode."""

    def test_a_sqlite_backup_restores_into_postgresql(self):
        import psycopg2

        from server.storage import open_store

        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)

        local_config = root / "local.json"
        local_config.write_text(json.dumps({
            "agent_name": "Local", "memory_file": str(root / "memory.json"),
            "vault_dir": str(root / "vault"),
            "database_file": str(root / "agentic.db")}), encoding="utf-8")
        local = TestClient(closing(self, create_app(local_config)), raise_server_exceptions=False)
        run = local.post("/api/runs", json={
            "goal": "Local work that must survive the move",
            "dataset_text": "team,sales\nA,100\nB,90\n",
            "dataset_name": "local.csv"}).json()
        for _ in range(len(analytics.PIPELINE) + 5):
            run = local.post(f"/api/runs/{run['id']}/advance").json()
            if run["state"] == "awaiting_approval":
                break
        self.assertEqual(run["state"], "awaiting_approval")

        payload = create_backup(
            closing_store(self, open_store(None, root / "agentic.db")))

        conn = psycopg2.connect(PG_TEST_URL)
        conn.autocommit = True
        conn.cursor().execute(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE")
        conn.close()
        restore_backup(closing_store(self, open_store(PG_TEST_URL)), payload)

        hosted_config = root / "hosted.json"
        hosted_config.write_text(json.dumps({
            "agent_name": "Hosted", "memory_file": str(root / "memory.json"),
            "vault_dir": str(root / "vault-hosted"),
            "database_url": PG_TEST_URL}), encoding="utf-8")
        hosted = TestClient(closing(self, create_app(hosted_config)), raise_server_exceptions=False)
        moved = hosted.get(f"/api/runs/{run['id']}").json()
        self.assertEqual(moved["report"]["content"], run["report"]["content"])
        self.assertIn("total_sales | 190.0", moved["report"]["content"])
        # And the run continues in its new home.
        decided = hosted.post(
            f"/api/runs/{run['id']}/approvals/{moved['approvals'][0]['id']}",
            json={"decision": "approve"}).json()
        self.assertEqual(decided["state"], "completed")


if __name__ == "__main__":
    unittest.main()
