"""Operational acceptance: isolation, explicit maintenance authority and recovery."""

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from pathlib import Path

from server.auth import Principal
from server.backup import create_backup, restore_backup
from server.erasure import erase, survey
from server.operations import LIMITS, Operations, OperationsError, require_org_access
from server.storage import TABLES, RESTORE_ORDER, open_store


class OperationsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = open_store(None, Path(self.temp.name) / "operations.db")
        self.addCleanup(self.store.close)
        self.ops = Operations(self.store)
        self.alice = Principal("alice", "owner", "test")
        self.bob = Principal("bob", "analyst", "test")
        self.viewer = Principal("alice", "viewer", "test")
        self.admin = Principal("operator", "admin", "test")
        self.org = self.ops.create_organization(self.alice, {"name": "Test depot", "idempotency_key": "org-1"})
        self.oid = self.org["id"]
        self.site = self.ops.create_site(self.alice, self.oid, {"code": "D1", "name": "Depot one", "idempotency_key": "site-1"})
        self.asset_body = {"site_id": self.site["id"], "external_id": "PUMP-001", "source_system": "plant-register",
                           "name": "Feed pump", "criticality": "high", "idempotency_key": "asset-1"}
        self.asset = self.ops.create_asset(self.alice, self.oid, self.asset_body)
        self.store.insert("runs", {"id": "run-alice", "goal": "Inspect pump", "dataset_name": "readings.csv",
                          "dataset_text": "Asset,Temp\nPUMP-001,30\nPUMP-001,42\nOTHER,20\n",
                          "state": "awaiting_approval", "created_at": "2026-10-21T00:00:00Z",
                          "updated_at": "2026-10-21T00:00:01Z", "owner": "alice"})
        self.body = {"asset_id": self.asset["id"], "title": "Inspect bearing", "rationale": "Engineer review required",
                     "run_id": "run-alice", "asset_column": "Asset", "source_asset_id": "PUMP-001",
                     "priority": "high", "assignee": "alice", "due_date": "2026-11-01", "idempotency_key": "draft-1"}

    def error(self, code, callable_, *args):
        with self.assertRaises(OperationsError) as found:
            callable_(*args)
        self.assertEqual(found.exception.code, code)
        return found.exception

    def member(self, subject="bob", role="technician", key="member-1"):
        org = require_org_access(self.store, self.alice, self.oid)
        return self.ops.set_member(self.alice, self.oid,
                                  {"subject": subject, "role": role, "expected_version": org["version"], "idempotency_key": key})

    def draft(self, **changes):
        return self.ops.create_work_order(self.alice, self.oid, {**self.body, **changes})

    def transition(self, order, status, principal=None, **changes):
        return self.ops.update_work_order(principal or self.alice, self.oid, order["id"],
               {"expected_version": order["version"], "status": status,
                "idempotency_key": f"{order['id']}-{order['version']}-{status}", **changes})

    def test_cross_tenant_and_platform_admin_need_explicit_membership(self):
        for principal in (self.bob, self.admin):
            error = self.error("organization_not_found", self.ops.overview, principal, self.oid)
            self.assertEqual(error.status, 404)
        self.assertEqual(self.ops.list_organizations(self.bob), {"organizations": []})

    def test_platform_permission_intersects_org_role(self):
        self.assertFalse(self.ops.overview(self.viewer, self.oid)["permissions"]["manage"])
        self.error("permission_denied", self.ops.create_site, self.viewer, self.oid,
                   {"code": "X", "name": "Another", "idempotency_key": "viewer-attempt"})
        self.error("permission_denied", self.ops.create_organization, self.viewer,
                   {"name": "Another", "idempotency_key": "viewer-attempt"})

    def test_create_replay_and_payload_reuse_are_distinct(self):
        self.assertEqual(self.ops.create_asset(self.alice, self.oid, self.asset_body), self.asset)
        self.error("idempotency_conflict", self.ops.create_asset, self.alice, self.oid,
                   {**self.asset_body, "name": "Changed"})
        self.assertEqual(len(self.ops.overview(self.alice, self.oid)["assets"]), 1)

    def test_no_last_owner_removal_or_stale_membership_write(self):
        self.error("last_owner", self.member, "alice", "removed")
        self.member()
        self.error("stale_version", self.ops.set_member, self.alice, self.oid,
                   {"subject": "bob", "role": "manager", "expected_version": 1, "idempotency_key": "stale-member"})

    def test_org_membership_does_not_share_personal_run(self):
        self.member()
        self.error("run_not_found", self.ops.create_work_order, self.bob, self.oid,
                   {**self.body, "assignee": "bob", "idempotency_key": "bob-draft"})

    def test_asset_must_match_real_source_with_unambiguous_identifier(self):
        self.error("asset_mismatch", self.ops.create_work_order, self.alice, self.oid,
                   {**self.body, "source_asset_id": "OTHER"})
        self.error("ambiguous_asset_column", self.ops.create_work_order, self.alice, self.oid,
                   {**self.body, "asset_column": "Invented"})
        self.store.update("runs", "run-alice", {"dataset_text": "Asset,Temp\nOTHER,20\n"})
        self.error("asset_not_in_evidence", self.draft)

    def test_duplicate_source_ids_across_systems_require_resolution(self):
        self.ops.create_asset(self.alice, self.oid, {**self.asset_body, "source_system": "other-system", "idempotency_key": "asset-2"})
        self.error("ambiguous_asset_identity", self.draft)

    def test_import_is_atomic_and_rejects_duplicate_assets(self):
        record = {key: value for key, value in self.asset_body.items() if key != "idempotency_key"}
        record["external_id"] = "NEW"
        self.error("duplicate_asset", self.ops.import_assets, self.alice, self.oid,
                   {"schema_version": 1, "idempotency_key": "batch", "assets": [record, record]})
        self.assertEqual(len(self.ops.overview(self.alice, self.oid)["assets"]), 1)

    def test_import_refuses_foreign_site_and_preserves_other_org(self):
        other = self.ops.create_organization(self.bob, {"name": "Other", "idempotency_key": "other"})
        site = self.ops.create_site(self.bob, other["id"], {"code": "X", "name": "Other site", "idempotency_key": "x"})
        self.error("record_not_found", self.ops.create_asset, self.alice, self.oid,
                   {**self.asset_body, "site_id": site["id"], "idempotency_key": "foreign-site"})

    def test_draft_import_rolls_back_all_records_when_any_evidence_is_invalid(self):
        self.error("run_not_found", self.ops.import_work_orders, self.alice, self.oid,
                   {"schema_version": 1, "idempotency_key": "import-orders", "work_orders": [self.body,
                    {**self.body, "run_id": "missing", "idempotency_key": "draft-2"}]})
        self.assertEqual(self.ops.overview(self.alice, self.oid)["work_orders"], [])
        result = self.ops.import_work_orders(self.alice, self.oid,
                   {"schema_version": 1, "idempotency_key": "import-orders", "work_orders": [self.body]})
        self.assertEqual(result["work_orders"][0]["status"], "draft")

    def test_capacity_applies_to_api_and_import_writes(self):
        with patch.dict(LIMITS, {"operation_assets": 1}):
            self.error("capacity_reached", self.ops.create_asset, self.alice, self.oid,
                       {**self.asset_body, "external_id": "NEW", "idempotency_key": "bounded"})

    def test_report_publication_never_authorizes_work(self):
        self.store.update("runs", "run-alice", {"state": "completed"})
        order = self.draft()
        self.assertEqual(order["status"], "draft")
        self.assertIsNone(order["authorized_by"])
        self.error("invalid_transition", self.transition, order, "in_progress")
        self.assertEqual(order["evidence"]["matching_records"], 2)
        encoded = json.dumps(order["evidence"])
        self.assertNotIn("Temp", encoded)
        self.assertNotIn("dataset_text", encoded)

    def test_complete_operational_loop_records_actual_actor_and_outcome(self):
        self.member()
        order = self.draft(assignee="bob")
        self.error("permission_denied", self.transition, order, "authorized", self.bob)
        order = self.transition(order, "authorized")
        self.assertEqual(order["authorized_by"], "alice")
        order = self.transition(order, "in_progress", self.bob)
        completion = {"outcome": "bearing_replaced", "notes": "Inspection and replacement recorded by technician",
                      "labor_hours": 2.5, "parts": [{"part": "BRG-20", "quantity": 1}]}
        order = self.transition(order, "completed", self.bob, completion=completion)
        self.assertEqual(order["completion"], completion)
        self.assertEqual([a["actor"] for a in order["audit"]], ["alice", "alice", "bob", "bob"])
        self.assertEqual(order["version"], 4)
        self.error("terminal_order", self.transition, order, "cancelled")

    def test_completion_requires_in_progress_outcome_and_finite_labor(self):
        order = self.transition(self.draft(), "authorized")
        self.error("invalid_transition", self.transition, order, "completed")
        order = self.transition(order, "in_progress")
        self.error("completion_required", self.transition, order, "completed")
        bad = {"expected_version": order["version"], "status": "completed", "idempotency_key": "bad-outcome",
               "completion": {"outcome": "repaired", "notes": "done", "labor_hours": -1}}
        self.error("invalid_labor", self.ops.update_work_order, self.alice, self.oid, order["id"], bad)

    def test_stale_write_cannot_overwrite_authorization_and_replay_is_safe(self):
        order = self.draft()
        authorized = self.transition(order, "authorized")
        replay = self.transition(order, "authorized")
        self.assertEqual(authorized, replay)
        self.error("stale_version", self.ops.update_work_order, self.alice, self.oid, order["id"],
                   {"expected_version": 1, "priority": "critical", "idempotency_key": "stale"})
        self.assertEqual(len(self.ops.overview(self.alice, self.oid)["work_orders"][0]["audit"]), 2)

    def test_rescheduling_invalidates_authorization(self):
        order = self.transition(self.draft(), "authorized")
        changed = self.ops.update_work_order(self.alice, self.oid, order["id"],
                  {"expected_version": 2, "priority": "critical", "idempotency_key": "reschedule"})
        self.assertEqual(changed["status"], "draft")
        self.assertIsNone(changed["authorized_by"])

    def test_technician_can_progress_only_assigned_work(self):
        self.member()
        order = self.transition(self.draft(), "authorized")
        self.error("permission_denied", self.transition, order, "in_progress", self.bob)

    def test_member_removal_requires_open_work_reassignment(self):
        self.member()
        self.draft(assignee="bob")
        self.error("reassign_work_required", self.member, "bob", "removed", "remove-bob")

    def test_concurrent_connections_commit_only_one_stale_version_transition(self):
        order = self.draft()
        other = open_store(None, Path(self.temp.name) / "operations.db")
        self.addCleanup(other.close)
        services = (self.ops, Operations(other))
        def authorize(index):
            try:
                return services[index].update_work_order(self.alice, self.oid, order["id"],
                       {"expected_version": 1, "status": "authorized", "idempotency_key": f"race-{index}"})["status"]
            except OperationsError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(authorize, range(2)))
        self.assertCountEqual(outcomes, ["authorized", "stale_version"])
        self.assertEqual(len(self.ops.work_order(self.alice, self.oid, order["id"])["audit"]), 2)

    def test_survey_matches_removable_operational_rows(self):
        self.draft()
        counts = survey(self.store, "alice")
        removed = erase(self.store, "alice")
        self.assertEqual(counts["rows"], removed["deleted"])
        self.assertEqual(counts["total_rows"], removed["total_rows"])

    def test_replay_is_refused_after_membership_revocation(self):
        self.member(role="manager")
        order = self.draft()
        self.transition(order, "authorized", self.bob)
        self.member("bob", "removed", "remove")
        self.error("organization_not_found", self.transition, order, "authorized", self.bob)

    def test_noop_cannot_add_a_misleading_authorization_audit(self):
        order = self.transition(self.draft(), "authorized")
        self.error("no_changes", self.ops.update_work_order, self.alice, self.oid, order["id"],
                   {"expected_version": 2, "idempotency_key": "empty"})
        self.assertEqual(len(self.ops.work_order(self.alice, self.oid, order["id"])["audit"]), 2)

    def test_backup_restore_preserves_operational_history_and_replay(self):
        order = self.transition(self.draft(), "authorized")
        self.store.upsert_worker_heartbeat("worker-test", "2026-10-21T00:00:00Z", "idle")
        self.store.insert("reliability_trials", {"id": "trial", "org_id": self.oid, "created_by": "alice",
                          "created_at": "now", "updated_at": "now", "revision": 1,
                          "protocol_json": "{}", "predictions_json": "[]"})
        backup = create_backup(self.store)
        self.assertEqual(set(TABLES), set(RESTORE_ORDER))
        with tempfile.TemporaryDirectory() as directory:
            other = open_store(None, Path(directory) / "restored.db")
            try:
                restore_backup(other, backup)
                restored = Operations(other)
                self.assertEqual(restored.overview(self.alice, self.oid)["work_orders"][0], order)
                self.assertEqual(restored.create_work_order(self.alice, self.oid, self.body)["id"], order["id"])
                self.assertEqual(other.list_worker_heartbeats()[0]["state"], "idle")
                self.assertEqual(other._exec("SELECT id FROM reliability_trials"), [{"id": "trial"}])
            finally:
                other.close()

    def test_personal_erasure_deletes_sole_member_organization_and_trials(self):
        self.draft()
        report = erase(self.store, "alice")
        self.assertEqual(report["deleted"]["work_orders"], 1)
        self.assertEqual(self.ops.list_organizations(self.alice)["organizations"], [])
        self.assertEqual(survey(self.store, "alice")["total_rows"], 0)

    def test_shared_org_last_owner_preflight_blocks_before_personal_deletion(self):
        self.member()
        self.error("transfer_ownership_required", erase, self.store, "alice")
        self.assertIsNotNone(self.store.get_run("run-alice"))
        self.member("bob", "owner", "promote")
        self.draft(assignee="bob")
        report = erase(self.store, "alice")
        self.assertEqual(report["organization_data_retained"], [self.oid])
        self.assertEqual(len(self.ops.overview(self.bob, self.oid)["work_orders"]), 1)
        self.assertEqual(self.ops.list_organizations(self.alice)["organizations"], [])

    def test_export_has_version_and_no_implicit_external_action(self):
        self.draft()
        result = self.ops.export(self.alice, self.oid)
        self.assertEqual(result["schema_version"], 1)
        self.assertFalse(result["external_actions_performed"])
        self.assertNotIn("dataset_text", json.dumps(result))


