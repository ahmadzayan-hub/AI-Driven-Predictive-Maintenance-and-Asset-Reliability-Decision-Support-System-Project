"""Independent connections cannot admit excess work or execute one task twice."""

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from server import analytics, quota
from server.model_gateway import ModelGateway
from server.runs import RunEngine
from server.storage import TABLES, open_store
from tests.test_runs import PG_TEST_URL, _postgres_available


class AtomicAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.reset_database()
        self.stores = [self.open_store(), self.open_store()]
        for store in self.stores:
            self.addCleanup(store.close)
        limits = {"runs_per_day": 1, "datasets": 1, "dataset_bytes": 1000000}
        self.engines = [RunEngine(store, self.root / "vault", ModelGateway(env={}),
                                  limits=limits) for store in self.stores]

    def reset_database(self):
        pass

    def open_store(self):
        return open_store(sqlite_path=self.root / "atomic.db")

    def race(self, function):
        outcomes = []
        errors = []
        start = threading.Barrier(2)

        def run(index):
            try:
                start.wait(timeout=5)
                outcomes.append(function(self.engines[index], index))
            except quota.QuotaExceeded:
                outcomes.append("refused")
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive(), "concurrent admission hung")
        self.assertEqual(errors, [])
        return outcomes

    def overlap_check(self, original):
        barrier = threading.Barrier(2)

        def check(*args, **kwargs):
            original(*args, **kwargs)
            try:
                barrier.wait(timeout=0.2)
            except threading.BrokenBarrierError:
                pass  # With atomic admission the other writer must wait.
        return check

    def test_dataset_quota_is_atomic_across_connections(self):
        with patch.object(quota, "check_dataset", self.overlap_check(quota.check_dataset)):
            outcomes = self.race(lambda engine, i: engine.store_dataset(
                f"month,value\n2026-01,{i + 1}\n", f"source-{i}", "owner")["id"])
        self.assertEqual(outcomes.count("refused"), 1)
        self.assertEqual(self.stores[0].dataset_usage("owner")["datasets"], 1)

    def test_daily_run_quota_is_atomic_across_connections(self):
        dataset = self.engines[0].store_dataset("month,value\n2026-01,1\n", "source", "owner")
        with patch.object(quota, "check_run", self.overlap_check(quota.check_run)):
            outcomes = self.race(lambda engine, i: engine.create_run(
                "Synthetic review", owner="owner", dataset_id=dataset["id"])["id"])
        self.assertEqual(outcomes.count("refused"), 1)
        self.assertEqual(len(self.stores[0].list_runs("owner")), 1)

    def test_failed_run_creation_rolls_back_all_new_rows(self):
        original = self.stores[0].insert

        def failing_insert(table, row):
            if table == "tasks" and row["idx"] == 1:
                raise RuntimeError("synthetic interrupted creation")
            original(table, row)

        with patch.object(self.stores[0], "insert", failing_insert):
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                self.engines[0].create_run("Synthetic review", owner="owner")
        self.assertEqual(self.stores[1].list_runs("owner"), [])
        self.assertEqual(self.stores[1].dataset_usage("owner")["datasets"], 0)
        self.assertEqual(self.stores[1]._exec("SELECT * FROM tasks"), [])

    def test_two_clients_do_not_reclaim_a_live_task_as_an_orphan(self):
        run = self.engines[0].create_run("Synthetic review", owner="owner")
        entered = threading.Event()
        duplicate = threading.Event()
        release = threading.Event()
        calls = []
        errors = []
        role, collector = analytics.PIPELINE[0]

        def slow_collector(ctx):
            calls.append(1)
            entered.set()
            if len(calls) > 1:
                duplicate.set()
            if not release.wait(timeout=5):
                raise RuntimeError("test failed to release collector")
            return collector(ctx)

        def advance(engine):
            try:
                engine.advance(run["id"])
            except Exception as error:
                errors.append(error)

        with patch.object(analytics, "PIPELINE", [(role, slow_collector), *analytics.PIPELINE[1:]]):
            first = threading.Thread(target=advance, args=(self.engines[0],))
            second = threading.Thread(target=advance, args=(self.engines[1],))
            first.start()
            self.assertTrue(entered.wait(timeout=5))
            second.start()
            duplicate.wait(timeout=0.2)
            release.set()
            first.join(timeout=10)
            second.join(timeout=10)
            self.assertFalse(first.is_alive() or second.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(calls), 1, "a second client executed the same live task")
        tasks = self.stores[0].get_tasks(run["id"])
        self.assertEqual(sum(t["state"] == "succeeded" for t in tasks), 2)


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class AtomicAdmissionPostgresTests(AtomicAdmissionTests):
    def reset_database(self):
        import psycopg2
        with psycopg2.connect(PG_TEST_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE")

    def open_store(self):
        return open_store(database_url=PG_TEST_URL)


if __name__ == "__main__":
    unittest.main()
