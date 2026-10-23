"""Presentation choices cannot silently remove domain predictors or change time."""

import csv
import io
import unittest
from datetime import date, timedelta

from server import analytics
from server.maintenance import targets


def source_rows(dated=False):
    rows = []
    for i in range(500):
        row = {"Record_ID": f"R{i}", "Asset_Age_Years": (i % 100) + .001 * i,
               "Work_Order_Type": "Corrective", "Failure_Count": 2 if i % 100 >= 50 else 1,
               "Site": "North" if i % 2 else "South"}
        if dated:
            row["Record_Date"] = (date(2025, 1, 1) + timedelta(days=i)).isoformat()
        rows.append(row)
    return rows


def presentation(rows, *, feature_role="dimension", grain="month"):
    roles = {c: "dimension" for c in rows[0]}
    roles.update(Record_ID="ignore", Asset_Age_Years=feature_role, Failure_Count="measure")
    if "Record_Date" in roles:
        roles["Record_Date"] = "date"
    return {"version": 1, "roles": roles, "measure": "Failure_Count", "dimension": "Site",
            "date_order": "auto", "grain": grain}


def prepared(rows, chosen=None):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    ctx = {"dataset_text": text.getvalue(), "dataset_name": "synthetic.csv",
           "mapping": chosen, "governance": {
               "measure": chosen["measure"] if chosen else "Failure_Count"}}
    for role in ("collector", "profiler", "cleaner", "preparer"):
        result = getattr(analytics, role)(ctx)
        assert result["status"] == "succeeded", result
        ctx[role] = result["output"]
    return ctx


# The card's provenance (A14, A11) names the snapshot it was fitted on, the
# fitting time and the reasons inputs were refused, which legitimately
# differ between the mappings these tests compare; the scores must not.
PROVENANCE = ("snapshot", "fitted_at", "excluded_inputs")


def model(ctx):
    card = targets.MaintenanceRisk([targets.TARGETS[0]]).run(ctx)["output"]["models"][0]
    return {k: v for k, v in card.items() if k not in PROVENANCE}


class MaintenanceMappingTests(unittest.TestCase):
    def test_numeric_predictor_is_identical_as_measure_or_dimension_or_unmapped(self):
        rows = source_rows()
        contexts = [prepared(rows), prepared(rows, presentation(rows)),
                    prepared(rows, presentation(rows, feature_role="measure"))]
        cards = [model(ctx) for ctx in contexts]
        self.assertEqual(cards[0], cards[1])
        self.assertEqual(cards[0], cards[2])
        self.assertIn("Asset_Age_Years", cards[0]["inputs"])
        self.assertGreater(cards[0]["metric"]["model"], .9)

    def test_record_chronology_and_model_are_independent_of_chart_grain(self):
        rows = source_rows(dated=True)
        contexts = [prepared(rows), prepared(rows, presentation(rows, grain="day")),
                    prepared(rows, presentation(rows, grain="month")),
                    prepared(rows, presentation(rows, grain="year"))]
        cards = [model(ctx) for ctx in contexts]
        self.assertEqual(contexts[2]["cleaner"]["rows"][0]["Record_Date"], "2025-01")
        self.assertEqual(cards[0]["split"], {"kind": "time", "first_held_out": "2026-02-05"})
        for card in cards[1:]:
            self.assertEqual(cards[0], card)
        self.assertFalse(any("Record_Date" in name for name in cards[0]["inputs"]))

    def test_ignored_features_and_targets_are_not_restored_from_source_rows(self):
        rows = source_rows()
        chosen = presentation(rows, feature_role="ignore")
        result = targets.MaintenanceRisk().run(prepared(rows, chosen))
        self.assertNotIn("Asset_Age_Years", result["output"]["models"][0]["inputs"])
        self.assertIn("explicitly ignored",
                      result["output"]["model_inputs_excluded"]["Asset_Age_Years"])
        chosen["roles"]["Failure_Count"] = "ignore"
        chosen["roles"]["Asset_Age_Years"] = "measure"
        chosen["measure"] = "Asset_Age_Years"
        ctx = prepared(rows, chosen)
        card = model(ctx)
        self.assertEqual(card["details"]["verdict"], "not_supported")
        self.assertNotIn("metric", card)

    def test_personal_values_in_a_known_before_field_remain_excluded(self):
        rows = source_rows()
        for row in rows:
            row["Site"] = row["Site"].lower() + "@example.test"
        result = targets.MaintenanceRisk().run(prepared(rows))
        self.assertIn("personal data", result["output"]["model_inputs_excluded"]["Site"])
        self.assertFalse(any(name.startswith("Site") for name in
                             result["output"]["models"][0]["inputs"]))

    def test_source_positions_survive_cleaning_without_assuming_unique_identifiers(self):
        rows = source_rows(dated=True)
        for row in rows:
            row["Record_ID"] = "reused-label"
        original = model(prepared(rows, presentation(rows)))
        with_gaps = [{c: "" for c in rows[0]}, *rows, dict(rows[10])]
        ctx = prepared(with_gaps, presentation(rows))
        self.assertEqual(ctx["cleaner"]["dropped"], 2)
        self.assertEqual(model(ctx), original)

    def test_inner_join_preserves_source_dates_and_lookup_ignore_policy(self):
        rows = source_rows(dated=True)
        ctx = prepared(rows, presentation(rows))
        ctx["joins"] = [{
            "content": "Site,Planned_Operating_Hours\nNorth,100\n",
            "name": "lookup.csv", "alias": "lookup", "how": "inner",
            "keys": [{"left": "Site", "right": "Site"}],
            "mapping": {"roles": {"Site": "dimension", "Planned_Operating_Hours": "ignore"}},
        }]
        result = analytics.merge(ctx)
        self.assertEqual(result["status"], "succeeded")
        ctx["merge"] = result["output"]
        self.assertEqual(ctx["merge"]["rows_after"], 250)
        self.assertEqual(ctx["merge"]["source_indices"][:3], [1, 3, 5])
        self.assertTrue(all(set(row) == set(ctx["merge"]["columns"])
                            for row in ctx["merge"]["rows"]))
        result = targets.MaintenanceRisk().run(ctx)
        self.assertIn("explicitly ignored",
                      result["output"]["model_inputs_excluded"]["Planned_Operating_Hours"])
        card = result["output"]["models"][0]
        self.assertEqual(card["split"]["kind"], "time")
        self.assertEqual(card["test_records"], 50)
        self.assertNotIn("Planned_Operating_Hours", card["inputs"])


if __name__ == "__main__":
    unittest.main()
