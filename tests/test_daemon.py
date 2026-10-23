"""Non-activating daemon contract, shutdown, and private bytes after restart."""

import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from server.daemon import validate_environment
from server.auth import Principal
from server.model_gateway import ModelGateway
from server.rmd_service import RmdService
from server.runs import RunEngine
from server.storage import RESTORE_ORDER, open_store
from server.worker import RunWorker, main
from tests.test_rmd_ingestion import document, workbook
from tests.test_runs import PG_TEST_URL, _postgres_available

ROOT = Path(__file__).resolve().parent.parent


class DaemonContractTests(unittest.TestCase):
    def env(self):
        return {"AGENTIC_OS_DAEMON_ACTIVATION": "reviewed",
                "DATABASE_URL": "postgresql://dev@127.0.0.1/disposable_test",
                "AGENTIC_OS_PUBLISH_TARGET": "database",
                "AGENTIC_OS_RUN_EXECUTION": "worker",
                "AGENTIC_OS_REQUIRE_AUTH": "1",
                "SUPABASE_URL": "https://synthetic.supabase.invalid",
                "AGENTIC_OS_JWKS_URL": "https://synthetic.supabase.invalid/auth/v1/.well-known/jwks.json"}

    def test_candidate_is_not_active_and_keeps_existing_deploy_guard(self):
        live = json.loads((ROOT / "vercel.json").read_text())
        self.assertNotIn("daemons", live)
        self.assertFalse(live["git"]["deploymentEnabled"]["main"])
        example = json.loads((ROOT / "deploy/vercel.daemons.example.json").read_text())
        daemon = example["daemons"]["miyaar-worker"]
        self.assertEqual(daemon["instances"], {"iad1": 0})
        self.assertEqual(daemon["root"], ".")
        self.assertEqual(daemon["entrypoint"], "Dockerfile.worker")
        self.assertNotEqual(live["outputDirectory"], daemon["root"])
        self.assertEqual(daemon["resources"]["requests"]["memory"], "1Gi")

    def test_image_copies_only_runtime_allowlist_without_secret_build_arguments(self):
        image = (ROOT / "Dockerfile.worker").read_text()
        instructions = [line for line in image.splitlines() if line.startswith(("COPY ", "ADD ", "ARG "))]
        self.assertEqual(instructions, ["COPY requirements.txt ./", "COPY server/ ./server/",
                                        "COPY config.json agent.py assistant.py utils.py ./"])
        self.assertIn("--require-hashes", image)
        self.assertIn("USER 10001:10001", image)
        self.assertIn('ENTRYPOINT ["python", "-m", "server.daemon"]', image)
        ignore = (ROOT / "Dockerfile.worker.dockerignore").read_text()
        self.assertTrue(ignore.startswith("**\n"))
        self.assertNotIn("!.env", ignore)

    def test_allowlisted_runtime_imports_without_repo_docs_tests_or_local_data(self):
        # Source-layout smoke test only; this does not claim Docker was built.
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copytree(ROOT / "server", target / "server",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for name in ("config.json", "agent.py", "assistant.py", "utils.py"):
                shutil.copyfile(ROOT / name, target / name)
            env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(target),
                   "PYTHONDONTWRITEBYTECODE": "1"}
            result = subprocess.run([sys.executable, "-m", "server.daemon"],
                cwd=target, env=env, text=True, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("Daemon configuration rejected", result.stderr)
            self.assertFalse((target / "data").exists())

    def test_config_validation_is_network_free(self):
        with patch.object(ModelGateway, "_post", side_effect=AssertionError("Provider call")):
            validate_environment(self.env())

    def test_specialist_candidate_requires_explicit_single_model_and_admission(self):
        env = {**self.env(), "AGENTIC_OS_SPECIALISTS_ENABLED": "1",
               "AGENTIC_OS_SPECIALIST_MODEL": "ollama:synthetic-model",
               "OLLAMA_MODEL": "synthetic-model", "AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "20"}
        with patch.object(ModelGateway, "_post", side_effect=AssertionError("Provider call")):
            validate_environment(env)
            for changes in ({"AGENTIC_OS_SPECIALIST_MODEL": "ollama:other"},
                            {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "0"},
                            {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": ""},
                            {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": None},
                            {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": " "},
                            {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "-1"},
                            {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "1.0"},
                            {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "NaN"},
                            {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "Infinity"},
                            {"AGENTIC_OS_DAEMON_ACTIVATION": ""},
                            {"AGENTIC_OS_TASK_MODELS": "agents=ollama:synthetic-model"}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    validate_environment({**env, **changes})

    def test_missing_activation_database_publication_execution_or_identity_fails(self):
        for field in ("AGENTIC_OS_DAEMON_ACTIVATION", "DATABASE_URL", "AGENTIC_OS_PUBLISH_TARGET",
                      "AGENTIC_OS_RUN_EXECUTION", "AGENTIC_OS_REQUIRE_AUTH", "AGENTIC_OS_JWKS_URL"):
            with self.subTest(field=field):
                env = self.env(); env.pop(field)
                with self.assertRaises(Exception):
                    validate_environment(env)

    def test_ephemeral_state_and_external_models_are_not_silently_enabled(self):
        for field, value in (("AGENTIC_OS_EVAL_INTERVAL_SECONDS", "60"),
                             ("AGENTIC_OS_KNOWLEDGE_DIR", "/data/knowledge"),
                             ("OLLAMA_MODEL", "synthetic-model"),
                             ("AI_GATEWAY_MODEL", "synthetic/model"),
                             ("AGENTIC_OS_TASK_MODELS", "hermes=ollama:synthetic"),
                             ("AGENTIC_OS_ROUTER", "external.router")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_environment({**self.env(), field: value})

    def test_entrypoint_rejects_before_database_open_without_leaking_values(self):
        from server import daemon
        with patch.dict(os.environ, {"DATABASE_URL": "secret-not-to-log"}, clear=True), \
                patch("server.daemon.worker_main") as worker, patch("sys.stderr") as stderr:
            self.assertEqual(daemon.main(), 2)
            worker.assert_not_called()
            self.assertNotIn("secret-not-to-log", str(stderr.write.call_args_list))

    def test_sigterm_sets_stop_restores_handler_and_closes_store(self):
        worker = Mock()
        worker.worker_id = "synthetic-worker"
        previous = signal.getsignal(signal.SIGTERM)
        def run(**kwargs):
            self.assertFalse(kwargs["stop"].is_set())
            signal.raise_signal(signal.SIGTERM)
            self.assertTrue(kwargs["stop"].is_set())
        worker.run_forever.side_effect = run
        with patch("server.worker.build_worker", return_value=worker):
            self.assertEqual(main(["--poll", "15"]), 0)
        worker.store.close.assert_called_once()
        worker.heartbeat.assert_called_with("stopped")
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

    def test_failed_builder_restores_sigterm_handler(self):
        previous = signal.getsignal(signal.SIGTERM)
        with patch("server.worker.build_worker", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                main([])
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

    def test_idle_wait_is_interruptible_and_does_not_spin(self):
        worker = RunWorker(Mock(), Mock())
        worker.step = Mock(return_value=None)
        worker.refresh_due = Mock(return_value=None)
        stop = Mock()
        stop.is_set.side_effect = [False, False, False, True]
        worker.run_forever(poll_seconds=15, stop=stop)
        stop.wait.assert_called_once_with(15)
        worker.step.assert_called_once_with(stop=stop)
        worker.store.upsert_worker_heartbeat.assert_called()

    def test_sigterm_during_stage_releases_lease_and_skips_refresh_and_evaluation(self):
        stop = threading.Event()
        store, engine, connectors, steward = Mock(), Mock(), Mock(), Mock()
        store.claim_run.return_value = "synthetic-run"
        engine.owner_of.return_value = "synthetic-owner"
        def finish_stage(*args, **kwargs):
            stop.set()
            return {"state": "running", "tasks": [{"state": "pending"}]}
        engine.advance.side_effect = finish_stage
        worker = RunWorker(engine, store, connectors=connectors, steward=steward)
        worker.run_forever(stop=stop)
        engine.advance.assert_called_once()
        store.release_lease.assert_called_once_with("synthetic-run", worker.worker_id)
        connectors.step.assert_not_called()
        steward.tick.assert_not_called()
        self.assertEqual(store.upsert_worker_heartbeat.call_args.args[-1], "stopped")

    def test_stopped_worker_cannot_claim_new_work(self):
        stop = threading.Event(); stop.set()
        store = Mock()
        self.assertIsNone(RunWorker(Mock(), store).step(stop=stop))
        store.claim_run.assert_not_called()


class DurableBytesRestartTests(unittest.TestCase):
    database_url = None

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.db = self.root / "state.db"
        self.store = open_store(self.database_url, self.db)
        if self.database_url:
            # Only the explicitly configured disposable CI test database.
            for table in reversed(RESTORE_ORDER):
                if table != "schema_migrations":
                    self.store._exec(f"DELETE FROM {table}")
        self.addCleanup(self.store.close)

    def test_shutdown_finishes_one_atomic_stage_then_successor_resumes(self):
        engine = RunEngine(self.store, self.root / "unused", ModelGateway({}),
                           publish_target="database", execution_mode="worker")
        run = engine.create_run("Review synthetic sample", owner="synthetic-owner")
        first = RunWorker(engine, self.store, worker_id="first")
        stop = threading.Event()
        advance = engine.advance
        def finish_current(*args, **kwargs):
            state = advance(*args, **kwargs)
            stop.set()
            return state
        with patch.object(engine, "advance", side_effect=finish_current) as stepped:
            first.run_forever(stop=stop)
        stepped.assert_called_once()
        finished = [task["id"] for task in self.store.get_tasks(run["id"]) if task["state"] == "succeeded"]
        self.assertTrue(finished)
        self.assertIsNone(self.store.get_run(run["id"])["lease_owner"])
        reopened = open_store(self.database_url, self.db, schema_mode="verify")
        self.addCleanup(reopened.close)
        successor = RunWorker(RunEngine(reopened, self.root / "different-unused", ModelGateway({}),
            publish_target="database", execution_mode="worker"), reopened, worker_id="successor")
        self.assertEqual(successor.step(), run["id"])
        self.assertEqual(successor.engine.get_run(run["id"])["state"], "awaiting_approval")
        for task in reopened.get_tasks(run["id"]):
            if task["id"] in finished:
                self.assertEqual(task["state"], "succeeded")

    def test_private_sources_artifacts_dataset_report_and_memory_survive_new_process(self):
        owner = Principal("synthetic-owner", "owner", "test")
        service = RmdService(self.store, identity_mode="jwt", env={})
        pack = service.create_pack(owner, {"title": "Synthetic restart acceptance"})
        sources = []
        for filename, payload, kind in (("procedure.docx", document(), "procedure"),
                                         ("workbook.xlsx", workbook(), "workbook")):
            source = service.import_source(owner, pack["id"], filename, payload, kind)
            sources.append({"id": source["id"], "bytes": payload.hex(),
                "artifacts": [{"id": artifact["id"], "bytes": service.download_source(
                    owner, pack["id"], source["id"], artifact["id"])[0].hex()}
                    for artifact in source["artifacts"]]})
        self.assertTrue(sources[0]["artifacts"])
        engine = RunEngine(self.store, self.root / "never-created-vault", ModelGateway({}),
                           publish_target="database", execution_mode="worker")
        csv = "month,region,revenue\n2026-01,North,10\n2026-02,North,12\n"
        dataset = engine.store_dataset(csv, "synthetic.csv", owner.subject)
        run = engine.create_run("Review synthetic monthly revenue", owner=owner.subject, dataset_id=dataset["id"])
        with patch.object(ModelGateway, "_post", side_effect=AssertionError("Provider call")):
            RunWorker(engine, self.store).step()
        state = engine.get_run(run["id"])
        self.assertEqual(state["state"], "awaiting_approval")
        approved = engine.decide_approval(run["id"], state["approvals"][0]["id"], "approve", owner.subject)
        report = approved["report"]
        note = self.store.get_note(report["published_path"], owner.subject)
        self.assertIn(report["content"], note["content"])
        memory = {"synthetic": {"text": "A durable note", "category": "test", "updated": "2026-10-23"}}
        self.store.memory_save(memory, owner.subject)
        session = {"id": "synthetic-session", "owner": owner.subject, "created_at": "2026-10-23",
                   "updated_at": "2026-10-23", "ended": 0, "preferences_json": "{}",
                   "history_json": "[]", "transcript_json": "[]", "next_entry_id": 1}
        self.store.upsert_session(session)
        self.assertFalse((self.root / "never-created-vault").exists())
        self.store.close()
        fresh = self.root / "fresh-container-workdir"; fresh.mkdir()
        request = {"db": str(self.db), "pack": pack["id"], "sources": sources,
                   "dataset": dataset["id"], "csv": csv, "run": run["id"],
                   "report": report, "note": note["content"], "memory": memory, "session": session}
        script = '''
import json, os, sys
from server.auth import Principal
from server.rmd_service import RmdService, RmdError
from server.storage import open_store
request = json.load(sys.stdin)
store = open_store(os.environ.get("PG_TEST_URL"), request["db"], schema_mode="verify")
service = RmdService(store, identity_mode="jwt", env={})
owner = Principal("synthetic-owner", "owner", "test")
other = Principal("synthetic-other", "owner", "test")
for source in request["sources"]:
    assert service.download_source(owner, request["pack"], source["id"])[0].hex() == source["bytes"]
    for artifact in source["artifacts"]:
        assert service.download_source(owner, request["pack"], source["id"], artifact["id"])[0].hex() == artifact["bytes"]
    try:
        service.download_source(other, request["pack"], source["id"])
    except RmdError as error:
        assert error.status == 404
    else:
        raise AssertionError("Cross-owner source access")
assert store.get_dataset(request["dataset"])["content"] == request["csv"]
assert store.latest_artifact(request["run"])["content"] == request["report"]["content"]
note = store.get_note(request["report"]["published_path"], owner.subject)
assert note["content"] == request["note"]
assert store.get_note(request["report"]["published_path"], other.subject) is None
assert store.memory_load(owner.subject) == request["memory"]
assert store.memory_load(other.subject) == {}
assert store.get_session(request["session"]["id"]) == request["session"]
store.close()
print("Private durable bytes verified in a fresh process.")
'''
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")}
        if self.database_url:
            env["PG_TEST_URL"] = self.database_url
        completed = subprocess.run([sys.executable, "-c", script], input=json.dumps(request),
            text=True, capture_output=True, cwd=fresh, env=env, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("fresh process", completed.stdout)
        self.assertEqual(list(fresh.iterdir()), [])


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class DurableBytesPostgresRestartTests(DurableBytesRestartTests):
    database_url = PG_TEST_URL


if __name__ == "__main__":
    unittest.main()
