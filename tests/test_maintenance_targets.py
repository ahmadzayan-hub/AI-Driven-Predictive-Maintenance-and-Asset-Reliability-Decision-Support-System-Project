"""Validated maintenance risk models (milestone S3).

Synthetic fixtures. The tests that earn their place are the ones that
assert a *refusal*: that a model near chance is not called useful however
large its relative margin, that a date is never used as a baseline
grouping rule, that a column defining the label is disclosed when it is
also an input, and that an unfittable target reports no score at all.

Each of those three defects was present in the first working version and
was found by running the stage on a real panel rather than on fixtures.
They are pinned here so they cannot come back.
"""

import csv
import io
import json
import random
import tempfile
import unittest
from pathlib import Path

from server import analytics, stages
from server.maintenance import targets as T
from server.maintenance.targets import MaintenanceRisk
from server.model_gateway import ModelGateway
from server.runs import RunEngine
from server.storage import open_store


def rows_for(n=400, signal=True):
    """Corrective records with an SLA target and an optional real signal.

    When `signal` is false the label comes from a seeded generator that
    is independent of every column, so nothing knowable predicts it and
    an honest evaluation must return a weak verdict. An earlier version
    derived it from the row index, which `Site = i % 4` encoded exactly -
    the fixture had the signal it claimed to withhold, and the test that
    depended on it passed without ever exercising its branch.
    """
    coin = random.Random(7)
    out = []
    for i in range(n):
        age = float(i % 20)
        critical = "Critical" if i % 3 == 0 else "Low"
        # With signal: old and critical assets repeat-fail.
        failures = 2.0 if (signal and age > 10 and critical == "Critical") else 1.0
        if not signal:
            failures = 2.0 if coin.random() < 0.5 else 1.0
        out.append({
            "Record_ID": f"R{i}",
            "Record_Date": f"202{4 + i // 200}-{(i % 12) + 1:02d}-01",
            "Work_Order_Type": "Corrective",
            "Criticality": critical,
            "Site": f"Site-{i % 4}",
            "Asset_Age_Years": age,
            "Planned_Operating_Hours": 100.0 + (i % 7),
            "SLA_Target_Hours": 4.0 if critical == "Critical" else 24.0,
            "SLA_Actual_Hours": 8.0 if i % 3 == 0 else 2.0,
            "Failure_Count": failures,
            "Downtime_Hours": 10.0 + i % 5,
        })
    return out


def context(rows=None, language="en"):
    rows = rows_for() if rows is None else rows
    columns = list(rows[0]) if rows else []
    numeric = [c for c in columns
               if any(isinstance(row.get(c), float) for row in rows)]
    return {"cleaner": {"rows": rows, "date_col": "Record_Date"},
            "collector": {"columns": columns},
            "profiler": {"numeric_columns": numeric},
            "preparer": {"date_col": "Record_Date"},
            "governance": {"measure": "Downtime_Hours"},
            "report_language": language, "dataset_name": "fixture"}


