"""Real API transport and temporary stores; all model calls are mocked."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from server.app import create_app
from server.local_resources import MIN_FREE_BYTES
from tests.support import closing


class ChatAvailabilityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.config = root / "config.json"
        self.config.write_text(json.dumps({
            "agent_name": "Synthetic chat test", "version": "1",
            "preferences": {"language": "English"},
            "memory_file": str(root / "memory.json"),
            "database_file": str(root / "test.db"), "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        memory = patch("server.assistant_availability.free_memory_bytes", return_value=MIN_FREE_BYTES)
        self.memory = memory.start()
        self.addCleanup(memory.stop)

    def client(self, enabled=False):
        env = {"OLLAMA_MODEL": "synthetic-model", "OLLAMA_HOST": "http://127.0.0.1:11434"} if enabled else {}
        app = closing(self, create_app(self.config, env=env))
        self.model = app.state.gateway.ask_json = Mock(return_value=json.dumps({
            "action": "chat", "arguments": {}, "reply": "Synthetic model response."}))
        self.app = app
        return TestClient(app)

    def session(self, client, language="en"):
        response = client.post("/api/sessions", json={"language": language})
        self.assertEqual(response.status_code, 201)
        return response.json()

    def send(self, client, sid, question="What is preventive maintenance?"):
        response = client.post(f"/api/sessions/{sid}/messages", json={"text": question})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_unconfigured_status_and_answer_are_explicit_in_both_languages(self):
        client = self.client()
        for language, expected in (("en", "not enabled"), ("ar", "غير مفعّل")):
            state = self.session(client, language)
            self.assertEqual(state["assistant_status"]["code"], "not_configured")
            self.assertFalse(state["assistant_status"]["inference_verified"])
            reply = self.send(client, state["session_id"])["reply"]
            self.assertIn(expected, reply["text"])
            self.assertEqual(reply["source"], "rules")
            self.assertEqual(reply["why"], "not_configured")
        self.model.assert_not_called()

    def test_configured_is_not_verified_until_a_real_message_response(self):
        client = self.client(True)
        state = self.session(client)
        self.assertEqual(state["assistant_status"]["code"], "configured")
        self.assertFalse(state["assistant_status"]["inference_verified"])
        self.model.assert_not_called()
        reply = self.send(client, state["session_id"])["reply"]
        self.assertEqual((reply["source"], reply["provider"], reply["text"]),
                         ("model", "ollama", "Synthetic model response."))
        self.model.assert_called_once()

    def test_low_unknown_and_invalid_memory_never_invoke_model(self):
        client = self.client(True)
        sid = self.session(client)["session_id"]
        for value in (MIN_FREE_BYTES - 1, 0, None, True, float("nan"), "unknown"):
            with self.subTest(value=value):
                self.memory.return_value = value
                body = self.send(client, sid)
                self.assertEqual(body["reply"]["source"], "rules")
                self.assertIn(body["reply"]["why"], ("low_memory", "memory_unavailable"))
                self.assertEqual(body["state"]["assistant_status"]["code"], body["reply"]["why"])
        self.model.assert_not_called()

    def test_manual_retry_after_memory_recovers_does_not_need_a_new_session(self):
        client = self.client(True)
        sid = self.session(client)["session_id"]
        self.memory.return_value = 0
        self.assertEqual(self.send(client, sid)["reply"]["why"], "low_memory")
        self.memory.return_value = MIN_FREE_BYTES
        body = self.send(client, sid)
        self.assertEqual(body["reply"]["source"], "model")
        self.assertEqual(len(body["state"]["transcript"]), 4)
        self.model.assert_called_once()

    def test_provider_failure_is_bounded_redacted_and_rules_labelled(self):
        client = self.client(True)
        sid = self.session(client)["session_id"]
        for answer in (None, '{"action":"chat","reply":""}', '{"action":"delete_everything"}'):
            self.model.return_value = answer
            self.model.reset_mock()
            reply = self.send(client, sid)["reply"]
            self.assertEqual(reply["source"], "rules")
            self.assertIn(reply["why"], ("model_unavailable", "invalid_model_output"))
            self.model.assert_called_once()
        self.model.side_effect = RuntimeError("SECRET_PROVIDER_SENTINEL")
        body = self.send(client, sid)
        self.assertEqual(body["reply"]["why"], "model_unavailable")
        self.assertNotIn("SECRET_PROVIDER_SENTINEL", json.dumps(body))

    def test_workspace_commands_remain_available_when_local_model_is_blocked(self):
        client = self.client(True)
        sid = self.session(client)["session_id"]
        self.memory.return_value = 0
        for question in ("/help", "analysis status", "/remember synthetic inspection note"):
            self.send(client, sid, question)
        state = client.get(f"/api/sessions/{sid}").json()
        self.assertIn("synthetic inspection note", state["memory"].values())
        self.model.assert_not_called()

    def test_session_and_workspace_memory_survive_server_recreation(self):
        client = self.client()
        sid = self.session(client)["session_id"]
        before = self.send(client, sid, "/remember synthetic continuity marker")["state"]
        restored_client = self.client()
        response = restored_client.get(f"/api/sessions/{sid}")
        self.assertEqual(response.status_code, 200)
        after = response.json()
        self.assertEqual(before["transcript"], after["transcript"])
        self.assertEqual(before["memory"], after["memory"])
        self.assertEqual(after["assistant_status"]["code"], "not_configured")

    def test_unknown_session_does_not_create_a_replacement_or_call_a_model(self):
        client = self.client(True)
        self.assertEqual(client.post("/api/sessions/missing/messages", json={"text": "Hello"}).status_code, 404)
        self.model.assert_not_called()

    def test_local_runtime_cannot_bypass_memory_guard(self):
        client = self.client(True)
        sid = self.session(client)["session_id"]
        self.app.state.assistant.runtime = Mock()
        self.memory.return_value = 0
        reply = self.send(client, sid)["reply"]
        self.assertEqual(reply["why"], "low_memory")
        self.app.state.assistant.runtime.assert_not_called()
        self.model.assert_not_called()

    def test_model_failure_does_not_turn_negated_report_context_into_a_report_action(self):
        client = self.client(True)
        sid = self.session(client)["session_id"]
        self.model.return_value = None
        reply = self.send(client, sid,
            "What is preventive maintenance? Do not repeat reports or saved memory, and take no workspace actions.")["reply"]
        self.assertEqual(reply["action"], "chat")
        self.assertEqual(reply["source"], "rules")
        self.assertEqual(reply["why"], "model_unavailable")
        self.assertIn("did not return a usable answer", reply["text"])
        self.model.assert_called_once()


if __name__ == "__main__":
    unittest.main()
