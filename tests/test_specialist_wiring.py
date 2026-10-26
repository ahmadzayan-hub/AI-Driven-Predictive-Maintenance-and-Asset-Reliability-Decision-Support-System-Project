"""Synthetic HTTP/worker wiring. Every model transport is mocked; no live proof."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from server.app import create_app
from server.model_gateway import ModelGateway
from server.quota import ModelBudget, load_limits
from server.runs import _stamp, _utcnow
from server.specialist_config import configure_specialists, PROFILE, worker_prefix
from server.specialists import ROLE_NAMES, ScopedToolBox, CATALOGUE
from server.storage import open_store, RESTORE_ORDER
from server.worker import build_worker, worker_status
from tests.support import closing, scoped_token, isolated_process_env
from tests.test_specialists import ScriptedDecisions
from tests.test_runs import PG_TEST_URL, _postgres_available


class SpecialistWiringTests(unittest.TestCase):
    database_url = None

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"database_file": str(self.root / "state.db"),
            "database_url": self.database_url,
            "vault_dir": str(self.root / "vault"), "memory_file": str(self.root / "memory.json")}))
        if self.database_url:
            store = open_store(self.database_url)
            try:
                for table in reversed(RESTORE_ORDER):
                    if table != "schema_migrations":
                        store._exec(f"DELETE FROM {table}")
            finally:
                store.close()
        self.env = {"AGENTIC_OS_SPECIALISTS_ENABLED": "1",
            "AGENTIC_OS_SPECIALIST_MODEL": "ollama:synthetic-model",
            "OLLAMA_MODEL": "synthetic-model", "AGENTIC_OS_RUN_EXECUTION": "worker",
            "AGENTIC_OS_PUBLISH_TARGET": "database",
            "AGENTIC_OS_JWT_SECRET": "synthetic-test-only-not-a-real-secret-12345",
            "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "30"}
        self.transport = patch.object(ModelGateway, "_post", side_effect=AssertionError("Unmocked transport"))
        self.transport.start()
        self.addCleanup(self.transport.stop)

    def headers(self, subject="fixture-owner", role="owner"):
        return {"Authorization": "Bearer " + scoped_token(self.env["AGENTIC_OS_JWT_SECRET"], subject, role)}

    def app(self, changes=None):
        return closing(self, create_app(self.config, env={**self.env, **(changes or {})}))

    def worker(self, changes=None):
        worker = build_worker(config_path=self.config, env={**self.env, **(changes or {})})
        self.addCleanup(worker.store.close)
        return worker

    def create(self, client, **values):
        return client.post("/api/runs", headers=self.headers(), json={
            "goal": "Inspect authorized aggregate evidence", "profile": PROFILE,
            "dataset_text": "month,sales\nJan,10\nFeb,20\nMar,30\n", **values})

    def factory(self, changes=None, **options):
        env = {**self.env, **(changes or {})}
        store = open_store(None, self.root / "factory.db")
        self.addCleanup(store.close)
        gateway = ModelGateway(env)
        gateway.budget = ModelBudget(store, load_limits(env))
        return configure_specialists(gateway, store, env, **{
            "identity_mode": "jwt", "execution_mode": "worker", "publish_target": "database", **options})

    def test_factory_is_default_off_and_never_infers_readiness_from_configuration(self):
        driver, status = self.factory({"AGENTIC_OS_SPECIALISTS_ENABLED": "0"})
        self.assertIsNone(driver)
        self.assertEqual(status["reason"], "disabled")
        driver, status = self.factory()
        self.assertIsNotNone(driver)
        self.assertTrue(status["configured"])
        self.assertFalse(status["worker_capable"])
        self.assertFalse(status["live_model_verified"])
        self.assertEqual(status["acceptance_basis"], "configuration_only_not_a_live_test")

    def test_explicit_identity_worker_durability_and_model_gates(self):
        cases = [({}, {"identity_mode": "local"}, "managed_identity_required"),
                 ({}, {"execution_mode": "client"}, "worker_execution_required"),
                 ({}, {"publish_target": "filesystem"}, "database_publication_required"),
                 ({"VERCEL": "1"}, {}, "hosted_postgres_required"),
                 ({"AGENTIC_OS_SPECIALIST_MODEL": "ollama"}, {}, "explicit_model_required"),
                 ({"AGENTIC_OS_SPECIALIST_MODEL": "ollama:other-model"}, {}, "model_unavailable"),
                 ({"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "0"}, {}, "model_budget_zero"),
                 ({"AGENTIC_OS_SPECIALISTS_ENABLED": "true"}, {}, "invalid_flag")]
        for env, options, reason in cases:
            with self.subTest(reason=reason):
                driver, status = self.factory(env, **options)
                self.assertIsNone(driver)
                self.assertEqual(status["reason"], reason)

    def test_specialist_admission_never_falls_back_to_legacy_default_on_invalid_input(self):
        for raw in (None, "", " ", "-1", "1.0", "NaN", "Infinity", "not-a-number", "1_000", "2147483648"):
            with self.subTest(raw=raw):
                driver, status = self.factory({"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": raw})
                self.assertIsNone(driver)
                self.assertEqual(status["reason"], "explicit_budget_required")
        self.assertEqual(load_limits({})["model_calls_per_day"], 500)
        self.assertEqual(load_limits({"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "-1"})["model_calls_per_day"], 500)

    def test_cross_provider_fallback_is_not_an_accepted_specialist_driver(self):
        driver, status = self.factory({"GROQ_API_KEY": "synthetic-not-real",
            "GROQ_MODEL": "synthetic-model", "OPENAI_API_KEY": "synthetic-not-real",
            "OPENAI_MODEL": "synthetic-model", "AGENTIC_OS_SPECIALIST_MODEL": "openai:synthetic-model",
            "AGENTIC_OS_MODEL_FAILOVER": "openai>groq"})
        self.assertIsNone(driver)
        self.assertEqual(status["reason"], "model_unavailable")

    def test_recipient_endpoint_change_cannot_share_checkpoint_or_worker_binding(self):
        first, first_status = self.factory()
        second, second_status = self.factory({"OLLAMA_HOST": "http://127.0.0.1:11435"})
        self.assertNotEqual(first.identifier, second.identifier)
        self.assertNotEqual(worker_prefix(first_status), worker_prefix(second_status))
        driver, status = self.factory({"OLLAMA_HOST": "https://user:synthetic@model.invalid"})
        self.assertIsNone(driver)
        self.assertEqual(status["reason"], "model_unavailable")

    def test_enabled_but_invalid_worker_refuses_instead_of_running_an_ordinary_fallback(self):
        for changes in ({"AGENTIC_OS_SPECIALIST_MODEL": "ollama:other"},
                        {"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "0"},
                        {"AGENTIC_OS_RUN_EXECUTION": "client"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "configuration rejected"):
                self.worker(changes)

    def test_different_model_or_larger_budget_skips_checkpoint_before_claim_without_starvation(self):
        app = self.app({"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "1"}); client = TestClient(app)
        specialist = self.create(client).json()
        for changes in ({}, {"OLLAMA_MODEL": "other", "AGENTIC_OS_SPECIALIST_MODEL": "ollama:other"}):
            with self.subTest(changes=changes):
                worker = self.worker(changes)
                ordinary = client.post("/api/runs", headers=self.headers(),
                    json={"goal": "Ordinary evidence"}).json()
                # Selection, not execution: ordinary narration is outside this test.
                self.assertEqual(worker.claim(), ordinary["id"])
                self.assertIsNone(worker.claim())
                self.assertIsNone(worker.claim())
                self.assertNotEqual(worker.engine.specialists.driver.identifier,
                                    app.state.engine.specialists.driver.identifier)
        untouched = app.state.engine.get_run(specialist["id"])
        self.assertEqual(untouched["state"], "queued")
        self.assertIsNone(app.state.store.get_run(specialist["id"])["lease_owner"])
        self.assertEqual(client.get("/api/usage", headers=self.headers()).json()["model_calls"]["used"], 0)

    def test_many_incompatible_and_malformed_checkpoints_do_not_block_ordinary_claims(self):
        app = self.app({"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "1"}); client = TestClient(app)
        incompatible = [self.create(client).json()["id"] for _ in range(8)]
        task = next(t for t in app.state.store.get_tasks(incompatible[0]) if t["role"] == ROLE_NAMES[0])
        app.state.store.update("tasks", task["id"], {"result_json": "{malformed"})
        ordinary = client.post("/api/runs", headers=self.headers(), json={"goal": "Ordinary evidence"}).json()
        worker = self.worker()
        self.assertEqual(worker.claim(), ordinary["id"])
        self.assertIsNone(worker.claim())
        for run_id in incompatible:
            self.assertIsNone(app.state.store.get_run(run_id)["lease_owner"])
        self.assertEqual(app.state.store.get_tasks(incompatible[0])[0]["result_json"], "{malformed")

    def test_unconfigured_api_refuses_bilingually_before_any_run_write(self):
        app = self.app({"AGENTIC_OS_SPECIALISTS_ENABLED": "0"})
        client = TestClient(app)
        for language in ("en", "ar"):
            response = self.create(client, language=language)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertIn("specialist_unavailable", response.text)
        self.assertEqual(app.state.store.list_runs(), [])
        pipelines = client.get("/api/pipelines", headers=self.headers()).json()
        self.assertNotIn(PROFILE, pipelines["profiles"])

    def test_plan_is_exactly_four_specialists_and_publish_not_twenty_one_stages(self):
        client = TestClient(self.app())
        plan = client.get("/api/pipelines", headers=self.headers()).json()
        self.assertEqual(plan["explicit_plans"][PROFILE], [*ROLE_NAMES, "publish"])
        run = self.create(client).json()
        self.assertEqual([t["role"] for t in run["tasks"]], plan["explicit_plans"][PROFILE])
        self.assertEqual(client.get("/api/pipelines").status_code, 401)

    def test_health_requires_matching_recent_factory_worker_not_generic_heartbeat(self):
        app = self.app(); client = TestClient(app)
        status = lambda: client.get("/api/health", headers=self.headers()).json()["specialist_execution"]
        self.assertFalse(status()["worker_capable"])
        app.state.store.upsert_worker_heartbeat("ordinary-worker", _stamp(_utcnow()), "idle")
        self.assertFalse(status()["worker_capable"])
        other = self.worker({"AGENTIC_OS_SPECIALIST_MODEL": "ollama:other", "OLLAMA_MODEL": "other"})
        other.heartbeat()
        self.assertFalse(status()["worker_capable"])
        matching = self.worker(); matching.heartbeat()
        self.assertTrue(status()["worker_capable"])
        self.assertFalse(status()["live_model_verified"])
        matching.heartbeat("stopped")
        self.assertFalse(status()["worker_capable"])
        self.assertNotIn("specialist_execution", client.get("/api/health").json())

    def test_api_to_separate_worker_restart_report_and_human_publication(self):
        app = self.app(); client = TestClient(app)
        run = self.create(client).json(); run_id = run["id"]
        worker = self.worker()
        # Commit one model intent/result through a different connection before restart.
        fixture = ScriptedDecisions()
        stop = threading.Event()
        def answer(url, headers, payload):
            self.assertEqual(payload["model"], "synthetic-model")
            context = json.loads(payload["messages"][-1]["content"])
            result = fixture.decide(context)
            stop.set()
            return {"message": {"content": json.dumps(result)}}
        with patch.object(ModelGateway, "_post", side_effect=answer):
            self.assertEqual(worker.step(stop=stop), run_id)
        self.assertEqual(len(fixture.calls), 1)
        worker.store.close()
        # A new interpreter has no previous gateway, in-memory state or fixture.
        script = '''
import json, sys
from unittest.mock import patch
from server.model_gateway import ModelGateway
from server.worker import build_worker
from tests.test_specialists import ScriptedDecisions
fixture = ScriptedDecisions()
def answer(gateway, url, headers, payload):
    context = json.loads(payload["messages"][-1]["content"])
    return {"message": {"content": json.dumps(fixture.decide(context))}}
worker = build_worker(config_path=sys.argv[1], env=json.loads(sys.stdin.read()))
try:
    with patch.object(ModelGateway, "_post", autospec=True, side_effect=answer):
        run_id = worker.step()
    print(json.dumps({"id": run_id, "roles": [c["role"] for c in fixture.calls], "calls": len(fixture.calls)}))
finally:
    worker.store.close()
'''
        env = isolated_process_env()
        if self.database_url:
            env["PG_TEST_URL"] = self.database_url
        child = subprocess.run([sys.executable, "-c", script, str(self.config)],
            input=json.dumps(self.env), env=env, text=True, capture_output=True, timeout=25)
        self.assertEqual(child.returncode, 0, child.stderr)
        replay = json.loads(child.stdout)
        self.assertEqual(replay["id"], run_id)
        result = client.get("/api/runs/" + run_id, headers=self.headers()).json()
        self.assertEqual(result["state"], "awaiting_approval", result.get("error"))
        self.assertEqual(set(replay["roles"]) | {c["role"] for c in fixture.calls}, set(ROLE_NAMES))
        self.assertIsNone(result["report"]["published_path"])
        tasks = {task["role"]: task for task in result["tasks"]}
        for role in (ROLE_NAMES[1], ROLE_NAMES[2]):
            self.assertTrue(tasks[role]["claims"])
            self.assertTrue(all(claim["evidence"] for claim in tasks[role]["claims"]))
            section = next(section for section in result["reports"] if section["type"] == role)
            self.assertIn("| Figure | Value | Method |", section["content"])
            self.assertIn("c_mean", section["content"])
            self.assertIn("20", section["content"])
            self.assertIn("SHA-256", section["content"])
        check = tasks[ROLE_NAMES[3]]["quality_checks"][0]
        self.assertEqual(check["name"], "independent_evidence_replay")
        self.assertTrue(check["passed"])
        self.assertIn("not human publication approval", check["detail"])
        self.assertNotIn('"specialist":', json.dumps(result))
        self.assertNotIn('"pending":', json.dumps(result))
        self.assertNotIn('"observations":', json.dumps(result))
        self.assertEqual(client.get("/api/runs/" + run_id,
                                   headers=self.headers("other-owner")).status_code, 404)
        approval = result["approvals"][0]["id"]
        target = f"/api/runs/{run_id}/approvals/{approval}"
        self.assertEqual(client.post(target, headers=self.headers(role="viewer"),
                                     json={"decision": "approve"}).status_code, 403)
        approved = client.post(target, headers=self.headers(), json={"decision": "approve"})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["state"], "completed")
        self.assertIsNotNone(approved.json()["report"]["published_path"])
        self.assertEqual(client.get("/api/usage", headers=self.headers()).json()["model_calls"]["used"],
                         len(fixture.calls) + replay["calls"])

    def test_disabled_worker_does_not_consume_specialist_tasks_or_starve_ordinary_runs(self):
        app = self.app(); client = TestClient(app)
        specialist = self.create(client).json()
        ordinary = client.post("/api/runs", headers=self.headers(), json={"goal": "Ordinary evidence"}).json()
        worker = self.worker({"AGENTIC_OS_SPECIALISTS_ENABLED": "0", "OLLAMA_MODEL": ""})
        self.assertEqual(worker.step(), ordinary["id"])
        self.assertIsNone(worker.step())
        untouched = app.state.engine.get_run(specialist["id"])
        self.assertEqual(untouched["state"], "queued")
        self.assertTrue(all(t["state"] == "pending" for t in untouched["tasks"]))

    def test_viewer_cannot_create_and_foreign_source_cannot_be_selected(self):
        app = self.app(); client = TestClient(app)
        self.assertEqual(client.post("/api/runs", headers=self.headers(role="viewer"),
            json={"goal": "Read evidence", "profile": PROFILE}).status_code, 403)
        source = app.state.engine.store_dataset("month,sales\nJan,10\nFeb,20", "private.csv", "other-owner")
        self.assertEqual(self.create(client, dataset_id=source["id"]).status_code, 404)
        self.assertEqual(app.state.store.list_runs(), [])

    def test_hash_provenance_cannot_be_mistaken_for_private_phone_data(self):
        app = self.app(); client = TestClient(app)
        # Source SHA contains the digit run 78646528810. It remains visible to
        # the human, but is encoded/omitted in the model-only projection.
        source = "month,sales\nJan,3\nFeb,20\nMar,30\n"
        run = self.create(client, dataset_text=source).json()
        fixture = ScriptedDecisions()
        def answer(url, headers, payload):
            context = json.loads(payload["messages"][-1]["content"])
            return {"message": {"content": json.dumps(fixture.decide(context))}}
        with patch.object(ModelGateway, "_post", side_effect=answer):
            self.worker().step()
        result = client.get("/api/runs/" + run["id"], headers=self.headers()).json()
        self.assertEqual(result["state"], "awaiting_approval", result.get("error"))
        self.assertIn("78646528810", result["report"]["content"])
        self.assertNotIn("78646528810", json.dumps(fixture.calls))
        self.assertNotIn(source, json.dumps(fixture.calls))

    def test_mismatched_worker_in_a_fresh_process_skips_specialists_and_claims_ordinary(self):
        app = self.app({"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "1"}); client = TestClient(app)
        specialist = self.create(client).json()
        ordinary = client.post("/api/runs", headers=self.headers(), json={"goal": "Ordinary evidence"}).json()
        script = """
