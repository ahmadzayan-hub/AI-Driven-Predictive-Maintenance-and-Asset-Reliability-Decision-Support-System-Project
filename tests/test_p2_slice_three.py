"""The third P2 slice (assessment A7, A11, A14, A18, B6, B11): a corrective
repair-time KPI, screened inputs on every model card, versioned cards with
the snapshot and training window, reversible cleaning, a store-backed rate
limit with a per-tenant model budget, and one PostgreSQL connection per
thread."""

import json
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient

from server import analytics, modelling, quota, tenant
from server.app import create_app
from server.maintenance import kpis
from server.model_gateway import ModelGateway
from server.rate_limit import RateLimiter, RateLimitUnavailable, StoreRateLimiter
from server.storage import PostgresStore, open_store
from tests.support import closing, closing_store
from tests.test_analytics import run_pipeline
from tests.test_runs import PG_TEST_URL, _postgres_available


class CorrectiveRepairTimeTest(unittest.TestCase):
    """A7: a repair time over corrective work only, beside the one that
    includes planned downtime."""

    def test_the_register_carries_the_corrective_basis(self):
        kpi = kpis.REGISTER["mttr_corrective"]
        self.assertIs(kpi.population, kpis.corrective_only)
        self.assertIn("Work_Order_Type", kpi.source_columns)
        self.assertIsNot(kpis.REGISTER["mttr"].population, kpis.corrective_only)

    def test_planned_downtime_is_left_out(self):
        rows = [{"Work_Order_Type": "Corrective", "Downtime_Hours": 4, "Failure_Count": 1},
                {"Work_Order_Type": "Corrective", "Downtime_Hours": 2, "Failure_Count": 1},
                {"Work_Order_Type": "Preventive", "Downtime_Hours": 30, "Failure_Count": 1}]
        corrective = kpis.REGISTER["mttr_corrective"].compute(rows)
        self.assertEqual(corrective["value"], 3.0)
        self.assertEqual(corrective["rows"] if "rows" in corrective else corrective["records"], 2)
        self.assertEqual(kpis.REGISTER["mttr"].compute(rows)["value"], 12.0)


class ReversibleCleaningTest(unittest.TestCase):
    """A18: every removal is recorded by source row; unreadable numbers
    are a calculation and a claim."""

    def test_dropped_rows_and_unreadable_values_are_recorded(self):
        numbers = "\n".join(f"{i},{i * 2}" for i in range(4, 20))
        text = f"job,hours\n1,4\n,\n1,4\n2,n/a\n{numbers}\n"
        ctx, results = run_pipeline(text)
        output = ctx["cleaner"]
        self.assertEqual(output["dropped_indices"], {"empty": [1], "duplicates": [2]})
        self.assertEqual(output["unreadable_values"],
                         [{"row": 3, "column": "hours", "value": "n/a"}])
        calc = next(c for c in results["cleaner"]["calculations"] if c["id"] == "c_coercion")
        self.assertEqual(calc["value"], 1)
        claim = next(c for c in results["cleaner"]["claims"] if c["id"] == "cl_coercion")
        self.assertEqual(claim["type"], "limitation")
        self.assertIn("hours", claim["text"])
        self.assertEqual(claim["evidence"], ["c_coercion"])

    def test_a_clean_dataset_makes_no_coercion_claim(self):
        ctx, results = run_pipeline("job,hours\n1,4\n2,5\n3,6\n")
        self.assertEqual(ctx["cleaner"]["unreadable_values"], [])
        self.assertFalse([c for c in results["cleaner"]["claims"] if c["id"] == "cl_coercion"])
        self.assertEqual(ctx["cleaner"]["dropped_indices"], {"empty": [], "duplicates": []})

    def test_the_record_of_unreadable_values_is_capped(self):
        bad = analytics.MAX_UNREADABLE_RECORDED + 50
        rows = [f"{i},bad" for i in range(bad)] + [f"{i},{i}" for i in range(bad, bad * 12)]
        ctx, results = run_pipeline("job,hours\n" + "\n".join(rows))
        calc = next(c for c in results["cleaner"]["calculations"] if c["id"] == "c_coercion")
        self.assertEqual(calc["value"], bad)
        self.assertEqual(len(ctx["cleaner"]["unreadable_values"]),
                         analytics.MAX_UNREADABLE_RECORDED)


