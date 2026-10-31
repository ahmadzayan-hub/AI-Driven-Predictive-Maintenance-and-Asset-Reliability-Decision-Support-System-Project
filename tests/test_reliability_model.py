"""R1: the reliability model (31 October 2026).

Days between failures per asset, with assets still running counted as
censored, fitted to a Weibull pattern per asset class. The pattern is named
only when its whole likely range agrees; otherwise the claim stays weak.
"""
import datetime
import json
import random
import unittest
from pathlib import Path

from server import analytics, stages
from server.maintenance import reliability as R
from server.maintenance.reliability import ReliabilityModel

START = datetime.date(2022, 1, 1)
AS_OF = datetime.date(2025, 12, 31)


def censored_sample(shape, scale, n, seed):
    rng = random.Random(seed)
    failed, running = [], []
    for _ in range(n):
        life, cut = rng.weibullvariate(scale, shape), rng.uniform(100, 900)
        (failed if life <= cut else running).append(life if life <= cut else cut)
    return failed, running


def fleet_rows(shape, asset_class, assets=40, seed=1):
    """Maintenance records: each asset fails at Weibull-spaced days until AS_OF."""
    rng = random.Random(seed)
    rows = []
    for a in range(assets):
        unit, day = f"{asset_class[:3]}-{a}", START
        rows.append({"Asset_ID": unit, "Asset_Class": asset_class,
                     "Record_Date": day.isoformat(), "Failure_Count": "0"})
        while True:
            day += datetime.timedelta(days=max(1, round(rng.weibullvariate(200, shape))))
            if day > AS_OF:
                break
            rows.append({"Asset_ID": unit, "Asset_Class": asset_class,
                         "Record_Date": day.isoformat(), "Failure_Count": "1"})
        rows.append({"Asset_ID": unit, "Asset_Class": asset_class,
                     "Record_Date": AS_OF.isoformat(), "Failure_Count": "0"})
    return rows


def context(rows, language="en"):
    return {"cleaner": {"rows": rows}, "collector": {"columns": list(rows[0]) if rows else []},
            "report_language": language}


class FitTests(unittest.TestCase):

    def test_known_patterns_are_recovered_with_censoring(self):
        for shape, expected in ((0.7, "early"), (1.0, "random"), (2.5, "wear")):
            with self.subTest(shape=shape):
                failed, running = censored_sample(shape, 300, 1000, seed=7)
                self.assertGreater(len(running), 50)
                result = R.fit(failed, running)
                self.assertLess(abs(result["shape"] - shape) / shape, 0.1)
                self.assertLess(abs(result["scale"] - 300) / 300, 0.1)
                self.assertLessEqual(result["shape_low"], result["shape"])
                self.assertLessEqual(result["shape"], result["shape_high"])
                self.assertEqual(R.pattern(result), expected)

    def test_ignoring_running_assets_would_understate_life(self):
        failed, running = censored_sample(2.0, 300, 400, seed=3)
        with_running = R.fit(failed, running)["scale"]
        failures_only = R.fit(failed, [])["scale"]
        self.assertLess(failures_only, with_running * 0.9)

    def test_b10_and_mean_follow_the_fitted_shape_and_scale(self):
        result = R.fit(*censored_sample(1.8, 250, 300, seed=5))
        k, eta = result["shape"], result["scale"]
        self.assertAlmostEqual(1 - __import__("math").exp(-(result["b10"] / eta) ** k), 0.1)
        self.assertAlmostEqual(result["mean_life"],
                               eta * __import__("math").gamma(1 + 1 / k))

    def test_no_spread_or_too_few_failures_gives_no_fit(self):
        self.assertIsNone(R.fit([5], [10]))
        self.assertIsNone(R.fit([100] * 12, []))

    def test_intervals_restart_at_each_failure_and_censor_the_tail(self):
        d = datetime.date
        records = [("A", d(2025, 1, 1), 0), ("A", d(2025, 1, 11), 1),
                   ("A", d(2025, 1, 31), 2), ("A", d(2025, 1, 31), 1),
                   ("B", d(2025, 1, 1), 1), ("B", d(2025, 3, 1), 0)]
        failed, running, notes = R.intervals(records)
        self.assertEqual(sorted(failed), [10, 20])
        self.assertEqual(sorted(running), [29, 59])
        self.assertEqual(notes["no_interval"], 2)  # same day; first seen at a failure
        self.assertEqual(notes["several_on_one_record"], 1)
        self.assertEqual(notes["as_of"], "2025-03-01")


