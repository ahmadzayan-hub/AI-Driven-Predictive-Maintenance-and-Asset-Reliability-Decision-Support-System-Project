"""A saved dashboard view per owner and dataset (ADR 2026-10-27-interactive-dashboard).

The view a reader saves on one run's dashboard is applied to every run of
theirs over the same dataset, stored or named; another owner's run is a
404, never a 403; a viewer cannot save; an address that is not the
dashboard's own is refused in the reader's language. Checked on SQLite
and, when a test database is reachable, PostgreSQL.
"""

import json
import re
import tempfile
import uuid
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - the CLI-only install
    FASTAPI_AVAILABLE = False

if FASTAPI_AVAILABLE:
    from server.app import create_app

from server import dashboard_views
from server.storage import RESTORE_ORDER, TABLES, open_store
from tests.support import closing, scoped_token
from tests.test_runs import PG_TEST_URL, _postgres_available

SECRET = "dashboard-views-test-secret"
SALES = "month,product,sales\n2025-01,A,10\n2025-02,A,12\n2025-03,B,9\n2025-04,B,11\n"
VIEW = {"page": "breakdown", "query": "f.product=A&by=product&per=1"}


class ValidationTests(unittest.TestCase):
    def test_the_dataset_key_prefers_the_stored_dataset(self):
        self.assertEqual(dashboard_views.dataset_key({"dataset_id": "d1", "dataset_name": "x"}), "dataset:d1")
        self.assertEqual(dashboard_views.dataset_key({"dataset_id": None, "dataset_name": "sample"}), "name:sample")

    def test_a_dashboard_address_is_kept_in_canonical_form(self):
        page, query = dashboard_views.validate("trend", "f.region=North&f.region=South&from=2025-01&o=25")
        self.assertEqual(page, "trend")
        self.assertEqual(query, "f.region=North&f.region=South&from=2025-01&o=25")
        self.assertEqual(dashboard_views.validate("overview", ""), ("overview", ""))

    def test_refusals_name_the_problem_in_both_languages(self):
        cases = [
            (("records ", ""), "not one of the dashboard's pages", "ليست من صفحات"),
            (("overview", "page=1"), "“page” is not a dashboard setting", "ليس إعداداً"),
            (("overview", "f.=x"), "“f.” is not a dashboard setting", "ليس إعداداً"),
            (("overview", "f.a=" + "x" * 201), "longer than 200 characters", "أطول من 200"),
            (("overview", "&".join(f"f.c{i}=v" for i in range(61))), "more than 60 settings", "أكثر من 60"),
            (("overview", "f.a=b" * 500), "longer than 2000 characters", "أطول من 2000"),
        ]
        for (page, query), en, ar in cases:
            with self.subTest(page=page, query=query[:20]):
                with self.assertRaises(dashboard_views.ViewError) as caught:
                    dashboard_views.validate(page, query)
                self.assertIn(en, caught.exception.detail("en"))
                self.assertIn(ar, caught.exception.detail("ar"))

    def test_the_table_is_backed_up_and_restored(self):
        self.assertIn("dashboard_views", TABLES)
        self.assertIn("dashboard_views", RESTORE_ORDER)
        self.assertLess(RESTORE_ORDER.index("runs"), RESTORE_ORDER.index("dashboard_views"))


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class SavedViewMixin:
    def build_client(self, root):  # pragma: no cover - provided by subclasses
        raise NotImplementedError

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.client = self.build_client(self.root)

    def auth(self, subject, role="owner"):
        return {"Authorization": "Bearer " + scoped_token(SECRET, subject=subject, role=role)}

    def upload(self, subject, name="sales.csv", text=SALES):
        response = self.client.post(f"/api/datasets?name={name}", content=text.encode(),
                                    headers=self.auth(subject))
        self.assertIn(response.status_code, (200, 201), response.text)
        return response.json()["dataset"]["id"]

    def start(self, subject, **body):
        response = self.client.post("/api/runs", headers=self.auth(subject),
                                    json={"goal": "Sales by product", **body})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def view(self, run_id, subject, language="en"):
        response = self.client.get(f"/api/runs/{run_id}/view?language={language}", headers=self.auth(subject))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["view"]

    def save(self, run_id, subject, body=VIEW, language="en", role="owner"):
        return self.client.put(f"/api/runs/{run_id}/view?language={language}", json=body,
                               headers=self.auth(subject, role))

    def test_a_view_follows_the_dataset_across_runs_and_owners(self):
        sales = self.upload("alice")
        first = self.start("alice", dataset_id=sales)
        self.assertIsNone(self.view(first, "alice"))
        saved = self.save(first, "alice")
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["view"]["page"], "breakdown")
        self.assertEqual(saved.json()["view"]["query"], VIEW["query"])
        self.assertEqual(saved.json()["view"]["run_id"], first)
        # A later run over the same stored dataset opens the same way.
        second = self.start("alice", dataset_id=sales)
        self.assertEqual(self.view(second, "alice")["query"], VIEW["query"])
        # A run over another dataset has no view; another owner sees nothing.
        # The same bytes are one stored dataset, so the other one differs.
        other = self.start("alice", dataset_id=self.upload("alice", "other.csv", SALES + "2025-05,B,8\n"))
        self.assertIsNone(self.view(other, "alice"))
        self.assertEqual(self.client.get(f"/api/runs/{first}/view", headers=self.auth("mallory")).status_code, 404)
        self.assertEqual(self.save(first, "mallory").status_code, 404)
        self.assertEqual(self.save(first, "alice", role="viewer").status_code, 403)
        # Saving again replaces, one row per owner and dataset.
        again = self.save(second, "alice", {"page": "trend", "query": "from=2025-02"})
        self.assertEqual(again.status_code, 200, again.text)
        self.assertEqual(self.view(first, "alice"), {**self.view(second, "alice")})
        self.assertEqual(self.view(first, "alice")["page"], "trend")
        self.assertEqual(self.view(first, "alice")["run_id"], second)
        # Forgetting it.
        self.assertEqual(self.client.delete(f"/api/runs/{first}/view", headers=self.auth("alice")).status_code, 204)
        self.assertIsNone(self.view(second, "alice"))
        self.assertEqual(self.client.delete(f"/api/runs/{first}/view", headers=self.auth("alice")).status_code, 204)

    def test_sample_runs_share_a_view_by_name_and_refusals_are_bilingual(self):
        first, second = self.start("alice"), self.start("alice")
        self.assertEqual(self.save(first, "alice", {"page": "records", "query": "sort=sales&desc=1"}).status_code, 200)
        self.assertEqual(self.view(second, "alice")["page"], "records")
        for language, needle in (("en", "“x” is not a dashboard setting"), ("ar", "«x» ليس إعداداً")):
            response = self.save(first, "alice", {"page": "records", "query": "x=1"}, language)
            self.assertEqual(response.status_code, 422, response.text)
            self.assertIn(needle, response.json()["error"]["message"])
        self.assertEqual(self.save(first, "alice", {"page": "nowhere", "query": ""}).status_code, 422)
        self.assertEqual(self.view(second, "alice")["query"], "sort=sales&desc=1")


