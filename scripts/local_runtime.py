#!/usr/bin/env python3
"""Install, check and run the opt-in local AI workspace. No cloud keys needed."""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from utils import load_config
MODEL_REPO = "Systran/faster-whisper-small"
MODEL_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
MODEL_FILES = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
MODEL_DIR = Path.home() / ".cache" / "miyaar" / "models" / "faster-whisper-small"
OLLAMA_URL = "http://127.0.0.1:11434"
LLM = "gemma3:4b"


def local_json(path, payload=None, timeout=5):
    """Loopback requests never use an ambient corporate/cloud proxy."""
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(OLLAMA_URL + path, data=data,
                                     headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.load(response)


def ollama_executable():
    found = shutil.which("ollama")
    if found:
        return found
    candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(candidate) if candidate.is_file() else None


def packages():
    found = {}
    for name in ("fastapi", "uvicorn", "httpx", "psycopg2-binary", "PyJWT",
                 "faster-whisper", "ctranslate2", "av", "langgraph", "pydantic-ai-slim", "mcp"):
        try:
            found[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            found[name] = None
    return found


def ensure_ollama():
    try:
        return local_json("/api/tags")
    except Exception:
        pass
    executable = ollama_executable()
    if not executable:
        raise SystemExit("Install Ollama from https://ollama.com/download/windows")
    logs = ROOT / "private" / "runtime"
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / "ollama-launch.log").open("ab") as log:
        environment = dict(os.environ, OLLAMA_HOST="127.0.0.1:11434")
        process = subprocess.Popen([executable, "serve"], stdout=log, stderr=log,
                                   env=environment,
                                   creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            return local_json("/api/tags", timeout=1)
        except Exception:
            if process.poll() is not None:
                break
            time.sleep(0.25)
    raise SystemExit("Ollama did not start. See private/runtime/ollama-launch.log.")


def installed_local(models, model):
    return any(m.get("name") == model and m.get("size", 0) > 1_000_000
               and not m.get("remote_model") and not m.get("remote_host")
               and not model.endswith((":cloud", "-cloud")) for m in models)


def doctor(model_dir, model=LLM):
    result = {"python": sys.version.split()[0], "packages": packages(),
              "node": bool(shutil.which("node")), "git": bool(shutil.which("git")),
              "ollama_installed": bool(ollama_executable()),
              "whisper_model_ready": all((model_dir / name).is_file() for name in MODEL_FILES),
              "cloud_credentials_present": {name: bool(os.environ.get(name)) for name in
                  ("ANTHROPIC_API_KEY", "GROQ_API_KEY", "DATABASE_URL", "SUPABASE_URL")}}
    try:
        models = local_json("/api/tags").get("models", [])
        result["ollama_running"] = True
        result["local_llm_ready"] = installed_local(models, model)
        result["local_model"] = model
    except Exception:
        result["ollama_running"] = result["local_llm_ready"] = False
    # Optional cloud credentials are reported as presence only and are not
    # requirements of this explicitly local profile.
    required = ("fastapi", "uvicorn", "httpx")
    result["local_profile_ready"] = bool(all(result["packages"][n] for n in required)
        and result["local_llm_ready"] and result["packages"]["faster-whisper"]
        and result["whisper_model_ready"] and (ROOT / "frontend/dist/index.html").is_file())
    print(json.dumps(result, indent=2))
    return 0 if result["local_profile_ready"] else 1


def install(model_dir, voice, agents=False, model=LLM):
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Run with the project's .venv Python; this does not install into global Python.")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
    if agents:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements-agents.txt")], check=True)
    if voice:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements-voice.txt")], check=True)
        from huggingface_hub import snapshot_download
        model_dir.mkdir(parents=True, exist_ok=True)
        snapshot_download(MODEL_REPO, revision=MODEL_REVISION, local_dir=str(model_dir),
                          allow_patterns=[*MODEL_FILES, "README.md"], token=False)
        print("Downloaded pinned multilingual Whisper small weights. No audio was uploaded.")
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    executable = ollama_executable()
    if not executable:
        print("Install Ollama from https://ollama.com/download/windows, then run ollama pull " + model)
        return 1
    models = ensure_ollama().get("models", [])
    if not installed_local(models, model):
        subprocess.run([executable, "pull", model], check=True)
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise SystemExit("Node.js/npm is required to build the frontend.")
    subprocess.run([npm, "ci"], cwd=ROOT / "frontend", check=True)
    subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", check=True)
    return doctor(model_dir, model)


def start(model_dir, port, worker, model=LLM):
    if os.environ.get("DATABASE_URL") or os.environ.get("AGENTIC_OS_ENV", "").lower() == "production":
        raise SystemExit("Use the hosted launcher for a hosted database/production environment; this profile is for local SQLite.")
    # The API resolves a relative config from ROOT after os.chdir below.
    # Check that same file before starting a service or prewarming a model.
    selected_config = os.environ.get("AGENTIC_OS_CONFIG")
    config_path = Path(selected_config) if selected_config else ROOT / "config.json"
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        if selected_config:
            raise SystemExit("The selected local configuration is missing; no service was started.") from None
        # Keep the existing missing-default path: later app startup reports
        # its missing config, rather than changing other launcher checks.
        config = {}
    except (OSError, ValueError):
        raise SystemExit("The local configuration could not be read; no service was started.") from None
    if config.get("database_url"):
        raise SystemExit("Use the hosted launcher for a configured hosted database; this profile is for local SQLite.")
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        raise SystemExit("Build the frontend first: npm --prefix frontend run build")
    models = ensure_ollama().get("models", [])
    if not installed_local(models, model):
        raise SystemExit("Download a local model first: ollama pull " + model)
    # Explicit local profile. Cloud environment/config is not overwritten on
    # disk. Existing outer secrets remain server-side and are never printed.
    os.environ["OLLAMA_MODEL"] = model
    os.environ["OLLAMA_HOST"] = OLLAMA_URL
    os.environ["OLLAMA_THINK"] = "0"
    os.environ["OLLAMA_CONTEXT_LENGTH"] = "4096"
    os.environ["OLLAMA_NUM_THREAD"] = "6"
    os.environ["OLLAMA_TEMPERATURE"] = "0.2"
    os.environ["AGENTIC_OS_MODEL_TIMEOUT_SECONDS"] = "45"
    os.environ["AGENTIC_OS_WHISPER_ENABLED"] = "1" if all(
        (model_dir / name).is_file() for name in MODEL_FILES) else "0"
    os.environ["AGENTIC_OS_WHISPER_MODEL_DIR"] = str(model_dir)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    print("Loading local model into memory: " + model, flush=True)
    try:
        loaded = local_json("/api/generate", {"model": model, "prompt": "", "stream": False,
                            "keep_alive": "10m", "options": {"num_ctx": 4096, "num_thread": 6}}, timeout=90)
        if not loaded.get("done"):
            raise ValueError("Model did not finish loading")
    except Exception:
        raise SystemExit("The local model did not load; check Ollama before starting the workspace.") from None
    os.chdir(ROOT)
    print(f"Miyaar local workspace: http://localhost:{port}", flush=True)
    print("Local LLM: " + model + "; Whisper: " + os.environ["AGENTIC_OS_WHISPER_ENABLED"], flush=True)
    child = None
    try:
        if worker:
            worker_args = [sys.executable, str(ROOT / "scripts" / "worker.py")]
            config_path = os.environ.get("AGENTIC_OS_CONFIG")
            if config_path:
                # The API reads this variable; the worker accepts it as a
                # CLI option. Both processes must use the same data store.
                worker_args.extend(["--config", config_path])
            child = subprocess.Popen(worker_args,
                                     cwd=ROOT, creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        import uvicorn
        uvicorn.run("server.app:app", host="127.0.0.1", port=port, log_level="warning")
    finally:
        if child and child.poll() is None:
            child.terminate()
            child.wait(timeout=10)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("doctor", "install", "start"))
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--model", default=LLM, help="Installed local Ollama model; cloud tags are refused")
    parser.add_argument("--voice", action="store_true", help="Install optional local voice and download pinned weights")
    parser.add_argument("--agents", action="store_true", help="Install SDKs for the existing optional runtime examples")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--worker", action="store_true", help="Run the scheduled connector worker while this server runs")
    args = parser.parse_args()
    args.model_dir = args.model_dir.expanduser().resolve()
    if args.command == "doctor":
        return doctor(args.model_dir, args.model)
    if args.command == "install":
        return install(args.model_dir, args.voice, args.agents, args.model)
    return start(args.model_dir, args.port, args.worker, args.model)


if __name__ == "__main__":
    raise SystemExit(main())