class StageTests(unittest.TestCase):

    def rows(self):
        return fleet_rows(2.5, "Pumps", seed=11) + fleet_rows(0.6, "Signals", seed=12)

    def test_each_class_gets_its_own_pattern(self):
        result = ReliabilityModel().run(context(self.rows()))
        stages.validate_result(ReliabilityModel.role, result)
        found = {g["group"]: g["pattern"] for g in result["output"]["groups"]}
        self.assertEqual(found, {"Pumps": "wear", "Signals": "early"})
        self.assertFalse(result["output"]["remaining_useful_life_estimated"])
        self.assertTrue(result["output"]["human_approval_required"])

    def test_claims_cite_their_figures_and_avoid_jargon_in_both_languages(self):
        for language in ("en", "ar"):
            with self.subTest(language=language):
                result = ReliabilityModel().run(context(self.rows(), language))
                calcs = {c["id"]: c for c in result["calculations"]}
                for claim in result["claims"]:
                    self.assertTrue(all(e in calcs for e in claim["evidence"]), claim["id"])
                    self.assertTrue(analytics.claim_figures_match(claim, calcs), claim["text"])
                    self.assertEqual(analytics._jargon_in(claim["text"]), [], claim["text"])
                    if language == "ar":
                        self.assertEqual(analytics.figures(claim["text"]),
                                         analytics.figures(claim["text_ar"]), claim["id"])
                        self.assertEqual(analytics._jargon_in(claim["text_ar"]), [])

    def test_a_random_pattern_is_left_unverified(self):
        rows = fleet_rows(1.0, "Relays", assets=15, seed=4)
        result = ReliabilityModel().run(context(rows))
        group = result["output"]["groups"][0]
        claim = next(c for c in result["claims"] if c["id"].endswith("cl_pattern_0"))
        self.assertEqual(group["pattern"], "random")
        self.assertEqual(claim["status"], "unverified")

    def test_a_class_with_too_few_failures_is_named_not_fitted(self):
        rows = self.rows() + fleet_rows(3.0, "Doors", assets=1, seed=2)[:4]
        result = ReliabilityModel().run(context(rows))
        self.assertEqual(result["output"]["not_fitted"], ["Doors"])
        self.assertIn("reliability_model.cl_too_few", {c["id"] for c in result["claims"]})

    def test_missing_fields_or_month_dates_make_no_claim(self):
        rows = [{"Asset_ID": "A", "Record_Date": "2025-01-01"}]
        self.assertFalse(ReliabilityModel().run(context(rows))["output"]["applicable"])
        monthly = [dict(r, Record_Date=r["Record_Date"][:7]) for r in self.rows()]
        result = ReliabilityModel().run(context(monthly))
        self.assertFalse(result["output"]["applicable"])
        self.assertEqual(result["claims"], [])

    def test_it_is_registered_on_the_maintenance_profile_only(self):
        self.assertIsNone(stages.check_descriptor(ReliabilityModel(), {}))
        cfg = json.loads((Path(__file__).parents[1] / "config.json").read_text(encoding="utf-8"))
        loaded, issues = stages.load_stages(env={}, config=cfg)
        self.assertEqual(issues, [])
        self.assertIn("reliability_model", loaded)
        self.assertIn("reliability_model", cfg["profiles"]["maintenance"])
        self.assertNotIn("reliability_model", cfg["profiles"]["default"])


class GovernedRunTests(unittest.TestCase):

    def test_the_uneven_periods_finding_cites_every_figure_in_both_languages(self):
        # Found while wiring R1: the listing of each period's count was not
        # cited, and the Arabic text dropped the figures.
        from server.maintenance.governance import MaintenanceGovernance
        rows = fleet_rows(2.5, "Pumps", seed=11)
        ctx = {"cleaner": {"rows": rows, "date_col": "Record_Date"},
               "collector": {"columns": list(rows[0])}, "profiler": {"numeric_columns": []},
               "report_language": "ar", "dataset_name": "fleet"}
        result = MaintenanceGovernance().run(ctx)
        calcs = {c["id"]: c for c in result["calculations"]}
        uneven = [c for c in result["claims"] if "Periods in" in c["text"]]
        self.assertEqual(len(uneven), 1)
        self.assertTrue(analytics.claim_figures_match(uneven[0], calcs))
        self.assertEqual(analytics.figures(uneven[0]["text"]),
                         analytics.figures(uneven[0]["text_ar"]))

    def test_a_maintenance_run_reaches_approval_with_the_pattern_in_both_languages(self):
        import csv, io, tempfile
        from server.model_gateway import ModelGateway
        from server.runs import RunEngine
        from server.storage import open_store
        cfg = json.loads((Path(__file__).parents[1] / "config.json").read_text(encoding="utf-8"))
        registry, problems = stages.load_stages(env={}, config=cfg)
        self.assertEqual(problems, [])
        rows = fleet_rows(2.5, "Pumps", seed=11) + fleet_rows(0.6, "Signals", seed=12)
        source = io.StringIO(newline="")
        writer = csv.DictWriter(source, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        for language in ("en", "ar"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                store = open_store(sqlite_path=str(Path(directory) / "runs.db"))
                try:
                    engine = RunEngine(store, Path(directory) / "vault", ModelGateway(env={}),
                                       stages=registry, profiles=cfg["profiles"])
                    run = engine.create_run("Failure pattern by class", source.getvalue(),
                                            "fleet.csv", profile="maintenance",
                                            language=language)
                    for _ in range(80):
                        run = engine.advance(run["id"])
                        if run["state"] not in ("queued", "running"):
                            break
                    self.assertEqual(run["state"], "awaiting_approval", run.get("error"))
                    validator = next(t for t in run["tasks"] if t["role"] == "validator")
                    failed = [c for c in validator["quality_checks"] if not c["passed"]]
                    self.assertEqual(failed, [])
                    task = next(t for t in store.get_tasks(run["id"])
                                if t["role"] == "reliability_model")
                    output = json.loads(task["result_json"])["output"]
                    self.assertEqual({g["group"]: g["pattern"] for g in output["groups"]},
                                     {"Pumps": "wear", "Signals": "early"})
                finally:
                    store.close()


if __name__ == "__main__":
    unittest.main()
