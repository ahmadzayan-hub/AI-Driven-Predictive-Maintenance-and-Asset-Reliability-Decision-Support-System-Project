"""One slow model call must not stall every tenant (assessment finding B4).

The process-wide lock now covers only in-memory session state. The
assistant's model call and a run's pipeline stage run outside it, so a
concurrent read from another caller returns while the model is still
thinking.
"""

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    from server.app import create_app
    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - CLI-only environments
    FASTAPI_AVAILABLE = False

from tests.support import closing

SLOW_SECONDS = 2.0


class SlowGateway:
    """Looks configured, answers nothing, and takes its time doing so."""

    def __init__(self, seconds=SLOW_SECONDS):
        self.seconds = seconds
        self.calls = 0
        self.ollama_think = None

    def status(self):
        return {"provider": "ollama", "model": "slow", "configured": True,
                "local_only": True}

    def providers(self):
        return [{"provider": "ollama", "model": "slow", "local_only": True}]

    def ask(self, system, user, provider=None, max_tokens=None, task=None):
        self.calls += 1
        time.sleep(self.seconds)
        return None

    def ask_json(self, system, user, provider=None, max_tokens=None, schema=None, task=None):
        return self.ask(system, user)

    def narrate(self, goal, facts, provider=None, language="en", task=None):
        self.calls += 1
        time.sleep(self.seconds)
        return {"text": " ".join(facts[:2]), "source": "deterministic"}

    def ledger(self):
        return {"entries_kept": 0, "entries_limit": 0, "providers": {}}


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class ConcurrencyTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "Concurrency Test",
            "database_file": str(root / "agentic.db"),
            "memory_file": str(root / "memory.json"),
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        self.app = closing(self, create_app(config))
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.slow = SlowGateway()

    def timed(self, client, path):
        started = time.monotonic()
        response = client.get(path)
        return response.status_code, time.monotonic() - started

    def run_concurrently(self, slow_call, paths):
        """Start the slow request, then time each quick path while it runs."""
        outcome = {}

        def slow():
            outcome["response"] = slow_call()

        worker = threading.Thread(target=slow)
        worker.start()
        time.sleep(0.3)  # the slow request is inside the model call by now
        quick = TestClient(self.app, raise_server_exceptions=False)
        timings = {path: self.timed(quick, path) for path in paths}
        worker.join(timeout=SLOW_SECONDS * 5)
        self.assertFalse(worker.is_alive())
        return outcome["response"], timings

    def test_a_slow_assistant_call_does_not_block_other_callers(self):
        self.app.state.assistant.gateway = self.slow
        session = self.client.post("/api/sessions").json()["session_id"]

        def chat():
            return self.client.post(f"/api/sessions/{session}/messages",
                                    json={"text": "tell me about the weather today"})

        response, timings = self.run_concurrently(chat, ["/api/health", "/api/runs", "/api/sessions/" + session])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.slow.calls, 1)
        for path, (status, seconds) in timings.items():
            self.assertEqual(status, 200, path)
            self.assertLess(seconds, SLOW_SECONDS / 2, path)
        # The conversation itself was recorded in order, model or not.
        transcript = self.client.get(f"/api/sessions/{session}").json()["transcript"]
        self.assertEqual([entry["role"] for entry in transcript], ["user", "agent"])

    def test_two_messages_to_one_session_are_answered_in_turn(self):
        self.app.state.assistant.gateway = SlowGateway(seconds=0.4)
        session = self.client.post("/api/sessions").json()["session_id"]
        results = []

        def say(text):
            results.append(self.client.post(f"/api/sessions/{session}/messages",
                                            json={"text": text}).status_code)

        threads = [threading.Thread(target=say, args=(f"message number {n}",)) for n in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertEqual(results, [200, 200, 200])
        transcript = self.client.get(f"/api/sessions/{session}").json()["transcript"]
        self.assertEqual([entry["role"] for entry in transcript],
                         ["user", "agent"] * 3)
        self.assertEqual([entry["id"] for entry in transcript], list(range(1, 7)))

    def test_a_slow_pipeline_stage_does_not_hold_the_process_lock(self):
        """The narrating stage runs inside the engine's own run transaction,
        never under the process-wide lock. On SQLite that transaction still
        serialises store reads (KNOWN_LIMITATIONS 31), so the proof is that
        the process lock is free while the model is called, observed from
        inside the stub, rather than a timed read that the store would hold."""
        engine = self.app.state.engine
        process_lock = self.app.state.request_lock
        observed = []

        class Observing(SlowGateway):
            def narrate(inner, goal, facts, provider=None, language="en", task=None):
                observed.append(process_lock.locked())
                return super().narrate(goal, facts, provider=provider, language=language)

        engine.gateway = Observing(seconds=0.2)
        run = self.client.post("/api/runs", json={
            "goal": "Analyze team sales",
            "dataset_text": "team,quarter,sales\nA,Q1,100\nA,Q2,150\nB,Q1,90\nB,Q2,60\n",
            "dataset_name": "sales.csv"}).json()
        state = run
        for _ in range(40):
            state = self.client.post(f"/api/runs/{run['id']}/advance").json()
            if observed or state["state"] not in ("planned", "running"):
                break
        self.assertEqual(observed, [False], state["state"])
        self.assertEqual(engine.gateway.calls, 1)

if __name__ == "__main__":
    unittest.main()
