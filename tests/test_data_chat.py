"""Synthetic owned data, real session API, no training or model invocation."""
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from server.app import create_app, Session
from server.data_chat import DataChat, DataQueryIn, question_metrics
from server.maintenance import kpis
from tests.support import closing, scoped_token as issue_local_test_token
from tests.test_executive import SECRET

ROWS = [
    {"Record_ID": "r1", "Asset_ID": "reused", "Asset_Class": "Railway Signaling", "Asset_Age_Years": 10,
     "Maintenance_Cost_USD": 120, "Production_Loss_USD": 600, "Failure_Count": 1,
     "Operating_Hours": 50, "Planned_Operating_Hours": 100, "Downtime_Hours": 10},
    {"Record_ID": "r2", "Asset_ID": "reused", "Asset_Class": "Railway Signalling", "Asset_Age_Years": 20,
     "Maintenance_Cost_USD": 300, "Production_Loss_USD": 0, "Failure_Count": 0,
     "Operating_Hours": 270, "Planned_Operating_Hours": 300, "Downtime_Hours": 0},
    {"Record_ID": "r3", "Asset_ID": "reused", "Asset_Class": "Pump", "Asset_Age_Years": 40,
     "Maintenance_Cost_USD": 80, "Production_Loss_USD": 200, "Failure_Count": 1,
     "Operating_Hours": 80, "Planned_Operating_Hours": 100, "Downtime_Hours": 0},
]


class DataChatApiTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.config = root / "config.json"
        self.config.write_text(json.dumps({"agent_name": "Synthetic data chat", "database_file": str(root / "a.db"),
            "memory_file": str(root / "memory.json"), "vault_dir": str(root / "vault")}), encoding="utf-8")
        self.env = {"AGENTIC_OS_ENV": "production", "AGENTIC_OS_JWT_SECRET": SECRET,
                    "SUPABASE_URL": "https://test.supabase.invalid"}
        self.app = closing(self, create_app(self.config, env=self.env))
        self.client = TestClient(self.app)
        self.app.state.gateway.ask_json = Mock(side_effect=TimeoutError("synthetic timeout; must not be called"))
        created = self.client.post("/api/sessions", headers=self.auth(), json={"language": "en"})
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["data_chat_labels"]["title"], "Data for this chat")
        self.sid = created.json()["session_id"]
        self.run = self.make_run()

    def auth(self, owner="alice", role="analyst"):
        return {"Authorization": "Bearer " + issue_local_test_token(SECRET, subject=owner, role=role)}

    def make_run(self, owner="alice", rows=None):
        rows = copy.deepcopy(ROWS if rows is None else rows)
        output = io.StringIO()
        writer = csv.DictWriter(output, list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
        response = self.client.post("/api/runs", headers=self.auth(owner),
            json={"goal": "Synthetic aggregate test", "dataset_name": "synthetic.csv", "dataset_text": output.getvalue()})
        self.assertEqual(response.status_code, 201, response.text)
        run = response.json()
        store = self.app.state.store
        outputs = {"cleaner": {"rows": rows}, "profiler": {"numeric_columns": list(rows[0])[3:]}}
        for task in store.get_tasks(run["id"]):
            if task["role"] in outputs:
                store.update("tasks", task["id"], {"state": "succeeded", "result_json": json.dumps({"output": outputs[task["role"]]})})
        store.update("runs", run["id"], {"state": "completed"})
        return store.get_run(run["id"])

    def bind(self, run=None, filters=None):
        response = self.client.put(f"/api/sessions/{self.sid}/data-context", headers=self.auth(),
                                   json={"run_id": (run or self.run)["id"], "filters": filters or []})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data_context"]

    def ask(self, text, data_query=None):
        body = {"text": text}
        if data_query is not None:
            body["data_query"] = data_query
        response = self.client.post(f"/api/sessions/{self.sid}/messages", headers=self.auth(), json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["reply"]

    def test_no_selection_or_multiple_reports_never_uses_latest_or_memory(self):
        self.make_run()
        for text in ("What do you know about my data?", "ماذا تتذكر عن البيانات؟", "how much railway signaling age ?"):
            reply = self.ask(text)
            self.assertEqual((reply["action"], reply["why"]), ("data_query", "selection_required"))
        choices = self.client.get(f"/api/sessions/{self.sid}/data-context", headers=self.auth()).json()
        self.assertIsNone(choices["selected"])
        self.assertEqual(len(choices["choices"]), 2)
        self.app.state.gateway.ask_json.assert_not_called()

    def test_exact_screenshot_and_arabic_queries_compute_record_age_with_citations(self):
        selected = self.bind()
        for text in ("how much railway signaling age ?", "how much railway signalling age?", "كم عمر إشارات السكك الحديدية؟"):
            reply = self.ask(text)
            self.assertEqual((reply["action"], reply["source"]), ("data_query", "rules"))
            self.assertNotIn("provider", reply)
            result = reply["result"]
            age = result["measures"][0]
            self.assertEqual((age["value"], age["minimum"], age["maximum"], age["records"]), (15, 10, 20, 2))
            self.assertEqual(result["source_sha256"], selected["source_sha256"])
            self.assertEqual(result["filters"], [{"column": "Asset_Class", "op": "in", "values": ["Railway Signaling", "Railway Signalling"]}])
            self.assertIn("not unique physical assets", age["grain"])
            self.assertIn("Asset_Age_Years", reply["text"])
            self.assertIsNone(result["llm_explanation"])
        self.app.state.gateway.ask_json.assert_not_called()

    def test_cost_failure_and_availability_reuse_authoritative_fleet_register(self):
        self.bind()
        questions = [("What is total maintenance cost?", 500), ("كم تكلفة الصيانة؟", 500),
                     ("How many failures?", 2), ("ما هي الإتاحة؟", 98)]
        for text, value in questions:
            reply = self.ask(text)
            self.assertEqual(reply["result"]["measures"][0]["value"], value)
            self.assertIsNone(reply["result"]["currency"])
        expected = kpis.REGISTER["availability"].compute(ROWS)
        actual = self.ask("availability")["result"]["measures"][0]
        for key in ("formula", "value", "numerator", "denominator", "records"):
            self.assertEqual(actual[key], expected[key])

    def test_filters_and_selection_survive_session_reload(self):
        filters = [{"column": "Asset_Class", "op": "in", "values": ["Pump"]}]
        context = self.bind(filters=filters)
        stored = self.app.state.store.get_session(self.sid)
        restored = Session(json.loads(self.config.read_text()), row=stored)
        self.assertEqual(restored.data_context, context)
        self.assertNotIn("_data_context", restored.agent.preferences)
        self.assertEqual(json.loads(restored.to_row()["preferences_json"])["_data_context"], context)
        reply = self.ask("total maintenance cost")
        self.assertEqual(reply["result"]["measures"][0]["value"], 80)
        self.assertEqual(reply["result"]["filters"], filters)

    def test_wrong_owner_and_admin_inspection_cannot_bind_foreign_data(self):
        foreign = self.make_run("bob")
        path = f"/api/sessions/{self.sid}/data-context"
        for headers, run in ((self.auth(), foreign), (self.auth("root", "admin"), self.run), (self.auth("bob"), self.run)):
            response = self.client.put(path, headers=headers, json={"run_id": run["id"]})
            self.assertIn(response.status_code, (403, 404))
        self.bind()
        self.app.state.store.update("runs", self.run["id"], {"owner": "bob"})
        self.assertEqual(self.ask("maintenance cost")["why"], "unavailable")

    def test_changed_analysis_and_deleted_source_abstain(self):
        self.bind()
        task = next(t for t in self.app.state.store.get_tasks(self.run["id"]) if t["role"] == "cleaner")
        changed = json.loads(task["result_json"])
        changed["output"]["rows"][0]["Maintenance_Cost_USD"] = 999
        self.app.state.store.update("tasks", task["id"], {"result_json": json.dumps(changed)})
        self.assertEqual(self.ask("maintenance cost")["why"], "stale")
        # Rebinding uses the new content hash even if task timestamp did not move.
        self.bind()
        self.assertEqual(self.ask("maintenance cost")["result"]["measures"][0]["value"], 1379)
        with patch.object(self.app.state.store, "get_dataset", return_value=None):
            self.assertEqual(self.ask("maintenance cost")["why"], "unavailable")

    def test_source_hash_change_and_mid_query_revocation_refuse_answer(self):
        self.bind()
        service = self.app.state.assistant.data_chat
        original = service._source
        calls = 0
        def changed(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.app.state.store.update("runs", self.run["id"], {"owner": "bob"})
            return original(*args)
        with patch.object(service, "_source", side_effect=changed):
            self.assertEqual(self.ask("maintenance cost")["why"], "unavailable")

    def test_changed_canonical_bytes_and_cleared_selection_refuse_reuse(self):
        self.bind()
        dataset = self.app.state.store.get_dataset(self.run["dataset_id"])
        self.app.state.store.update("datasets", dataset["id"], {"content": dataset["content"] + "\n"})
        self.assertEqual(self.ask("maintenance cost")["why"], "stale")
        response = self.client.put(f"/api/sessions/{self.sid}/data-context", headers=self.auth(), json={"run_id": None})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data_context"])
        self.assertEqual(self.ask("maintenance cost")["why"], "selection_required")

    def test_malformed_tool_and_filter_requests_fail_without_model_or_code(self):
        self.bind()
        for request in ({"metrics": ["sql"], "sql": "SELECT 1"}, {"metrics": ["maintenance_cost"], "code": "print(1)"},
                        {"metrics": []}, {"metrics": ["maintenance_cost"] * 7}, {"metrics": ["availability"], "asset_class": "any"}):
            response = self.client.post(f"/api/sessions/{self.sid}/messages", headers=self.auth(),
                                       json={"text": "data question", "data_query": request})
            self.assertEqual(response.status_code, 422)
        response = self.client.put(f"/api/sessions/{self.sid}/data-context", headers=self.auth(),
                                   json={"run_id": self.run["id"], "filters": [{"column": "Asset_Class", "op": "in", "values": ["Pump"], "sql": "anything"}]})
        self.assertEqual(response.status_code, 422)
        self.app.state.gateway.ask_json.assert_not_called()

    def test_unsupported_scope_prediction_and_broad_questions_do_not_fabricate(self):
        self.bind()
        for text in ("What do you remember about my data?", "predict availability next year", "maintenance cost by site", "availability during 2026", "maintenance cost for pumps", "asset age for pumps"):
            self.assertEqual(self.ask(text)["why"], "unsupported_question")
        self.app.state.gateway.ask_json.assert_not_called()

    def test_empty_missing_and_undefined_populations_stay_explicit(self):
        self.bind(filters=[{"column": "Asset_Class", "op": "in", "values": ["Absent"]}])
        answer = self.ask("availability")["result"]["measures"][0]
        self.assertIsNone(answer["value"])
        self.assertEqual(answer["records"], 0)
        self.bind()
        result = self.ask("mtbf", {"metrics": ["mtbf", "first_time_fix"]})["result"]
        self.assertEqual(result["measures"][0]["value"], 200)
        self.assertIsNone(result["measures"][1]["value"])

    def test_data_answers_do_not_enter_later_model_context(self):
        self.bind()
        self.ask("total maintenance cost")
        session = Session(json.loads(self.config.read_text()), row=self.app.state.store.get_session(self.sid))
        context = self.app.state.assistant._context(session)
        self.assertNotIn("deterministic_kpi_register", context)
        self.assertNotIn("SHA-256:", context)
        self.assertNotIn("sum(Maintenance_Cost_USD)", context)


if __name__ == "__main__":
    unittest.main()
