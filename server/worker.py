"""Background run worker: database-backed leases with heartbeats.

Without this, an analytics run only advances while somebody has the Runs
view open — close the tab and the work stops. The worker claims runnable
runs and steps them server-side.

Concurrency control is a lease on the run row: a worker sets
`lease_owner` and `lease_expires_at`, renews the expiry after every task,
and releases the lease when the run stops being runnable. Two workers
cannot claim the same run because the claim is a conditional UPDATE — the
loser changes zero rows. A worker that crashes simply stops renewing; the
expiry passes and another worker (or a client) takes over from the run's
durable state. There is no lock to clean up after a crash, which is the
whole reason to prefer a lease over one.

What the worker deliberately does **not** do: decide approvals. It stops
at the approval gate and waits for a human, exactly like a client-stepped
run. An autonomous publisher would defeat the point of the gate.

It also refreshes live sources whose refresh is due (ADR 0034), under the
same kind of lease, so two workers never fetch one source at once. A
refresh with new content starts a run, which this loop then advances to
the gate like any other.
"""

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from server import agent_learning, tenant
from server.connectors import Connectors
from server.model_gateway import ModelGateway
from server.orchestration import ModelRoles
from server.quota import ModelBudget, load_limits
from server.routing import RoutedGateway, build_router
from server.stages import load_stages
from server.runs import RunEngine, _stamp, _utcnow, resolve_publish_target, resolve_vault_dir
from server.storage import open_store

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNNABLE_STATES = ("queued", "running")
DEFAULT_LEASE_SECONDS = 30
# A bounded loop cannot spin forever if an unexpected state ever leaves a
# run runnable with nothing to do, including when custom stages are enabled.
MAX_STEPS_PER_CLAIM = 64
HEARTBEAT_STALE_SECONDS = 120


def worker_status(store, mode="client", clock=_utcnow,
                  stale_seconds=HEARTBEAT_STALE_SECONDS):
    """Recent database activity, not a promise that a process is alive.

    Heartbeats bracket bounded stages, so the threshold exceeds the model
    timeout. A stalled or terminated process eventually becomes unready.
    No worker identifier, owner, goal or source configuration is exposed.
    """
    observed = []
    now = clock()
    for row in store.list_worker_heartbeats():
        try:
            seen = datetime.fromisoformat(row["seen_at"])
            age = (now - seen).total_seconds()
        except (ValueError, TypeError, KeyError):
            continue
        # A badly skewed clock must not make a dead worker ready forever.
        if age < -5:
            continue
        observed.append((max(0, age), row))
    latest = min(observed, key=lambda item: item[0]) if observed else None
    recent = any(age <= stale_seconds and row["state"] in
                 ("idle", "running", "refreshing", "evaluating")
                 for age, row in observed)
    return {"mode": mode, "ready": mode == "client" or recent,
            "last_seen_at": latest[1]["seen_at"] if latest else None,
            "heartbeat_age_seconds": round(latest[0], 1) if latest else None,
            "stale_after_seconds": stale_seconds}


