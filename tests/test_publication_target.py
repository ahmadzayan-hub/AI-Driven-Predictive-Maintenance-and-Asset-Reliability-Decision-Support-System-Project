"""Approved publication on a read-only host, with rollback and source fidelity."""

import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from server.model_gateway import ModelGateway
from server.runs import RunEngine, resolve_publish_target
from server.storage import open_store
from tests.test_runs import PG_TEST_URL, _postgres_available


class PublicationTargetTests(unittest.TestCase):
    database_url = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = open_store(self.database_url, self.root / "test.db")
        self.addCleanup(self.store.close)
        self.engine = RunEngine(self.store, self.root / "read-only-vault", ModelGateway(env={}), publish_target="database")

    def ready(self, language="en"):
        run = self.engine.create_run("Synthetic publication target", owner="alice", language=language)
        for _ in range(40):
            if run["state"] == "awaiting_approval":
                return run
            run = self.engine.advance(run["id"])
        self.fail("The synthetic run did not reach its human gate")

    def test_serverless_default_and_explicit_local_override(self):
        self.assertEqual(resolve_publish_target({"VERCEL": "1"}), "database")
        self.assertEqual(resolve_publish_target({}), "vault")
        self.assertEqual(resolve_publish_target({"VERCEL": "1", "AGENTIC_OS_PUBLISH_TARGET": "vault"}), "vault")
        self.assertEqual(resolve_publish_target({}, {"publish_target": "database"}), "database")
        with self.assertRaises(ValueError):
            resolve_publish_target({"AGENTIC_OS_PUBLISH_TARGET": "arbitrary-remote"})

    def test_approved_report_is_durable_without_any_filesystem_write(self):
        run = self.ready()
        self.assertEqual(run["approvals"][0]["target"], "database:Reports")
        self.assertEqual(self.store.list_notes(owner="alice"), [])
        with patch.object(Path, "mkdir", side_effect=AssertionError("Filesystem is read-only")), \
             patch.object(Path, "write_text", side_effect=AssertionError("Filesystem is read-only")):
            result = self.engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "alice")
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["approvals"][0]["state"], "approved_once")
        path = result["report"]["published_path"]
        self.assertTrue(path.startswith("Reports/"))
        self.assertFalse(Path(path).is_absolute())
        self.assertIn(run["report"]["content"], self.store.get_note(path, owner="alice")["content"])
        self.assertEqual(len(self.store.list_notes(owner="alice")), 2)
        self.assertEqual(self.store.list_notes(owner="bob"), [])
        self.assertFalse(self.engine.vault_dir.exists())

    def test_failed_second_note_rolls_back_notes_approval_and_publication(self):
        run = self.ready()
        original = self.store.upsert_note

        def broken(path, *args):
            if path.startswith("Runs/"):
                raise RuntimeError("Synthetic database failure")
            return original(path, *args)

        with patch.object(self.store, "upsert_note", side_effect=broken):
            with self.assertRaises(RuntimeError):
                self.engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "alice")
        after = self.engine.get_run(run["id"])
        self.assertEqual(after["state"], "awaiting_approval")
        self.assertIsNone(after["report"]["published_path"])
        self.assertEqual(after["approvals"][0]["state"], "pending")
        self.assertEqual(self.store.list_notes(owner="alice"), [])
        retried = self.engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "alice")
        self.assertEqual(retried["state"], "completed")

    def test_changed_destination_does_not_reuse_an_approval(self):
        run = self.ready()
        self.engine.publish_target = "vault"
        with self.assertRaisesRegex(ValueError, "destination changed"):
            self.engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "alice")
        self.assertEqual(self.store.list_notes(owner="alice"), [])
        self.assertFalse(self.engine.vault_dir.exists())

    def test_source_name_cannot_inject_frontmatter_keys_in_either_report_language(self):
        name = 'synthetic "ملف"\nadmin: true\\tail.csv'
        for language in ("en", "ar"):
            run = self.ready(language)
            self.store.update("runs", run["id"], {"dataset_name": name})
            result = self.engine.decide_approval(run["id"], run["approvals"][0]["id"], "approve", "alice")
            content = self.store.get_note(result["report"]["published_path"], owner="alice")["content"]
            frontmatter = content.split("---", 2)[1]
            self.assertNotIn("\nadmin:", frontmatter)
            line = next(line for line in frontmatter.splitlines() if line.startswith("dataset: "))
            self.assertEqual(json.loads(line[len("dataset: "):]), name)


@unittest.skipUnless(_postgres_available(), "Disposable PostgreSQL is not configured")
class PublicationTargetPostgresTests(PublicationTargetTests):
    database_url = PG_TEST_URL

    def setUp(self):
        import psycopg2
        from server.storage import TABLES
        with closing(psycopg2.connect(PG_TEST_URL)) as connection:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE")
        super().setUp()


if __name__ == "__main__":
    unittest.main()
