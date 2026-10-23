"""The first P2 slice of the release gate (assessment A9, A10, A12, B8,
B14, G10): verdict bounds, declared splits, incomplete periods, loopback
by default, idempotent run creation and wall-clock limits."""

import json
import os
import random
import tempfile
import threading
import time
import unittest
from pathlib import Path

from server import analytics, deadline, modelling
from server.maintenance.targets import MaintenanceRisk
from server.model_gateway import ModelGateway
from server.runs import RunEngine
from server.storage import open_store
from tests.support import closing_store
from tests.test_maintenance_targets import context, rows_for


def noise_rows(seed, n=1200):
    """Records whose label is independent of every column."""
    coin = random.Random(seed)
    rows = rows_for(n=n, signal=True)
    for row in rows:
        row["Failure_Count"] = 2.0 if coin.random() < 0.5 else 1.0
    return rows


class VerdictBoundTest(unittest.TestCase):
    """A9: the lower confidence bound must clear chance, so noise is never
    called useful, whichever seed drew it."""

    def test_the_card_carries_the_bound_and_the_held_out_counts(self):
        result = MaintenanceRisk().run(context(rows_for()))
        card = next(c for c in result["output"]["models"] if c.get("fitted", True)
                    and c["details"]["verdict"] == "useful")
        details = card["details"]
        self.assertLess(details["balanced_accuracy_lower_bound"], card["metric"]["model"])
        self.assertGreater(details["balanced_accuracy_lower_bound"], 0.5)
        self.assertEqual(details["held_out_records"], card["test_records"])
        self.assertGreater(details["held_out_positives"], 0)
        claim = next(c for c in result["claims"] if c["id"].endswith("cl_repeat_failure"))
        self.assertIn("maintenance_risk.c_repeat_failure_lower_bound", claim["evidence"])

    def test_noise_is_never_useful_across_seeds(self):
        for seed in range(1, 13):
            with self.subTest(seed=seed):
                result = MaintenanceRisk().run(context(noise_rows(seed)))
                for card in result["output"]["models"]:
                    self.assertNotEqual(card["details"]["verdict"], "useful")

    def test_the_wilson_bound_is_below_the_point_estimate_and_narrows_with_n(self):
        from server.maintenance.targets import _wilson_lower
        self.assertLess(_wilson_lower(30, 50), 0.6)
        self.assertLess(_wilson_lower(30, 50), _wilson_lower(300, 500))
        self.assertEqual(_wilson_lower(0, 0), 0.0)


class DeclaredSplitTest(unittest.TestCase):
    """A10: the split is never silently random."""

    def test_too_few_periods_name_the_reason_on_the_split(self):
        rows = [{"d": f"2025-0{1 + i % 3}", "x": float(i)} for i in range(40)]
        _, _, split = modelling._split(rows, "d")
        self.assertEqual(split["kind"], "every_fifth")
        self.assertIn("3 period", split["reason"])
        self.assertIn("period", modelling._split_text({"report_language": "en"}, split))

    def test_no_date_names_the_reason_on_the_split(self):
        _, _, split = modelling._split([{"x": 1.0}] * 20, None)
        self.assertEqual(split["reason"], "no date column")

    def test_a_maintenance_model_with_a_date_but_three_periods_is_not_scored(self):
        rows = rows_for()
        for i, row in enumerate(rows):
            row["Record_Date"] = f"2025-0{1 + i % 3}-01"
        result = MaintenanceRisk().run(context(rows))
        for card in result["output"]["models"]:
            self.assertEqual(card["details"]["verdict"], "not_supported")
            self.assertIn("chronological", card["details"]["reason"])
            self.assertNotIn("metric", card)


class IncompletePeriodTest(unittest.TestCase):
    """A12: a partial last period is left out of the trend, and said."""

    @staticmethod
    def dataset(last_period_records):
        lines = ["month,team,sales"]
        for index in range(8):
            month = f"2025-{index + 1:02d}"
            records = last_period_records if index == 7 else 4
            for r in range(records):
                lines.append(f"{month},T{r},{100 + 10 * index}")
        return "\n".join(lines) + "\n"

    def run_pipeline(self, text):
        ctx = {"goal": "Analyze the data", "dataset_name": "t.csv", "dataset_text": text,
               "run_id": "test-run", "glossary": None, "report_language": "en", "mapping": None}
        results = {}
        for role, stage in analytics.PIPELINE:
            result = stage(ctx, gateway=None) if role in analytics.NARRATED_STAGES else stage(ctx)
            results[role] = result
            self.assertNotEqual(result["status"], "failed", role)
            ctx[role] = result["output"]
            ctx[role + "_result"] = result
        return ctx, results

    def test_a_half_filled_last_month_is_left_out_of_forecast_and_anomaly(self):
        ctx, results = self.run_pipeline(self.dataset(2))
        forecast_claims = {c["id"]: c for c in results["predictive"]["claims"]}
        self.assertIn("cl_forecast_incomplete", forecast_claims)
        self.assertEqual(forecast_claims["cl_forecast_incomplete"]["type"], "limitation")
        self.assertIn("2025-08", forecast_claims["cl_forecast_incomplete"]["text"])
        # The forecast starts at the incomplete period, read from the seven
        # complete ones, and does not read the half month as a fall.
        first = next(c for c in results["predictive"]["calculations"] if c["id"] == "c_forecast_0")
        self.assertEqual(first["name"], "forecast_2025-08")
        self.assertGreater(first["value"], 4 * 160)
        anomaly_claims = {c["id"] for c in results["anomaly"]["claims"]}
        self.assertIn("cl_anom_incomplete", anomaly_claims)
        self.assertNotIn("cl_anom", anomaly_claims)

    def test_a_full_last_month_changes_nothing(self):
        ctx, results = self.run_pipeline(self.dataset(4))
        self.assertNotIn("cl_forecast_incomplete", {c["id"] for c in results["predictive"]["claims"]})
        self.assertNotIn("cl_anom_incomplete", {c["id"] for c in results["anomaly"]["claims"]})


