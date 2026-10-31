"""R3: what-if scenarios (31 October 2026).

Planned replacement after T running days against run to failure, per asset
class, with the standard age-replacement model. Only a wear pattern can gain
from it; the lowest-cost interval is named only when it saves cost.
"""
import csv
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

from server import analytics, stages
from server.maintenance import scenarios as S
from server.maintenance.scenarios import WhatIfScenarios
from tests.test_reliability_model import context, fleet_rows


def costed(rows, failure, planned):
    out = []
    for row in rows:
        failed = row["Failure_Count"] != "0"
        out.append(dict(row, Work_Order_Type="Corrective" if failed else "Preventive",
                        Maintenance_Cost_USD=str(failure if failed else planned),
                        Production_Loss_USD="0"))
    return out


def fleet():
    return (costed(fleet_rows(2.5, "Pumps", seed=11), 5000, 500)
            + costed(fleet_rows(0.6, "Signals", seed=12), 800, 100))


class ModelTests(unittest.TestCase):

    def test_a_random_pattern_gains_nothing_from_planned_replacement(self):
        for T in (50, 150, 400):
            self.assertAlmostEqual(S.at_interval(T, 1.0, 200)["failures"],
                                   S.run_to_failure(1.0, 200)["failures"], places=6)

    def test_a_long_interval_tends_to_run_to_failure(self):
        self.assertAlmostEqual(S.at_interval(5000, 2.5, 200, 100, 1000)["cost"],
                               S.run_to_failure(2.5, 200, 1000)["cost"], places=5)

    def test_the_mean_running_time_matches_the_mean_life_at_the_limit(self):
        self.assertAlmostEqual(S.mean_running(3000, 2.0, 100), 100 * math.gamma(1.5), places=5)

    def test_the_best_interval_meets_the_optimality_condition(self):
        # Barlow and Proschan: at the optimum, h(T) L(T) - F(T) = Cp / (Cf - Cp).
        shape, scale, cp, cf = 2.5, 200.0, 100.0, 1000.0
        best = S.best_interval(shape, scale, cp, cf)
        T = best["interval_days"]
        hazard = shape / scale * (T / scale) ** (shape - 1)
        left = hazard * S.mean_running(T, shape, scale) - (1 - S.survival(T, shape, scale))
        self.assertAlmostEqual(left, cp / (cf - cp), delta=0.02)
        self.assertLess(best["cost"], S.run_to_failure(shape, scale, cf)["cost"])

    def test_costly_planned_work_names_no_interval(self):
        self.assertIsNone(S.best_interval(2.5, 200, 900, 1000))

    def test_declared_intervals_are_checked(self):
        self.assertEqual(WhatIfScenarios(intervals_days=[45, 30, 30]).intervals, [30, 45])
        for bad in ([0], [-5], ["30"], [True], list(range(1, 9))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                WhatIfScenarios(intervals_days=bad)


class StageTests(unittest.TestCase):

    def classes(self, result):
        return {c["group"]: c for c in result["output"]["classes"]}

    def test_wear_gets_a_lowest_cost_interval_and_early_life_is_told_no(self):
        result = WhatIfScenarios().run(context(fleet()))
        stages.validate_result(WhatIfScenarios.role, result)
        found = self.classes(result)
        self.assertIsNotNone(found["Pumps"]["best"])
        self.assertEqual((found["Pumps"]["cost_per_failure"], found["Pumps"]["cost_per_planned_job"]),
                         (5000, 500))
        self.assertIsNone(found["Signals"]["best"])
        claims = {c["id"]: c for c in result["claims"]}
        pumps = next(c for c in claims.values() if c["text"].startswith("Pumps"))
        signals = next(c for c in claims.values() if c["text"].startswith("Signals"))
        self.assertEqual(pumps["type"], "recommendation")
        self.assertEqual(signals["type"], "limitation")
        self.assertIn("does not reduce failures", signals["text"])
        self.assertFalse(result["output"]["plan_changed"])

    def test_declared_intervals_are_the_ones_compared(self):
        result = WhatIfScenarios(intervals_days=[30, 45]).run(context(fleet()))
        pumps = self.classes(result)["Pumps"]
        self.assertEqual([o["interval_days"] for o in pumps["options"]], [30, 45])
        self.assertLess(pumps["options"][0]["failures"], pumps["options"][1]["failures"])

    def test_without_costs_failures_are_compared_and_no_interval_is_recommended(self):
        rows = [{k: v for k, v in r.items() if not k.endswith("_USD")} for r in fleet()]
        result = WhatIfScenarios().run(context(rows))
        pumps = self.classes(result)["Pumps"]
        self.assertFalse(pumps["costed"])
        self.assertIsNone(pumps["best"])
        claim = next(c for c in result["claims"] if c["text"].startswith("Pumps"))
        self.assertIn("not both recorded", claim["text"])

    def test_claims_cite_their_figures_in_both_languages(self):
        for rows in (fleet(), [{k: v for k, v in r.items() if not k.endswith("_USD")}
                               for r in fleet()]):
            for language in ("en", "ar"):
                with self.subTest(language=language):
                    result = WhatIfScenarios().run(context(rows, language))
                    calcs = {c["id"]: c for c in result["calculations"]}
                    for claim in result["claims"]:
                        self.assertTrue(all(e in calcs for e in claim["evidence"]), claim["id"])
                        self.assertTrue(analytics.claim_figures_match(claim, calcs),
                                        claim["text"])
                        self.assertEqual(analytics._jargon_in(claim["text"]), [])
                        if language == "ar":
                            self.assertEqual(analytics.figures(claim["text"]),
                                             analytics.figures(claim["text_ar"]), claim["id"])

    def test_missing_fields_compare_nothing(self):
        out = WhatIfScenarios().run(context([{"Asset_ID": "A", "Record_Date": "2025-01-01"}]))
        self.assertFalse(out["output"]["applicable"])

    def test_it_is_registered_on_the_maintenance_profile_only(self):
        self.assertIsNone(stages.check_descriptor(WhatIfScenarios(), {}))
        cfg = json.loads((Path(__file__).parents[1] / "config.json").read_text(encoding="utf-8"))
        loaded, issues = stages.load_stages(env={}, config=cfg)
        self.assertEqual(issues, [])
        self.assertIn("what_if_scenarios", loaded)
        self.assertIn("what_if_scenarios", cfg["profiles"]["maintenance"])
        self.assertNotIn("what_if_scenarios", cfg["profiles"]["default"])


class GovernedRunTests(unittest.TestCase):

    def test_governance_and_risk_claims_cite_their_figures_on_work_order_data(self):
        # Found while wiring R3: on data with work-order types and costs, the
        # governance split finding left its listing uncited (and out of the
        # Arabic text), and an unanswered risk target left its counts uncited.
        from server.maintenance.governance import MaintenanceGovernance
        from server.maintenance.targets import MaintenanceRisk
        from tests.test_maintenance_targets import context as risk_context
        rows = fleet()
        ctx = {"cleaner": {"rows": rows, "date_col": "Record_Date"},
               "collector": {"columns": list(rows[0])}, "profiler": {"numeric_columns": []},
               "report_language": "ar", "dataset_name": "fleet"}
        for result in (MaintenanceGovernance().run(ctx),
                       MaintenanceRisk().run(risk_context(rows, "ar"))):
            calcs = {c["id"]: c for c in result["calculations"]}
            for claim in result["claims"]:
                self.assertTrue(analytics.claim_figures_match(claim, calcs), claim["text"])
                self.assertEqual(analytics.figures(claim["text"]),
                                 analytics.figures(claim["text_ar"]), claim["id"])

    def test_a_maintenance_run_reaches_approval_with_the_scenarios(self):
        from server.model_gateway import ModelGateway
        from server.runs import RunEngine
        from server.storage import open_store
        cfg = json.loads((Path(__file__).parents[1] / "config.json").read_text(encoding="utf-8"))
        registry, problems = stages.load_stages(env={}, config=cfg)
        self.assertEqual(problems, [])
        rows = fleet()
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
                    run = engine.create_run("What if we service on a schedule",
                                            source.getvalue(), "fleet.csv",
                                            profile="maintenance", language=language)
                    for _ in range(80):
                        run = engine.advance(run["id"])
                        if run["state"] not in ("queued", "running"):
                            break
                    self.assertEqual(run["state"], "awaiting_approval", run.get("error"))
                    task = next(t for t in store.get_tasks(run["id"])
                                if t["role"] == "what_if_scenarios")
                    output = json.loads(task["result_json"])["output"]
                    self.assertTrue(output["applicable"])
                finally:
                    store.close()


if __name__ == "__main__":
    unittest.main()
