"""The view-only public demo: no sign-in, nothing writable, fictional data.

The attacks that matter for an unauthenticated public page: any write at
all, a token that tries to upgrade a visitor, and a demo switched on next
to real accounts.
"""

import json
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient

    from server import demo
    from server.app import create_app
    from server.auth import AuthNotConfigured, build_identity
    from tests.support import closing
    DEPS_AVAILABLE = True
except ImportError:  # pragma: no cover - CLI-only environments
    DEPS_AVAILABLE = False

DEMO = {"AGENTIC_OS_DEMO": "1"}


@unittest.skipUnless(DEPS_AVAILABLE, "fastapi is not installed")
class DemoIdentityTests(unittest.TestCase):
    def test_demo_mode_is_one_read_only_principal(self):
        identity = build_identity(DEMO)
        principal = identity.authenticate(None)
        self.assertEqual(identity.mode, "demo")
        self.assertTrue(principal.can("read"))
        for permission in ("write", "approve", "admin"):
            self.assertFalse(principal.can(permission), permission)

    def test_a_token_does_not_upgrade_a_visitor(self):
        principal = build_identity(DEMO).authenticate("Bearer anything.at.all")
        self.assertEqual(principal.role, "viewer")

    def test_demo_and_a_sign_in_provider_together_refuse_to_start(self):
        for extra in ({"AGENTIC_OS_JWT_SECRET": "x"}, {"SUPABASE_JWT_SECRET": "x"},
                      {"AGENTIC_OS_JWKS_URL": "https://issuer.example/jwks"}):
            with self.assertRaises(AuthNotConfigured):
                build_identity({**DEMO, **extra})

    def test_demo_is_allowed_in_production_because_it_cannot_write(self):
        self.assertEqual(build_identity({**DEMO, "AGENTIC_OS_ENV": "production"}).mode, "demo")

    def test_vercel_without_a_database_or_sign_in_serves_the_demo(self):
        self.assertEqual(build_identity({"VERCEL": "1"}).mode, "demo")

    def test_vercel_keeps_its_configured_mode(self):
        self.assertEqual(build_identity({"VERCEL": "1", "DATABASE_URL": "postgresql://x"}).mode, "local")
        self.assertEqual(build_identity({"VERCEL": "1", "SUPABASE_JWT_SECRET": "x"}).mode, "jwt")
        self.assertEqual(build_identity({"VERCEL": "1", "AGENTIC_OS_DEMO": "0"}).mode, "local")
        self.assertEqual(build_identity({}).mode, "local")

    def test_only_the_value_one_switches_it_on(self):
        self.assertEqual(build_identity({"AGENTIC_OS_DEMO": "true"}).mode, "local")