class DeadlineTest(unittest.TestCase):
    """G10: a hung call is abandoned on its thread, not waited for."""

    def test_a_slow_call_raises_timeout_and_a_quick_one_returns(self):
        self.assertEqual(deadline.call_with_deadline(lambda x: x + 1, 1.0, 1), 2)
        started = time.monotonic()
        with self.assertRaises(deadline.Timeout):
            deadline.call_with_deadline(time.sleep, 0.1, 2.0)
        self.assertLess(time.monotonic() - started, 1.5)

    def test_the_callee_s_own_error_propagates(self):
        def boom():
            raise ValueError("boom")
        with self.assertRaises(ValueError):
            deadline.call_with_deadline(boom, 1.0)

    def test_seconds_from_env_falls_back_on_nonsense(self):
        for raw, expected in (("", 5.0), ("abc", 5.0), ("-1", 5.0), ("0", 5.0), ("2.5", 2.5)):
            os.environ["AGENTIC_OS_TEST_DEADLINE"] = raw
            self.assertEqual(deadline.seconds_from_env("AGENTIC_OS_TEST_DEADLINE", 5), expected)
        del os.environ["AGENTIC_OS_TEST_DEADLINE"]


class SleepingStage:
    role = "sleeper"
    title = "Sleeper"
    after = "sensitivity"
    can_fail_run = False
    question = None

    def run(self, ctx):
        time.sleep(3.0)
        return {"status": "succeeded", "summary": "late", "claims": [], "calculations": [],
                "quality_checks": [], "output": {}}


class StageTimeoutTest(unittest.TestCase):
    def test_a_hung_custom_stage_fails_its_task_and_the_run_goes_on(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = open_store(None, Path(tmp.name) / "agentic.db")
        closing_store(self, store)
        engine = RunEngine(store, Path(tmp.name) / "vault", ModelGateway(env={}),
                           stages={"sleeper": SleepingStage()}, profiles={"default": ["sleeper"]},
                           stage_timeout=0.2)
        run = engine.create_run("Analyze the sample sales dataset", profile="default")
        started = time.monotonic()
        for _ in range(40):
            run = engine.advance(run["id"])
            if run["state"] in ("awaiting_approval", "completed", "failed", "partially_completed"):
                break
        self.assertLess(time.monotonic() - started, 30)
        task = next(t for t in run["tasks"] if t["role"] == "sleeper")
        self.assertEqual(task["state"], "failed")
        self.assertIn("timed out after 0.2 s", task["summary"])
        self.assertNotEqual(run["state"], "failed", "the stage did not declare can_fail_run")


class IdempotentRunCreationTest(unittest.TestCase):
    """B14: the same key creates one run."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = open_store(None, Path(tmp.name) / "agentic.db")
        closing_store(self, store)
        self.engine = RunEngine(store, Path(tmp.name) / "vault", ModelGateway(env={}))

    def test_a_repeated_key_returns_the_first_run(self):
        first = self.engine.create_run("Analyze the sample sales dataset", idempotency_key="k-1")
        again = self.engine.create_run("Analyze the sample sales dataset", idempotency_key="k-1")
        self.assertEqual(again["id"], first["id"])
        self.assertTrue(again["idempotent_replay"])
        self.assertNotIn("idempotent_replay", first)
        self.assertEqual(len(self.engine.list_runs()), 1)

    def test_keys_are_per_owner_and_runs_without_a_key_are_never_matched(self):
        a = self.engine.create_run("Analyze the sample sales dataset", owner="a", idempotency_key="k")
        b = self.engine.create_run("Analyze the sample sales dataset", owner="b", idempotency_key="k")
        self.assertNotEqual(a["id"], b["id"])
        c = self.engine.create_run("Analyze the sample sales dataset", owner="a")
        d = self.engine.create_run("Analyze the sample sales dataset", owner="a")
        self.assertNotEqual(c["id"], d["id"])

    def test_a_bad_key_is_refused_before_anything_is_written(self):
        with self.assertRaises(ValueError):
            self.engine.create_run("Analyze the sample sales dataset", idempotency_key="x" * 201)
        with self.assertRaises(ValueError):
            self.engine.create_run("Analyze the sample sales dataset", idempotency_key="   ")
        self.assertEqual(len(self.engine.list_runs()), 0)


if __name__ == "__main__":
    unittest.main()
