"""Executive evidence is computed, scoped and read-only; all data is synthetic."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from server import query
from server.executive import (ExecutiveDashboardAgent, parse_filters, MAX_FILTER_CHARS,
                              MAX_FINDINGS, MAX_EVIDENCE, MAX_MODELS)
from server.runs import model_cards
from tests.support import closing


COLUMNS = ["Record_ID", "Record_Date", "Site", "Work_Order_Type", "Downtime_Hours",
           "Operating_Hours", "Planned_Operating_Hours", "Preventive_WO_Count",
           "Corrective_WO_Count", "Completed_WO_Count", "First_Time_Fix_Count",
           "Repeat_Repair_Count", "Overdue_WO_Count", "Maintenance_Cost_USD",
           "Production_Loss_USD"]
ROWS = [
    ["PRIVATE_ROW_A", "2026-01", "North", "Corrective", 10., 80., 100., 0., 10., 10., 9., 1., 2., 100., 1000.],
    ["PRIVATE_ROW_B", "2026-02", "North", "Corrective", None, 90., 100., 0., 10., 10., 5., 5., 0., 200., 0.],
    ["PRIVATE_ROW_C", "2026-03", "South", "Preventive", 30., 70., 100., 20., 0., 20., 0., 0., 0., 900., 2000.],
]
CSV = ",".join(COLUMNS) + "\n" + "\n".join(
    ",".join("" if value is None else str(value) for value in row) for row in ROWS) + "\n"


def table():
    return query.Table(COLUMNS, set(COLUMNS[4:]), copy.deepcopy(ROWS), {"Site": "breakdown"})


def run():
    return {"id": "r1", "dataset_name": "synthetic.csv", "state": "awaiting_approval"}


def stage(claims=None, models=None):
    return {"role": "maintenance_governance", "state": "succeeded", "title": "Governance",
            "result": {"calculations": [{"id": "g.c_count", "name": "whole_run_records", "value": 3,
                                        "method": "count records before executive filters"}],
                       "claims": claims if claims is not None else [{"id": "g.cl_count", "type": "fact",
                           "status": "verified", "text": "The original run has three records.",
                           "text_ar": "يحتوي التشغيل الأصلي على ثلاثة سجلات.", "evidence": ["g.c_count"]}],
                       "output": {"models": models or []}}}


class ExecutiveTests(unittest.TestCase):
    def setUp(self):
        self.agent = ExecutiveDashboardAgent()

    def brief(self, filters=None, tasks=(), language="en", current=None):
        return self.agent.brief(current or table(), run(), tasks, filters, language)

    def test_content_revision_is_deterministic_and_covers_language_scope_and_stored_evidence(self):
        first = self.brief(tasks=[stage()])
        same = self.brief(tasks=[stage()])
        self.assertRegex(first["snapshot_id"], r"^[a-f0-9]{64}$")
        self.assertEqual(first["snapshot_id"], same["snapshot_id"])
        self.assertNotEqual(first["snapshot_id"], self.brief(tasks=[stage()], language="ar")["snapshot_id"])
        self.assertNotEqual(first["snapshot_id"], self.brief([{"column": "Site", "op": "in", "values": ["North"]}], [stage()])["snapshot_id"])
        revised = stage()
        revised["result"]["claims"][0]["text"] = "A revised stored observation over the same records."
        self.assertNotEqual(first["snapshot_id"], self.brief(tasks=[revised])["snapshot_id"])

    def test_filters_reuse_query_semantics_and_kpis_keep_population_and_missing_counts(self):
        filters = [{"column": "Site", "op": "in", "values": ["North"]}]
        snapshot = copy.deepcopy(filters)
        result = self.brief(filters)
        self.assertEqual(result["scope"], {"records": 2, "total_records": 3, "filters": filters})
        measures = {m["key"]: m for m in result["kpis"]["measures"]}
        self.assertEqual(measures["downtime_per_record"]["value"], 10.)
        self.assertEqual(measures["downtime_per_record"]["records"], 1)
        self.assertEqual(measures["downtime_per_record"]["records_unmeasured"], 1)
        self.assertEqual(measures["first_time_fix"]["value"], 70.)
        # One of the two North records has no downtime reading, so availability is
        # measured on the other alone: 1 - 10 / 100. It is not read as zero downtime.
        self.assertEqual(measures["availability"]["value"], 90.)
        self.assertEqual((measures["availability"]["records"], measures["availability"]["records_unmeasured"]), (1, 1))
        self.assertEqual(filters, snapshot)
        self.assertEqual(table().rows, ROWS)
        self.assertEqual(result["source"], "engine")
        self.assertNotIn("PRIVATE_ROW_", json.dumps(result))

    def test_group_priorities_and_drilldowns_preserve_the_entire_scope(self):
        filters = [{"column": "Record_Date", "op": "gte", "value": "2026-02"}]
        result = self.brief(filters)
        priority = next(p for p in result["priorities"] if p["id"] == "downtime_hours")
        drill = next(d for d in result["drilldowns"] if d["id"] == priority["drilldown_id"])
        self.assertEqual(drill["filters"], filters + [{"column": "Site", "op": "in", "values": ["South"]}])
        rows, _ = query.filtered(table(), drill["filters"])
        self.assertEqual(len(rows), 1)
        evidence = next(e for e in result["evidence"] if e["id"] in priority["evidence_refs"])
        self.assertEqual(evidence["value"], 30.)
        self.assertEqual(evidence["scope"], "filtered")

    def test_empty_scope_does_not_manufacture_zero_performance(self):
        result = self.brief([{"column": "Site", "op": "eq", "value": "Absent"}])
        self.assertEqual(result["readiness"]["status"], "empty")
        self.assertEqual(result["scope"]["records"], 0)
        self.assertFalse(result["priorities"])
        self.assertTrue(all(m["value"] is None for m in result["kpis"]["measures"]))
        self.assertTrue(all(m["records"] == 0 for m in result["kpis"]["measures"]))

    def test_general_table_reports_unavailable_kpis_and_no_forecast(self):
        general = query.Table(["Region", "Spend"], {"Spend"}, [("A", 10.), ("B", 20.)])
        result = self.brief(current=general)
        self.assertFalse(result["kpis"]["measures"])
        self.assertIn("availability", result["kpis"]["unavailable"])
        self.assertEqual(result["readiness"]["status"], "limited")
        self.assertFalse(result["models"])
        self.assertNotIn("failure_probability", result)
        self.assertTrue(any("future asset failure" in s for s in result["readiness"]["limitations"]))

    def test_findings_need_existing_calculations_and_remain_whole_run_when_filtered(self):
        valid = stage()["result"]["claims"][0]
        unverified = {**valid, "id": "bad1", "status": "unverified", "text": "SECRET_UNVERIFIED"}
        dangling = {**valid, "id": "bad2", "evidence": ["absent"], "text": "DANGLING_CLAIM"}
        forecast = {**valid, "id": "bad3", "type": "forecast", "text": "INVENTED_FUTURE"}
        result = self.brief([{"column": "Site", "op": "eq", "value": "North"}],
                            [stage([valid, unverified, dangling, forecast])])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["scope"], "whole_run")
        self.assertEqual(next(e for e in result["evidence"] if e["id"] == "g.c_count")["value"], 3)
        rendered = json.dumps(result)
        for excluded in ("SECRET_UNVERIFIED", "DANGLING_CLAIM", "INVENTED_FUTURE"):
            self.assertNotIn(excluded, rendered)
        self.assertTrue(any("whole run" in text for text in result["readiness"]["limitations"]))

    def test_arabic_uses_arabic_templates_and_source_claim_without_rewriting_numbers(self):
        english = self.brief(tasks=[stage()])
        arabic = self.brief(tasks=[stage()], language="ar")
        self.assertEqual(arabic["findings"][0]["text"], "يحتوي التشغيل الأصلي على ثلاثة سجلات.")
        self.assertNotEqual(english["headline"], arabic["headline"])
        en = {m["key"]: m for m in english["kpis"]["measures"]}
        for item in arabic["kpis"]["measures"]:
            self.assertEqual(item["value"], en[item["key"]]["value"])
            self.assertNotEqual(item["title"], en[item["key"]]["title"])
            self.assertNotIn("title_ar", item)
            # The population is shown in Arabic; its code stays for exports.
            self.assertEqual(item["population"], en[item["key"]]["population"])
            self.assertRegex(item["population_label"], "[\u0600-\u06FF]")
            self.assertNotIn("population_ar", item)

    def test_response_is_bounded_and_every_reference_resolves(self):
        claims = [{"id": f"g.cl_{i}", "type": "fact", "status": "verified", "text": "Measured.",
                   "evidence": ["g.c_count"]} for i in range(100)]
        cards = [{"kind": "maintenance_risk", "target": f"t{i}", "fitted": False,
                  "details": {"verdict": "not_supported", "reason": "Too few records"}} for i in range(100)]
        result = self.brief(tasks=[stage(claims, cards)])
        self.assertLessEqual(len(result["findings"]), MAX_FINDINGS)
        self.assertLessEqual(len(result["models"]), MAX_MODELS)
        self.assertLessEqual(len(result["evidence"]), MAX_EVIDENCE)
        ids = {e["id"] for e in result["evidence"]}
        for item in result["findings"] + result["priorities"] + result["questions"]:
            self.assertTrue(set(item["evidence_refs"]) <= ids)
        self.assertTrue(all(c["scope"] == "whole_run" and "metric" not in c for c in result["models"]))

    def test_transport_and_query_validation_refuse_invalid_filters(self):
        for encoded in ("not-json", "null", "{}", '["bad"]',
                        json.dumps([{"column": "Site", "op": "eq", "value": {"bad": 1}}]),
                        json.dumps([{"column": "Site", "op": "eq", "value": float("nan")}]),
                        " " * (MAX_FILTER_CHARS + 1)):
            with self.subTest(encoded=encoded[:60]), self.assertRaises(query.QueryError):
                parse_filters(encoded)
        for filters in ([{"column": "Missing", "op": "eq", "value": "x"}],
                        [{"column": "Site", "op": "eq", "value": "North"}] * 13):
            with self.assertRaises(query.QueryError):
                self.brief(filters)

    def test_zero_denominators_limit_readiness_even_when_a_model_card_is_useful(self):
        current = table()
        current.rows = [tuple(list(row[:4]) + [0.] * (len(row) - 4)) for row in current.rows]
        card = {"kind": "maintenance_risk", "target": "same record", "inputs": [],
                "beats_baseline": True, "details": {"verdict": "useful"}}
        result = self.brief(tasks=[stage(claims=[], models=[card])], current=current)
        self.assertEqual(result["readiness"]["status"], "limited")
        self.assertTrue(any("undefined" in text for text in result["readiness"]["limitations"]))

    def test_valid_maximum_filter_scope_is_not_rejected_by_internal_group_drill(self):
        filters = [{"column": "Site", "op": "in", "values": ["North"]}] * query.MAX_FILTERS
        result = self.brief(filters)
        self.assertEqual(result["scope"]["records"], 2)
        self.assertEqual(result["scope"]["filters"], filters)
        groups = [p for p in result["priorities"] if p["id"] in {"downtime_hours", "maintenance_cost_usd"}]
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(p["drilldown_id"] is None for p in groups))
        self.assertTrue(all(len(d["filters"]) <= query.MAX_FILTERS for d in result["drilldowns"]))
        self.assertEqual(result["drilldowns"][0]["filters"], filters)

    def test_blank_group_normalisation_never_widens_an_offered_drilldown(self):
        current = table()
        current.rows[0][2], current.rows[0][4] = None, 10.
        current.rows[1][2], current.rows[1][4] = "", 2.
        current.rows[2][4] = 1.
        result = self.brief(current=current)
        priority = next(p for p in result["priorities"] if p["id"] == "downtime_hours")
        self.assertIsNone(priority["drilldown_id"])

    def test_numeric_overflow_is_explicitly_refused_not_turned_into_zero(self):
        current = query.Table(["Downtime_Hours"], {"Downtime_Hours"}, [(1e308,), (1e308,)])
        with self.assertRaises(query.QueryError) as caught:
            self.brief(current=current)
        self.assertIn("numeric range", caught.exception.problems[0].en)

    def test_missing_source_translation_and_failed_validation_are_disclosed(self):
        original = stage()
        del original["result"]["claims"][0]["text_ar"]
        original["result"]["quality_checks"] = [{"name": "source_check", "passed": False}]
        result = self.brief(tasks=[original], language="ar")
        self.assertFalse(result["findings"])
        self.assertEqual(result["readiness"]["status"], "limited")
        self.assertTrue(any("باللغة المطلوبة" in text for text in result["readiness"]["limitations"]))
        check = next(e for e in result["evidence"] if e["id"] == "executive.validation.failed_checks")
        self.assertEqual(check["value"], 1)
        self.assertEqual(check["scope"], "whole_run")

    def test_model_card_reader_preserves_legacy_and_batch_without_fabricating_fields(self):
        legacy = {"kind": "regression", "target": "spend", "inputs": []}
        unsupported = {"kind": "maintenance_risk", "target": "repeat_failure", "fitted": False,
                       "details": {"verdict": "not_supported"}}
        self.assertEqual(model_cards({"output": {"model_card": legacy}}), [legacy])
        self.assertEqual(model_cards({"output": {"models": [unsupported, "not a card", {}]}}), [unsupported])


try:
    from fastapi.testclient import TestClient
    from server.app import create_app
    from tests.support import scoped_token as issue_local_test_token
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

SECRET = "synthetic-executive-test-secret-at-least-32-characters"


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class ExecutiveApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Executive tests", "database_file": str(root / "a.db"),
            "memory_file": str(root / "m.json"), "vault_dir": str(root / "vault"),
            "stages": ["server.maintenance.targets.MaintenanceRisk"],
            "profiles": {"default": [], "maintenance": ["maintenance_risk"]}}), encoding="utf-8")
        self.app = create_app(config, env={"AGENTIC_OS_ENV": "production", "AGENTIC_OS_JWT_SECRET": SECRET, "SUPABASE_URL": "https://test.supabase.invalid"})
        self.client = TestClient(closing(self, self.app), raise_server_exceptions=False)

    def auth(self, owner="alice", role="analyst"):
        return {"Authorization": "Bearer " + issue_local_test_token(SECRET, subject=owner, role=role)}

    def make_run(self, finish=True, profile=None):
        response = self.client.post("/api/runs", headers=self.auth(),
            json={"goal": "Review synthetic maintenance", "dataset_text": CSV, "profile": profile})
        self.assertEqual(response.status_code, 201, response.text)
        current = response.json()
        if finish:
            for _ in range(80):
                if current["state"] not in {"queued", "running"}:
                    break
                current = self.client.post(f"/api/runs/{current['id']}/advance", headers=self.auth()).json()
            self.assertEqual(current["state"], "awaiting_approval", current.get("error"))
        return current

    def test_api_filters_scoped_kpis_and_does_not_call_models_or_mutate_run(self):
        current = self.make_run()
        path = f"/api/runs/{current['id']}/executive"
        filters = [{"column": "Site", "op": "in", "values": ["North"]}]
        before = self.client.get(f"/api/runs/{current['id']}", headers=self.auth()).json()
        with patch.object(self.app.state.engine.gateway, "narrate", side_effect=AssertionError("No model calls")):
            response = self.client.get(path, headers=self.auth(), params={"filters": json.dumps(filters)})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["source"], "engine")
        self.assertEqual(body["scope"]["records"], 2)
        self.assertEqual(next(m for m in body["kpis"]["measures"] if m["key"] == "downtime_per_record")["value"], 10.)
        after = self.client.get(f"/api/runs/{current['id']}", headers=self.auth()).json()
        self.assertEqual(before, after)

    def test_timestamp_uses_stored_snapshot_and_refreshes_after_intervening_progress(self):
        current = self.make_run()
        identifier = current["id"]
        path = f"/api/runs/{identifier}/executive"
        engine = self.app.state.engine
        initial = self.client.get(path, headers=self.auth()).json()
        self.assertEqual(initial["run"]["updated_at"], current["updated_at"])
        newer = "2030-04-05T12:00:00+00:00"
        load_table = engine.load_table

        def external_progress(*args):
            table = load_table(*args)
            # A synthetic concurrent writer advances metadata after run_table's
            # first read, before the executive evidence snapshot is captured.
            engine.store.update("runs", identifier, {"updated_at": newer})
            return table

        with patch.object(engine, "load_table", side_effect=external_progress):
            response = self.client.get(path, headers=self.auth())
        self.assertEqual(response.status_code, 200, response.text)
        refreshed = response.json()
        self.assertEqual(refreshed["run"]["updated_at"], newer)
        self.assertNotEqual(initial["run"]["updated_at"], refreshed["run"]["updated_at"])
        before = engine.get_run(identifier)
        stable = self.client.get(path, headers=self.auth()).json()
        self.assertEqual(stable["run"]["updated_at"], newer)
        self.assertEqual(engine.get_run(identifier), before, "Preparing a brief must not advance its timestamp or run")

    def test_read_permission_ownership_and_ready_guard_precede_filter_parsing(self):
        current = self.make_run(finish=False)
        path = f"/api/runs/{current['id']}/executive"
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, headers=self.auth("mallory"), params={"filters": "invalid"}).status_code, 404)
        self.assertEqual(self.client.get(path, headers=self.auth(), params={"filters": "invalid"}).status_code, 409)
        self.assertEqual(self.client.get("/api/runs/absent/executive", headers=self.auth()).status_code, 404)

    def test_viewer_can_read_owned_and_admin_can_read_across_owners(self):
        current = self.make_run()
        path = f"/api/runs/{current['id']}/executive"
        for headers in (self.auth(role="viewer"), self.auth("ops", "admin")):
            response = self.client.get(path, headers=headers)
            self.assertEqual(response.status_code, 200, response.text)

    def test_api_invalid_filters_return_localized_422_not_internal_errors(self):
        current = self.make_run()
        path = f"/api/runs/{current['id']}/executive"
        for filters in ("{}", '["bad"]', '[{"column":"absent","op":"eq","value":1}]'):
            response = self.client.get(path, headers=self.auth(), params={"filters": filters, "language": "ar"})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertIn("errors", response.json()["detail"])
            self.assertNotIn("Traceback", response.text)

    def test_maintenance_batch_cards_survive_real_run_serialization(self):
        current = self.make_run(profile="maintenance")
        self.assertEqual(len(current["models"]), 2)
        self.assertTrue(all(c["kind"] == "maintenance_risk" and c["fitted"] is False for c in current["models"]))
        response = self.client.get(f"/api/runs/{current['id']}/executive", headers=self.auth(), params={"language": "ar"})
        self.assertEqual(response.status_code, 200, response.text)
        models = response.json()["models"]
        self.assertEqual(len(models), 2)
        self.assertTrue(all(c["scope"] == "whole_run" and "metric" not in c for c in models))


if __name__ == "__main__":
    unittest.main()
