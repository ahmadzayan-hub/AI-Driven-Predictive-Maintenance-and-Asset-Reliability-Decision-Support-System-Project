"""R2: risk ranking (31 October 2026).

Each asset's chance of failing within 90 days, from its class's failure
pattern and the days since its last failure, times the class's recorded cost
per failure. Criticality is shown, never weighted. A proposal, not a work order.
"""
import csv
import datetime
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

from server import analytics, stages
from server.maintenance import risk_ranking as K
from server.maintenance.risk_ranking import RiskRanking
from tests.test_reliability_model import AS_OF, context, fleet_rows


def costed(rows, maintenance, loss, criticality):
    out = []
    for row in rows:
        failed = row["Failure_Count"] != "0"
        out.append(dict(row, Criticality=criticality,
                        Maintenance_Cost_USD=str(maintenance if failed else 0),
                        Production_Loss_USD=str(loss if failed else 0)))
    return out


def fleet():
    return (costed(fleet_rows(2.5, "Pumps", seed=11), 1000, 4000, "High")
            + costed(fleet_rows(0.6, "Signals", seed=12), 200, 300, "Medium"))


class ChanceTests(unittest.TestCase):

    def test_the_chance_matches_the_survival_ratio(self):
        shape, scale = 2.0, 200.0
        survive = lambda t: math.exp(-(t / scale) ** shape)  # noqa: E731
        expected = 1 - survive(250) / survive(160)
        self.assertAlmostEqual(K.chance_within(160, 90, shape, scale), expected)

    def test_wear_raises_the_chance_with_age_and_random_does_not(self):
        self.assertGreater(K.chance_within(300, 90, 2.5, 200), K.chance_within(10, 90, 2.5, 200))
        self.assertAlmostEqual(K.chance_within(300, 90, 1.0, 200),
                               K.chance_within(10, 90, 1.0, 200))

    def test_ages_count_from_the_last_failure_or_first_record(self):
        d = datetime.date
        items = [("A", d(2025, 1, 1), 0), ("A", d(2025, 2, 1), 1), ("A", d(2025, 3, 1), 0),
                 ("B", d(2025, 1, 15), 0), ("B", d(2025, 3, 1), 0)]
        self.assertEqual(K.ages(items), {"A": 28, "B": 45})


class StageTests(unittest.TestCase):

    def test_assets_are_ranked_by_expected_cost(self):
        result = RiskRanking().run(context(fleet()))
        stages.validate_result(RiskRanking.role, result)
        out = result["output"]
        self.assertEqual(out["ranked_by"], "expected_cost")
        self.assertEqual(out["assets_ranked"], 80)
        costs = [item["expected_cost"] for item in out["ranked"]]
        self.assertEqual(costs, sorted(costs, reverse=True))
        top = out["ranked"][0]
        self.assertEqual(top["cost_per_failure"], 5000 if top["group"] == "Pumps" else 500)
        # The chance is stored to three decimals; the cost uses the exact chance.
        self.assertAlmostEqual(top["expected_cost"], top["chance"] * top["cost_per_failure"],
                               delta=0.0005 * top["cost_per_failure"] + 1)
        self.assertFalse(out["criticality_weighted"])
        self.assertFalse(out["work_orders_issued"])
        self.assertTrue(out["human_approval_required"])

    def test_without_cost_columns_the_chance_ranks_and_says_so(self):
        rows = [{k: v for k, v in r.items() if not k.endswith("_USD")} for r in fleet()]
        result = RiskRanking().run(context(rows))
        out = result["output"]
        self.assertEqual(out["ranked_by"], "chance")
        chances = [item["chance"] for item in out["ranked"]]
        self.assertEqual(chances, sorted(chances, reverse=True))
        basis = next(c for c in result["claims"] if c["id"].endswith("cl_basis"))
        self.assertIn("no cost columns are recorded", basis["text"])

    def test_claims_cite_their_figures_in_both_languages(self):
        for language in ("en", "ar"):
            with self.subTest(language=language):
                result = RiskRanking().run(context(fleet(), language))
                calcs = {c["id"]: c for c in result["calculations"]}
                self.assertEqual(len([c for c in result["claims"]
                                      if c["type"] == "recommendation"]), K.CLAIMED)
                for claim in result["claims"]:
                    self.assertTrue(all(e in calcs for e in claim["evidence"]), claim["id"])
                    self.assertTrue(analytics.claim_figures_match(claim, calcs), claim["text"])
                    self.assertEqual(analytics._jargon_in(claim["text"]), [])
                    if language == "ar":
                        self.assertEqual(analytics.figures(claim["text"]),
                                         analytics.figures(claim["text_ar"]), claim["id"])

    def test_an_age_beyond_the_data_is_called_an_extrapolation(self):
        result = RiskRanking().run(context(fleet()))
        top = result["output"]["ranked"]
        flagged = [i for i, item in enumerate(top[:K.CLAIMED]) if item["beyond_data"]]
        self.assertTrue(all(item["beyond_data"] == (item["days_running"] > item["longest_seen"])
                            for item in top))
        for i in range(K.CLAIMED):
            claim = next(c for c in result["claims"] if c["id"].endswith(f"cl_rank_{i}"))
            self.assertEqual("extrapolation" in claim["text"], i in flagged)
            self.assertEqual(claim["status"] == "unverified", i in flagged)

    def test_a_thin_class_is_counted_not_ranked(self):
        rows = fleet() + costed(fleet_rows(3.0, "Doors", assets=1, seed=2)[:4], 10, 10, "Low")
        out = RiskRanking().run(context(rows))["output"]
        self.assertEqual(out["assets_not_ranked"], 1)
        self.assertNotIn("Doors", {item["group"] for item in out["ranked"]})

    def test_missing_fields_rank_nothing(self):
        out = RiskRanking().run(context([{"Asset_ID": "A", "Record_Date": "2025-01-01"}]))
        self.assertFalse(out["output"]["applicable"])

    def test_it_is_registered_on_the_maintenance_profile_only(self):
        self.assertIsNone(stages.check_descriptor(RiskRanking(), {}))
        cfg = json.loads((Path(__file__).parents[1] / "config.json").read_text(encoding="utf-8"))
        loaded, issues = stages.load_stages(env={}, config=cfg)
        self.assertEqual(issues, [])
        self.assertIn("risk_ranking", loaded)
        self.assertIn("risk_ranking", cfg["profiles"]["maintenance"])
        self.assertNotIn("risk_ranking", cfg["profiles"]["default"])


class GovernedRunTests(unittest.TestCase):

    def test_a_maintenance_run_reaches_approval_with_the_ranking(self):
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
                    run = engine.create_run("Which assets first", source.getvalue(),
                                            "fleet.csv", profile="maintenance",
                                            language=language)
                    for _ in range(80):
                        run = engine.advance(run["id"])
                        if run["state"] not in ("queued", "running"):
                            break
                    self.assertEqual(run["state"], "awaiting_approval", run.get("error"))
                    task = next(t for t in store.get_tasks(run["id"])
                                if t["role"] == "risk_ranking")
                    output = json.loads(task["result_json"])["output"]
                    self.assertEqual(output["ranked_by"], "expected_cost")
                    self.assertEqual(len(output["ranked"]), K.TOP)
                finally:
                    store.close()


if __name__ == "__main__":
    unittest.main()
