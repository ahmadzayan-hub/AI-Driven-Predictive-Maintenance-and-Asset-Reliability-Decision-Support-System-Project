"""Condition surveys: averaged scores, observation dates, condition measures (ADR 2026-11-05).

Every row here is invented. A real survey stays outside tracked files; its
validation run is recorded in the ADR, not reproduced.
"""
import csv
import io
import unittest

from server import analytics, layout_plan as L, query
from server.maintenance import kpis
from tests import test_datasets

COLUMNS = ["Survey_Date", "Station", "Equipment_Type", "Status", "Condition_Score",
           "Ageing_Level", "Intrinsic_RAMS_Level", "Operating_RAMS_Level", "Maintenance_Level"]


def fixture():
    """Three invented stations, one not-applicable line in the third."""
    rows = []
    plan = {"S1": [7.8, 6.6, 7.2, 6.9], "S2": [6.6, 6.6, 5.2, 7.5], "S3": [7.8, 7.8, 7.5, None]}
    dates = {"S1": "2025-07-07", "S2": "2025-07-12", "S3": "2025-07-24"}
    for station, scores in plan.items():
        for i, score in enumerate(scores):
            intrinsic = 9 if score in (7.8, 7.5) else 6 if score is not None else None
            rows.append({"Survey_Date": dates[station], "Station": station,
                         "Equipment_Type": ["DB", "MCC", "UPS", "FACP"][i],
                         "Status": "Scored" if score is not None else "Not applicable",
                         "Condition_Score": "" if score is None else score,
                         "Ageing_Level": "" if score is None else (5 if score == 5.2 else 7),
                         "Intrinsic_RAMS_Level": "" if intrinsic is None else intrinsic,
                         "Operating_RAMS_Level": "" if score is None else 6,
                         "Maintenance_Level": "" if score is None else 6})
    return rows


def as_csv(rows):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


class Additivity(unittest.TestCase):
    def test_scores_levels_and_rates_are_not_added_up(self):
        for name in ("Condition_Score", "Ageing_Level", "Availability_Pct", "SLA_Compliance_Score",
                     "Failure_Probability", "Asset_Health_Index", "Asset_Age_Years"):
            self.assertFalse(query.additive(name), name)
        for name in ("Downtime_Hours", "Failure_Count", "Maintenance_Cost_USD", "Operating_Hours"):
            self.assertTrue(query.additive(name), name)

    def test_fields_carry_the_flag_and_count_skips_blanks(self):
        rows = fixture()
        table = query.table_from(COLUMNS, ["Condition_Score", "Ageing_Level"],
                                 [{**r, "Condition_Score": r["Condition_Score"] or None} for r in rows])
        flags = {f["name"]: f.get("additive") for f in query.fields(table)}
        self.assertIs(flags["Condition_Score"], False)
        answer = query.aggregate(table, {"group_by": ["Station"], "measures": [
            {"agg": "count"}, {"agg": "count", "column": "Condition_Score"},
            {"agg": "mean", "column": "Condition_Score"}], "sort": {"by": "Station"}})
        s3 = next(g for g in answer["groups"] if g["keys"] == ["S3"])
        self.assertEqual((s3["records"], s3["values"][0], s3["values"][1]), (4, 4, 3))
        self.assertAlmostEqual(s3["values"][2], (7.8 + 7.8 + 7.5) / 3)


class ObservationDates(unittest.TestCase):
    def test_survey_and_inspection_dates_are_the_time_axis(self):
        for name in ("Survey_Date", "Inspection Date", "assessment-date", "Reading_Month"):
            self.assertEqual(analytics._date_like_column(["Station", name]), name)

    def test_event_dates_stay_out_as_decided_on_3_november(self):
        for name in ("Failure_Date", "Due_Date", "Install_Date", "Record_Date", "Survey_Date_Old"):
            self.assertIsNone(analytics._date_like_column(["Station", name]), name)

    def test_an_exact_name_still_wins(self):
        self.assertEqual(analytics._date_like_column(["Survey_Date", "Date"]), "Date")


