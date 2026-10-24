"""Bounded synthetic checks; no live Hermes, web server or model is invoked."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.hermes_mcp import ROOT, build, read_scope
from server.mcp import McpServer


def call(server, name, arguments=None):
    return server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": name, "arguments": arguments or {}}})


def scope_in(root, tools=None):
    return {"scope": "miyaar-local-workspace-v1",
            "database_file": str(root / "synthetic.db"),
            "memory_file": str(root / "synthetic-memory.json"),
            "vault_dir": str(root / "synthetic-vault"),
            "knowledge_dir": str(root / "synthetic-knowledge"),
            "enabled_tools": ["help", "run_status", "explain_report"] if tools is None else tools,
            "language": "en"}


class HermesPackageTestCase(unittest.TestCase):
    def test_preview_is_help_only_and_has_no_storage_or_models(self):
        with build() as server:
            self.assertIsNone(server.assistant.engine)
            self.assertFalse(server.session.agent.memory_persistent)
            self.assertEqual([t["name"] for t in server._dispatch("tools/list", {})["tools"]], ["help"])
            self.assertFalse(call(server, "help")["result"]["isError"])
            for name in ("remember", "recall", "set_preference", "start_run",
                         "run_status", "search_knowledge", "agent_scorecard", "explain_report"):
                with self.subTest(name=name):
                    self.assertTrue(call(server, name)["result"]["isError"])

    def test_direct_calls_cannot_bypass_discovery_filter(self):
        with build() as server, patch.object(server.assistant, "_execute") as execute:
            self.assertTrue(call(server, "remember", {"information": "synthetic"})["result"]["isError"])
            execute.assert_not_called()

    def test_empty_allowlist_denies_everything_and_unknown_names_fail(self):
        empty = McpServer(None, None, allowed_tools=[])
        self.assertEqual(empty._dispatch("tools/list", {})["tools"], [])
        self.assertTrue(call(empty, "help")["result"]["isError"])
        for invalid in (["misspelt"], "help"):
            with self.assertRaises(ValueError):
                McpServer(None, None, allowed_tools=invalid)

    def test_invalid_scope_never_opens_a_default_store(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for key, value in (("scope", ""), ("database_file", "relative.db"),
                               ("database_file", "\\\\example.invalid\\share\\db"),
                               ("enabled_tools", "help"), ("enabled_tools", []),
                               ("database_url", "postgresql://invalid"),
                               ("language", "fr")):
                candidate = scope_in(root)
                candidate[key] = value
                config = root / "scope.json"
                config.write_text(json.dumps(candidate), encoding="utf-8")
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    read_scope(config)
            self.assertFalse((root / "synthetic.db").exists())
            with self.assertRaises(ValueError):
                with build(scope_in(root, ["typo"])):
                    self.fail("unknown tool should fail before opening storage")
            self.assertFalse((root / "synthetic.db").exists())

    def test_other_known_tools_cannot_be_opted_in_before_storage_opens(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "scope.json"
            for name in ("recall", "remember", "set_preference", "start_run",
                         "search_knowledge", "agent_scorecard", "typo"):
                candidate = scope_in(root, ["help", name])
                config.write_text(json.dumps(candidate), encoding="utf-8")
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        read_scope(config)
                    with self.assertRaises(ValueError):
                        with build(candidate):
                            self.fail("unsupported opt-in must fail before storage opens")
                    self.assertFalse((root / "synthetic.db").exists())

    def test_workspace_read_tools_and_startup_side_effects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scope = scope_in(root)
            scope["language"] = "ar"
            memory = root / "synthetic-memory.json"
            memory.write_text('{"memory_1": "SYNTHETIC_MEMORY_SENTINEL"}', encoding="utf-8")
            before = memory.read_bytes()
            config_file = root / "approved-synthetic-scope.json"
            config_file.write_text(json.dumps(scope), encoding="utf-8")
            scope = read_scope(config_file)
            with build(scope) as server:
                # These startup effects exist even without recall/write tools.
                self.assertEqual(server.session.agent.memory["memory_1"], "SYNTHETIC_MEMORY_SENTINEL")
                store = server.assistant.engine.store
                self.assertTrue((root / "synthetic.db").exists())
                self.assertEqual(store._exec("PRAGMA journal_mode")[0]["journal_mode"], "wal")
                self.assertTrue(store._exec("SELECT name FROM sqlite_master WHERE name = 'runs'"))
                # Seed through the test harness, not an exposed MCP write tool.
                server.assistant.engine.create_run("Synthetic sample check", owner="local-owner")
                status = call(server, "run_status")["result"]["content"][0]["text"]
                self.assertIn("Synthetic sample check", status)
                self.assertFalse(call(server, "explain_report")["result"]["isError"])
                with patch.object(server.assistant, "_execute") as execute:
                    for name in ("recall", "remember", "set_preference", "start_run",
                                 "search_knowledge", "agent_scorecard"):
                        self.assertTrue(call(server, name)["result"]["isError"])
                    execute.assert_not_called()
                arabic = call(server, "help")["result"]["content"][0]["text"]
                self.assertTrue(any("\u0600" <= char <= "\u06ff" for char in arabic))
            self.assertEqual(memory.read_bytes(), before)
            self.assertFalse((root / "synthetic-vault").exists())
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "recall"}},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "run_status"}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "search_knowledge"}},
            ]
            completed = subprocess.run(
                [sys.executable, "-I", "-B", "-X", "utf8",
                 str(ROOT / "scripts/hermes_mcp.py"), "--config", str(config_file)],
                input="\n".join(map(json.dumps, messages)) + "\n",
                capture_output=True, text=True, encoding="utf-8", timeout=20, cwd=root)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            responses = [json.loads(line) for line in completed.stdout.splitlines()]
            self.assertEqual({t["name"] for t in responses[0]["result"]["tools"]}, set(scope["enabled_tools"]))
            self.assertTrue(responses[1]["result"]["isError"])
            self.assertNotIn("SYNTHETIC_MEMORY_SENTINEL", completed.stdout + completed.stderr)
            self.assertIn("Synthetic sample check", responses[2]["result"]["content"][0]["text"])
            self.assertTrue(responses[3]["result"]["isError"])

    def test_real_stdio_preview_ignores_ambient_app_and_provider_settings(self):
        with tempfile.TemporaryDirectory(prefix="miyaar path spaces ") as temporary:
            root = Path(temporary)
            sentinel = root / "private-memory.json"
            sentinel.write_text('{"private": "DO_NOT_FORWARD_SYNTHETIC"}', encoding="utf-8")
            config = root / "ambient.json"
            config.write_text(json.dumps({"memory_file": str(sentinel)}), encoding="utf-8")
            env = {k: v for k, v in os.environ.items()
                   if k.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP"}}
            env.update(AGENTIC_OS_CONFIG=str(config), DATABASE_URL="postgresql://invalid",
                       OPENAI_API_KEY="synthetic-not-a-secret", OPENAI_MODEL="invalid",
                       AGENTIC_OS_KNOWLEDGE_DIR=str(root), OLLAMA_MODEL="invalid")
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "help"}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "recall"}},
            ]
            result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8",
                                     str(ROOT / "scripts/hermes_mcp.py")],
                                    input="\n".join(map(json.dumps, messages)) + "\n",
                                    capture_output=True, text=True, encoding="utf-8",
                                    timeout=20, cwd=root, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            responses = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([r["id"] for r in responses], [1, 2, 3, 4])
            self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "miyaar")
            self.assertEqual([t["name"] for t in responses[1]["result"]["tools"]], ["help"])
            self.assertFalse(responses[2]["result"]["isError"])
            self.assertTrue(responses[3]["result"]["isError"])
            self.assertNotIn("DO_NOT_FORWARD_SYNTHETIC", result.stdout + result.stderr)
            self.assertEqual({p.name for p in root.iterdir()}, {"ambient.json", "private-memory.json"})

    def test_missing_explicit_config_fails_instead_of_falling_back(self):
        result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8",
                                 str(ROOT / "scripts/hermes_mcp.py"), "--config", "missing-scope.json"],
                                input="", capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("configuration refused", result.stderr)


if __name__ == "__main__":
    unittest.main()
