"""Publication retains tenant ownership; CORS permits authenticated clients."""

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from server.app import create_app
from tests.support import scoped_token as issue_local_test_token
from tests.support import closing
from tests.test_runs import PG_TEST_URL, _postgres_available

SECRET = "published-note-test-secret-only-not-a-real-key"


class PublishedNoteAccessTests(unittest.TestCase):
    def database_config(self):
        return {"database_file": str(self.root / "agentic.db")}

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        config = self.root / "config.json"
        config.write_text(json.dumps({
            **self.database_config(),
            "memory_file": str(self.root / "memory.json"),
            "vault_dir": str(self.root / "vault"),
        }), encoding="utf-8")
        self.app = closing(self, create_app(config, env={
            "AGENTIC_OS_JWT_SECRET": SECRET,
            "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_ROLE_ASSIGNMENTS": "operator:admin",
        }))
        self.client = TestClient(self.app)

    def headers(self, subject, role="owner"):
        return {"Authorization": "Bearer " +
                issue_local_test_token(SECRET, subject, role)}

    def publish(self, subject):
        headers = self.headers(subject)
        response = self.client.post("/api/runs", json={
            "goal": "Analyze sample sales"}, headers=headers)
        self.assertEqual(response.status_code, 201, response.text)
        run = response.json()
        for _ in range(60):
            if run["state"] not in ("queued", "running"):
                break
            response = self.client.post(f"/api/runs/{run['id']}/advance",
                                        headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            run = response.json()
        self.assertEqual(run["state"], "awaiting_approval", run.get("error"))
        response = self.client.post(
            f"/api/runs/{run['id']}/approvals/{run['approvals'][0]['id']}",
            json={"decision": "approve"}, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        notes = self.client.get("/api/vault", headers=headers).json()["notes"]
        self.assertEqual(len(notes), 2)
        return run["id"], notes

    def test_another_owner_or_viewer_cannot_list_or_read_published_notes(self):
        run_id, notes = self.publish("owner-a")
        for role in ("owner", "viewer", "auditor"):
            with self.subTest(role=role):
                headers = self.headers("other-user", role)
                self.assertEqual(self.client.get(f"/api/runs/{run_id}",
                                                headers=headers).status_code, 404)
                response = self.client.get("/api/vault", headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["notes"], [])
                missing = self.client.get("/api/vault/note",
                                          params={"path": "missing.md"},
                                          headers=headers)
                for note in notes:
                    response = self.client.get("/api/vault/note",
                                               params={"path": note["path"]},
                                               headers=headers)
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(response.json(), missing.json())

    def test_owner_and_platform_admin_keep_access_without_filesystem_fallback(self):
        run_id, notes = self.publish("owner-a")
        for subject in ("owner-a", "operator"):
            headers = self.headers(subject, "viewer")
            listing = self.client.get("/api/vault", headers=headers).json()["notes"]
            self.assertEqual({n["run_id"] for n in listing}, {run_id})
            self.assertEqual(len(listing), 2)
            for note in notes:
                response = self.client.get("/api/vault/note",
                                           params={"path": note["path"]}, headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["content"])
        # A file alone is not authorization or a readable published record.
        path = "Reports/untracked.md"
        (self.root / "vault" / path).write_text("synthetic private content", encoding="utf-8")
        for subject in ("owner-a", "other-user", "operator"):
            response = self.client.get("/api/vault/note", params={"path": path},
                                       headers=self.headers(subject))
            self.assertEqual(response.status_code, 404)

    def test_store_filters_existing_notes_by_their_runs_owner(self):
        first, first_notes = self.publish("owner-a")
        second, _ = self.publish("owner-b")
        store = self.app.state.store
        self.assertEqual({n["run_id"] for n in store.list_notes(owner="owner-a")}, {first})
        self.assertEqual({n["run_id"] for n in store.list_notes(owner="owner-b")}, {second})
        self.assertEqual(len(store.list_notes()), 4)  # trusted operator API
        for note in first_notes:
            self.assertIsNone(store.get_note(note["path"], owner="owner-b"))
            self.assertEqual(store.get_note(note["path"], owner="owner-a")["run_id"], first)

    def test_allowed_origin_accepts_bearer_header_but_untrusted_origin_does_not(self):
        headers = {"Origin": "http://localhost:5173",
                   "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "authorization,content-type"}
        allowed = self.client.options("/api/runs", headers=headers)
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertIn("authorization", allowed.headers["access-control-allow-headers"].lower())
        self.assertEqual(allowed.headers["access-control-allow-origin"], headers["Origin"])
        headers["Origin"] = "https://untrusted.invalid"
        denied = self.client.options("/api/runs", headers=headers)
        self.assertEqual(denied.status_code, 400)
        self.assertNotIn("access-control-allow-origin", denied.headers)


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class PublishedNotePostgresTests(PublishedNoteAccessTests):
    def database_config(self):
        return {"database_url": PG_TEST_URL}

    def setUp(self):
        import psycopg2
        from server.storage import TABLES
        with psycopg2.connect(PG_TEST_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE")
        super().setUp()


if __name__ == "__main__":
    unittest.main()
