"""Worker execution stays off request threads and reports observed readiness."""

import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from server import analytics
from server.model_gateway import ModelGateway
from server.runs import RunEngine, _stamp
from server.storage import open_store
from server.worker import RunWorker, main, worker_status
from server.app import create_app
from tests.support import closing


class DurableExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = self.open_store()
        self.engine = self.engine_for(self.store)

    def open_store(self):
        store = open_store(None, self.root / "runs.db")
        self.addCleanup(store.close)
        return store

    def engine_for(self, store):
        return RunEngine(store, self.root / "vault", ModelGateway({}),
                         execution_mode="worker")

    def test_worker_mode_requests_are_idempotent_reads_until_a_worker_executes(self):
        run = self.engine.create_run("Analyze the sample", owner="alice")
        for _ in range(3):
            state = self.engine.advance(run["id"])
            self.assertEqual(state["execution"], {"mode": "worker", "poll_after_ms": 2500})
            self.assertEqual(state["state"], "queued")
            self.assertTrue(all(task["state"] == "pending" for task in state["tasks"]))
        worker_store = self.open_store()
        worker = RunWorker(self.engine_for(worker_store), worker_store)
        self.assertEqual(worker.step(), run["id"])
        self.assertEqual(self.engine.get_run(run["id"])["state"], "awaiting_approval")
        self.assertFalse((self.root / "vault" / "Reports").exists())

    def test_a_request_reads_durable_state_while_an_independent_worker_stage_is_blocked(self):
        run = self.engine.create_run("Analyze the sample")
        worker_store = self.open_store()
        worker = RunWorker(self.engine_for(worker_store), worker_store)
        entered, release, read_finished = threading.Event(), threading.Event(), threading.Event()
        errors, responses = [], []
        role, original = analytics.PIPELINE[0]

        def delayed(context):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("Test did not release the bounded stage")
            return original(context)

        def work():
            try:
                worker.step()
            except BaseException as error:
                errors.append(error)

        def request():
            try:
                responses.append(self.engine.advance(run["id"]))
            except BaseException as error:
                errors.append(error)
            finally:
                read_finished.set()

        pipeline = [(role, delayed), *analytics.PIPELINE[1:]]
        with patch.object(analytics, "PIPELINE", pipeline):
            thread = threading.Thread(target=work)
            thread.start()
            reader = None
            try:
                self.assertTrue(entered.wait(5))
                reader = threading.Thread(target=request)
                reader.start()
                self.assertTrue(read_finished.wait(2), "Read waited for the slow stage transaction")
                self.assertEqual(responses[0]["state"], "queued")
            finally:
                release.set()
                thread.join(15)
                if reader:
                    reader.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_worker_configuration_survives_restart_without_client_advances(self):
        run = self.engine.create_run("Analyze the sample")
        first_store = self.open_store()
        first = RunWorker(self.engine_for(first_store), first_store, worker_id="first")
        self.assertEqual(first.claim(), run["id"])
        first.engine.advance(run["id"], lease_owner="first")
        # Equivalent durable state after a stopped process: the committed
        # stage remains, and only an expired lease permits a successor.
        self.store.update("runs", run["id"], {"lease_expires_at": "2000-01-01T00:00:00.000000+00:00"})
        second_store = self.open_store()
        second = RunWorker(self.engine_for(second_store), second_store, worker_id="second")
        self.assertEqual(second.step(), run["id"])
        self.assertEqual(self.engine.get_run(run["id"])["state"], "awaiting_approval")
        self.assertEqual(len({task["id"] for task in self.engine.get_run(run["id"])["tasks"]}),
                         len(self.engine.get_run(run["id"])["tasks"]))

    def test_heartbeat_readiness_expires_and_graceful_shutdown_is_immediate(self):
        now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        worker = RunWorker(self.engine, self.store, clock=lambda: now)
        self.assertFalse(worker_status(self.store, "worker", lambda: now)["ready"])
        worker.heartbeat("running")
        status = worker_status(self.store, "worker", lambda: now)
        self.assertTrue(status["ready"])
        self.assertNotIn(worker.worker_id, str(status))
        self.assertFalse(worker_status(self.store, "worker", lambda: now + timedelta(seconds=121))["ready"])
        worker.heartbeat("stopped")
        self.assertFalse(worker_status(self.store, "worker", lambda: now)["ready"])
        self.assertTrue(worker_status(self.store, "client", lambda: now)["ready"])

    def test_invalid_or_future_heartbeats_do_not_claim_readiness(self):
        now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        for value in ("bad", "2026-10-21", _stamp(now + timedelta(days=1))):
            self.store.upsert_worker_heartbeat("future", value, "running")
            self.assertFalse(worker_status(self.store, "worker", lambda: now)["ready"])

    def test_worker_exception_details_are_not_logged(self):
        worker = RunWorker(self.engine, self.store)
        stop = threading.Event()
        output = io.StringIO()
        with patch.object(worker, "step", side_effect=RuntimeError("credential-value-private")):
            with redirect_stderr(output):
                worker.run_forever(stop=stop, sleep=lambda _: stop.set())
        self.assertIn("RuntimeError", output.getvalue())
        self.assertNotIn("credential-value-private", output.getvalue())
        self.assertEqual(self.store.list_worker_heartbeats()[0]["state"], "stopped")

    def test_one_shot_worker_is_not_advertised_as_ready_after_exit(self):
        worker_store = self.open_store()
        worker = RunWorker(self.engine_for(worker_store), worker_store)
        with patch("server.worker.build_worker", return_value=worker), redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--once"]), 0)
        self.assertFalse(worker_status(self.store, "worker")["ready"])
        self.assertEqual(self.store.list_worker_heartbeats()[0]["state"], "stopped")

    def test_invalid_execution_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            RunEngine(self.store, self.root / "vault", ModelGateway({}), execution_mode="wroker")

    def test_api_accepts_worker_mode_without_executing_a_stage_and_reports_readiness(self):
        config = self.root / "config.json"
        config.write_text(json.dumps({"database_file": str(self.root / "runs.db"),
                                      "vault_dir": str(self.root / "vault")}), encoding="utf-8")
        app = closing(self, create_app(config, env={"AGENTIC_OS_RUN_EXECUTION": "worker"}))
        with TestClient(app) as client:
            created = client.post("/api/runs", json={"goal": "Analyze the sample"})
            self.assertEqual(created.status_code, 201)
            run = created.json()
            self.assertFalse(client.get("/api/health").json()["execution"]["ready"])
            # Fails if the HTTP path enters the transaction that performs
            # stages, even when a stage happens to finish quickly in tests.
            with patch.object(app.state.engine, "_advance_atomic", side_effect=AssertionError("HTTP ran a stage")):
                response = client.post(f"/api/runs/{run['id']}/advance")
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json()["state"], "queued")
            worker_store = self.open_store()
            worker = RunWorker(self.engine_for(worker_store), worker_store)
            worker.step()
            self.assertTrue(client.get("/api/health").json()["execution"]["ready"])
            self.assertEqual(client.get(f"/api/runs/{run['id']}").json()["state"], "awaiting_approval")


if __name__ == "__main__":
    unittest.main()
