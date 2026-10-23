"""Managed-identity integration for pilot readiness and prospective evidence.

Every database and token is a disposable test fixture. No model, hosted
identity provider, customer database or source connector is contacted.
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from server.app import create_app
from tests.support import scoped_token as issue_local_test_token
from tests.support import closing


SECRET = "pilot-api-test-signing-secret-not-a-real-credential"


class PilotApiTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Pilot integration fixture",
                          "database_file": str(root / "pilot.db"),
                          "memory_file": str(root / "memory.json"),
                          "vault_dir": str(root / "vault")}), encoding="utf-8")
        self.app = closing(self, create_app(config, env={
            "AGENTIC_OS_ENV": "production", "AGENTIC_OS_JWT_SECRET": SECRET, "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_RUN_EXECUTION": "worker"}))
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.clock = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
        self.app.state.reliability_trials.clock = lambda: self.clock
        self.alice = self.auth("alice")
        self.bob = self.auth("bob")
        self.org = self.organization(self.alice, "Alice depot")
        self.org_path = "/api/operations/organizations/" + self.org["id"]
        self.asset = self.register_asset(self.alice, self.org["id"], "A-001")
        self.protocol = {
            "request_id": "protocol-first", "name": "Synthetic API acceptance fixture",
            "model_version": "test-model-1", "baseline_name": "test-fixed-baseline",
            "trained_through": (self.clock - timedelta(days=1)).isoformat(),
            "horizon_hours": 24.0, "threshold": 0.5,
            "failure_definition": "Technician-adjudicated fixture failure",
            "cohort_definition": "Registered fixture asset windows only"}

    def auth(self, subject, role="owner"):
        return {"Authorization": "Bearer " + issue_local_test_token(SECRET, subject=subject, role=role)}

    def post(self, path, payload, headers=None, expected=201):
        response = self.client.post(path, json=payload, headers=headers or self.alice)
        self.assertEqual(response.status_code, expected, response.text)
        return response.json()

    def organization(self, headers, name):
        return self.post("/api/operations/organizations", {"name": name, "idempotency_key": "new-org"}, headers)

    def register_asset(self, headers, org_id, external_id):
        base = "/api/operations/organizations/" + org_id
        site = self.post(base + "/sites", {"code": "DEPOT", "name": "Fixture depot", "idempotency_key": "new-site"}, headers)
        return self.post(base + "/assets", {"site_id": site["id"], "external_id": external_id,
            "source_system": "fixture-register", "name": "Fixture pump", "criticality": "high",
            "idempotency_key": "new-asset"}, headers)

    def trial(self):
        return self.post(self.org_path + "/trials", self.protocol)

    def prediction(self, trial, **changes):
        return {"revision": trial["revision"], "request_id": "prediction-first", "asset_id": self.asset["id"],
                "probability": 0.8, "baseline_probability": 0.2, **changes}

    def member(self, subject, role):
        version = self.client.get(self.org_path + "/overview", headers=self.alice).json()["organization"]["version"]
        return self.post(self.org_path + "/members", {"subject": subject, "role": role,
                         "expected_version": version, "idempotency_key": f"member-{subject}-{role}-{version}"}, expected=200)

    def test_unauthenticated_readiness_and_trial_requests_are_rejected(self):
        for suffix in ("/readiness", "/trials"):
            response = self.client.get(self.org_path + suffix)
            self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.post(self.org_path + "/trials", json=self.protocol).status_code, 401)

    def test_cross_tenant_trial_and_readiness_access_is_refused(self):
        trial = self.trial()
        for path in (self.org_path + "/readiness", self.org_path + "/trials",
                     "/api/operations/trials/" + trial["id"]):
            response = self.client.get(path, headers=self.bob)
            self.assertEqual(response.status_code, 404, response.text)
            self.assertNotIn("test-model-1", response.text)
            self.assertNotIn(self.asset["id"], response.text)
        response = self.client.post("/api/operations/trials/" + trial["id"] + "/predictions",
                                    headers=self.bob, json=self.prediction(trial))
        self.assertEqual(response.status_code, 404)

    def test_trial_presence_is_not_disclosed_to_another_tenant(self):
        trial = self.trial()
        headers = {**self.bob, "X-Request-ID": "synthetic-isolation-check"}
        existing = self.client.get("/api/operations/trials/" + trial["id"], headers=headers)
        missing = self.client.get("/api/operations/trials/not-a-trial", headers=headers)
        self.assertEqual(existing.status_code, 404)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(existing.json(), missing.json(), "Cross-tenant trial existence is distinguishable from a missing trial")

    def test_managed_read_only_claim_overrides_organization_owner_role(self):
        viewer = self.auth("alice", "viewer")
        self.assertEqual(self.client.get(self.org_path + "/readiness", headers=viewer).status_code, 200)
        response = self.client.post(self.org_path + "/trials", headers=viewer, json=self.protocol)
        self.assertEqual(response.status_code, 403)
        trial = self.trial()
        response = self.client.post("/api/operations/trials/" + trial["id"] + "/predictions",
                                    headers=viewer, json=self.prediction(trial))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/api/operations/trials/" + trial["id"], headers=viewer).json()["predictions"], [])

    def test_organization_viewer_cannot_inherit_platform_owner_writes(self):
        self.member("bob", "viewer")
        trial = self.trial()
        response = self.client.post("/api/operations/trials/" + trial["id"] + "/predictions",
                                    headers=self.bob, json=self.prediction(trial))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get(self.org_path + "/trials", headers=self.bob).status_code, 200)

    def test_trial_creation_retry_keeps_one_protocol_and_rejects_changed_payload(self):
        trial = self.trial()
        self.clock += timedelta(minutes=3)
        retried = self.trial()
        self.assertEqual(retried["id"], trial["id"])
        self.assertEqual(retried["created_at"], trial["created_at"])
        self.assertEqual(retried["protocol"]["registered_at"], trial["protocol"]["registered_at"])
        response = self.client.post(self.org_path + "/trials", headers=self.alice,
                                    json={**self.protocol, "threshold": 0.7})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "replay")
        self.assertEqual(len(self.client.get(self.org_path + "/trials", headers=self.alice).json()["trials"]), 1)

    def test_client_cannot_backdate_prediction_or_inject_outcome_and_actor(self):
        trial = self.trial()
        path = "/api/operations/trials/" + trial["id"] + "/predictions"
        forbidden = {"predicted_at": "2020-01-01T00:00:00Z", "window_end": "2020-01-02T00:00:00Z",
                     "submitted_by": "another-subject", "outcome": {"failed": True}}
        for field, value in forbidden.items():
            with self.subTest(field=field):
                response = self.client.post(path, headers=self.alice, json={**self.prediction(trial), field: value})
                self.assertEqual(response.status_code, 422, response.text)
        read = self.client.get("/api/operations/trials/" + trial["id"], headers=self.alice).json()
        self.assertEqual(read["predictions"], [])
        self.assertEqual(read["revision"], 1)

    def test_prediction_timestamp_is_server_owned_and_retry_does_not_duplicate(self):
        trial = self.trial()
        self.clock += timedelta(minutes=7)
        path = "/api/operations/trials/" + trial["id"] + "/predictions"
        recorded = self.post(path, self.prediction(trial), expected=200)
        prediction = recorded["predictions"][0]
        self.assertEqual(prediction["predicted_at"], self.clock.isoformat())
        self.assertEqual(prediction["submitted_by"], "alice")
        self.assertEqual(prediction["window_end"], (self.clock + timedelta(hours=24)).isoformat())
        self.clock += timedelta(minutes=7)
        replayed = self.post(path, self.prediction(trial), expected=200)
        self.assertEqual(replayed["revision"], recorded["revision"])
        self.assertEqual(replayed["predictions"], recorded["predictions"])
        self.assertEqual(replayed["metrics"]["evaluated"], 0)
        self.assertIsNone(replayed["metrics"]["failure_alert_precision"]["value"])

    def test_prediction_cannot_reference_another_organization_asset(self):
        other = self.organization(self.bob, "Bob depot")
        asset = self.register_asset(self.bob, other["id"], "B-001")
        trial = self.trial()
        response = self.client.post("/api/operations/trials/" + trial["id"] + "/predictions",
                                    headers=self.alice, json=self.prediction(trial, asset_id=asset["id"]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "asset")
        readiness = self.client.get(self.org_path + "/readiness", headers=self.alice).json()
        self.assertEqual(readiness["counts"]["assets"], 1)

    def test_early_outcome_refused_then_different_manager_can_adjudicate(self):
        self.member("bob", "manager")
        trial = self.trial()
        recorded = self.post("/api/operations/trials/" + trial["id"] + "/predictions",
                             self.prediction(trial), expected=200)
        prediction = recorded["predictions"][0]
        path = "/api/operations/trials/" + trial["id"] + "/predictions/" + prediction["id"] + "/outcome"
        outcome = {"revision": recorded["revision"], "failed": False, "actionable": True,
                   "observed_through": prediction["window_end"], "evidence_reference": "synthetic-inspection-reference"}
        response = self.client.post(path, headers=self.bob, json=outcome)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "immature")
        self.clock += timedelta(hours=25)
        response = self.client.post(path, headers=self.auth("bob", "viewer"), json=outcome)
        self.assertEqual(response.status_code, 403)
        adjudicated = self.post(path, outcome, headers=self.bob, expected=200)
        self.assertEqual(adjudicated["predictions"][0]["outcome"]["adjudicated_by"], "bob")
        self.assertEqual(adjudicated["metrics"]["different_actor_adjudications"], 1)
        self.assertIn("no_causal_savings_claim", adjudicated["metrics"]["limitations"])

    def test_worker_readiness_has_no_false_success_without_worker_evidence(self):
        response = self.client.get(self.org_path + "/readiness", headers=self.alice)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["execution"]["mode"], "worker")
        self.assertFalse(result["execution"]["ready"])
        self.assertIsNone(result["execution"]["last_seen_at"])
        checks = {entry["id"]: entry["observed"] for entry in result["checks"]}
        self.assertFalse(checks["background_execution"])
        self.assertTrue(checks["managed_identity"])
        self.assertTrue(checks["registered_assets"])
        self.assertFalse(checks["maintenance_action_closed"])
        self.assertTrue(result["external_acceptance"])
        self.assertEqual(result["scope"], "observed_configuration_and_records_not_release_approval")
        self.assertNotIn("score", result)

    def test_worker_heartbeat_stopped_state_removes_readiness(self):
        stamp = datetime.now(timezone.utc).isoformat()
        self.app.state.store.upsert_worker_heartbeat("synthetic-worker", stamp, "idle")
        self.assertTrue(self.client.get(self.org_path + "/readiness", headers=self.alice).json()["execution"]["ready"])
        self.app.state.store.upsert_worker_heartbeat("synthetic-worker", stamp, "stopped")
        self.assertFalse(self.client.get(self.org_path + "/readiness", headers=self.alice).json()["execution"]["ready"])

    def test_background_advance_returns_202_without_executing_model_or_stages(self):
        run = self.post("/api/runs", {"goal": "Synthetic asynchronous execution acceptance",
                        "dataset_name": "fixture.csv", "dataset_text": "Asset,Temperature\nA-001,23\n"})
        engine = self.app.state.engine
        with patch.object(engine, "_advance_atomic", side_effect=AssertionError("HTTP executed a stage")) as execute:
            response = self.client.post("/api/runs/" + run["id"] + "/advance", headers=self.alice)
        self.assertEqual(response.status_code, 202, response.text)
        execute.assert_not_called()
        self.assertEqual(response.json()["state"], "queued")
        self.assertTrue(all(task["state"] == "pending" for task in response.json()["tasks"]))
        self.assertEqual(response.json()["execution"]["mode"], "worker")
        denied = self.client.post("/api/runs/" + run["id"] + "/advance", headers=self.bob)
        self.assertEqual(denied.status_code, 404)

    def test_domain_conflict_is_returned_in_arabic_without_internal_detail(self):
        self.trial()
        response = self.client.post(self.org_path + "/trials?language=ar", headers=self.alice,
                                    json={**self.protocol, "threshold": 0.9})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "replay")
        self.assertTrue(any("\u0600" <= character <= "\u06ff" for character in response.json()["detail"]["message"]))
        self.assertNotIn("Traceback", response.text)


if __name__ == "__main__":
    unittest.main()
