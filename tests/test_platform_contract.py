"""Synthetic HTTP contracts shared by web and native clients.

Use ASGITransport and an inline dependency dispatcher: these tests assert the
wire contract and authorization, not Starlette's threadpool implementation.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from server.app import create_app
from tests.test_authorization import AUDIENCE, ISSUER, SECRET, token


async def inline(function, /, *args, **kwargs):
    return function(*args, **kwargs)


class PlatformContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "Synthetic contract test", "database_file": str(root / "test.db"),
            "memory_file": str(root / "memory.json"), "vault_dir": str(root / "vault"),
        }))
        self.app = create_app(config, env={
            "AGENTIC_OS_AUTH_MODE": "jwt", "AGENTIC_OS_JWT_SECRET": SECRET,
            "AGENTIC_OS_JWT_AUDIENCE": AUDIENCE, "AGENTIC_OS_JWT_ISSUER": ISSUER,
            "AGENTIC_OS_DEFAULT_ROLE": "owner", "AGENTIC_OS_ALLOWED_ORIGINS": "https://client.invalid",
            "AGENTIC_OS_PUBLISH_TARGET": "database",
        })
        self.addCleanup(self.app.state.store.close)
        for name in ("fastapi.routing.run_in_threadpool", "fastapi.dependencies.utils.run_in_threadpool",
                     "server.app.run_in_threadpool"):
            self.enterContext(patch(name, inline))
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(
            app=self.app, raise_app_exceptions=False), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.headers = {"Authorization": "Bearer " + token("alice"), "X-Request-ID": "synthetic-request"}

    async def test_contract_is_private_and_describes_core_operations_and_rmd(self):
        denied = await self.client.get("/api/openapi.json")
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(denied.json()["error"]["code"], "authentication_required")
        response = await self.client.get("/api/openapi.json", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        schema = response.json()
        self.assertIn("/api/runs", schema["paths"])
        self.assertIn("/api/operations/organizations", schema["paths"])
        self.assertIn("/api/rmd/packs", schema["paths"])
        self.assertNotIn("/api/openapi.json", schema["paths"])
        error = schema["paths"]["/api/runs"]["post"]["responses"]["422"]
        self.assertEqual(error["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/ApiErrorEnvelope")
        self.assertEqual(response.headers["cache-control"], "no-store")

    async def test_core_operations_rmd_and_routing_failures_have_one_envelope(self):
        for path in ("/api/runs/missing", "/api/operations/organizations/missing",
                     "/api/rmd/packs/missing", "/api/not-a-route"):
            with self.subTest(path=path):
                result = await self.client.get(path, headers=self.headers)
                self.assertEqual(result.status_code, 404, result.text)
                body = result.json()
                self.assertEqual(set(body["error"]), {"code", "message", "problems", "request_id"})
                self.assertEqual(body["error"]["request_id"], "synthetic-request")
                self.assertEqual(result.headers["X-Request-ID"], "synthetic-request")
                self.assertTrue(body["error"]["message"])
                self.assertIn("detail", body)

    async def test_validation_has_field_locations_without_echoing_private_input(self):
        response = await self.client.post("/api/runs?language=ar", headers=self.headers,
                                          json={"goal": {"secret": "PRIVATE_INPUT_CANARY"}})
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "validation_failed")
        self.assertIn("راجع", body["error"]["message"])
        self.assertTrue(body["error"]["problems"])
        self.assertIn("goal", body["error"]["problems"][0]["loc"])
        self.assertNotIn("PRIVATE_INPUT_CANARY", response.text)

    async def test_cross_origin_clients_can_send_recovery_headers_and_patch(self):
        # Use an actual allowed origin rather than weakening the production list.
        origin = "https://client.invalid"
        response = await self.client.options("/api/runs", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,idempotency-key,x-request-id,content-type",
        })
        self.assertEqual(response.status_code, 200, response.text)
        patch_response = await self.client.options("/api/operations/organizations/test", headers={
            "Origin": origin, "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        self.assertEqual(patch_response.status_code, 200)

    async def test_dataset_wire_format_matches_native_client_and_run_replay_is_safe(self):
        upload = await self.client.post("/api/datasets?name=synthetic.csv&language=en",
                                        headers={**self.headers, "Content-Type": "text/csv"},
                                        content=b"month,team,sales\n2025-01,A,2\n2025-02,A,4\n")
        self.assertEqual(upload.status_code, 201, upload.text)
        dataset_id = upload.json()["dataset"]["id"]
        headers = {**self.headers, "Idempotency-Key": "native-uncertain-response"}
        payload = {"goal": "Synthetic contract analysis", "dataset_id": dataset_id}
        first = await self.client.post("/api/runs", headers=headers, json=payload)
        replay = await self.client.post("/api/runs", headers=headers, json=payload)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(first.json()["id"], replay.json()["id"])

    async def test_assets_find_older_stage_without_recent_list_or_cross_owner_reads(self):
        engine, store = self.app.state.engine, self.app.state.store
        old = engine.create_run("Synthetic asset history", owner="alice")
        task = store.get_tasks(old["id"])[0]
        store.update("tasks", task["id"], {"role": "rail_asset_manager", "state": "succeeded",
                                           "summary": "Synthetic observed evidence"})
        for index in range(55):
            engine.create_run(f"Newer unrelated analysis {index}", owner="alice")
        other = engine.create_run("Private Bob asset evidence", owner="bob")
        task = store.get_tasks(other["id"])[0]
        store.update("tasks", task["id"], {"role": "rail_asset_manager", "state": "succeeded"})
        with patch.object(engine, "list_runs", side_effect=AssertionError("Must not scan recent payloads")):
            result = await self.client.get("/api/assets/evidence", headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["run"]["id"], old["id"])
        self.assertNotIn("Private Bob", result.text)
        self.assertTrue(result.json()["prepared_at"])
        empty = await self.client.get("/api/assets/evidence", headers={"Authorization": "Bearer " + token("carol")})
        self.assertEqual(empty.status_code, 200)
        self.assertIsNone(empty.json()["run"])

    async def test_unexpected_errors_are_redacted_and_keep_the_request_id(self):
        with patch.object(self.app.state.store, "runs_with_completed_stage", side_effect=RuntimeError("PRIVATE_EXCEPTION_CANARY")):
            result = await self.client.get("/api/assets/evidence", headers=self.headers)
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.json()["error"]["code"], "internal_error")
        self.assertEqual(result.json()["error"]["request_id"], "synthetic-request")
        self.assertNotIn("PRIVATE_EXCEPTION_CANARY", result.text)

    async def test_a_changed_request_cannot_reuse_a_creation_key(self):
        headers = {**self.headers, "Idempotency-Key": "bound-inputs"}
        first = await self.client.post("/api/runs", headers=headers, json={"goal": "First request"})
        self.assertEqual(first.status_code, 201)
        changed = await self.client.post("/api/runs", headers=headers, json={"goal": "Different request"})
        self.assertEqual(changed.status_code, 409, changed.text)
        self.assertEqual(changed.json()["error"]["code"], "idempotency_conflict")
        self.assertEqual(len(self.app.state.engine.list_runs(owner="alice")), 1)

    async def test_rate_limit_uses_the_same_contract_and_preserves_retry_after(self):
        with patch("server.app.RateLimiter.check", return_value=(False, 0, 3)):
            response = await self.client.post("/api/runs", headers=self.headers, json={"goal": "Synthetic"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "rate_limited")
        self.assertEqual(response.headers["retry-after"], "3")

    async def test_actual_api_publishes_owned_notes_to_the_database_after_the_human_gate(self):
        created = await self.client.post("/api/runs", headers=self.headers, json={"goal": "Synthetic publication contract"})
        self.assertEqual(created.status_code, 201, created.text)
        run = created.json()
        for _ in range(40):
            if run["state"] == "awaiting_approval":
                break
            response = await self.client.post(f"/api/runs/{run['id']}/advance", headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            run = response.json()
        self.assertEqual(run["state"], "awaiting_approval")
        self.assertIsNone(run["report"]["published_path"])
        self.assertEqual(run["approvals"][0]["target"], "database:Reports")
        with patch.object(Path, "mkdir", side_effect=AssertionError("Read-only host")):
            approved = await self.client.post(f"/api/runs/{run['id']}/approvals/{run['approvals'][0]['id']}",
                                              headers=self.headers, json={"decision": "approve"})
        self.assertEqual(approved.status_code, 200, approved.text)
        result = approved.json()
        self.assertEqual(result["state"], "completed")
        path = result["report"]["published_path"]
        self.assertTrue(path.startswith("Reports/"))
        note = await self.client.get("/api/vault/note", headers=self.headers, params={"path": path})
        self.assertEqual(note.status_code, 200, note.text)
        self.assertIn(run["report"]["content"], note.json()["content"])
        private = await self.client.get("/api/vault/note", headers={"Authorization": "Bearer " + token("bob")}, params={"path": path})
        self.assertEqual(private.status_code, 404)

    async def test_changed_destination_requires_authorized_fresh_review_and_a_new_approval_id(self):
        self.app.state.engine.publish_target = "vault"
        run = (await self.client.post("/api/runs", headers=self.headers, json={"goal": "Synthetic destination recovery"})).json()
        for _ in range(40):
            if run["state"] == "awaiting_approval": break
            run = (await self.client.post(f"/api/runs/{run['id']}/advance", headers=self.headers)).json()
        self.assertEqual(run["state"], "awaiting_approval")
        old_id = run["approvals"][0]["id"]
        self.app.state.engine.publish_target = "database"
        refused = await self.client.post(f"/api/runs/{run['id']}/approvals/{old_id}", headers=self.headers, json={"decision": "approve"})
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(refused.json()["error"]["code"], "publication_destination_changed")
        path = f"/api/runs/{run['id']}/approvals/refresh"
        hidden = await self.client.post(path, headers={"Authorization": "Bearer " + token("bob")})
        self.assertEqual(hidden.status_code, 404)
        denied = await self.client.post(path, headers={"Authorization": "Bearer " + token("alice", {"agentic_os_role": "viewer"})})
        self.assertEqual(denied.status_code, 403)
        refreshed = await self.client.post(path, headers=self.headers)
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        body = refreshed.json()
        pending = next(a for a in body["approvals"] if a["state"] == "pending")
        self.assertNotEqual(pending["id"], old_id)
        self.assertIsNone(body["report"]["published_path"])
        self.assertEqual((await self.client.post(f"/api/runs/{run['id']}/approvals/{old_id}", headers=self.headers, json={"decision": "approve"})).status_code, 409)
        published = await self.client.post(f"/api/runs/{run['id']}/approvals/{pending['id']}", headers=self.headers, json={"decision": "approve"})
        self.assertEqual(published.status_code, 200, published.text)
        self.assertTrue(published.json()["report"]["published_path"].startswith("Reports/"))


if __name__ == "__main__":
    unittest.main()