def read_config(config_path=None):
    path = Path(config_path or PROJECT_ROOT / "config.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


class RunWorker:
    def __init__(self, engine, store, worker_id=None,
                 lease_seconds=DEFAULT_LEASE_SECONDS, clock=_utcnow, connectors=None,
                 steward=None):
        self.engine = engine
        self.store = store
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        if lease_seconds < 1:
            raise ValueError("Worker lease must be at least one second.")
        self.lease_seconds = lease_seconds
        self.clock = clock
        # Live sources (ADR 0034); None leaves them to "Refresh now".
        self.connectors = connectors
        # Periodic agent measurement (docs/adr/2026-10-20-agent-measurement-loop.md); None leaves it to the CLI.
        self.steward = steward

    def _expiry(self):
        return _stamp(self.clock() + timedelta(seconds=self.lease_seconds))

    def claim(self):
        return self.store.claim_run(self.worker_id, _stamp(self.clock()),
                                    self._expiry())

    def heartbeat(self, state="idle"):
        self.store.upsert_worker_heartbeat(self.worker_id, _stamp(self.clock()), state)

    def step(self):
        """Claim one run and advance it until a human is needed or it ends.

        Returns the run id worked on, or None when nothing was runnable.
        """
        self.heartbeat()
        run_id = self.claim()
        if run_id is None:
            return None
        try:
            for _ in range(MAX_STEPS_PER_CLAIM):
                self.heartbeat("running")
                try:
                    tenant.current_owner.set(self.engine.owner_of(run_id))
                    run = self.engine.advance(run_id, lease_owner=self.worker_id)
                except ValueError:
                    # The run stopped being ours to advance between the
                    # claim and this call — a human paused it, cancelled
                    # it, or it reached the approval gate. Ordinary, not
                    # an error: release the lease and take the next run.
                    break
                if run["state"] not in RUNNABLE_STATES:
                    break
                if not any(t["state"] == "pending" for t in run["tasks"]):
                    break
                # Losing the lease means a successor already owns this run
                # (we were too slow); stop rather than race it.
                if not self.store.renew_lease(run_id, self.worker_id,
                                              self._expiry()):
                    return run_id
        finally:
            self.store.release_lease(run_id, self.worker_id)
            self.heartbeat()
        return run_id

    def refresh_due(self):
        """Refresh one live source whose refresh is due. Returns its id,
        or None when none was due."""
        if self.connectors is None:
            return None
        self.heartbeat("refreshing")
        try:
            return self.connectors.step(self.worker_id)
        finally:
            self.heartbeat()

    def run_forever(self, poll_seconds=1.0, stop=None, sleep=time.sleep):
        """Work until `stop` (a threading.Event) is set.

        One failing run must never take the worker down — the next run,
        and the same run after a fix, still deserve to make progress. The
        failure is reported on stderr and the loop continues. A failing
        source is the same: its refresh records the failure and waits.
        """
        if not 0 < poll_seconds <= 60:
            raise ValueError("Worker polling must be greater than zero and at most 60 seconds.")
        try:
            while stop is None or not stop.is_set():
                try:
                    worked = self.step()
                except Exception as error:  # one bad run, not a dead worker
                    print(f"Worker run failed ({type(error).__name__}).",
                          file=sys.stderr, flush=True)
                    worked = None
                try:
                    refreshed = self.refresh_due()
                except Exception as error:  # never log upstream exception contents
                    print(f"Worker refresh failed ({type(error).__name__}).",
                          file=sys.stderr, flush=True)
                    refreshed = None
                try:
                    if self.steward is not None:
                        self.heartbeat("evaluating")
                        self.steward.tick()
                        self.heartbeat()
                except Exception as error:
                    print(f"Worker evaluation failed ({type(error).__name__}).",
                          file=sys.stderr, flush=True)
                if worked is None and refreshed is None:
                    sleep(poll_seconds)
        finally:
            self.heartbeat("stopped")


def build_worker(env=None, config_path=None, **kwargs):
    """A worker wired to the same database and vault as the API."""
    import os

    env = os.environ if env is None else env
    config = read_config(config_path or env.get("AGENTIC_OS_CONFIG"))
    store = open_store(
        env.get("DATABASE_URL") or config.get("database_url"),
        config.get("database_file") or PROJECT_ROOT / "data" / "agentic.db",
        schema_mode="verify",
    )
    gateway = ModelGateway(env)
    limits = load_limits(env)
    gateway.budget = ModelBudget(store, limits)
    # Like the API, roles use the plain gateway so each named provider/model
    # remains explicit even when a separate router selects report narration.
    model_roles = ModelRoles(gateway, env)
    # The worker narrates the same reports the API does, so it routes the
    # same way; a run advanced in the background must not be narrated by a
    # different model than one advanced in a browser.
    router, router_name, problem = build_router(env, config)
    if router is not None:
        gateway = RoutedGateway(gateway, router, router_name)
    elif problem:
        # The API reports this in /api/health. A worker has no health
        # endpoint, so a misconfigured router would be invisible here.
        print(problem, file=sys.stderr, flush=True)
    # The worker runs the same custom stages the API does: a run
    # advanced in the background must not lack a stage the browser has.
    stage_registry, stage_problems = load_stages(env, config)
    for stage_problem in stage_problems:
        print(stage_problem, file=sys.stderr, flush=True)
    engine = RunEngine(store, resolve_vault_dir(env=env, config=config),
                       gateway, limits=limits, stages=stage_registry,
                       profiles=config.get("profiles") or {}, execution_mode="worker",
                       roles=model_roles if model_roles.active else None,
                       publish_target=resolve_publish_target(env, config))
    interval = agent_learning.interval_from(env)
    steward = agent_learning.Steward(
        interval, ledger=agent_learning.Ledger(agent_learning.ledger_path(env))) \
        if interval else None
    return RunWorker(engine, store, connectors=Connectors(engine, env=env),
                     steward=steward, **kwargs)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Advance analytics runs server-side.")
    parser.add_argument("--once", action="store_true",
                        help="claim and finish at most one run, then exit")
    parser.add_argument("--poll", type=float, default=1.0,
                        help="seconds to wait when no run is available")
    parser.add_argument("--lease", type=int, default=DEFAULT_LEASE_SECONDS,
                        help="lease duration in seconds")
    parser.add_argument("--config", help="config.json to read the database from")
    args = parser.parse_args(argv)

    worker = build_worker(config_path=args.config, lease_seconds=args.lease)
    try:
        if args.once:
            run_id = worker.step()
            connector_id = worker.refresh_due()
            print(json.dumps({"worker": worker.worker_id, "run": run_id,
                              "connector": connector_id}))
            return 0
        print(json.dumps({"worker": worker.worker_id, "polling_seconds": args.poll}),
              flush=True)
        try:
            worker.run_forever(poll_seconds=args.poll)
        except KeyboardInterrupt:
            pass
    finally:
        # A one-shot worker is known to have stopped; do not advertise it
        # as ready for the full freshness window after the process exits.
        try:
            worker.heartbeat("stopped")
        finally:
            worker.store.close()
    return 0
