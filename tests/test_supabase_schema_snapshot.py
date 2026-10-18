"""Check the committed Supabase schema against the existing store contract.

The migration is applied through Supabase management, not via public REST
or on every application request. No network calls or credentials needed.
"""
import re
import unittest
from pathlib import Path

from server.storage import SCHEMA_STATEMENTS, TABLES

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "database" / "migrations" / "20261018_asset_reliability_ai_initial.sql"

ADDITIVE = {
    "runs": {"owner": "TEXT", "dataset_id": "TEXT", "lease_owner": "TEXT",
             "lease_expires_at": "TEXT", "report_language": "TEXT",
             "mapping_json": "TEXT", "joins_json": "TEXT",
             "connector_id": "TEXT", "paused": "INTEGER"},
    "sessions": {"owner": "TEXT"},
    "datasets": {"source_format": "TEXT", "row_count": "INTEGER",
                 "column_count": "INTEGER", "mapping_json": "TEXT",
                 "mapping_updated_at": "TEXT"},
}


class SupabaseSchemaSnapshotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = SQL.read_text(encoding="utf-8")

    def test_nine_application_tables_match_store(self):
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

    def test_all_tables_are_inaccessible_to_direct_public_api(self):
        for table in TABLES:
            self.assertIn(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;", self.sql)
            self.assertIn(
                f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC, anon, authenticated;",
                self.sql)
        self.assertNotIn("CREATE POLICY", self.sql.upper())
        self.assertNotRegex(self.sql, r"(?im)^\s*GRANT\s+.*\s+TO\s+(?:anon|authenticated)\b")


if __name__ == "__main__":
    unittest.main()
