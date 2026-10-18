"""Local launch safety, without installing packages or starting services."""

import contextlib
import io
import os
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import local_runtime as runtime


class LocalRuntimeTest(unittest.TestCase):
    def test_cli_selects_the_project_node_without_changing_the_remaining_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            portable = root / "private" / "tools" / "node-v24.22.0-win-x64"
            portable.mkdir(parents=True)
            (portable / "node.exe").write_bytes(b"fixture; never executed")
            inherited = os.pathsep.join((str(root / "other-tools"), str(root / "system-node")))
            with patch.object(runtime, "ROOT", root), patch.object(runtime.sys, "platform", "win32"), \
                    patch.dict(os.environ, {"PATH": inherited}), \
                    patch.object(runtime.sys, "argv", ["local_runtime.py", "doctor"]), \
                    patch.object(runtime, "doctor", return_value=0) as doctor:
                self.assertEqual(runtime.main(), 0)
                self.assertEqual(os.environ["PATH"], str(portable) + os.pathsep + inherited)
                runtime.activate_project_node()
                self.assertEqual(os.environ["PATH"], str(portable) + os.pathsep + inherited)
                doctor.assert_called_once()

    def test_absent_project_runtime_leaves_the_system_selection_unchanged(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(runtime, "ROOT", Path(directory)), \
                patch.object(runtime.sys, "platform", "win32"), \
                patch.dict(os.environ, {"PATH": "inherited-tools"}):
            runtime.activate_project_node()
            self.assertEqual(os.environ["PATH"], "inherited-tools")

    def test_doctor_requires_a_supported_node_even_when_all_other_local_tools_are_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            interface = root / "frontend" / "dist"
            interface.mkdir(parents=True)
            (interface / "index.html").write_text("fixture", encoding="utf-8")
            model = root / "model"
            model.mkdir()
            for name in runtime.MODEL_FILES:
                (model / name).write_bytes(b"fixture")
            cases = ((None, False), ("22.22.1", False), ("22.22.2", True),
                     ("23.9.0", False), ("24.14.0", False), ("24.15.0", True),
                     ("24.22.0", True), ("25.9.0", False), ("26.0.0", True))
            for version, ready in cases:
                with self.subTest(version=version), \
                        patch.object(runtime, "ROOT", root), \
                        patch.object(runtime, "packages", return_value={
                            "fastapi": "1", "uvicorn": "1", "httpx": "1", "faster-whisper": "1"}), \
                        patch.object(runtime, "node_version", return_value=version), \
                        patch.object(runtime.shutil, "which", return_value="installed-tool"), \
                        patch.object(runtime, "local_json", return_value={"models": [{"name": runtime.LLM, "size": 2_000_000}]}), \
                        contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(runtime.doctor(model), 0 if ready else 1)
                    report = json.loads(output.getvalue())
                    self.assertTrue(report["node"])
                    self.assertEqual(report["node_version"], version)
                    self.assertEqual(report["node_supported"], ready)
                    self.assertEqual(report["local_profile_ready"], ready)

    def test_node_version_probe_is_bounded_and_rejects_a_broken_executable(self):
        with patch.object(runtime.shutil, "which", return_value="selected-node"), \
                patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(
                    stdout="v24.22.0\n", returncode=0)) as run:
            self.assertEqual(runtime.node_version(), "24.22.0")
            self.assertEqual(run.call_args.args[0], ["selected-node", "--version"])
            self.assertEqual(run.call_args.kwargs["timeout"], 5)
            run.return_value = SimpleNamespace(stdout="unusable", returncode=0)
            self.assertIsNone(runtime.node_version())

    def test_worker_forwards_the_apis_private_acceptance_configuration(self):
        # No real service/process starts, and os.chdir is mocked so this
        # fixture cannot change the test runner's current directory.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            interface = root / "frontend" / "dist"
            interface.mkdir(parents=True)
            (interface / "index.html").write_text("test interface", encoding="utf-8")
            private = root / "private" / "runtime"
            private.mkdir(parents=True)
            config = private / "acceptance-config.json"
            config.write_text(json.dumps({"database_file": str(private / "acceptance.sqlite")}), encoding="utf-8")
            child = Mock()
            child.poll.return_value = None
            run = Mock()
            warming = patch.object(runtime, "local_json", return_value={"done": True})
            warming.start()
            self.addCleanup(warming.stop)
            with patch.dict(os.environ, {"AGENTIC_OS_CONFIG": str(config),
                                         "LANGCHAIN_TRACING_V2": "true", "LANGSMITH_TRACING": "true"}, clear=True), \
                    patch.object(runtime, "ROOT", root), \
                    patch.object(runtime.os, "chdir") as change_directory, \
                    patch.object(runtime, "ensure_ollama", return_value={"models": [{"name": runtime.LLM, "size": 2_000_000}]}), \
                    patch.object(runtime.subprocess, "Popen", return_value=child) as spawn, \
                    patch.dict(sys.modules, {"uvicorn": SimpleNamespace(run=run)}), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runtime.start(root / "model", 8012, True), 0)
                self.assertEqual(spawn.call_args.args[0], [sys.executable, str(root / "scripts" / "worker.py"),
                                                          "--config", str(config)])
                self.assertEqual(spawn.call_args.kwargs["cwd"], root)
                self.assertEqual(os.environ["AGENTIC_OS_CONFIG"], str(config))
                self.assertEqual(os.environ["LANGCHAIN_TRACING_V2"], "false")
                self.assertEqual(os.environ["LANGSMITH_TRACING"], "false")
                change_directory.assert_called_once_with(root)
                run.assert_called_once_with("server.app:app", host="127.0.0.1", port=8012, log_level="warning")
                child.terminate.assert_called_once()
                child.wait.assert_called_once_with(timeout=10)

    def test_local_profile_rejects_a_cloud_alias_before_loading(self):
        with patch.dict(os.environ, {}, clear=True), tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            interface = root / "frontend/dist"
            interface.mkdir(parents=True)
            (interface / "index.html").write_text("fixture", encoding="utf-8")
            with patch.object(runtime, "ROOT", root), patch.object(runtime, "ensure_ollama", return_value={
                    "models": [{"name": "remote:latest", "size": 2_000_000, "remote_model": "remote"}]}), \
                    patch.object(runtime, "local_json") as loading:
                with self.assertRaises(SystemExit):
                    runtime.start(root / "model", 8012, False, "remote:latest")
                loading.assert_not_called()

    def test_an_existing_ollama_service_is_reused(self):
        with patch.object(runtime, "local_json", return_value={"models": []}), \
                patch.object(runtime.subprocess, "Popen") as spawn:
            self.assertEqual(runtime.ensure_ollama(), {"models": []})
            spawn.assert_not_called()

    def test_new_local_ollama_ignores_an_external_bind_setting(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(runtime, "ROOT", Path(directory)), \
                patch.dict(os.environ, {"OLLAMA_HOST": "0.0.0.0:11434"}), \
                patch.object(runtime, "ollama_executable", return_value="ollama"), \
                patch.object(runtime, "local_json", side_effect=[OSError(), {"models": []}]), \
                patch.object(runtime.subprocess, "Popen") as spawn:
            runtime.ensure_ollama()
            self.assertEqual(spawn.call_args.kwargs["env"]["OLLAMA_HOST"], "127.0.0.1:11434")

    def test_doctor_does_not_expose_keys_or_call_an_incomplete_voice_profile_ready(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(runtime, "packages", return_value={"fastapi": "1", "uvicorn": "1", "httpx": "1", "faster-whisper": None}), \
                patch.object(runtime, "local_json", return_value={"models": [{"name": runtime.LLM, "size": 2_000_000}]}), \
                patch.dict(os.environ, {"ANTHROPIC_API_KEY": "not-for-display"}), \
                contextlib.redirect_stdout(output):
            self.assertEqual(runtime.doctor(Path(directory)), 1)
        self.assertNotIn("not-for-display", output.getvalue())
        self.assertIn('"local_profile_ready": false', output.getvalue())

    def test_local_profile_never_launches_against_an_inherited_hosted_database(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://never-display-this"}), \
                patch.object(runtime, "ensure_ollama") as ollama:
            with self.assertRaises(SystemExit) as stopped:
                runtime.start(Path("unused"), 8000, False)
            self.assertNotIn("never-display-this", str(stopped.exception))
            ollama.assert_not_called()

    def test_configured_hosted_database_is_refused_without_an_environment_database_url(self):
        for explicit in (False, True):
            with self.subTest(explicit_config=explicit), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                config = root / ("selected.json" if explicit else "config.json")
                config.write_text(json.dumps({"database_url": "postgresql://never-display-config-value"}), encoding="utf-8")
                environment = {"AGENTIC_OS_CONFIG": str(config)} if explicit else {}
                with patch.dict(os.environ, environment, clear=True), \
                        patch.object(runtime, "ROOT", root), \
                        patch.object(runtime, "ensure_ollama") as service, \
                        patch.object(runtime, "local_json") as prewarm, \
                        patch.object(runtime.subprocess, "Popen") as spawn:
                    with self.assertRaises(SystemExit) as stopped:
                        runtime.start(root / "model", 8012, True)
                    self.assertNotIn("never-display-config-value", str(stopped.exception))
                    service.assert_not_called()
                    prewarm.assert_not_called()
                    spawn.assert_not_called()

    def test_missing_selected_config_is_refused_before_services_start(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {"AGENTIC_OS_CONFIG": str(Path(directory) / "missing.json")}, clear=True), \
                patch.object(runtime, "ensure_ollama") as service:
            with self.assertRaises(SystemExit) as stopped:
                runtime.start(Path(directory), 8012, True)
            self.assertNotIn(directory, str(stopped.exception))
            service.assert_not_called()
