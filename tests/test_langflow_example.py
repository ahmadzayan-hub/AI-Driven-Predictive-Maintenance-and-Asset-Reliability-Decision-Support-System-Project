"""Bounded synthetic protocol checks, not a Langflow import or flow test."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from examples.langflow import miyaar_synthetic as example

SCRIPT = Path(example.__file__).resolve()
ARGV = [sys.executable, "-I", "-B", "-X", "utf8", str(SCRIPT)]


def request(number, method, params=None):
    return {"jsonrpc": "2.0", "id": number, "method": method, "params": params or {}}


class LangflowExampleTestCase(unittest.TestCase):
    def execute(self, args, messages=(), **kwargs):
        return subprocess.run(ARGV + args, input="".join(json.dumps(m) + "\n" for m in messages),
                              capture_output=True, text=True, encoding="utf-8", timeout=20, **kwargs)

    def test_config_is_exact_and_printing_and_default_help_create_no_files(self):
        with tempfile.TemporaryDirectory(prefix="langflow path spaces ") as directory:
            for language in ("en", "ar"):
                result = self.execute(["--print-config", "--language", language], cwd=directory)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {"mcpServers": {
                    f"miyaar-synthetic-{language}": {
                        "command": str(Path(sys.executable).absolute()),
                        "args": ["-I", "-B", "-X", "utf8", str(SCRIPT),
                                 "--serve-synthetic", "--language", language], "env": {}}}})
            result = self.execute([], cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--serve-synthetic", result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_invalid_arguments_fail_before_storage_and_do_not_echo_input(self):
        with tempfile.TemporaryDirectory() as directory:
            for args in (["--config", "SYNTHETIC_SECRET"], ["--language", "SYNTHETIC_SECRET"],
                         ["--serve-synthetic", "--print-config"], ["--serve"]):
                result = self.execute(args, cwd=directory)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("SYNTHETIC_SECRET", result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_ndjson_english_and_arabic_allow_only_three_read_tools(self):
        names = [*example.TOOLS, "start_run", "remember", "recall", "search_knowledge",
                 "approve", "publish", "set_preference", "agent_scorecard"]
        messages = [request(1, "initialize", {"protocolVersion": "2025-06-18"}),
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    request(2, "tools/list")]
        messages += [request(i + 3, "tools/call", {"name": name, "arguments": {}})
                     for i, name in enumerate(names)]
        for language in ("en", "ar"):
            with self.subTest(language=language):
                result = self.execute(["--serve-synthetic", "--language", language], messages)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                replies = [json.loads(line) for line in result.stdout.splitlines()]
                self.assertEqual(len(replies), len(messages) - 1)
                self.assertEqual(replies[0]["result"]["serverInfo"]["name"], f"miyaar-synthetic-{language}")
                self.assertIn("Synthetic" if language == "en" else "اصطناعي",
                              replies[0]["result"]["instructions"])
                self.assertEqual([t["name"] for t in replies[1]["result"]["tools"]], example.TOOLS)
                for name, reply in zip(names, replies[2:]):
                    self.assertEqual(reply["result"]["isError"], name not in example.TOOLS, name)
                status = replies[3]["result"]["content"][0]["text"]
                report = replies[4]["result"]["content"][0]["text"]
                self.assertIn("approval" if language == "en" else "الموافقة", status)
                self.assertIn("Revenue" if language == "en" else "الإيرادات", report)
                self.assertNotIn("no report yet", report.lower())

    def test_ambient_settings_and_files_are_ignored_and_temporary_state_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sentinel = root / "private.json"
            sentinel.write_text('{"memory_1":"SYNTHETIC_PRIVATE_SENTINEL"}', encoding="utf-8")
            config = root / "config.json"
            config.write_text(json.dumps({"memory_file": str(sentinel), "vault_dir": str(root / "vault")}), encoding="utf-8")
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            env = dict(os.environ, AGENTIC_OS_CONFIG=str(config), DATABASE_URL="postgresql://invalid",
                       AGENTIC_OS_DB=str(root / "ambient.db"), AGENTIC_OS_MEMORY_FILE=str(sentinel),
                       AGENTIC_OS_VAULT_DIR=str(root / "vault"), AGENTIC_OS_KNOWLEDGE_DIR=str(root),
                       OPENAI_API_KEY="synthetic-not-a-key", OPENAI_MODEL="invalid",
                       OLLAMA_MODEL="invalid", AGENTIC_OS_RUN_EXECUTION="worker",
                       TEMP=directory, TMP=directory, TMPDIR=directory)
            messages = [request(1, "tools/call", {"name": "run_status"}),
                        request(2, "tools/call", {"name": "explain_report"})]
            # Observe attempted reads as well as checking unchanged files/output.
            code = """
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("example", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
forbidden = set(sys.argv[2:])
reads = []
def observe(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        if os.fsdecode(args[0]) in forbidden:
            reads.append(args[0])
sys.addaudithook(observe)
result = m.main(["--serve-synthetic"])
assert not reads, "ambient files were accessed"
raise SystemExit(result)
"""
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-X", "utf8", "-c", code,
                 str(SCRIPT), str(sentinel), str(config)],
                input="".join(json.dumps(m) + "\n" for m in messages),
                capture_output=True, text=True, encoding="utf-8", timeout=20,
                cwd=directory, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("SYNTHETIC_PRIVATE_SENTINEL", result.stdout + result.stderr)
            self.assertIn("approval", result.stdout)
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, before)

    def test_state_reaches_gate_never_publishes_and_cleans_up_on_error(self):
        root = None
        with self.assertRaisesRegex(RuntimeError, "test exit"):
            with example.synthetic_server("en") as server:
                engine = server.assistant.engine
                root = engine.vault_dir.parent
                runs = engine.list_runs(owner=server.session.owner)
                self.assertEqual(len(runs), 1)
                run = engine.get_run(runs[0]["id"])
                self.assertEqual(run["state"], "awaiting_approval")
                self.assertTrue(run["reports"])
                self.assertTrue(run["approvals"])
                self.assertTrue(all(a["state"] == "pending" for a in run["approvals"]))
                self.assertFalse(run["report"]["published_path"])
                self.assertFalse(engine.vault_dir.exists())
                with patch.object(server, "_call", side_effect=ValueError("SYNTHETIC_SECRET")):
                    response = server.handle(request(1, "tools/call", {"name": "help"}))
                    self.assertEqual(response["error"]["message"], example.REFUSED)
                raise RuntimeError("test exit")
        self.assertIsNotNone(root)
        self.assertFalse(root.exists())

    def test_audit_guard_blocks_real_socket_dns_subprocess_and_system_attempts(self):
        code = '''
import importlib.util, socket, subprocess, os, sys
spec = importlib.util.spec_from_file_location("example", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.addaudithook(m.deny_external_effects)
operations = [lambda: socket.socket(), lambda: socket.getaddrinfo("localhost", 80),
              lambda: subprocess.run([sys.executable, "-c", "pass"]), lambda: os.system("exit 0")]
for operation in operations:
    try:
        operation()
    except PermissionError:
        continue
    raise AssertionError("guard failed")
for event in ("socket.connect", "socket.bind", "socket.gethostbyname", "os.exec", "os.posix_spawn", "os.fork"):
    try:
        m.deny_external_effects(event, ())
    except PermissionError:
        continue
    raise AssertionError(event)
'''
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(SCRIPT)],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "official mcp SDK is not installed (optional)")
    def test_official_sdk_initializes_lists_and_calls_using_printed_config(self):
        # The subprocess timeout bounds SDK startup/shutdown as well as calls.
        code = '''
import asyncio, json, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def drive():
    cfg = next(iter(json.load(sys.stdin)["mcpServers"].values()))
    async with stdio_client(StdioServerParameters(**cfg)) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "miyaar-synthetic-en"
            listed = await session.list_tools()
            assert [t.name for t in listed.tools] == ["help", "run_status", "explain_report"]
            for name in ("help", "run_status", "explain_report"):
                reply = await session.call_tool(name, {})
                assert not reply.isError
            reply = await session.call_tool("start_run", {"goal": "denied"})
            assert reply.isError
asyncio.run(asyncio.wait_for(drive(), timeout=15))
'''
        config = self.execute(["--print-config"])
        self.assertEqual(config.returncode, 0, config.stderr)
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code],
                                input=config.stdout, capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
