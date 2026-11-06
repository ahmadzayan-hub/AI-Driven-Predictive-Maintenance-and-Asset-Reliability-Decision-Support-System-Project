"""AI-proposed executive mapping (ADR 2026-11-06-ai-proposed-mapping).

Model answers are recorded fakes; no test here proves a real provider proposed a
mapping. Synthetic rows only."""
import json
import unittest

from server import mapping as colmap
from server import mapping_advisor as advisor

COLUMNS = ["Record_Date", "Station", "Criticality", "Downtime_Hours", "Availability_Pct", "Work_Order"]
ROWS = [{"Record_Date": f"2025-{1 + i % 12:02d}-01", "Station": f"ST{i % 4:02d}", "Criticality": ["High", "Low"][(i // 4) % 2],
         "Downtime_Hours": str(1 + i % 7), "Availability_Pct": str(95 + i % 5), "Work_Order": f"WO-SECRET-{1000 + i}"}
        for i in range(60)]

GOOD = {"roles": {"Record_Date": "date", "Station": "dimension", "Criticality": "dimension",
                  "Downtime_Hours": "measure", "Availability_Pct": "measure", "Work_Order": "ignore"},
        "measure": "Downtime_Hours", "dimension": "Station",
        "better": {"Downtime_Hours": "lower", "Availability_Pct": "higher"},
        "cross": ["Station", "Criticality"],
        "reasons": {"Downtime_Hours": {"en": "Lost hours are what an executive watches first.",
                                       "ar": "الساعات المفقودة أول ما يتابعه المسؤول."},
                    "Work_Order": {"en": "See https://example.invalid", "ar": "رابط"}}}


class Gateway:
    """A recorded model answer. Never a real provider."""

    def __init__(self, answer, configured=True):
        self.answer, self.configured, self.calls = answer, configured, []

    def status(self):
        return {"provider": "recorded-fake", "model": "fixture", "configured": self.configured}

    def ask_json(self, system, user, **kwargs):
        self.calls.append(user)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def proposal(gateway, model_allowed=True, rows=ROWS, columns=COLUMNS):
    sampled = colmap.sample(rows)
    profiles = colmap.profile(columns, sampled)
    rules = colmap.suggest(columns, sampled, (), profiles)
    return advisor.propose(columns, rows, profiles, rules, gateway, model_allowed)


class ProposalTests(unittest.TestCase):

    def test_a_valid_model_proposal_is_used_and_labelled(self):
        result = proposal(Gateway(GOOD))
        self.assertEqual((result["source"], result["provider"]), ("model", "recorded-fake fixture"))
        self.assertEqual(result["mapping"]["measure"], "Downtime_Hours")
        self.assertEqual(result["mapping"]["better"], {"Downtime_Hours": "lower", "Availability_Pct": "higher"})
        self.assertEqual(result["cross"], ["Station", "Criticality"])
        self.assertEqual(result["mapping"]["cross"], ["Station", "Criticality"])   # saved with the mapping
        self.assertIn("executive watches first", result["reasons"]["Downtime_Hours"]["en"])
        # A reason with a link is dropped; the column keeps the rules' reason.
        self.assertNotIn("https", json.dumps(result["reasons"]["Work_Order"]))

    def test_no_value_ever_reaches_the_model(self):
        gateway = Gateway(GOOD)
        proposal(gateway)
        sent = gateway.calls[0]
        for value in ("WO-SECRET", "ST00", "High", "2025-01-01", "95"):
            self.assertNotIn(value, sent, value)
        self.assertIn("Downtime_Hours", sent)          # names and counts only

    def test_a_bad_answer_falls_back_to_the_rules_and_says_so(self):
        for answer in ({"roles": {"Station": "dimension"}},                     # columns missing
                       {**GOOD, "roles": {**GOOD["roles"], "Station": "kpi"}},  # unknown role
                       {**GOOD, "roles": {**GOOD["roles"], "Station": "measure"}, "measure": "Station"},  # text as a measure
                       "not json", RuntimeError("provider down")):
            result = proposal(Gateway(answer))
            self.assertEqual(result["source"], "rules", answer)
            self.assertTrue(result["notes"])

    def test_without_a_model_or_permission_the_rules_propose(self):
        self.assertIn("No language model", proposal(Gateway(GOOD, configured=False))["notes"][0]["en"])
        self.assertIn("personal data", proposal(Gateway(GOOD), model_allowed=False)["notes"][0]["ar"] and
                      proposal(Gateway(GOOD), model_allowed=False)["notes"][0]["en"])
        self.assertEqual(proposal(None)["source"], "rules")

    def test_a_column_the_rules_found_empty_stays_out(self):
        rows = [{**r, "Notes": ""} for r in ROWS]
        answer = {**GOOD, "roles": {**GOOD["roles"], "Notes": "dimension"}}
        result = proposal(Gateway(answer), rows=rows, columns=COLUMNS + ["Notes"])
        self.assertEqual(result["mapping"]["roles"]["Notes"], "ignore")


class DeclaredPairTests(unittest.TestCase):
    def test_a_saved_pair_is_validated_and_crossed_first(self):
        from server import layout_plan, query
        base = {k: v for k, v in GOOD.items() if k != "reasons"}
        mapping = colmap.validate({**base, "cross": ["Criticality", "Station"]}, COLUMNS, ROWS)
        self.assertEqual(mapping["cross"], ["Criticality", "Station"])
        with self.assertRaises(colmap.MappingError):
            colmap.validate({**base, "cross": ["Station", "Downtime_Hours"]}, COLUMNS, ROWS)
        table = query.table_from(COLUMNS, ["Downtime_Hours", "Availability_Pct"],
                                 [{**r, "Downtime_Hours": float(r["Downtime_Hours"]),
                                   "Availability_Pct": float(r["Availability_Pct"])} for r in ROWS],
                                 {"Record_Date": "date", "Downtime_Hours": "analysed"})
        plan = layout_plan.plan_for(table, cross=["Criticality", "Station"])["plan"]
        matrix = next(s for s in plan["sections"] if s["component"] == "matrix")
        self.assertEqual(matrix["binding"]["group_by"], ["Criticality", "Station"])


class ProposalApiTests(unittest.TestCase):
    def test_the_endpoint_proposes_without_saving_and_hides_other_owners(self):
        from tests import test_dataset_deletion as base
        case = base.SqliteDatasetDeletionTestCase("test_the_mapping_goes_with_the_dataset")
        case.setUp()
        try:
            text = ",".join(COLUMNS) + "\n" + "\n".join(",".join(r[c] for c in COLUMNS) for r in ROWS) + "\n"
            dataset = case.upload(text, "orders.csv", "alice")
            reply = case.client.post(f"/api/datasets/{dataset}/mapping/proposal?language=ar", headers=case.auth("alice"))
            self.assertEqual(reply.status_code, 200, reply.text)
            body = reply.json()
            self.assertEqual(body["source"], "rules")                 # no model in tests
            self.assertIn("لا يوجد نموذج", body["notes"][0])
            self.assertIn("Downtime_Hours", body["mapping"]["roles"])
            self.assertIsNone(case.store.get_dataset(dataset).get("mapping_json"))
            self.assertEqual(case.client.post(f"/api/datasets/{dataset}/mapping/proposal",
                                              headers=case.auth("mallory")).status_code, 404)
        finally:
            case.doCleanups()


if __name__ == "__main__":
    unittest.main()