class SqliteSavedViewTestCase(SavedViewMixin, unittest.TestCase):
    def build_client(self, root):
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "View Test",
            "database_file": str(root / "agentic.db"),
            "memory_file": str(root / "memory.json"),
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        return TestClient(closing(self, create_app(config, env={
            "AGENTIC_OS_JWT_SECRET": SECRET, "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_ENV": "production"})), raise_server_exceptions=False)


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class PostgresSavedViewTestCase(SavedViewMixin, unittest.TestCase):
    def build_client(self, root):
        store = open_store(PG_TEST_URL)
        for table in reversed(RESTORE_ORDER):
            if table != "schema_migrations":
                store._exec(f"DELETE FROM {table}")
        store.close()
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "View Test", "database_url": PG_TEST_URL,
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        return TestClient(closing(self, create_app(config, env={
            "AGENTIC_OS_JWT_SECRET": SECRET, "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_ENV": "production"})), raise_server_exceptions=False)


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class DashboardViewsMigrationTest(unittest.TestCase):
    """The operator's migration on a disposable schema: it applies, re-applies,
    refuses a table of another shape, and leaves the table the way the store
    expects it (ADR 2026-10-27-interactive-dashboard)."""

    MIGRATION = Path(__file__).resolve().parents[1] / "database" / "migrations" / "20261027_dashboard_views.sql"

    def test_applies_twice_refuses_drift_and_matches_the_store(self):
        import psycopg2
        from psycopg2 import sql

        connection = psycopg2.connect(PG_TEST_URL, connect_timeout=3)
        schema = "dashboard_views_" + uuid.uuid4().hex
        try:
            connection.autocommit = False
            with connection.cursor() as cursor:
                cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
                cursor.execute(sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(sql.Identifier(schema)))
                prefix = sql.Identifier(schema).as_string(connection) + "."
                # The file's own BEGIN and COMMIT would end this test's transaction
                # and leave the schema behind; they are stripped, as the snapshot test does.
                script = re.sub(r"(?im)^[ \t]*(?:BEGIN|COMMIT)[ \t]*;[ \t]*\r?$", "",
                                self.MIGRATION.read_text(encoding="utf-8")).replace("public.", prefix)
                # Every schema name the file uses must point at the disposable schema.
                script = script.replace("'public'", f"'{schema}'")
                cursor.execute(script)
                cursor.execute(script)  # a second run changes nothing and does not fail
                cursor.execute("SELECT column_name FROM information_schema.columns "
                               "WHERE table_schema = %s AND table_name = 'dashboard_views' "
                               "ORDER BY ordinal_position", (schema,))
                self.assertEqual([r[0] for r in cursor.fetchall()],
                                 ["id", "owner", "dataset_key", "run_id", "page", "query", "updated_at"])
                cursor.execute("SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                               "WHERE n.nspname = %s AND c.relname = 'dashboard_views'", (schema,))
                self.assertTrue(cursor.fetchone()[0])
                # A table of another shape is refused, not altered.
                cursor.execute("ALTER TABLE dashboard_views DROP COLUMN query")
                with self.assertRaises(psycopg2.Error):
                    cursor.execute(script)
        finally:
            try:
                connection.rollback()
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
