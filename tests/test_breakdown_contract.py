"""A grouping request must be honored or refused before run admission."""

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import closing

try:
    from fastapi.testclient import TestClient
    from server.app import create_app
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


SYNTHETIC_CSV = (
    "month,team,site,sales\n"
    "2026-01,Alpha,North,10\n2026-01,Beta,South,20\n"
    "2026-02,Alpha,South,30\n2026-02,Beta,North,40\n"
    "2026-03,Alpha,North,50\n2026-03,Beta,South,60\n"
    "2026-04,Alpha,South,70\n2026-04,Beta,North,80\n"
)


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class BreakdownContractTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "Synthetic breakdown contract",
            "database_file": str(root / "test.db"),
            "memory_file": str(root / "memory.json"),
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        self.app = closing(self, create_app(config, env={
            "AGENTIC_OS_QUOTA_RUNS_PER_DAY": "1",
        }))
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def upload(self):
        response = self.client.post("/api/datasets?name=synthetic.csv",
                                    content=SYNTHETIC_CSV.encode("utf-8"))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["dataset"]["id"]

    def usage(self):
        response = self.client.get("/api/usage")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_single_dataset_override_is_localized_and_refused_before_any_write(self):
        dataset_id = self.upload()
        before = self.usage()
        paths = ({}, {"dataset_text": SYNTHETIC_CSV, "dataset_name": "inline.csv"},
                 {"dataset_id": dataset_id})
        for language in ("en", "ar"):
            for source in paths:
                for joins in (None, []):
                    with self.subTest(language=language, source=list(source), joins=joins):
                        response = self.client.post("/api/runs", json={
                            "goal": "Synthetic site comparison", "language": language,
                            "breakdown": "site", "joins": joins, **source,
                        })
                        self.assertEqual(response.status_code, 422, response.text)
                        self.assertIn("تعيين الأعمدة المحفوظ" if language == "ar"
                                      else "saved column mapping", response.json()["detail"])
                        self.assertEqual(self.usage(), before)
                        self.assertEqual(self.app.state.store.list_runs(), [])
                        self.assertEqual(self.app.state.store._exec("SELECT * FROM tasks"), [])

        # Refusals have not spent the one daily run. Normal admission still
        # succeeds once, and the next valid request reaches the real quota.
        body = {"goal": "Synthetic site comparison", "dataset_id": dataset_id}
        self.assertEqual(self.client.post("/api/runs", json=body).status_code, 201)
        self.assertEqual(self.client.post("/api/runs", json=body).status_code, 429)
        self.assertEqual(self.usage()["runs_today"]["used"], 1)

    def test_blank_optional_breakdown_keeps_single_dataset_admission(self):
        response = self.client.post("/api/runs", json={
            "goal": "Synthetic blank option", "dataset_text": SYNTHETIC_CSV,
            "breakdown": "  ", "joins": [],
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotIn("merge", [task["role"] for task in response.json()["tasks"]])

    def test_single_dataset_mapping_still_controls_and_snapshots_the_grouping(self):
        dataset_id = self.upload()
        mapping = {
            "roles": {"month": "date", "team": "dimension",
                      "site": "dimension", "sales": "measure"},
            "measure": "sales", "dimension": "site",
            "date_order": "auto", "grain": "month",
        }
        response = self.client.put(f"/api/datasets/{dataset_id}/mapping", json=mapping)
        self.assertEqual(response.status_code, 200, response.text)
        response = self.client.post("/api/runs", json={
            "goal": "Synthetic mapped site comparison", "dataset_id": dataset_id,
        })
        self.assertEqual(response.status_code, 201, response.text)
        run = response.json()
        response = self.client.put(f"/api/datasets/{dataset_id}/mapping",
                                   json={**mapping, "dimension": "team"})
        self.assertEqual(response.status_code, 200, response.text)
        for _ in range(80):
            response = self.client.post(f"/api/runs/{run['id']}/advance")
            self.assertEqual(response.status_code, 200, response.text)
            run = response.json()
            if run["state"] not in ("queued", "running"):
                break
        self.assertEqual(run["state"], "awaiting_approval", run.get("error"))
        self.assertNotIn("merge", [task["role"] for task in run["tasks"]])
        task = next(task for task in self.app.state.store.get_tasks(run["id"])
                    if task["role"] == "preparer")
        prepared = json.loads(task["result_json"])["output"]
        self.assertEqual(prepared["group_col"], "site")
        self.assertEqual(prepared["groups"], {"North": 180.0, "South": 180.0})


if __name__ == "__main__":
    unittest.main()