def incomplete_input_rows():
    """The grouping rule is perfect on scored rows, wrong on omitted rows."""
    rows = []
    for i in range(1000):
        high = (i // 5) % 2 == 0
        incomplete = i % 5 == 0 and i >= 500
        positive = not high if incomplete else high
        rows.append({
            "Record_ID": f"R{i}",
            "Asset_Age_Years": None if incomplete else (10.0 if high else 20.0),
            "Criticality": "High" if high else "Low",
            "Work_Order_Type": "Corrective",
            "Failure_Count": 2.0 if positive else 1.0,
        })
    return rows


def near_chance_rows():
    """A real fitted score clears the relative margin but fails the floor."""
    rng = random.Random(0)
    rows = []
    for i in range(2000):
        positive = bool(rng.randrange(2))
        rows.append({
            "Record_ID": f"R{i}",
            "Asset_Age_Years": rng.gauss(10 + 0.15 * positive, 1),
            "Work_Order_Type": "Corrective",
            "Failure_Count": 2.0 if positive else 1.0,
        })
    return rows


def clear_signal_rows():
    return [{"Record_ID": f"R{i}", "Asset_Age_Years": 10.0 if i % 2 else 20.0,
             "Work_Order_Type": "Corrective", "Failure_Count": 2.0 if i % 2 else 1.0}
            for i in range(400)]


class ContractComplianceTest(unittest.TestCase):

    def test_the_descriptor_is_a_valid_stage(self):
        self.assertIsNone(stages.check_descriptor(MaintenanceRisk(), {}))

    def test_the_result_passes_the_stage_contract(self):
        result = MaintenanceRisk().run(context())
        clean = stages.validate_result(MaintenanceRisk.role, result)
        self.assertEqual(clean["status"], "succeeded")

    def test_every_claim_cites_calculations_that_exist(self):
        result = MaintenanceRisk().run(context())
        ids = {c["id"] for c in result["calculations"]}
        for claim in result["claims"]:
            for reference in claim["evidence"]:
                self.assertIn(reference, ids, f"{claim['id']} cites {reference}")

    def test_it_runs_after_the_other_models_and_before_the_audited_tail(self):
        after = stages.describe(MaintenanceRisk())["after"]
        self.assertIn(after, stages.PLACEMENTS)
        self.assertNotIn(after, stages.GUARDED_TAIL)


class CuratedInputTest(unittest.TestCase):

    def test_outcome_columns_are_never_offered_to_a_model(self):
        result = MaintenanceRisk().run(context())
        for card in result["output"]["models"]:
            for name in card.get("inputs", []):
                base = name.split(" =")[0]
                self.assertNotIn(base, ("Failure_Count", "Downtime_Hours",
                                        "SLA_Actual_Hours"),
                                 f"{base} is an outcome and must not be an input")

    def test_the_curation_is_stated_as_an_assumption_claim(self):
        result = MaintenanceRisk().run(context())
        claim = next(c for c in result["claims"] if c["id"].endswith("cl_inputs"))
        self.assertEqual(claim["type"], "assumption")
        self.assertIn("withheld", claim["text"])


class BaselineTest(unittest.TestCase):

    def test_rule_baseline_scores_the_same_complete_records_as_the_model(self):
        result = MaintenanceRisk([T.TARGETS[0]]).run(context(incomplete_input_rows()))
        card = result["output"]["models"][0]
        self.assertEqual(card["test_records"], 100)
        self.assertEqual(card["details"]["test_records_unmeasured"], 100)
        # Criticality predicts every scored label exactly. Comparing its score
        # on all 200 test rows used to invent a 100% model improvement.
        self.assertEqual(card["metric"]["model"], 1.0)
        self.assertEqual(card["metric"]["baseline"], 1.0)
        self.assertEqual(card["improvement"], 0.0)
        self.assertEqual(card["details"]["verdict"], "weak")

    def test_class_coverage_is_rechecked_after_incomplete_records_are_removed(self):
        for side in ("train", "test"):
            rows = incomplete_input_rows()
            for i, row in enumerate(rows):
                on_side = bool(i % 5) if side == "train" else i % 5 == 0
                if on_side and row["Failure_Count"] > 1:
                    row["Asset_Age_Years"] = None
            with self.subTest(side=side):
                card = MaintenanceRisk([T.TARGETS[0]]).run(
                    context(rows))["output"]["models"][0]
                self.assertEqual(card["details"]["verdict"], "not_supported")
                self.assertNotIn("metric", card)
                self.assertIn("only one class", card["details"]["reason"])

    def test_held_out_categories_do_not_choose_training_inputs(self):
        rows = incomplete_input_rows()
        for i, row in enumerate(rows):
            row["Site"] = (f"unseen-{i}" if i % 5 == 0 else
                           "North" if (i // 5) % 2 == 0 else "South")
        card = MaintenanceRisk([T.TARGETS[0]]).run(
            context(rows))["output"]["models"][0]
        self.assertIn("Site = South", card["inputs"])
        self.assertFalse(any("unseen-" in name for name in card["inputs"]))

    def test_a_date_is_never_used_as_a_baseline_grouping_rule(self):
        # Grouping by date memorises the training set rather than
        # describing it, and makes a baseline look beatable.
        result = MaintenanceRisk().run(context())
        for card in result["output"]["models"]:
            column = card.get("details", {}).get("baseline_rule_column")
            self.assertNotEqual(column, "Record_Date")

    def test_the_baseline_is_the_stronger_of_majority_and_best_rule(self):
        result = MaintenanceRisk().run(context())
        for card in result["output"]["models"]:
            details, metric = card.get("details", {}), card.get("metric")
            if not metric:
                continue
            self.assertAlmostEqual(
                metric["baseline"],
                max(details["baseline_majority"], details["baseline_best_rule"]),
                places=4)

    def test_a_grouping_rule_needs_groups_not_near_unique_values(self):
        best = T._grouping_rules(
            [{"K": f"k{i}"} for i in range(60)], [i % 2 == 0 for i in range(60)],
            [{"K": f"k{i}"} for i in range(60)], [i % 2 == 0 for i in range(60)],
            ["K"])
        self.assertIsNone(best[0], "60 distinct values is not a grouping")


class VerdictTest(unittest.TestCase):

    def test_relative_improvement_cannot_turn_a_near_chance_model_into_advice(self):
        result = MaintenanceRisk([T.TARGETS[0]]).run(context(near_chance_rows()))
        card = result["output"]["models"][0]
        self.assertTrue(card["beats_baseline"], "exercise the relative-margin pass")
        self.assertLess(card["metric"]["model"], 0.55)
        self.assertEqual(card["details"]["verdict"], "weak")
        claim = next(c for c in result["claims"] if c["id"].endswith("cl_repeat_failure"))
        self.assertEqual(claim["type"], "limitation")
        self.assertIn("should not be used to decide", claim["text"])
        self.assertNotIn(T.TARGETS[0].decision, claim["text"])
        self.assertNotIn(T.TARGETS[0].decision, result["output"]["report_markdown"])
        self.assertFalse(result["quality_checks"][0]["passed"])

    def test_a_model_near_chance_is_weak_however_large_its_relative_margin(self):
        # The point of the absolute floor: under balanced accuracy a
        # majority-class baseline is 0.5 exactly, so a 5% relative margin
        # can still be a coin flip.
        result = MaintenanceRisk().run(context(rows_for(n=2400, signal=False)))
        card = next(c for c in result["output"]["models"]
                    if c["target"].startswith("repeat_failure"))
        self.assertIsNotNone(card.get("metric"), "the fixture must fit a model")
        score = card["metric"]["model"]
        self.assertLess(score, T.CHANCE + T.CHANCE_MARGIN,
                        "a signal-free fixture must score near chance, or this "
                        "test proves nothing")
        self.assertEqual(card["details"]["verdict"], "weak")
        self.assertFalse(card["details"]["clearly_above_chance"])

    def test_a_weak_verdict_produces_a_limitation_not_a_calculation_claim(self):
        result = MaintenanceRisk().run(context(rows_for(n=2400, signal=False)))
        for card in result["output"]["models"]:
            if card.get("details", {}).get("verdict") != "weak":
                continue
            key = card["target"].split(":")[0]
            claim = next(c for c in result["claims"]
                         if c["id"].endswith(f"cl_{key}"))
            self.assertEqual(claim["type"], "limitation")
            self.assertIn("should not be used", claim["text"])

    def test_the_verdict_needs_both_tests_to_pass(self):
        result = MaintenanceRisk().run(context())
        for card in result["output"]["models"]:
            details = card.get("details", {})
            if details.get("verdict") == "useful":
                self.assertTrue(details["beats_baseline_margin"])
                self.assertTrue(details["clearly_above_chance"])

    def test_the_summary_carries_the_absolute_score_not_just_the_verdict(self):
        result = MaintenanceRisk().run(context())
        self.assertIn("%", result["summary"])
        self.assertIn("balanced accuracy", result["summary"])


class DisclosureTest(unittest.TestCase):

    def test_a_column_that_defines_the_label_is_disclosed_when_it_is_an_input(self):
        result = MaintenanceRisk().run(context())
        claim = next((c for c in result["claims"]
                      if c["id"].endswith("cl_sla_breach_defining")), None)
        self.assertIsNotNone(claim, "SLA_Target_Hours defines the label and is "
                                    "an input; that must be disclosed")
        self.assertEqual(claim["type"], "assumption")
        self.assertIn("legitimate", claim["text"])


class UnsupportedTargetTest(unittest.TestCase):

    def test_a_missing_column_reports_no_score_at_all(self):
        rows = [{k: v for k, v in row.items() if k != "SLA_Target_Hours"}
                for row in rows_for()]
        result = MaintenanceRisk().run(context(rows))
        card = next(c for c in result["output"]["models"]
                    if c["target"].startswith("sla_breach"))
        self.assertFalse(card.get("fitted", False))
        self.assertEqual(card["details"]["verdict"], "not_supported")
        self.assertNotIn("metric", card)

    def test_too_few_records_is_a_limitation_not_a_failure(self):
        result = MaintenanceRisk().run(context(rows_for(n=12)))
        self.assertEqual(result["status"], "succeeded")
        for card in result["output"]["models"]:
            self.assertEqual(card["details"]["verdict"], "not_supported")

    def test_an_unfitted_target_still_names_the_decision_it_would_support(self):
        result = MaintenanceRisk().run(context(rows_for(n=12)))
        for card in result["output"]["models"]:
            self.assertTrue(card["details"]["decision"])


class SplitTest(unittest.TestCase):

    def test_the_split_is_chronological_when_a_date_is_available(self):
        result = MaintenanceRisk().run(context())
        for card in result["output"]["models"]:
            if card.get("split"):
                self.assertEqual(card["split"]["kind"], "time")
                self.assertIn("first_held_out", card["split"])


class ArabicTest(unittest.TestCase):

    def test_arabic_model_claims_preserve_every_evaluation_figure(self):
        # Useful, below-chance-floor, below-relative-margin and unfitted
        # branches all reach the independent bilingual validator.
        cases = ((clear_signal_rows(), "useful"), (near_chance_rows(), "weak"),
                 (incomplete_input_rows(), "weak"), (rows_for(12), "not_supported"))
        for rows, verdict in cases:
            with self.subTest(records=len(rows), verdict=verdict):
                result = MaintenanceRisk().run(context(rows, language="ar"))
                self.assertEqual(result["output"]["models"][0]["details"]["verdict"], verdict)
                for claim in result["claims"]:
                    self.assertEqual(analytics.figures(claim["text"]),
                                     analytics.figures(claim["text_ar"]), claim["id"])

    def test_an_arabic_run_writes_its_claims_in_arabic(self):
        result = MaintenanceRisk().run(context(language="ar"))
        for claim in result["claims"]:
            self.assertIn("text_ar", claim, claim["id"])
            self.assertTrue(claim["text_ar"].strip())


class MaintenanceInGovernedRunTest(unittest.TestCase):

    def test_useful_model_claim_reaches_the_arabic_validation_gate(self):
        rows = clear_signal_rows()
        source = io.StringIO(newline="")
        writer = csv.DictWriter(source, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        with tempfile.TemporaryDirectory() as directory:
            store = open_store(sqlite_path=str(Path(directory) / "runs.db"))
            try:
                engine = RunEngine(store, Path(directory) / "vault", ModelGateway(env={}),
                                   stages={"maintenance_risk": MaintenanceRisk()})
                run = engine.create_run("Assess maintenance risk", source.getvalue(),
                                        "synthetic.csv", language="ar")
                for _ in range(80):
                    run = engine.advance(run["id"])
                    if run["state"] not in ("queued", "running"):
                        break
                self.assertEqual(run["state"], "awaiting_approval", run.get("error"))
                card = next(c for c in run["models"]
                            if c["target"].startswith("repeat_failure:"))
                self.assertEqual(card["details"]["verdict"], "useful")
                self.assertIn(T.TARGETS[0].decision_ar,
                              store.latest_artifact(run["id"])["content"])
            finally:
                store.close()

    def test_weak_evidence_reaches_approval_in_both_languages_without_intervention_advice(self):
        config = json.loads((Path(__file__).resolve().parents[1] / "config.json")
                            .read_text(encoding="utf-8"))
        registry, problems = stages.load_stages(env={}, config=config)
        self.assertEqual(problems, [])
        rows = near_chance_rows()
        source = io.StringIO(newline="")
        writer = csv.DictWriter(source, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        for language in ("en", "ar"):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                store = open_store(sqlite_path=str(Path(directory) / "runs.db"))
                try:
                    engine = RunEngine(store, Path(directory) / "vault", ModelGateway(env={}),
                                       stages=registry, profiles=config["profiles"])
                    run = engine.create_run("Assess maintenance risk", source.getvalue(),
                                            "synthetic.csv", profile="maintenance",
                                            language=language)
                    for _ in range(80):
                        run = engine.advance(run["id"])
                        if run["state"] not in ("queued", "running"):
                            break
                    self.assertEqual(run["state"], "awaiting_approval", run.get("error"))
                    validator = next(t for t in run["tasks"] if t["role"] == "validator")
                    self.assertTrue(all(c["passed"] for c in validator["quality_checks"]))
                    card = next(c for c in run["models"]
                                if c["target"].startswith("repeat_failure:"))
                    self.assertEqual(card["details"]["verdict"], "weak")
                    report = store.latest_artifact(run["id"])["content"]
                    self.assertNotIn(T.TARGETS[0].decision, report)
                    self.assertNotIn(T.TARGETS[0].decision_ar, report)
                    risk = next(t for t in store.get_tasks(run["id"])
                                if t["role"] == "maintenance_risk")
                    result = json.loads(risk["result_json"])
                    claim = next(c for c in result["claims"]
                                 if c["id"].endswith("cl_repeat_failure"))
                    self.assertEqual(claim["type"], "limitation")
                finally:
                    store.close()


if __name__ == "__main__":
    unittest.main()