class ConditionMeasures(unittest.TestCase):
    def results(self, rows):
        return {r["key"]: r for r in kpis.compute_all(COLUMNS, rows)["results"]}

    def test_three_measures_on_scored_lines_only(self):
        out = self.results(fixture())
        scored = [7.8, 6.6, 7.2, 6.9, 6.6, 6.6, 5.2, 7.5, 7.8, 7.8, 7.5]
        mean = out["condition_score_mean"]
        self.assertAlmostEqual(mean["value"], sum(scored) / len(scored))
        self.assertEqual((mean["records"], mean["records_unmeasured"]), (11, 1))
        self.assertEqual(out["condition_poor_share"]["value"], 0.0)
        faults = sum(1 for s in scored if s not in (7.8, 7.5))
        self.assertAlmostEqual(out["condition_cm_fault_share"]["value"], 100 * faults / len(scored))

    def test_poor_starts_below_five(self):
        rows = fixture()
        rows[0]["Condition_Score"], rows[1]["Condition_Score"] = 5.0, 4.9
        out = self.results(rows)
        self.assertAlmostEqual(out["condition_poor_share"]["value"], 100 / 11)

    def test_a_score_off_the_one_to_nine_scale_gives_no_figure(self):
        rows = fixture()
        rows[0]["Condition_Score"] = 72
        out = self.results(rows)
        self.assertIsNone(out["condition_score_mean"]["value"])
        self.assertIn("outside the 1 to 9 condition scale", out["condition_score_mean"]["undefined_reason"])

    def test_maintenance_files_are_unaffected(self):
        available, unavailable = kpis.computable(["Downtime_Hours", "Planned_Operating_Hours"])
        self.assertNotIn("condition_score_mean", [k.key for k in available])
        self.assertIn("condition_score_mean", unavailable)
        # A maintenance file's 0 to 100 Condition_Score is not a survey on this scale.
        available, _ = kpis.computable(["Condition_Score", "Downtime_Hours"])
        self.assertFalse([k for k in available if k.key.startswith("condition_")])


class ConditionLayout(unittest.TestCase):
    def plan(self):
        rows = fixture()
        table = query.table_from(COLUMNS, [c for c in COLUMNS if c.endswith(("Score", "Level"))],
                                 [{k: (v if v != "" else None) for k, v in r.items()} for r in rows],
                                 {"Survey_Date": "date", "Station": "breakdown", "Condition_Score": "analysed"})
        prof = L.profile(table)
        return L.domain(prof), L.rule_plan(prof, L.capabilities(prof))

    def test_no_score_is_summed_and_the_weakest_come_first(self):
        kind, plan = self.plan()
        self.assertEqual(kind, "condition")
        measures = [m for s in plan["sections"] for m in s["binding"].get("measures", [])]
        self.assertFalse([m for m in measures if m.get("agg") == "sum"])
        priorities = next(s for s in plan["sections"] if s["component"] == "priorities")
        self.assertIs(priorities["binding"]["sort"]["desc"], False)
        self.assertEqual(priorities["binding"]["measures"][0]["agg"], "mean")
        average = next(s for s in plan["sections"] if s["title"]["en"] == "Average Condition_Score")
        self.assertEqual(average["binding"]["measures"][1], {"agg": "count", "column": "Condition_Score"})
        self.assertTrue(any(s["id"] == "scored" for s in plan["sections"]))


@unittest.skipUnless(test_datasets.FASTAPI_AVAILABLE, "fastapi is not installed")
class ConditionRun(test_datasets.DatasetApiTestCase):
    """Upload, run and read the brief, as a reader would."""

    def test_the_brief_has_a_period_and_the_condition_measures(self):
        response = self.upload(as_csv(fixture()), "SYNTHETIC_condition.csv")
        self.assertEqual(response.status_code, 201, response.text)
        run = self.client.post("/api/runs", json={"goal": "Condition review",
                                                  "dataset_id": response.json()["dataset"]["id"]}).json()
        for _ in range(40):
            if run["state"] not in ("queued", "running"):
                break
            run = self.client.post(f"/api/runs/{run['id']}/advance").json()
        brief = self.client.get(f"/api/runs/{run['id']}/executive").json()
        self.assertEqual(brief["scope"]["period"]["from"], "2025-07-07")
        self.assertEqual(brief["scope"]["period"]["to"], "2025-07-24")
        keys = {m["key"] for m in brief["kpis"]["measures"]}
        self.assertTrue({"condition_score_mean", "condition_poor_share", "condition_cm_fault_share"} <= keys)


# The inherited dataset tests would run again under this class; keep only this file's own.
for _name in [n for n in dir(ConditionRun) if n.startswith("test_")
              and n != "test_the_brief_has_a_period_and_the_condition_measures"]:
    setattr(ConditionRun, _name, None)


if __name__ == "__main__":
    unittest.main()