import json, sys
from unittest.mock import patch
from server.model_gateway import ModelGateway
from server.worker import build_worker
with patch.object(ModelGateway, '_post', side_effect=AssertionError('No model call allowed')):
    worker = build_worker(config_path=sys.argv[1], env=json.loads(sys.stdin.read()))
    try:
        print(json.dumps([worker.claim(), worker.claim()]))
    finally:
        worker.store.close()
"""
        child = subprocess.run([sys.executable, "-c", script, str(self.config)],
            input=json.dumps(self.env), text=True, capture_output=True, timeout=25,
            env=isolated_process_env())
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(json.loads(child.stdout), [ordinary["id"], None])
        self.assertIsNone(app.state.store.get_run(specialist["id"])["lease_owner"])
        self.assertEqual(client.get("/api/usage", headers=self.headers()).json()["model_calls"]["used"], 0)

    def test_utf8_tool_bounds_are_bytes_not_unicode_character_count(self):
        called = []
        box = ScopedToolBox(CATALOGUE, {"draft_report": lambda **args: called.append(args)}, {"draft_report"})
        result = box.call("draft_report", {"claim_refs": [], "text": "ع" * 13000})
        self.assertFalse(result["ok"])
        self.assertEqual(called, [])
        box = ScopedToolBox(CATALOGUE, {"inspect_source": lambda: {"value": "ع" * 17000}}, {"inspect_source"})
        self.assertFalse(box.call("inspect_source", {})["ok"])


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class SpecialistWiringPostgresTests(SpecialistWiringTests):
    database_url = PG_TEST_URL


if __name__ == "__main__":
    unittest.main()
