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
            with patch.dict(os.environ, {"AGENTIC_OS_CONFIG": str(config)}, clear=True), \
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
