"""The sixth P2 slice (assessment U10, U11, U14, U15, U16, U18, U19): the
server-side pieces. The interface changes are covered by the frontend
unit tests and the end-to-end specs they name."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from server.app import create_app
from tests.support import closing

ROOT = Path(__file__).resolve().parent.parent


class AssetEvidenceEndpointTest(unittest.TestCase):
    """U10: one answer carries the newest run with a succeeded asset screen."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Slice Six",
                                      "database_file": str(root / "agentic.db"),
                                      "memory_file": str(root / "memory.json"),
                                      "vault_dir": str(root / "vault")}), encoding="utf-8")
        self.app = create_app(config)
        self.client = TestClient(closing(self, self.app), raise_server_exceptions=False)

    def test_no_run_means_an_empty_answer_with_its_scope(self):
        response = self.client.get("/api/assets/evidence")
        self.assertEqual(response.status_code, 200)
        answer = response.json()
        self.assertIsNone(answer["run"])
        self.assertEqual(answer["scope"], "latest_completed_maintenance_stage")
        self.assertTrue(answer["prepared_at"])

    def test_a_run_with_a_succeeded_screen_is_returned_in_full(self):
        created = self.client.post("/api/runs", json={"goal": "Audit test run"}).json()
        store = self.app.state.store
        # A generic run has no asset screen: nothing to report yet.
        self.assertIsNone(self.client.get("/api/assets/evidence").json()["run"])
        tasks = store.get_tasks(created["id"])
        self.assertTrue(tasks)
        store._exec("UPDATE tasks SET role = ?, state = ? WHERE id = ?",
                    ("rail_asset_manager", "succeeded", tasks[0]["id"]))
        answer = self.client.get("/api/assets/evidence").json()
        self.assertEqual(answer["run"]["id"], created["id"])
        self.assertIn("tasks", answer["run"])
        self.assertEqual(answer["scope"], "latest_completed_maintenance_stage")

    def test_the_endpoint_is_registered(self):
        self.assertIn("/api/assets/evidence", {getattr(r, "path", None) for r in self.app.routes})


class InterfaceContractTest(unittest.TestCase):
    """U19 and U14: what the build ships and what the navigation says."""

    def test_the_original_dubai_face_is_local_unmodified_and_loaded_once(self):
        folder = ROOT / "frontend" / "src" / "shared" / "fonts"
        css = (folder / "fonts.css").read_text(encoding="utf-8")
        original = ROOT / "server" / "assets" / "fonts" / "Dubai-Regular.ttf"
        self.assertEqual(len(original.read_bytes()), 139928)
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),
                         "e7b232e0d3a6699f9d9023c0b49a9288ead97a33bc5175b9d1619c09f8672298")
        self.assertEqual(css.count("url(../../../../server/assets/fonts/Dubai-Regular.ttf)"), 1)
        self.assertEqual(css.count("@font-face"), 1)
        self.assertIn("font-display: swap", css)
        self.assertNotIn("url(http", css)
        self.assertNotIn(".woff", css)
        self.assertTrue((original.parent / "DUBAI-FONT-NOTICE.md").exists())
        main = (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
        self.assertNotIn("from '@fontsource", main)
        self.assertNotIn("import '@fontsource", main)
        self.assertIn("./shared/fonts/fonts.css", main)

    def test_the_navigation_uses_one_noun_per_destination(self):
        en = (ROOT / "frontend" / "src" / "i18n" / "en.ts").read_text(encoding="utf-8")
        self.assertIn('"nav.runs": "Analyses"', en)
        self.assertIn('"nav.operations": "Administration"', en)

    def test_every_upload_call_to_action_reaches_the_datasets_flow(self):
        app = (ROOT / "frontend" / "src" / "app" / "App.tsx").read_text(encoding="utf-8")
        self.assertNotIn("kind: 'upload', profile: 'maintenance'", app)
        for path in ("features/dashboard/DashboardView.tsx", "features/maintenance/MaintenancePreview.tsx"):
            with self.subTest(path=path):
                text = (ROOT / "frontend" / "src" / path).read_text(encoding="utf-8")
                self.assertNotIn("runs?source=upload", text)
                self.assertIn("#/datasets", text)


if __name__ == "__main__":
    unittest.main()