@unittest.skipUnless(DEPS_AVAILABLE, "fastapi is not installed")
class DemoApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.config_path = root / "config.json"
        self.config_path.write_text(json.dumps({
            "agent_name": "Demo Test",
            "memory_file": str(root / "memory.json"),
            "database_file": str(root / "agentic.db"),
            "vault_dir": str(root / "vault"),
            "stages": ["server.maintenance.governance.MaintenanceGovernance",
                       "server.maintenance.targets.MaintenanceRisk",
                       "server.maintenance.rail_stage.RailAssetManagerStage"],
            "profiles": {"maintenance": ["maintenance_governance", "maintenance_risk",
                                         "rail_asset_manager"]},
        }), encoding="utf-8")
        self.client = self.build()

    def build(self):
        return TestClient(closing(self, create_app(self.config_path, env=DEMO)),
                          raise_server_exceptions=False)

    def test_the_browser_is_told_there_is_no_sign_in(self):
        body = self.client.get("/api/auth/config").json()
        self.assertEqual(body, {"mode": "demo", "flows": []})

    def test_visitors_read_one_fictional_analysis(self):
        runs = self.client.get("/api/runs").json()["runs"]
        self.assertEqual(len(runs), 1)
        run = self.client.get(f"/api/runs/{runs[0]['id']}").json()
        self.assertEqual(run["state"], "awaiting_approval")
        self.assertEqual([t for t in run["tasks"] if t["state"] == "failed"], [])
        datasets = self.client.get("/api/datasets").json()["datasets"]
        self.assertEqual([d["name"] for d in datasets], [demo.DATASET_NAME])
        executive = self.client.get(f"/api/runs/{runs[0]['id']}/executive")
        self.assertEqual(executive.status_code, 200)

    def test_every_write_is_refused(self):
        run_id = self.client.get("/api/runs").json()["runs"][0]["id"]
        dataset_id = self.client.get("/api/datasets").json()["datasets"][0]["id"]
        run = self.client.get(f"/api/runs/{run_id}").json()
        approval = (run.get("approvals") or [{"id": "any"}])[0]["id"]
        writes = [
            ("post", "/api/sessions", {}),
            ("post", "/api/datasets?name=x.csv", {"content": b"a,b\n1,2\n"}),
            ("put", f"/api/datasets/{dataset_id}/mapping", {"json": demo.mapping()}),
            ("delete", f"/api/datasets/{dataset_id}/mapping", {}),
            ("post", "/api/runs", {"json": {"goal": "x", "dataset_id": dataset_id}}),
            ("post", f"/api/runs/{run_id}/advance", {}),
            ("post", f"/api/runs/{run_id}/cancel", {}),
            ("put", f"/api/runs/{run_id}/kpi-policy", {"json": {"rules": []}}),
            ("post", f"/api/runs/{run_id}/approvals/{approval}", {"json": {"decision": "approve"}}),
            ("post", "/api/connectors", {"json": {"name": "x", "url": "https://example.com/a.csv"}}),
        ]
        for method, path, kwargs in writes:
            with self.subTest(path=path):
                response = getattr(self.client, method)(
                    path, headers={"Authorization": "Bearer forged"}, **kwargs)
                self.assertIn(response.status_code, (403, 422), response.text)
                if response.status_code == 422:
                    # A malformed body may be rejected first; the same call
                    # well formed must still be refused.
                    self.fail(f"{path} needs a well-formed body in this test")
        self.assertEqual(len(self.client.get("/api/runs").json()["runs"]), 1)

    def test_a_restart_on_the_same_store_does_not_seed_again(self):
        self.build()
        self.assertEqual(len(self.build().get("/api/runs").json()["runs"]), 1)

    def test_a_deployment_without_the_maintenance_profile_still_seeds(self):
        config = json.loads(self.config_path.read_text())
        config.pop("stages"), config.pop("profiles")
        config["database_file"] = str(Path(self.temp_dir.name) / "plain.db")
        self.config_path.write_text(json.dumps(config))
        runs = self.build().get("/api/runs").json()["runs"]
        self.assertEqual(len(runs), 1)

    def test_separate_instances_serve_the_same_run(self):
        # Vercel without a shared database: each instance has its own
        # SQLite file. A run id from one must be readable on the other.
        config = json.loads(self.config_path.read_text())
        config["database_file"] = str(Path(self.temp_dir.name) / "second.db")
        config["vault_dir"] = str(Path(self.temp_dir.name) / "second-vault")
        second_path = Path(self.temp_dir.name) / "second.json"
        second_path.write_text(json.dumps(config))
        second = TestClient(closing(self, create_app(second_path, env=DEMO)),
                            raise_server_exceptions=False)
        run_id = self.client.get("/api/runs").json()["runs"][0]["id"]
        self.assertEqual(second.get("/api/runs").json()["runs"][0]["id"], run_id)
        first, other = self.client.get(f"/api/runs/{run_id}").json(), second.get(f"/api/runs/{run_id}").json()
        self.assertEqual([t["id"] for t in other["tasks"]], [t["id"] for t in first["tasks"]])
        self.assertEqual(second.get(f"/api/runs/{run_id}/executive").status_code, 200)

    def test_seeding_leaves_ordinary_ids_random(self):
        engine = self.client.app.state.engine
        self.assertNotEqual(engine.new_id(), engine.new_id())
        self.assertEqual(len(engine.new_id()), 12)

    def test_the_seed_is_the_same_file_every_time(self):
        self.assertEqual(demo.fleet_csv(), demo.fleet_csv())
        self.assertEqual(len(demo.fleet_csv().strip().splitlines()), 241)


if __name__ == "__main__":
    unittest.main()
