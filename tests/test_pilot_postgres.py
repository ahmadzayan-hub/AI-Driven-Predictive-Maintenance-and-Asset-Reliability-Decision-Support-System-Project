"""Opt-in PostgreSQL acceptance for shared maintenance and shadow trials.

Run only against an isolated PG_TEST_URL, exclusively: fixtures clear the
application tables just like the existing worker/backup PostgreSQL suites.
REQUIRE_PG makes an unreachable test database fail instead of silently skip.
No customer database or external model is used.
"""

import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.auth import Principal
from server.backup import create_backup, restore_backup
from server.operations import Operations, OperationsError
from server.reliability_validation import ReliabilityTrials, ValidationError
from server.storage import TABLES, open_store
from tests.support import closing_store
from tests.test_runs import PG_TEST_URL, _postgres_available


def enabled():
    # Unlike a developer's normal DATABASE_URL, PG_TEST_URL explicitly opts
    # into disposable test data. REQUIRE_PG preserves the suite's fail-closed
    # behavior when CI expects this dependency to exist.
    if not os.environ.get("PG_TEST_URL") and not os.environ.get("REQUIRE_PG"):
        return False
    return _postgres_available()


@unittest.skipUnless(enabled(), "isolated test PostgreSQL not configured/reachable")
class PilotPostgresTest(unittest.TestCase):
    def _drop_tables(self):
        import psycopg2

        with psycopg2.connect(PG_TEST_URL, connect_timeout=3) as connection:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE")
        connection.close()

    def setUp(self):
        self._drop_tables()
        self.addCleanup(self._drop_tables)
        self.store = closing_store(self, open_store(PG_TEST_URL))
        self.second = closing_store(self, open_store(PG_TEST_URL))
        self.ops = Operations(self.store)
        self.other_ops = Operations(self.second)
        self.owner = Principal("pilot-owner", "owner", "jwt")
        self.manager = Principal("pilot-manager", "analyst", "jwt")
        self.tech = Principal("pilot-tech", "analyst", "jwt")
        self.org_id = self.ops.create_organization(self.owner,
            {"name": "Synthetic PostgreSQL depot", "idempotency_key": "org"})["id"]
        self.ops.set_member(self.owner, self.org_id, {"subject": self.manager.subject, "role": "manager",
            "expected_version": 1, "idempotency_key": "manager"})
        self.ops.set_member(self.owner, self.org_id, {"subject": self.tech.subject, "role": "technician",
            "expected_version": 2, "idempotency_key": "technician"})
        site = self.ops.create_site(self.owner, self.org_id,
            {"code": "DEPOT-TEST", "name": "Synthetic depot", "idempotency_key": "site"})
        self.asset = self.ops.create_asset(self.owner, self.org_id, {
            "site_id": site["id"], "external_id": "PUMP-001", "source_system": "test-register",
            "name": "Fixture pump", "criticality": "high", "idempotency_key": "asset"})
        self.asset_two = self.ops.create_asset(self.owner, self.org_id, {
            "site_id": site["id"], "external_id": "PUMP-002", "source_system": "test-register",
            "name": "Second fixture pump", "criticality": "medium", "idempotency_key": "asset-two"})
        self.store.insert("runs", {"id": "pilot-pg-run", "owner": self.owner.subject,
            "goal": "Synthetic work-evidence acceptance", "dataset_name": "fixture.csv",
            "dataset_text": "Asset,Temperature\nPUMP-001,30\nPUMP-001,31\nPUMP-002,25\n",
            "state": "awaiting_approval", "created_at": "2026-10-21T12:00:00+00:00",
            "updated_at": "2026-10-21T12:01:00+00:00"})
        self.draft = {"asset_id": self.asset["id"], "title": "Inspect fixture bearing",
            "rationale": "Synthetic engineer-reviewed request", "run_id": "pilot-pg-run",
            "asset_column": "Asset", "source_asset_id": "PUMP-001", "priority": "high",
            "assignee": self.tech.subject, "due_date": "2026-11-01", "idempotency_key": "draft"}
        self.clock = datetime(2026, 10, 21, 13, tzinfo=timezone.utc)

    def assert_code(self, expected, function, *args):
        with self.assertRaises((OperationsError, ValidationError)) as caught:
            function(*args)
        self.assertEqual(caught.exception.code, expected)

    def test_authorization_completion_persist_across_connections_and_reconnect(self):
        draft = self.ops.create_work_order(self.owner, self.org_id, self.draft)
        authorization = {"status": "authorized", "expected_version": 1, "idempotency_key": "authorize"}
        authorized = self.other_ops.update_work_order(self.manager, self.org_id, draft["id"], authorization)
        self.assertEqual(authorized["authorized_by"], self.manager.subject)
        self.assert_code("stale_version", self.ops.update_work_order, self.owner, self.org_id, draft["id"],
                         {"priority": "critical", "expected_version": 1, "idempotency_key": "old-edit"})
        self.store.close()
        reopened = closing_store(self, open_store(PG_TEST_URL))
        fresh = Operations(reopened)
        loaded = fresh.work_order(self.tech, self.org_id, draft["id"])
        self.assertEqual(loaded["version"], 2)
        self.assertEqual(loaded["evidence"]["matching_records"], 2)
        started = fresh.update_work_order(self.tech, self.org_id, draft["id"],
            {"status": "in_progress", "expected_version": 2, "idempotency_key": "start"})
        finished = fresh.update_work_order(self.tech, self.org_id, draft["id"], {
            "status": "completed", "expected_version": started["version"], "idempotency_key": "complete",
            "completion": {"outcome": "bearing_replaced", "notes": "Synthetic repair observation",
                           "labor_hours": 2.25, "parts": [{"part": "TEST-BEARING", "quantity": 1}]}})
        persisted = self.other_ops.work_order(self.manager, self.org_id, draft["id"])
        self.assertEqual(persisted, finished)
        self.assertEqual(persisted["status"], "completed")
        self.assertEqual([a["actor"] for a in persisted["audit"]],
                         [self.owner.subject, self.manager.subject, self.tech.subject, self.tech.subject])
        # Retrying an acknowledged-lost authorization returns its receipt,
        # without reverting the subsequently completed order.
        replay = self.other_ops.update_work_order(self.manager, self.org_id, draft["id"], authorization)
        self.assertEqual(replay, authorized)
        self.assertEqual(fresh.work_order(self.owner, self.org_id, draft["id"])["version"], 4)
        self.assert_code("organization_not_found", fresh.work_order,
                         Principal("outsider", "admin", "jwt"), self.org_id, draft["id"])

    def test_concurrent_authorizations_have_one_winner_and_one_stale_conflict(self):
        draft = self.ops.create_work_order(self.owner, self.org_id, self.draft)
        barrier = threading.Barrier(2)
        services = (self.ops, self.other_ops)

        def authorize(index):
            barrier.wait(timeout=10)
            try:
                result = services[index].update_work_order(self.manager, self.org_id, draft["id"], {
                    "status": "authorized", "expected_version": 1, "idempotency_key": f"race-{index}"})
                return result["status"]
            except OperationsError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(authorize, index) for index in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertCountEqual(results, ["authorized", "stale_version"])
        row = self.ops.work_order(self.owner, self.org_id, draft["id"])
        self.assertEqual(row["version"], 2)
        self.assertEqual(len(row["audit"]), 2)

    def test_concurrent_identical_drafts_commit_one_record_and_receipt(self):
        barrier = threading.Barrier(2)
        services = (self.ops, self.other_ops)

        def draft(index):
            barrier.wait(timeout=10)
            return services[index].create_work_order(self.owner, self.org_id, self.draft)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(draft, index) for index in range(2)]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.second._exec("SELECT COUNT(*) AS n FROM work_orders")[0]["n"], 1)
        self.assertEqual(self.second._exec("SELECT COUNT(*) AS n FROM operation_audit WHERE entity_id = ?",
                         (results[0]["id"],))[0]["n"], 1)
        self.assertEqual(self.second._exec("SELECT COUNT(*) AS n FROM operation_requests WHERE request_key = 'draft'")[0]["n"], 1)

    def test_prospective_ledger_revision_and_cross_dialect_restore_keep_evidence(self):
        ledger = ReliabilityTrials(self.store, clock=lambda: self.clock)
        second_ledger = ReliabilityTrials(self.second, clock=lambda: self.clock)
        protocol = {"request_id": "protocol", "name": "Synthetic PostgreSQL shadow acceptance",
            "model_version": "fixture-model-v1", "baseline_name": "fixture-reference",
            "trained_through": (self.clock - timedelta(days=30)).isoformat(), "horizon_hours": 24,
            "threshold": .5, "failure_definition": "Confirmed fixture loss of function",
            "cohort_definition": "Registered fixture pumps only"}
        trial = ledger.create(self.owner, self.org_id, protocol)
        self.assertEqual(second_ledger.create(self.owner, self.org_id, protocol)["id"], trial["id"])
        prediction_body = {"request_id": "prediction", "revision": 1, "asset_id": self.asset["id"],
                           "probability": .8, "baseline_probability": .1}
        recorded = ledger.predict(self.owner, trial["id"], prediction_body)
        self.assertEqual(second_ledger.get(self.manager, trial["id"])["evidence_hash"], recorded["evidence_hash"])
        self.assert_code("conflict", second_ledger.predict, self.owner, trial["id"], {
            **prediction_body, "request_id": "stale-prediction", "asset_id": self.asset_two["id"]})
        self.assertEqual(second_ledger.predict(self.owner, trial["id"], prediction_body)["revision"], 2)
        prediction = recorded["predictions"][0]
        failure_time = self.clock + timedelta(hours=3)
        self.clock += timedelta(hours=25)
        adjudicated = second_ledger.adjudicate(self.manager, trial["id"], prediction["id"], {
            "revision": 2, "failed": True, "failure_at": failure_time.isoformat(), "actionable": True,
            "observed_through": self.clock.isoformat(), "evidence_reference": "synthetic-inspection/pg-1"})
        self.assertEqual(adjudicated["metrics"]["different_actor_adjudications"], 1)
        self.assertEqual(adjudicated["metrics"]["lead_time_hours"]["mean"], 3)
        order = self.ops.create_work_order(self.owner, self.org_id, self.draft)
        backup = create_backup(self.second)
        self.assertTrue(backup["tables"]["reliability_trials"])
        self.assertTrue(backup["tables"]["operation_requests"])
        with tempfile.TemporaryDirectory() as directory:
            local = open_store(sqlite_path=Path(directory) / "restore.db")
            try:
                restore_backup(local, backup)
                restored_trial = ReliabilityTrials(local, clock=lambda: self.clock).get(self.owner, trial["id"])
                self.assertEqual(restored_trial, adjudicated)
                self.assertEqual(Operations(local).work_order(self.owner, self.org_id, order["id"]), order)
                # The reverse direction exercises PostgreSQL foreign-key
                # ordering and exact replay/audit restoration for new tables.
                restore_backup(self.store, create_backup(local))
            finally:
                local.close()
        self.assertEqual(second_ledger.get(self.manager, trial["id"]), adjudicated)
        self.assertEqual(self.other_ops.create_work_order(self.owner, self.org_id, self.draft), order)


if __name__ == "__main__":
    unittest.main()
