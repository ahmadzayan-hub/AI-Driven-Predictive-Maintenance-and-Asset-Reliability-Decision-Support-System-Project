"""The browser policy covers every serving path without relaxing scripts."""
import base64
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.responses import Response
    from fastapi.testclient import TestClient
except ImportError:  # CLI-only environments can still discover the core suite.
    FASTAPI_AVAILABLE = False
else:
    from server.app import (API_CONTENT_POLICY, PREPAINT_SCRIPT_HASH,
                            application_content_policy, create_app)
    FASTAPI_AVAILABLE = True
from server.executive_export import CONTENT_POLICY
from tests.support import closing

ROOT = Path(__file__).resolve().parent.parent


def directives(policy):
    return {part.split()[0]: part.split()[1:]
            for part in policy.split(";") if part.strip()}


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class ContentPolicyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.dist = root / "dist"
        (self.dist / "assets").mkdir(parents=True)
        (self.dist / "index.html").write_text("<!doctype html><title>Shell</title>", encoding="utf-8")
        (self.dist / "sw.js").write_text("self.addEventListener('fetch', () => {})", encoding="utf-8")
        (self.dist / "assets" / "app.js").write_text("export const app = true", encoding="utf-8")
        self.config = root / "config.json"
        self.config.write_text(json.dumps({"database_file": str(root / "test.db"),
            "memory_file": str(root / "memory.json"), "vault_dir": str(root / "vault")}), encoding="utf-8")
        self.app = closing(self, create_app(self.config, env={}, dist_dir=self.dist))
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_shell_assets_service_worker_and_miyaar_routes_have_the_shell_policy(self):
        for path in ("/", "/runs", "/?design=miyaar", "/sw.js", "/assets/app.js"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-security-policy"], application_content_policy({}))
        policy = directives(application_content_policy({}))
        self.assertEqual(policy["script-src"], ["'self'", f"'{PREPAINT_SCRIPT_HASH}'"])
        self.assertEqual(policy["script-src-attr"], ["'none'"])
        self.assertEqual(policy["connect-src"], ["'self'"])
        self.assertEqual(policy["worker-src"], ["'self'"])
        self.assertEqual(policy["media-src"], ["'self'", "blob:"])
        self.assertEqual(policy["font-src"], ["'self'"])
        self.assertEqual(policy["frame-ancestors"], ["'none'"])

    def test_prepaint_hash_matches_the_fixed_source_and_built_bytes(self):
        for path in (ROOT / "frontend/index.html", ROOT / "frontend/dist/index.html"):
            if not path.exists():
                continue  # Python checks can precede a frontend build.
            with self.subTest(path=path.name):
                scripts = re.findall(r"<script>(.*?)</script>", path.read_text(encoding="utf-8"), re.S)
                self.assertEqual(len(scripts), 1)
                actual = "sha256-" + base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
                self.assertEqual(actual, PREPAINT_SCRIPT_HASH,
                                 "Changing prepaint code requires a reviewed policy hash update")

    def test_configured_auth_and_api_origins_are_exact_and_never_credentials(self):
        policy = application_content_policy({
            "SUPABASE_URL": "https://auth.example.invalid/provider",
            "VITE_API_BASE": "http://127.0.0.1:8999/api-proxy/",
            "OLLAMA_HOST": "http://127.0.0.1:11434",
        })
        self.assertEqual(directives(policy)["connect-src"],
                         ["'self'", "http://127.0.0.1:8999", "https://auth.example.invalid"])
        self.assertNotIn("11434", policy)
        self.assertNotIn("/provider", policy)
        for bad in ("https://host.invalid;script-src *", "https://user:secret@host.invalid",
                    "https://*.invalid", "https://host.invalid\r\nX-Evil: true", "javascript:alert(1)"):
            with self.subTest(value=bad):
                self.assertEqual(directives(application_content_policy({"SUPABASE_URL": bad}))["connect-src"], ["'self'"])

    def test_api_success_validation_missing_and_unexpected_errors_deny_subresources(self):
        @self.app.get("/api/synthetic-error")
        def synthetic_error():
            raise RuntimeError("synthetic private details")
        self.app.router.routes.insert(0, self.app.router.routes.pop())
        responses = [self.client.get("/api/health"), self.client.get("/api/missing"),
                     self.client.post("/api/runs", json={}), self.client.get("/api/synthetic-error")]
        self.assertEqual([response.status_code for response in responses], [200, 404, 422, 500])
        for response in responses:
            self.assertEqual(response.headers["content-security-policy"], API_CONTENT_POLICY)
            self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertNotIn("synthetic private details", responses[-1].text)

    def test_unauthenticated_responses_also_get_the_api_policy(self):
        app = closing(self, create_app(self.config, env={"AGENTIC_OS_JWT_SECRET": "synthetic-policy-secret-not-a-real-key", "SUPABASE_URL": "https://test.supabase.invalid"}, dist_dir=self.dist))
        response = TestClient(app).get("/api/runs")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["content-security-policy"], API_CONTENT_POLICY)

    def test_export_document_policy_is_not_replaced_by_api_or_shell_policy(self):
        @self.app.get("/api/synthetic-export")
        def synthetic_export():
            return Response("<!doctype html><style>body{color:navy}</style>",
                            media_type="text/html", headers={"Content-Security-Policy": CONTENT_POLICY})
        self.app.router.routes.insert(0, self.app.router.routes.pop())
        response = self.client.get("/api/synthetic-export")
        self.assertEqual(response.headers["content-security-policy"], CONTENT_POLICY)

    def test_swagger_and_redoc_remain_disabled_without_cdn_exceptions(self):
        self.assertIsNone(self.app.docs_url)
        self.assertIsNone(self.app.redoc_url)
        self.assertIsNone(self.app.openapi_url)
        for path in ("/docs", "/redoc", "/openapi.json"):
            response = self.client.get(path)
            self.assertEqual(response.text, "<!doctype html><title>Shell</title>")
            self.assertNotIn("cdn", response.headers["content-security-policy"])

    def test_vercel_static_policy_matches_shell_rules_and_does_not_match_api_exports(self):
        deploy = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        rules = [(rule["source"], header["value"]) for rule in deploy["headers"]
                 for header in rule["headers"] if header["key"] == "Content-Security-Policy"]
        self.assertEqual(len(rules), 1)
        pattern, policy = rules[0]
        for path in ("/", "/api", "/runs", "/sw.js", "/assets/app.js"):
            self.assertIsNotNone(re.fullmatch(pattern, path))
        for path in ("/api/health", "/api/runs/x/executive/export"):
            self.assertIsNone(re.fullmatch(pattern, path))
        expected = directives(application_content_policy({}))
        expected["connect-src"] = ["'self'", "https://*.supabase.co"]
        self.assertEqual(directives(policy), expected)


if __name__ == "__main__":
    unittest.main()