class VersionedModelCardTest(unittest.TestCase):
    """A14 and A11: a card says which code scored it, on which snapshot,
    over which period, and which inputs were refused and why."""

    def test_a_card_carries_version_snapshot_window_and_fitting_time(self):
        card = modelling._card("regression", "y", ["x"], 300, 100,
                               {"method": "chronological"}, "r2", 0.5, 0.1,
                               "mean", 0.4, True, {},
                               ctx={"collector": {"snapshot": "sha256:abc"}},
                               window={"first": "2026-01", "last": "2026-06"},
                               excluded={"id": "an identifier, not a measurement"})
        self.assertEqual(card["version"], modelling.CARD_VERSION)
        self.assertEqual(card["snapshot"], "sha256:abc")
        self.assertEqual(card["training_window"], {"first": "2026-01", "last": "2026-06"})
        self.assertRegex(card["fitted_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(card["excluded_inputs"], {"id": "an identifier, not a measurement"})

    def test_a_card_without_a_context_still_says_its_version(self):
        card = modelling._card("regression", "y", ["x"], 300, 100, {}, "r2",
                               0.5, 0.1, "mean", 0.4, True, {})
        self.assertEqual(card["version"], modelling.CARD_VERSION)
        self.assertIsNone(card["snapshot"])
        self.assertNotIn("excluded_inputs", card)

    def test_the_training_window_comes_from_the_training_rows(self):
        rows = [{"d": "2026-03"}, {"d": "2026-01"}, {"d": ""}, {"d": "2026-02"}]
        self.assertEqual(modelling._window(rows, "d"), {"first": "2026-01", "last": "2026-03"})
        self.assertIsNone(modelling._window(rows, None))
        self.assertIsNone(modelling._window([{"d": None}], "d"))

    def test_a_model_stage_binds_its_card_to_the_run_snapshot(self):
        from tests.test_modelling import context, linear_rows
        ctx = context(linear_rows(), ["channel", "price", "ads", "sales"],
                      ["price", "ads", "sales"], "sales")
        ctx["collector"]["snapshot"] = "sha256:slice-three"
        card = modelling.RegressionModel().run(ctx)["output"]["model_card"]
        self.assertEqual(card["version"], modelling.CARD_VERSION)
        self.assertEqual(card["snapshot"], "sha256:slice-three")
        self.assertIsNone(card["training_window"])  # no date column


class StoreRateLimiterTest(unittest.TestCase):
    """B6: the window is counted in the store, so two instances share it."""

    def stores(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "agentic.db"
        first = closing_store(self, open_store(None, path))
        second = closing_store(self, open_store(None, path))
        return first, second

    def test_two_instances_share_one_window(self):
        first, second = self.stores()
        clock = [1000.0]
        a = StoreRateLimiter(first, limit=5, window_seconds=60, clock=lambda: clock[0])
        b = StoreRateLimiter(second, limit=5, window_seconds=60, clock=lambda: clock[0])
        verdicts = [a.check("ip:1")[0] if i % 2 else b.check("ip:1")[0] for i in range(7)]
        self.assertEqual(verdicts, [True] * 5 + [False, False])
        allowed, remaining, retry_after = a.check("ip:1")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)
        self.assertGreaterEqual(retry_after, 1)
        self.assertTrue(b.check("ip:2")[0], "another caller has its own window")

    def test_exact_boundary_resets_only_after_the_fixed_window(self):
        first, _ = self.stores()
        clock = [1259.999]
        limiter = StoreRateLimiter(first, limit=3, window_seconds=60, clock=lambda: clock[0])
        self.assertEqual([limiter.check("boundary")[0] for _ in range(4)], [True, True, True, False])
        clock[0] = 1260.0
        self.assertEqual([limiter.check("boundary")[0] for _ in range(4)], [True, True, True, False])
        rows = first._exec("SELECT window_start, count FROM rate_windows WHERE key=? ORDER BY window_start", ("boundary",))
        self.assertEqual([(r["window_start"], r["count"]) for r in rows], [(1200, 4), (1260, 4)])

    def test_a_new_window_opens_and_old_ones_are_dropped(self):
        first, _ = self.stores()
        clock = [1000.0]
        limiter = StoreRateLimiter(first, limit=2, window_seconds=60, clock=lambda: clock[0])
        for _ in range(3):
            limiter.check("ip:1")
        clock[0] += 200  # three windows on
        self.assertTrue(limiter.check("ip:1")[0])
        rows = first._exec("SELECT window_start FROM rate_windows WHERE key = ?", ("ip:1",))
        self.assertEqual([r["window_start"] for r in rows], [1200])

    def test_a_store_outage_refuses_the_request(self):
        class Broken:
            def rate_hit(self, *args):
                raise RuntimeError("down")
        with self.assertRaises(RateLimitUnavailable):
            StoreRateLimiter(Broken(), limit=3).check("ip:1")

    def test_the_in_process_limiter_evicts_idle_buckets(self):
        clock = [0.0]
        limiter = RateLimiter(limit=5, window_seconds=10, clock=lambda: clock[0])
        limiter.MAX_IDLE_BUCKETS = 3
        for key in ("a", "b", "c"):
            limiter.check(key)
        clock[0] += 10
        limiter.check("d")
        self.assertEqual(set(limiter._buckets), {"d"})


class ModelBudgetTest(unittest.TestCase):
    """B6: the owner's model calls per day are counted in the store, and
    the gateway makes no attempt once they are spent."""

    def store(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return closing_store(self, open_store(None, Path(tmp.name) / "agentic.db"))

    def test_calls_are_charged_to_the_owner_in_context(self):
        store = self.store()
        budget = quota.ModelBudget(store, {"model_calls_per_day": 2})
        token = tenant.current_owner.set("owner-a")
        try:
            self.assertTrue(budget.allow("anthropic"))
            budget.charge({"provider": "anthropic"})
            self.assertTrue(budget.allow("anthropic"))
            budget.charge({"provider": "anthropic"})
            self.assertFalse(budget.allow("anthropic"))
        finally:
            tenant.current_owner.reset(token)
        # Another owner, and the local owner when none is set, are untouched.
        token = tenant.current_owner.set("owner-b")
        try:
            self.assertTrue(budget.allow("anthropic"))
        finally:
            tenant.current_owner.reset(token)
        self.assertTrue(budget.allow("anthropic"))
        usage = quota.usage(store, "owner-a", {**quota.DEFAULTS, "model_calls_per_day": 2})
        self.assertEqual(usage["model_calls"], {"used": 2, "limit": 2, "remaining": 0})

    def test_the_gateway_makes_no_attempt_over_budget(self):
        store = self.store()
        gateway = ModelGateway(env={"ANTHROPIC_API_KEY": "test-key-not-real"})
        calls = []
        gateway._call_anthropic = lambda *a, **k: calls.append(a) or "model text"
        gateway.budget = quota.ModelBudget(store, {"model_calls_per_day": 0})
        answer = gateway.ask("system", "user", provider="anthropic")
        self.assertIsNone(answer)
        self.assertEqual(calls, [])
        narrated = gateway.narrate("goal", ["fact one"], provider="anthropic")
        self.assertEqual(narrated["source"], "deterministic")

    def test_the_limit_is_read_from_the_environment(self):
        limits = quota.load_limits({"AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "7"})
        self.assertEqual(limits["model_calls_per_day"], 7)
        self.assertEqual(quota.load_limits({})["model_calls_per_day"], 500)


class ApiBudgetWiringTest(unittest.TestCase):
    """B6 at the API: the budget is wired into the gateway, a refusal
    carries the error envelope, and the request sets the tenant."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Slice Three",
                                      "database_file": str(root / "agentic.db"),
                                      "memory_file": str(root / "memory.json"),
                                      "vault_dir": str(root / "vault")}), encoding="utf-8")
        self.env = {"AGENTIC_OS_RATE_LIMIT": "3", "AGENTIC_OS_RATE_LIMIT_STORE": "1"}
        # Keep this wiring test inside one fixed window even across a wall-clock
        # minute boundary. Production clock behavior is tested separately.
        with patch("server.app.StoreRateLimiter", side_effect=lambda *args, **kwargs:
                   StoreRateLimiter(*args, **kwargs, clock=lambda: 1200.0)):
            self.app = create_app(config, env=self.env)
        self.client = TestClient(closing(self, self.app), raise_server_exceptions=False)

    def test_the_gateway_has_the_store_budget(self):
        budget = self.app.state.gateway.budget
        self.assertIsInstance(budget, quota.ModelBudget)
        self.assertIs(budget.store, self.app.state.store)

    def test_the_store_limiter_refuses_with_the_envelope(self):
        for _ in range(3):
            self.assertEqual(self.client.post("/api/runs", json={"goal": "Audit test run"}).status_code, 201)
        response = self.client.post("/api/runs", json={"goal": "Audit test run"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"]["code"], "rate_limited")
        self.assertTrue(response.headers.get("Retry-After"))
        rows = self.app.state.store._exec("SELECT count FROM rate_windows")
        self.assertEqual(sum(r["count"] for r in rows), 4)


@unittest.skipUnless(_postgres_available(), "PostgreSQL test database not reachable")
class PostgresConnectionPerThreadTest(unittest.TestCase):
    """B11: a thread's read never waits behind another thread's transaction."""

    def test_reads_run_while_another_thread_holds_a_transaction(self):
        store = closing_store(self, open_store(database_url=PG_TEST_URL))
        self.assertIsInstance(store, PostgresStore)
        held = threading.Event()
        release = threading.Event()

        def holder():
            with store.atomic("slice-three-hold"):
                held.set()
                release.wait(5)
        thread = threading.Thread(target=holder)
        thread.start()
        self.assertTrue(held.wait(5))
        try:
            started = time.monotonic()
            results = []

            def reader():
                results.append(store.list_runs(limit=1))
            readers = [threading.Thread(target=reader) for _ in range(20)]
            for r in readers:
                r.start()
            for r in readers:
                r.join(10)
            elapsed = time.monotonic() - started
        finally:
            release.set()
            thread.join(5)
        self.assertEqual(len(results), 20)
        self.assertLess(elapsed, 2.0, "the reads queued behind the transaction")
        self.assertGreaterEqual(store.open_connections(), 2)
        store.close()
        self.assertEqual(store.open_connections(), 0)
        # The next statement on this thread opens a fresh connection.
        self.assertIsInstance(store.list_runs(limit=1), list)


if __name__ == "__main__":
    unittest.main()
