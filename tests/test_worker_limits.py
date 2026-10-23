"""The production worker must enforce the same resource policy as the API."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.worker import build_worker


class WorkerLimitsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({
            "database_file": str(self.root / "worker.db"),
            "vault_dir": str(self.root / "vault"),
        }), encoding="utf-8")

    def worker(self, **env):
        worker = build_worker(config_path=self.config, env=env)
        self.addCleanup(worker.store.close)
        worker.connectors.fetcher = lambda url: b"month,region,revenue\n2026-01,North,10\n"
        return worker

    def refresh(self, worker):
        connector = worker.connectors.create(
            "review-owner", "Synthetic source", "https://example.com/source.csv",
            "Review the source", every_minutes=15)
        self.assertEqual(worker.refresh_due(), connector["id"])
        return worker.store.get_connector(connector["id"])

    def test_scheduled_refresh_cannot_bypass_dataset_count_limit(self):
        worker = self.worker(AGENTIC_OS_QUOTA_DATASETS="0")
        self.assertEqual(self.refresh(worker)["last_status"], "failed")
        self.assertEqual(worker.store.dataset_usage("review-owner")["datasets"], 0)
        self.assertEqual(worker.store.list_runs("review-owner"), [])

    def test_scheduled_refresh_cannot_bypass_dataset_byte_limit(self):
        worker = self.worker(AGENTIC_OS_QUOTA_DATASET_BYTES="1")
        self.assertEqual(self.refresh(worker)["last_status"], "failed")
        self.assertEqual(worker.store.dataset_usage("review-owner")["bytes"], 0)

    def test_scheduled_refresh_cannot_bypass_daily_run_limit(self):
        worker = self.worker(AGENTIC_OS_QUOTA_RUNS_PER_DAY="0")
        result = self.refresh(worker)
        self.assertEqual(result["last_status"], "failed")
        self.assertIn("Daily run limit", result["last_error"])
        self.assertEqual(worker.store.list_runs("review-owner"), [])

    def test_scheduled_refresh_within_limits_still_starts_a_run(self):
        worker = self.worker()
        self.assertEqual(self.refresh(worker)["last_status"], "updated")
        self.assertEqual(len(worker.store.list_runs("review-owner")), 1)

    def test_environment_selects_worker_config_and_vault(self):
        selected_vault = self.root / "selected-vault"
        with patch("server.worker.open_store") as open_store:
            worker = build_worker(env={
                "AGENTIC_OS_CONFIG": str(self.config),
                "AGENTIC_OS_VAULT_DIR": str(selected_vault),
            })
        self.assertEqual(open_store.call_args.args[1], str(self.root / "worker.db"))
        self.assertEqual(worker.engine.vault_dir, selected_vault)

    def test_explicit_config_takes_precedence_over_environment(self):
        with patch("server.worker.open_store") as open_store:
            build_worker(config_path=self.config, env={
                "AGENTIC_OS_CONFIG": str(self.root / "other.json"),
            })
        self.assertEqual(open_store.call_args.args[1], str(self.root / "worker.db"))


if __name__ == "__main__":
    unittest.main()
