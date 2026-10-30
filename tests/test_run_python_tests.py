"""Tests for scripts/run_python_tests.py, the parallel Python suite runner."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_python_tests as runner  # noqa: E402


class PlanTests(unittest.TestCase):

    def files(self, contents):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [p.unlink() for p in folder.iterdir()] and folder.rmdir())
        paths = []
        for name, text in contents.items():
            path = folder / f"test_{name}.py"
            path.write_text(text, encoding="utf-8")
            paths.append(path)
        return paths

    def test_every_file_runs_once_and_role_files_never_overlap(self):
        files = self.files({
            "roles_a": "PG_TEST_URL\nCREATE ROLE x", "roles_b": "psycopg2\nDROP ROLE y",
            "pg": "PG_TEST_URL" + "x" * 500, "plain_big": "y" * 900, "plain": "z",
            "plain_2": "z", "plain_3": "z"})
        batches = runner.plan(files, isolated=True)
        flat = [f for batch in batches for f in batch]
        self.assertEqual(sorted(flat), sorted(files))
        roles = {f for f in files if "roles" in f.stem}
        self.assertIn(roles, [set(b) for b in batches])
        self.assertTrue(all(len(b) <= runner.BATCH for b in batches if not set(b) & roles))
        # The heaviest batch starts first: a PostgreSQL file weighs more.
        self.assertIn(files[2], batches[0])

    def test_without_isolated_databases_every_postgres_file_runs_in_one_batch(self):
        files = self.files({"a": "PG_TEST_URL", "b": "import psycopg2", "c": "plain"})
        batches = runner.plan(files, isolated=False)
        self.assertIn({files[0], files[1]}, [set(b) for b in batches])
        self.assertIn([files[2]], batches)


class DatabaseCopyTests(unittest.TestCase):

    def test_no_database_or_one_worker_needs_no_copy(self):
        self.assertEqual(runner.database_copies(None, 4), [None] * 4)
        url = "postgresql://dev@127.0.0.1:5432/agentic_test"
        self.assertEqual(runner.database_copies(url, 1), [url])

    def test_copies_are_named_after_the_database(self):
        connection = mock.MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)
        fake = mock.MagicMock(connect=mock.MagicMock(return_value=connection))
        with mock.patch.dict(sys.modules, {"psycopg2": fake}):
            urls = runner.database_copies("postgresql://dev@127.0.0.1:5432/agentic_test", 3)
        self.assertEqual(urls, ["postgresql://dev@127.0.0.1:5432/agentic_test",
                                "postgresql://dev@127.0.0.1:5432/agentic_test_w2",
                                "postgresql://dev@127.0.0.1:5432/agentic_test_w3"])

    def test_a_copy_that_refuses_the_user_means_the_safe_plan(self):
        connection = mock.MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)

        def connect(url, **_):
            if url.endswith("_w2"):
                raise RuntimeError("password authentication failed")
            return connection
        fake = mock.MagicMock(connect=connect)
        with mock.patch.dict(sys.modules, {"psycopg2": fake}), mock.patch("builtins.print"):
            self.assertIsNone(runner.database_copies("postgresql://dev@h:5432/agentic_test", 2))


if __name__ == "__main__":
    unittest.main()
