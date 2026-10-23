"""Check the committed Supabase schema against the existing store contract.

Static checks need no database. The conditional PostgreSQL smoke executes
the snapshot only in a disposable test database and rolls back every change.
"""
import re
import unittest
import uuid
from pathlib import Path

from server.storage import SCHEMA_STATEMENTS, TABLES
from tests.test_runs import PG_TEST_URL, _postgres_available

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "database" / "migrations" / "20261018_asset_reliability_ai_initial.sql"

ADDITIVE = {
    "runs": {"owner": "TEXT", "dataset_id": "TEXT", "lease_owner": "TEXT",
             "lease_expires_at": "TEXT", "report_language": "TEXT",
             "mapping_json": "TEXT", "joins_json": "TEXT",
             "connector_id": "TEXT", "assumptions_json": "TEXT",
             "idempotency_key": "TEXT", "request_hash": "TEXT", "paused": "INTEGER"},
    "approvals": {"decided_by": "TEXT"},
    "sessions": {"owner": "TEXT"},
    "datasets": {"source_format": "TEXT", "row_count": "INTEGER",
                 "column_count": "INTEGER", "mapping_json": "TEXT",
                 "mapping_updated_at": "TEXT"},
    "connectors": {"credential_id": "TEXT"},
}


class SupabaseSchemaSnapshotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = SQL.read_text(encoding="utf-8")

    def test_application_tables_match_store(self):
        expected = {re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", ddl).group(1)
                    for ddl in SCHEMA_STATEMENTS}
        found = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", self.sql))
        self.assertEqual(expected, set(TABLES))
        self.assertEqual(found, expected)

    def test_additive_columns_are_provisioned(self):
        for table, columns in ADDITIVE.items():
            matches = re.findall(
                rf"CREATE TABLE IF NOT EXISTS {table}\s*\((.*?)\);",
                self.sql, flags=re.DOTALL,
            )
            self.assertEqual(len(matches), 1, table)
            for col, typ in columns.items():
                with self.subTest(table=table, column=col):
                    self.assertRegex(matches[0], rf"\b{col}\s+{typ}\b")

    def test_base_columns_keys_and_relationships_match_store(self):
        # A table-name-only mirror can omit a field, weaken nullability or
        # drop a tenant uniqueness constraint while appearing complete.
        # Compare normalized DDL after removing explicitly migrated fields.
        normalize = lambda value: re.sub(r"\s+", "", value).lower()
        for statement in SCHEMA_STATEMENTS:
            table = re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", statement).group(1)
            expected = statement.split("(", 1)[1].rsplit(")", 1)[0]
            actual = re.search(rf"CREATE TABLE IF NOT EXISTS {table}\s*\((.*?)\);",
                               self.sql, flags=re.DOTALL).group(1)
            # Since 23 October the base statements carry the additive
            # columns too, so the mirror is compared in full.
            with self.subTest(table=table):
                self.assertEqual(normalize(actual), normalize(expected))

    def test_all_tables_are_inaccessible_to_direct_public_api(self):
        for table in TABLES:
            self.assertIn(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;", self.sql)
            self.assertIn(
                f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC, anon, authenticated;",
                self.sql)
        self.assertNotIn("CREATE POLICY", self.sql.upper())
        self.assertNotRegex(self.sql, r"(?im)^\s*GRANT\s+.*\s+TO\s+(?:anon|authenticated)\b")


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class SupabaseSchemaPostgresTest(unittest.TestCase):
    """Use PG_TEST_URL's disposable database, never a hosted project."""

    def test_snapshot_enables_rls_and_revokes_existing_default_grants(self):
        import psycopg2
        from psycopg2 import sql

        connection = psycopg2.connect(PG_TEST_URL, connect_timeout=3)
        schema = "schema_snapshot_" + uuid.uuid4().hex
        roles = ("anon", "authenticated")
        privileges = ("SELECT", "INSERT", "UPDATE", "DELETE",
                      "TRUNCATE", "REFERENCES", "TRIGGER")
        try:
            # No commits: new roles, schema, defaults and objects all disappear
            # on rollback, including when a SQL statement or assertion fails.
            connection.autocommit = False
            with connection.cursor() as cursor:
                for role in roles:
                    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                    if cursor.fetchone() is None:
                        cursor.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(
                            sql.Identifier(role)))
                cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
                cursor.execute(sql.SQL("SET LOCAL search_path TO {}, pg_catalog").format(
                    sql.Identifier(schema)))
                cursor.execute(sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA {} "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}, {}"
                ).format(sql.Identifier(schema), *(sql.Identifier(role) for role in roles)))

                snapshot = SQL.read_text(encoding="utf-8")
                snapshot = re.sub(
                    r"(?im)^[ \t]*(?:BEGIN|COMMIT)[ \t]*;[ \t]*\r?$", "", snapshot)
                self.assertNotRegex(snapshot, r"(?im)^[ \t]*(?:BEGIN|COMMIT)\b")
                prefix = sql.Identifier(schema).as_string(connection) + "."
                cursor.execute(snapshot.replace("public.", prefix))

                cursor.execute(
                    "SELECT c.relname, c.oid, c.relrowsecurity "
                    "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = %s AND c.relkind IN ('r', 'p')", (schema,))
                tables = {name: (oid, rls) for name, oid, rls in cursor.fetchall()}
                self.assertEqual(set(tables), set(TABLES))
                for table, (oid, rls) in tables.items():
                    with self.subTest(table=table):
                        self.assertTrue(rls)
                    for role in roles:
                        for privilege in privileges:
                            with self.subTest(table=table, role=role, privilege=privilege):
                                cursor.execute(
                                    "SELECT has_table_privilege(%s, %s::oid, %s)",
                                    (role, oid, privilege))
                                self.assertIs(cursor.fetchone()[0], False)
        finally:
            try:
                connection.rollback()
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
