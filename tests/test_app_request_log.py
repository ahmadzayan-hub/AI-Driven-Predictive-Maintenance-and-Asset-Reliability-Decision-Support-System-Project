"""Request ids and one JSON log line per request (assessment finding B10).

The line carries the id, method, path, status, duration and a hashed
subject. It never carries the token, the body, the query string or the
raw subject.
"""

import json
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    from server.app import create_app, request_id_for, subject_hash
    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - CLI-only environments
    FASTAPI_AVAILABLE = False

from tests.support import closing, scoped_token

SECRET = "request-log-test-secret-not-used-anywhere-else"
LOGGER = "agentic_os.requests"


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class RequestLogTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "Log Test",
            "database_file": str(root / "agentic.db"),
            "memory_file": str(root / "memory.json"),
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        self.app = closing(self, create_app(config, env={
            "AGENTIC_OS_JWT_SECRET": SECRET,
            "SUPABASE_URL": "https://test.supabase.invalid",
            "AGENTIC_OS_ENV": "production"}))
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def lines(self, logs):
        return [json.loads(record.getMessage()) for record in logs.records]

    def test_an_incoming_safe_id_is_echoed_and_logged(self):
        with self.assertLogs(LOGGER, level="INFO") as logs:
            response = self.client.get("/api/health", headers={"X-Request-ID": "trace-abc.123"})
        self.assertEqual(response.headers["X-Request-ID"], "trace-abc.123")
        (line,) = self.lines(logs)
        self.assertEqual(line["request_id"], "trace-abc.123")
        self.assertEqual(set(line), {"request_id", "method", "path", "status",
                                     "duration_ms", "subject"})
        self.assertEqual((line["method"], line["path"], line["status"], line["subject"]),
                         ("GET", "/api/health", 200, "anonymous"))
        self.assertGreaterEqual(line["duration_ms"], 0)

    def test_a_missing_or_unsafe_id_is_replaced_by_a_generated_one(self):
        with self.assertLogs(LOGGER, level="INFO") as logs:
            plain = self.client.get("/api/health")
            unsafe = self.client.get("/api/health", headers={"X-Request-ID": "bad id\twith space"})
            long = self.client.get("/api/health", headers={"X-Request-ID": "a" * 65})
        ids = [r.headers["X-Request-ID"] for r in (plain, unsafe, long)]
        self.assertEqual(len(set(ids)), 3)
        for value in ids:
            self.assertEqual(len(value), 32)
            self.assertEqual(value, request_id_for(value))
        self.assertEqual([line["request_id"] for line in self.lines(logs)], ids)

    def test_the_query_string_and_the_token_never_reach_the_log(self):
        token = scoped_token(SECRET, "person@example.com", role="admin")
        with self.assertLogs(LOGGER, level="INFO") as logs:
            response = self.client.get("/api/runs?state=secretfilter",
                                       headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        (line,) = self.lines(logs)
        self.assertEqual(line["path"], "/api/runs")
        self.assertEqual(line["subject"], subject_hash("person@example.com"))
        self.assertEqual(len(line["subject"]), 12)
        raw = logs.output[0]
        for forbidden in (token, "person@example.com", "secretfilter", "Bearer"):
            self.assertNotIn(forbidden, raw)

    def test_a_bad_token_is_logged_as_anonymous_with_its_status(self):
        with self.assertLogs(LOGGER, level="INFO") as logs:
            response = self.client.get("/api/runs", headers={"Authorization": "Bearer not-a-token"})
        self.assertEqual(response.status_code, 401)
        (line,) = self.lines(logs)
        self.assertEqual((line["status"], line["subject"]), (401, "anonymous"))
        self.assertNotIn("not-a-token", logs.output[0])

    def test_an_unexpected_error_still_carries_the_request_id(self):
        from fastapi.routing import APIRoute

        def explode():
            raise RuntimeError("boom")

        # Ahead of the interface's catch-all route, when a build is present.
        self.app.router.routes.insert(0, APIRoute("/api/explode", explode, methods=["GET"]))

        with self.assertLogs(LOGGER, level="INFO") as logs:
            response = self.client.get("/api/explode", headers={"X-Request-ID": "err-1"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers["X-Request-ID"], "err-1")
        self.assertNotIn("boom", response.text)
        (line,) = self.lines(logs)
        self.assertEqual((line["request_id"], line["status"]), ("err-1", 500))


if __name__ == "__main__":
    unittest.main()
