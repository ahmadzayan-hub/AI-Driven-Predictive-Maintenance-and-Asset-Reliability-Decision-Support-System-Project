"""Disposable browser fixture: real HTTP/worker wiring, no real model or identity.

Loaded explicitly by Playwright, never by the production app/worker factory.
All provider transport is blocked except the bounded scripted seed operation.
"""
import atexit
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from server.app import create_app
from server.model_gateway import ModelGateway
from server.specialist_config import PROFILE
from server.worker import build_worker
from tests.support import scoped_token
from tests.test_specialists import ScriptedDecisions


def build_fixture():
    if os.environ.get("MIYAAR_SYNTHETIC_SPECIALIST_BROWSER") != "1":
        raise RuntimeError("This synthetic test fixture must be explicitly selected.")
    root = tempfile.TemporaryDirectory(prefix="miyaar-synthetic-browser-")
    atexit.register(root.cleanup)
    folder = Path(root.name)
    config = folder / "config.json"
    config.write_text(json.dumps({"database_file": str(folder / "state.db"),
        "memory_file": str(folder / "memory.json"), "vault_dir": str(folder / "vault")}))
    env = {"AGENTIC_OS_SPECIALISTS_ENABLED": "1",
        "AGENTIC_OS_SPECIALIST_MODEL": "ollama:synthetic-model", "OLLAMA_MODEL": "synthetic-model",
        "AGENTIC_OS_RUN_EXECUTION": "worker", "AGENTIC_OS_PUBLISH_TARGET": "database",
        "AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY": "30",
        "AGENTIC_OS_JWT_SECRET": "synthetic-browser-test-only-not-a-real-key",
        "SUPABASE_URL": "https://test.supabase.invalid"}
    transport = patch.object(ModelGateway, "_post", side_effect=AssertionError("Live provider forbidden in fixture"))
    transport.start()
    atexit.register(transport.stop)
    app = create_app(config, env=env)
    worker = build_worker(config_path=config, env=env)
    client = TestClient(app)
    headers = {"Authorization": "Bearer " + scoped_token(env["AGENTIC_OS_JWT_SECRET"], "synthetic-browser-owner", "owner")}
    try:
        for language in ("en", "ar"):
            response = client.post("/api/runs", headers=headers, json={
                "goal": "Synthetic specialist browser evidence " + language,
                "profile": PROFILE, "language": language,
                "dataset_text": "month,sales\nJan,10\nFeb,20\nMar,30\n"})
            if response.status_code not in (200, 201):
                raise AssertionError(response.text)
            run_id = response.json()["id"]
            scripted = ScriptedDecisions()
            def answer(url, headers, payload):
                context = json.loads(payload["messages"][-1]["content"])
                return {"message": {"content": json.dumps(scripted.decide(context))}}
            with patch.object(ModelGateway, "_post", side_effect=answer):
                if worker.step() != run_id:
                    raise AssertionError("Fixture worker did not claim the seeded run")
            detail = client.get("/api/runs/" + run_id, headers=headers).json()
            if detail["state"] != "awaiting_approval" or detail["report"]["published_path"]:
                raise AssertionError("Synthetic report must await an actual human decision")
    finally:
        worker.store.close()
    return app


app = build_fixture()
