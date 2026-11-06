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


class DeclaredOptionTests(unittest.TestCase):
    """R6: the owner declares the horizon and the criticality weights."""

    def test_a_declared_horizon_is_used_and_cited(self):
        result = RiskRanking(horizon_days=30).run(context(fleet()))
        out = result["output"]
        self.assertEqual(out["horizon_days"], 30)
        calcs = {c["id"]: c for c in result["calculations"]}
        self.assertEqual(calcs["risk_ranking.c_horizon"]["value"], 30)
        self.assertIn("declared", calcs["risk_ranking.c_horizon"]["method"])
        longer = RiskRanking().run(context(fleet()))["output"]["ranked"]
        shorter = {item["asset"]: item["chance"] for item in out["ranked"]}
        for item in longer:
            if item["asset"] in shorter:
                self.assertLessEqual(shorter[item["asset"]], item["chance"])
        self.assertIn("within 30 days", result["claims"][0]["text"])

    def test_options_are_validated(self):
        for bad in ({"horizon_days": 0}, {"horizon_days": 30.5}, {"horizon_days": True},
                    {"horizon_days": 4000}, {"criticality_weights": {"High": 0}},
                    {"criticality_weights": {"High": -1}}, {"criticality_weights": {"": 2}},
                    {"criticality_weights": {"High": 2, "high": 3}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                RiskRanking(**bad)

    def test_complete_weights_reorder_and_are_stated(self):
        weights = {"High": 1, "medium": 50}
        result = RiskRanking(criticality_weights=weights).run(context(fleet()))
        out = result["output"]
        self.assertTrue(out["criticality_weighted"])
        scores = [item["score"] for item in out["ranked"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for item in out["ranked"]:
            expected = 50 if item["criticality"] == "Medium" else 1
            self.assertEqual(item["weight"], expected)
            self.assertAlmostEqual(item["score"], item["expected_cost"] * expected)
        basis = next(c for c in result["claims"] if c["id"].endswith("cl_basis"))
        self.assertIn("medium x50", basis["text"])
        self.assertIn("risk_ranking.c_weights", basis["evidence"])

    def test_incomplete_weights_are_not_applied_and_the_gap_is_named(self):
        result = RiskRanking(criticality_weights={"High": 3}).run(context(fleet()))
        out = result["output"]
        self.assertFalse(out["criticality_weighted"])
        self.assertEqual(out["weights_not_applied"]["missing_labels"], ["Medium"])
        unweighted = RiskRanking().run(context(fleet()))["output"]["ranked"]
        self.assertEqual([i["asset"] for i in out["ranked"]], [i["asset"] for i in unweighted])
        basis = next(c for c in result["claims"] if c["id"].endswith("cl_basis"))
        self.assertIn("no weight is declared for Medium", basis["text"])

    def test_declared_options_keep_claims_valid_in_both_languages(self):
        for options in ({"horizon_days": 180}, {"criticality_weights": {"High": 2.5, "Medium": 1}},
                        {"criticality_weights": {"High": 4}}):
            for language in ("en", "ar"):
                with self.subTest(options=options, language=language):
                    result = RiskRanking(**options).run(context(fleet(), language))
                    stages.validate_result(RiskRanking.role, result)
                    calcs = {c["id"]: c for c in result["calculations"]}
                    for claim in result["claims"]:
                        self.assertTrue(all(e in calcs for e in claim["evidence"]), claim["id"])
                        self.assertTrue(analytics.claim_figures_match(claim, calcs), claim["text"])
                        self.assertEqual(analytics._jargon_in(claim["text"]), [])
                        if language == "ar":
                            self.assertEqual(analytics.figures(claim["text"]),
                                             analytics.figures(claim["text_ar"]), claim["id"])

    def test_options_load_from_config(self):
        cfg = {"stages": [{"path": "server.maintenance.risk_ranking.RiskRanking",
                           "options": {"horizon_days": 60,
                                       "criticality_weights": {"High": 3, "Medium": 1}}}]}
        loaded, issues = stages.load_stages(env={}, config=cfg)
        self.assertEqual(issues, [])
        self.assertEqual(loaded["risk_ranking"].horizon, 60)
        self.assertEqual(loaded["risk_ranking"].weights, {"High": 3.0, "Medium": 1.0})


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


class BacktestTests(unittest.TestCase):
    """Phase 4 review, 6 November 2026: do the chances come true after a cutoff?"""

    def records(self, rows):
        out = {}
        for row in rows:
            out.setdefault(row["Asset_Class"], []).append(
                (row["Asset_ID"], datetime.date.fromisoformat(row["Record_Date"]),
                 int(row["Failure_Count"])))
        return out

    def test_wear_out_chances_beat_a_constant_rate_and_say_so(self):
        result = RiskRanking().run(context(fleet()))
        stages.validate_result(RiskRanking.role, result)
        checked = result["output"]["backtest"]
        self.assertTrue(checked["applicable"])
        self.assertEqual(checked["cutoff"], "2025-10-02")
        self.assertTrue(checked["better_than_baseline"])
        self.assertGreater(checked["top_hits"], checked["top_hits_at_base_rate"])
        self.assertEqual(sum(b["assets"] for b in checked["calibration"]), checked["assets_scored"])
        claim = next(c for c in result["claims"] if c["id"] == "risk_ranking.cl_backtest")
        self.assertIn("not a prospective validation", claim["text"])
        self.assertIn(f"{checked['brier']:.3f}", claim["text"])

    def test_records_after_the_cutoff_never_change_the_chances(self):
        rows = fleet()
        before = K.backtest(self.records(rows), 90)
        cutoff = datetime.date.fromisoformat(before["cutoff"])
        # Every record after the cutoff becomes a failure: the outcomes change,
        # the fitted chances (and so their sum) must not.
        changed = [dict(r, Failure_Count="1")
                   if datetime.date.fromisoformat(r["Record_Date"]) > cutoff else r for r in rows]
        after = K.backtest(self.records(changed), 90)
        self.assertEqual(before["expected_failures"], after["expected_failures"])
        self.assertGreater(after["failures"], before["failures"])

    def test_an_asset_not_seen_to_the_end_is_left_out_not_counted_as_surviving(self):
        rows = fleet()
        cutoff = datetime.date(2025, 10, 2)
        gone = "Pum-0"
        trimmed = [r for r in rows if not (r["Asset_ID"] == gone
                   and datetime.date.fromisoformat(r["Record_Date"]) > cutoff)]
        checked = K.backtest(self.records(trimmed), 90)
        self.assertEqual(checked["assets_unobserved"], 1)
        self.assertEqual(checked["assets_scored"], 79)

    def test_a_history_shorter_than_the_horizon_is_not_backtested(self):
        result = RiskRanking(horizon_days=3000).run(context(fleet()))
        stages.validate_result(RiskRanking.role, result)
        self.assertFalse(result["output"]["backtest"]["applicable"])
        claim = next(c for c in result["claims"] if c["id"] == "risk_ranking.cl_backtest")
        self.assertEqual(claim["type"], "limitation")
        self.assertIn("not backtested", claim["text"])

    def test_the_arabic_report_carries_the_backtest(self):
        result = RiskRanking().run(context(fleet(), language="ar"))
        claim = next(c for c in result["claims"] if c["id"] == "risk_ranking.cl_backtest")
        self.assertIn("لا تحقق مستقبلي", claim["text_ar"])


class HoldoutTests(unittest.TestCase):
    """Asset and site holdout (6 November 2026 review, Phase 4)."""

    records = BacktestTests.records

    def test_a_fold_s_own_records_never_reach_its_fit(self):
        from unittest.mock import patch
        records = self.records(fleet())
        assets = sorted({a for items in records.values() for a, _, _ in items})
        _, folds = K.asset_folds(assets)
        seen = []
        real = K.R.intervals

        def spy(items):
            seen.append({a for a, _, _ in items})
            return real(items)

        cutoff, as_of = datetime.date(2025, 10, 2), datetime.date(2025, 12, 31)
        with patch.object(K.R, "intervals", side_effect=spy):
            scored, _, _ = K._score(records, 90, cutoff, as_of,
                                    fitted_on=lambda a: folds[a] != 0,
                                    scored_on=lambda a: folds[a] == 0)
        held = {a for a in assets if folds[a] == 0}
        self.assertTrue(held and seen)
        for fitted in seen:
            self.assertFalse(fitted & held)
        self.assertEqual({a for *_, a in scored}, held)

    def test_sites_are_the_folds_when_every_asset_has_one(self):
        rows = [dict(r, Site=("North" if int(r["Asset_ID"].split("-")[1]) % 2 else "South"))
                for r in fleet()]
        result = RiskRanking().run(context(rows))
        stages.validate_result(RiskRanking.role, result)
        held = result["output"]["backtest"]["holdout"]
        self.assertEqual(held["by"], "site")
        self.assertEqual(held["folds"], 2)
        self.assertTrue(held["applicable"])
        claim = next(c for c in result["claims"] if c["id"] == "risk_ranking.cl_backtest")
        self.assertIn("never saw the site", claim["text"])
        self.assertIn("risk_ranking.c_bt_holdout", claim["evidence"])

    def test_without_sites_five_asset_folds_are_used(self):
        held = RiskRanking().run(context(fleet()))["output"]["backtest"]["holdout"]
        self.assertEqual((held["by"], held["folds"]), ("asset", 5))
        self.assertEqual(held["assets_scored"], 80)

    def test_one_site_falls_back_to_asset_folds(self):
        by, folds = K.asset_folds(["A", "B", "C"], {"A": "X", "B": "X", "C": "X"})
        self.assertEqual(by, "asset")
        self.assertTrue(set(folds.values()) <= set(range(5)))
        self.assertEqual(K.asset_folds(["A", "B"], {"A": "X", "B": "Y"})[0], "site")

    def test_a_single_fold_is_not_a_holdout(self):
        self.assertFalse(K.holdout(self.records(fleet()), 90,
                                   {r["Asset_ID"]: 0 for r in fleet()})["applicable"])

    def test_the_arabic_claim_names_the_holdout(self):
        result = RiskRanking().run(context(fleet(), language="ar"))
        claim = next(c for c in result["claims"] if c["id"] == "risk_ranking.cl_backtest")
        self.assertIn("لم يرَ سجلاته", claim["text_ar"])
