"""Synthetic transaction/child-environment regressions; no model or encoder."""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from server.motion_local import LocalMotion
from tests.support import isolated_process_env


class MotionConnectionLifetimeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        env = patch.dict(os.environ, {"AGENTIC_MOTION_ROOT": directory.name})
        env.start()
        self.addCleanup(env.stop)
        self.motion = LocalMotion()

    def test_commit_and_connection_release(self):
        with self.motion.connect() as connection:
            connection.execute("CREATE TABLE lifetime_test (value INTEGER)")
            connection.execute("INSERT INTO lifetime_test VALUES (1)")
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
        with self.motion.connect() as reopened:
            self.assertEqual(reopened.execute("SELECT value FROM lifetime_test").fetchone()[0], 1)

    def test_exception_rolls_back_and_releases_connection(self):
        with self.motion.connect() as connection:
            connection.execute("CREATE TABLE lifetime_test (value INTEGER)")
        with self.assertRaisesRegex(RuntimeError, "synthetic rollback"):
            with self.motion.connect() as failed:
                failed.execute("INSERT INTO lifetime_test VALUES (1)")
                raise RuntimeError("synthetic rollback")
        with self.assertRaises(sqlite3.ProgrammingError):
            failed.execute("SELECT 1")
        with self.motion.connect() as reopened:
            self.assertEqual(reopened.execute("SELECT COUNT(*) FROM lifetime_test").fetchone()[0], 0)


class ChildEnvironmentTests(unittest.TestCase):
    def test_windows_bootstrap_is_retained_without_credentials(self):
        with patch.dict(os.environ, {"PATH": "fixture-bin", "SystemRoot": "fixture-system",
                "OPENAI_API_KEY": "synthetic-not-a-key", "OLLAMA_MODEL": "not-inherited",
                "AGENTIC_OS_CONFIG": "private-config"}, clear=True):
            env = isolated_process_env()
        self.assertEqual(env, {"PATH": "fixture-bin", "PYTHONPATH": "",
                              "PYTHONDONTWRITEBYTECODE": "1", "SystemRoot": "fixture-system"})

    def test_absent_system_root_is_not_invented(self):
        with patch.dict(os.environ, {"PATH": "fixture-bin"}, clear=True):
            self.assertNotIn("SystemRoot", isolated_process_env())
