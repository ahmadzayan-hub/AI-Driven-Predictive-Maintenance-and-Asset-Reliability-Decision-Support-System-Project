"""Deleting a stored dataset (the dataset lifecycle slice, 27 October 2026).

A dataset an owner no longer needs can be removed; one an analysis still
reads cannot, because runs are never deleted and a published result points
at its table. Another owner's dataset is a 404, never a 403. A live source
that last stored the dataset forgets that snapshot. Checked on SQLite and,
when a test database is reachable, PostgreSQL.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - the CLI-only install
    FASTAPI_AVAILABLE = False

if FASTAPI_AVAILABLE:
    from server.app import create_app

from server.storage import RESTORE_ORDER, open_store
from tests.support import closing, scoped_token
from tests.test_runs import PG_TEST_URL, _postgres_available

SECRET = "dataset-deletion-test-secret"
SALES = "month,product,sales\n2025-01,A,10\n2025-02,A,12\n2025-03,B,9\n2025-04,B,11\n"
PRODUCTS = "code,line\nA,pumps\nB,motors\n"


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class DatasetDeletionMixin:
    """The same expectations against whichever store the subclass wires."""

    def build_client(self, root):  # pragma: no cover - provided by subclasses
        raise NotImplementedError

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.client = self.build_client(self.root)
        self.store = self.client.app.state.store

    def auth(self, subject, role="owner"):
        return {"Authorization": "Bearer " + scoped_token(SECRET, subject=subject, role=role)}

    def upload(self, text, name, subject):
        response = self.client.post(f"/api/datasets?name={name}", content=text.encode(),
                                    headers=self.auth(subject))
        self.assertIn(response.status_code, (200, 201), response.text)
        return response.json()["dataset"]["id"]

    def delete(self, dataset_id, subject, language="en"):
        return self.client.delete(f"/api/datasets/{dataset_id}?language={language}",
                                  headers=self.auth(subject))

    def ids(self, subject):
        return {d["id"] for d in self.client.get("/api/datasets", headers=self.auth(subject))
                .json()["datasets"]}

    def test_an_owner_removes_a_dataset_no_analysis_reads(self):
        sales = self.upload(SALES, "sales.csv", "alice")
        before = self.client.get("/api/usage", headers=self.auth("alice")).json()["datasets"]["used"]
        response = self.delete(sales, "alice")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["deleted"], sales)
        self.assertEqual(body["name"], "sales.csv")
        self.assertEqual(body["usage"]["datasets"], before - 1)
        self.assertNotIn(sales, self.ids("alice"))
        self.assertEqual(self.client.get(f"/api/datasets/{sales}",
                                         headers=self.auth("alice")).status_code, 404)
        # Gone for good: the same bytes uploaded again are stored anew.
        self.assertEqual(self.client.post("/api/datasets?name=sales.csv", content=SALES.encode(),
                                          headers=self.auth("alice")).status_code, 201)

    def test_another_owner_cannot_see_or_remove_it(self):
        sales = self.upload(SALES, "sales.csv", "alice")
        response = self.delete(sales, "mallory")
        self.assertEqual(response.status_code, 404)
        self.assertIn(sales, self.ids("alice"))

    def test_a_viewer_cannot_remove_anything(self):
        sales = self.upload(SALES, "sales.csv", "alice")
        self.assertEqual(self.delete(sales, "alice", "en").status_code, 200)
        lookup = self.upload(PRODUCTS, "products.csv", "alice")
        response = self.client.delete(f"/api/datasets/{lookup}", headers=self.auth("alice", "viewer"))
        self.assertEqual(response.status_code, 403)
        self.assertIn(lookup, self.ids("alice"))

    def test_a_dataset_an_analysis_reads_stays_and_the_analyses_are_named(self):
        sales = self.upload(SALES, "sales.csv", "alice")
        run = self.client.post("/api/runs", headers=self.auth("alice"), json={
            "goal": "Monthly sales by product", "dataset_id": sales}).json()
        for language, needle in (("en", "The dataset stays while an analysis reads it (1)"),
                                 ("ar", "تبقى مجموعة البيانات")):
            with self.subTest(language=language):
                response = self.delete(sales, "alice", language)
                self.assertEqual(response.status_code, 409, response.text)
                body = response.json()
                self.assertEqual(body["error"]["code"], "dataset_in_use")
                self.assertIn(needle, body["error"]["message"])
                self.assertIn("Monthly sales by product", body["error"]["message"])
                self.assertEqual([r["id"] for r in body["detail"]["runs"]], [run["id"]])
        self.assertIn(sales, self.ids("alice"))

    def test_a_joined_dataset_counts_as_read_too(self):
        sales = self.upload(SALES, "sales.csv", "alice")
        products = self.upload(PRODUCTS, "products.csv", "alice")
        created = self.client.post("/api/runs", headers=self.auth("alice"), json={
            "goal": "Sales by product line", "dataset_id": sales,
            "joins": [{"dataset_id": products, "keys": [{"left": "product", "right": "code"}]}]})
        self.assertEqual(created.status_code, 201, created.text)
        response = self.delete(products, "alice")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["runs"][0]["goal"], "Sales by product line")
        # An id that merely appears in a run's goal does not count: the
        # declared joins decide. (Different bytes, or it would be the same
        # content-addressed dataset.)
        decoy = self.upload(PRODUCTS + "C,fans\n", "decoy.csv", "alice")
        self.store.update("runs", created.json()["id"], {"goal": f"mentions {decoy} by name"})
        self.assertEqual(self.delete(decoy, "alice").status_code, 200)

    def test_a_live_source_forgets_the_snapshot_it_last_stored(self):
        sales = self.upload(SALES, "sales.csv", "alice")
        now = "2026-10-27T08:00:00+00:00"
        self.store.insert("connectors", {
            "id": "src-1", "owner": "alice", "name": "Depot export", "url": "https://example.invalid/x.csv",
            "credential_id": None, "format": "csv", "sheet": None, "every_minutes": None,
            "goal": "Watch the export", "language": "en", "profile": None, "enabled": 1,
            "failures": 0, "last_status": "unchanged", "last_error": None, "last_checked_at": now,
            "last_dataset_id": sales, "last_sha256": "abc", "last_run_id": None,
            "next_due_at": None, "lease_owner": None, "lease_expires_at": None,
            "created_at": now, "updated_at": now})
        self.assertEqual(self.delete(sales, "alice").status_code, 200)
        row = self.store.get_connector("src-1")
        self.assertIsNone(row["last_dataset_id"])
        self.assertIsNone(row["last_sha256"])

    def test_the_mapping_goes_with_the_dataset(self):
        sales = self.upload(SALES, "sales.csv", "alice")
        saved = self.client.put(f"/api/datasets/{sales}/mapping", headers=self.auth("alice"), json={
            "roles": {"sales": "measure", "product": "dimension", "month": "date"},
            "measure": "sales"})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.delete(sales, "alice").status_code, 200)
        self.assertIsNone(self.store.get_dataset(sales))


class SqliteDatasetDeletionTestCase(DatasetDeletionMixin, unittest.TestCase):
    def build_client(self, root):
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "Deletion Test",
            "database_file": str(root / "agentic.db"),
            "memory_file": str(root / "memory.json"),
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        return TestClient(closing(self, create_app(config, env={
            "AGENTIC_OS_JWT_SECRET": SECRET, "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_ENV": "production"})), raise_server_exceptions=False)


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class PostgresDatasetDeletionTestCase(DatasetDeletionMixin, unittest.TestCase):
    def build_client(self, root):
        store = open_store(PG_TEST_URL)
        for table in reversed(RESTORE_ORDER):
            if table != "schema_migrations":
                store._exec(f"DELETE FROM {table}")
        store.close()
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "Deletion Test", "database_url": PG_TEST_URL,
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        return TestClient(closing(self, create_app(config, env={
            "AGENTIC_OS_JWT_SECRET": SECRET, "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_ENV": "production"})), raise_server_exceptions=False)


if __name__ == "__main__":
    unittest.main()