class OperationsApiTest(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from server.operations_api import install_operations_api
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = open_store(None, Path(self.temp.name) / "api.db")
        self.addCleanup(self.store.close)
        app = FastAPI()
        self.actor = Principal("alice", "owner", "test")
        install_operations_api(app, self.store, lambda: self.actor)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_router_round_trip_strict_fields_and_language(self):
        root = "/api/operations/organizations"
        response = self.client.post(root, json={"name": "Depot", "idempotency_key": "org"})
        self.assertEqual(response.status_code, 201, response.text)
        org_id = response.json()["id"]
        self.assertEqual(self.client.get(root).json()["organizations"][0]["id"], org_id)
        response = self.client.post(root + "/" + org_id + "/sites", json={"name": "X", "code": "X", "idempotency_key": "site", "owner": "someone"})
        self.assertEqual(response.status_code, 422)
        self.actor = Principal("mallory", "admin", "test")
        response = self.client.get(root + "/" + org_id + "/overview?language=ar")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "organization_not_found")
        self.assertIn("المؤسسة", response.json()["detail"]["message"])

    def test_completion_schema_refuses_boolean_quantities_and_injected_authority(self):
        response = self.client.patch("/api/operations/organizations/missing/work-orders/missing", json={
            "expected_version": 1, "idempotency_key": "bad", "status": "completed",
            "completion": {"outcome": "repaired", "notes": "done", "labor_hours": True, "parts": []}})
        self.assertEqual(response.status_code, 422)
        response = self.client.post("/api/operations/organizations/missing/work-orders", json={
            "asset_id": "a", "title": "t", "rationale": "r", "run_id": "r", "asset_column": "Asset",
            "source_asset_id": "1", "assignee": "alice", "due_date": "2026-11-01",
            "idempotency_key": "bad", "authorized_by": "alice", "status": "authorized"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
