"""Tenant-scoped maintenance execution; publication never authorizes work.

All mutations serialize on the organization, check the caller again inside
the transaction, and commit state, audit and replay receipt together.
External integration is a versioned import/export contract, never a network
action. Source datasets and report bodies are not copied into shared records.
"""

import csv
import hashlib
import io
import json
import math
import uuid
from datetime import date, datetime, timezone


ROLES = {"owner", "manager", "technician", "viewer"}
PRIORITIES = {"low", "medium", "high", "critical"}
ORG_PERMISSIONS = {
    "read": ROLES,
    "write": {"owner", "manager", "technician"},
    "manage": {"owner"},
    "authorize": {"owner", "manager"},
}
PLATFORM_PERMISSION = {"read": "read", "write": "write", "manage": "write", "authorize": "approve"}
LIMITS = {"organizations": 20, "organization_members": 100, "operation_sites": 100,
          "operation_assets": 5000, "work_orders": 10000, "operation_requests": 50000}
OPERATION_DELETE_ORDER = ("reliability_trials", "operation_requests", "operation_audit", "work_orders",
                          "operation_assets", "operation_sites", "organization_members", "organizations")


class OperationsError(ValueError):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def fail(status, code, message):
    raise OperationsError(status, code, message)


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier():
    return uuid.uuid4().hex


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def text(value, field, maximum=160, required=True):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        fail(422, "invalid_field", f"Invalid {field}.")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        fail(422, "invalid_field", f"Invalid {field}.")
    return value.strip()


def require_org_access(store, principal, org_id, permission="read"):
    """Membership AND platform privilege; admin never implies membership."""
    rows = store._exec("SELECT o.*, m.role FROM organizations o JOIN organization_members m "
                       "ON m.org_id = o.id WHERE o.id = ? AND m.subject = ?",
                       (org_id, principal.subject))
    if not rows:
        fail(404, "organization_not_found", "Organization not found.")
    org = rows[0]
    if (permission not in ORG_PERMISSIONS or org["role"] not in ORG_PERMISSIONS[permission]
            or not principal.can(PLATFORM_PERMISSION[permission])):
        fail(403, "permission_denied", "Your role cannot perform this organization action.")
    return org


def permissions(principal, role):
    return {name: role in allowed and principal.can(PLATFORM_PERMISSION[name])
            for name, allowed in ORG_PERMISSIONS.items()}


class Operations:
    def __init__(self, store):
        self.store = store

    def _bound(self, table, org_id):
        n = self.store._exec(f"SELECT COUNT(*) AS n FROM {table} WHERE org_id = ?", (org_id,))[0]["n"]
        if n >= LIMITS[table]:
            fail(409, "capacity_reached", "The organization has reached this record limit.")

    def _audit(self, org_id, entity_id, actor, action, version, detail=None):
        self.store.insert("operation_audit", {
            "id": identifier(), "org_id": org_id, "entity_id": entity_id,
            "actor": actor, "action": action, "version": version,
            "detail_json": canonical(detail or {}), "created_at": now()})

    def _mutate(self, principal, org_id, permission, action, payload, callback):
        key = text(payload.get("idempotency_key"), "idempotency_key", 128)
        digest = hashlib.sha256(canonical({"action": action, "payload": payload}).encode()).hexdigest()
        with self.store.atomic("operations:" + org_id):
            require_org_access(self.store, principal, org_id, permission)
            previous = self.store._exec("SELECT * FROM operation_requests WHERE org_id = ? "
                                        "AND actor = ? AND request_key = ?", (org_id, principal.subject, key))
            if previous:
                if previous[0]["payload_hash"] != digest:
                    fail(409, "idempotency_conflict", "This request key was already used with different input.")
                return json.loads(previous[0]["response_json"])
            self._bound("operation_requests", org_id)
            result = callback()
            self.store.insert("operation_requests", {
                "id": identifier(), "org_id": org_id, "actor": principal.subject,
                "request_key": key, "payload_hash": digest,
                "response_json": canonical(result), "created_at": now()})
            return result

    def list_organizations(self, principal):
        if not principal.can("read"):
            fail(403, "permission_denied", "Read permission required.")
        return {"organizations": self.store._exec("SELECT o.*, m.role FROM organizations o "
                "JOIN organization_members m ON m.org_id = o.id WHERE m.subject = ? ORDER BY o.created_at, o.id",
                (principal.subject,))}

    def create_organization(self, principal, payload):
        if not principal.can("write"):
            fail(403, "permission_denied", "Write permission required.")
        name = text(payload.get("name"), "name")
        key = text(payload.get("idempotency_key"), "idempotency_key", 128)
        # Deterministic ID binds creation retries to the authenticated subject.
        org_id = hashlib.sha256((principal.subject + "\0" + key).encode()).hexdigest()[:32]
        with self.store.atomic("operations:create:" + principal.subject):
            existing = self.store._exec("SELECT id FROM organizations WHERE id = ?", (org_id,))
            if existing:
                org = require_org_access(self.store, principal, org_id)
                if org["name"] != name:
                    fail(409, "idempotency_conflict", "This request key was already used with different input.")
                return org
            count = self.store._exec("SELECT COUNT(*) AS n FROM organization_members WHERE subject = ?",
                                     (principal.subject,))[0]["n"]
            if count >= LIMITS["organizations"]:
                fail(409, "capacity_reached", "Organization membership limit reached.")
            instant = now()
            self.store.insert("organizations", {"id": org_id, "name": name, "version": 1,
                                                "created_at": instant, "updated_at": instant})
            self.store.insert("organization_members", {"id": identifier(), "org_id": org_id,
                              "subject": principal.subject, "role": "owner", "created_at": instant})
            self._audit(org_id, org_id, principal.subject, "organization_created", 1)
            return require_org_access(self.store, principal, org_id)

    def _record(self, table, org_id, entity_id):
        rows = self.store._exec(f"SELECT * FROM {table} WHERE id = ? AND org_id = ?", (entity_id, org_id))
        if not rows:
            fail(404, "record_not_found", "Record not found in this organization.")
        return rows[0]

    def _order(self, row):
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        result["completion"] = json.loads(result.pop("completion_json"))
        result["audit"] = []
        for entry in self.store._exec("SELECT * FROM operation_audit WHERE org_id = ? AND entity_id = ? "
                                      "ORDER BY version, created_at, id", (row["org_id"], row["id"])):
            entry["detail"] = json.loads(entry.pop("detail_json"))
            result["audit"].append(entry)
        return result

    def overview(self, principal, org_id):
        org = require_org_access(self.store, principal, org_id)
        result = {"organization": org, "permissions": permissions(principal, org["role"]),
                  "principal_subject": principal.subject}
        for name, table in (("members", "organization_members"), ("sites", "operation_sites"),
                            ("assets", "operation_assets")):
            result[name] = self.store._exec(f"SELECT * FROM {table} WHERE org_id = ? ORDER BY created_at, id", (org_id,))
        # Bounded initial queue; export provides all records for interoperability.
        rows = self.store._exec("SELECT * FROM work_orders WHERE org_id = ? ORDER BY "
            "CASE WHEN status IN ('completed', 'cancelled') THEN 1 ELSE 0 END, "
            "CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
            "due_date, updated_at DESC, id LIMIT 200", (org_id,))
        result["work_orders"] = [self._order(row) for row in rows]
        result["work_order_count"] = self.store._exec("SELECT COUNT(*) AS n FROM work_orders WHERE org_id = ?", (org_id,))[0]["n"]
        result["work_orders_truncated"] = result["work_order_count"] > len(rows)
        return result

    def set_member(self, principal, org_id, payload):
        def change():
            org = require_org_access(self.store, principal, org_id, "manage")
            self._version(org, payload)
            subject = text(payload.get("subject"), "subject", 256)
            # Coordinate account erasure with grants to this subject. A
            # database deadlock aborts the whole transaction rather than
            # publishing a partial membership change.
            self.store._lock_transaction("operations:create:" + subject)
            role = payload.get("role")
            if role not in ROLES | {"removed"}:
                fail(422, "invalid_role", "Invalid organization role.")
            existing = self.store._exec("SELECT * FROM organization_members WHERE org_id = ? AND subject = ?", (org_id, subject))
            if existing and existing[0]["role"] == "owner" and role != "owner":
                owners = self.store._exec("SELECT COUNT(*) AS n FROM organization_members WHERE org_id = ? AND role = 'owner'", (org_id,))[0]["n"]
                if owners <= 1:
                    fail(409, "last_owner", "Transfer ownership before removing the last owner.")
            if role in {"viewer", "removed"} and self.store._exec(
                    "SELECT id FROM work_orders WHERE org_id = ? AND assignee = ? "
                    "AND status NOT IN ('completed', 'cancelled') LIMIT 1", (org_id, subject)):
                fail(409, "reassign_work_required", "Reassign or close this member's open work before removing their execution role.")
            if role == "removed":
                self.store._exec("DELETE FROM organization_members WHERE org_id = ? AND subject = ?", (org_id, subject))
            elif existing:
                self.store.update("organization_members", existing[0]["id"], {"role": role})
            else:
                self._bound("organization_members", org_id)
                memberships = self.store._exec("SELECT COUNT(*) AS n FROM organization_members WHERE subject = ?", (subject,))[0]["n"]
                if memberships >= LIMITS["organizations"]:
                    fail(409, "capacity_reached", "Organization membership limit reached.")
                self.store.insert("organization_members", {"id": identifier(), "org_id": org_id,
                                  "subject": subject, "role": role, "created_at": now()})
            self.store.update("organizations", org_id, {"version": org["version"] + 1, "updated_at": now()})
            self._audit(org_id, org_id, principal.subject, "membership_changed", org["version"] + 1,
                        {"subject": subject, "role": role})
            return {"org_id": org_id, "version": org["version"] + 1, "subject": subject, "role": role}
        return self._mutate(principal, org_id, "manage", "membership", payload, change)

    def create_site(self, principal, org_id, payload):
        def create():
            self._bound("operation_sites", org_id)
            code, name = text(payload.get("code"), "code", 80), text(payload.get("name"), "name")
            if self.store._exec("SELECT id FROM operation_sites WHERE org_id = ? AND code = ?", (org_id, code)):
                fail(409, "duplicate_site", "A site with this code already exists.")
            row = {"id": identifier(), "org_id": org_id, "code": code, "name": name, "created_at": now()}
            self.store.insert("operation_sites", row)
            self._audit(org_id, row["id"], principal.subject, "site_created", 1)
            return row
        return self._mutate(principal, org_id, "manage", "site", payload, create)

    def _create_asset(self, principal, org_id, payload):
        self._bound("operation_assets", org_id)
        site = self._record("operation_sites", org_id, payload.get("site_id"))
        external_id = text(payload.get("external_id"), "external_id")
        system = text(payload.get("source_system"), "source_system", 80)
        name = text(payload.get("name"), "name")
        criticality = payload.get("criticality", "medium")
        if criticality not in PRIORITIES:
            fail(422, "invalid_priority", "Invalid criticality.")
        if self.store._exec("SELECT id FROM operation_assets WHERE org_id = ? AND source_system = ? AND external_id = ?", (org_id, system, external_id)):
            fail(409, "duplicate_asset", "This source system and asset identifier already exist.")
        row = {"id": identifier(), "org_id": org_id, "site_id": site["id"], "external_id": external_id,
               "source_system": system, "name": name, "criticality": criticality, "version": 1, "created_at": now()}
        self.store.insert("operation_assets", row)
        self._audit(org_id, row["id"], principal.subject, "asset_registered", 1)
        return row

    def create_asset(self, principal, org_id, payload):
        return self._mutate(principal, org_id, "manage", "asset", payload,
                            lambda: self._create_asset(principal, org_id, payload))

    def import_assets(self, principal, org_id, payload):
        def create():
            rows = payload.get("assets")
            if payload.get("schema_version") != 1 or not isinstance(rows, list) or not 1 <= len(rows) <= 500:
                fail(422, "invalid_import", "Provide schema_version 1 and between 1 and 500 asset records.")
            return {"schema_version": 1, "assets": [self._create_asset(principal, org_id, row) for row in rows]}
        return self._mutate(principal, org_id, "manage", "asset_import", payload, create)

    def _evidence(self, principal, asset, payload):
        identities = self.store._exec("SELECT COUNT(*) AS n FROM operation_assets WHERE org_id = ? AND external_id = ?",
                                      (asset["org_id"], asset["external_id"]))[0]["n"]
        if identities != 1:
            fail(422, "ambiguous_asset_identity", "This identifier occurs in multiple source systems; resolve its identity before sharing evidence.")
        run = self.store.get_run(text(payload.get("run_id"), "run_id", 64))
        # Even platform operators must explicitly own the source. Membership
        # in the organization never grants access to another member's runs.
        if not run or (run.get("owner") or "local-owner") != principal.subject:
            fail(404, "run_not_found", "Source run not found.")
        if run["state"] not in {"awaiting_approval", "completed"}:
            fail(409, "evidence_not_ready", "Source analysis must finish before drafting maintenance work.")
        column = text(payload.get("asset_column"), "asset_column", 200)
        source_id = text(payload.get("source_asset_id"), "source_asset_id")
        if source_id != asset["external_id"]:
            fail(422, "asset_mismatch", "Source asset identifier does not match the registered asset.")
        source = self.store.get_dataset(run["dataset_id"]) if run.get("dataset_id") else None
        if source and source.get("owner") != principal.subject:
            fail(404, "run_not_found", "Source run not found.")
        content = source["content"] if source else run.get("dataset_text", "")
        reader = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames or []
        if headers.count(column) != 1:
            fail(422, "ambiguous_asset_column", "Select one unambiguous source asset column.")
        matches = sum(1 for row in reader if row.get(column) == source_id)
        if not matches:
            fail(422, "asset_not_in_evidence", "The registered asset identifier is absent from the source analysis.")
        return {"run_id": run["id"], "run_updated_at": run["updated_at"],
                "dataset_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "asset_column": column, "source_asset_id": source_id,
                "matching_records": matches, "captured_at": now()}

    def _schedule(self, org_id, payload):
        assignee = text(payload.get("assignee"), "assignee", 256)
        member = self.store._exec("SELECT role FROM organization_members WHERE org_id = ? AND subject = ?", (org_id, assignee))
        if not member or member[0]["role"] not in ORG_PERMISSIONS["write"]:
            fail(422, "invalid_assignee", "Assign work to an active owner, manager or technician.")
        due = payload.get("due_date")
        try:
            if not isinstance(due, str) or len(due) != 10 or date.fromisoformat(due).isoformat() != due:
                raise ValueError
        except ValueError:
            fail(422, "invalid_date", "Use a valid due date in YYYY-MM-DD format.")
        priority = payload.get("priority")
        if priority not in PRIORITIES:
            fail(422, "invalid_priority", "Invalid priority.")
        return {"assignee": assignee, "due_date": due, "priority": priority}

    def create_work_order(self, principal, org_id, payload):
        def create():
            self._bound("work_orders", org_id)
            asset = self._record("operation_assets", org_id, payload.get("asset_id"))
            row = {"id": identifier(), "org_id": org_id, "asset_id": asset["id"],
                   "title": text(payload.get("title"), "title", 200),
                   "rationale": text(payload.get("rationale"), "rationale", 2000),
                   "status": "draft", **self._schedule(org_id, payload),
                   "evidence_json": canonical(self._evidence(principal, asset, payload)),
                   "completion_json": "{}", "version": 1, "created_by": principal.subject,
                   "authorized_by": None, "created_at": now(), "updated_at": now()}
            self.store.insert("work_orders", row)
            self._audit(org_id, row["id"], principal.subject, "work_drafted", 1)
            return self._order(row)
        return self._mutate(principal, org_id, "write", "work_draft", payload, create)

    def import_work_orders(self, principal, org_id, payload):
        def create():
            rows = payload.get("work_orders")
            if payload.get("schema_version") != 1 or not isinstance(rows, list) or not 1 <= len(rows) <= 100:
                fail(422, "invalid_import", "Provide schema_version 1 and between 1 and 100 work order drafts.")
            keys = [row.get("idempotency_key") for row in rows if isinstance(row, dict)]
            if len(keys) != len(rows) or len(set(keys)) != len(keys) or payload["idempotency_key"] in keys:
                fail(422, "invalid_import", "Each draft and the import require distinct request keys.")
            return {"schema_version": 1, "work_orders": [self.create_work_order(principal, org_id, row) for row in rows]}
        return self._mutate(principal, org_id, "write", "work_import", payload, create)

    def work_order(self, principal, org_id, order_id):
        require_org_access(self.store, principal, org_id)
        return self._order(self._record("work_orders", org_id, order_id))

    def _version(self, row, payload):
        version = payload.get("expected_version")
        if isinstance(version, bool) or not isinstance(version, int) or version != row["version"]:
            fail(409, "stale_version", "The record changed. Reload before saving.")

    def _completion(self, value):
        if not isinstance(value, dict):
            fail(422, "completion_required", "Record a maintenance outcome before completing work.")
        result = {"outcome": text(value.get("outcome"), "outcome", 120),
                  "notes": text(value.get("notes"), "notes", 2000)}
        hours = value.get("labor_hours")
        if isinstance(hours, bool) or not isinstance(hours, (int, float)) or not math.isfinite(hours) or not 0 <= hours <= 10000:
            fail(422, "invalid_labor", "Record finite, nonnegative labor hours.")
        result["labor_hours"] = hours
        parts = value.get("parts", [])
        if not isinstance(parts, list) or len(parts) > 100:
            fail(422, "invalid_parts", "Invalid parts list.")
        result["parts"] = []
        for item in parts:
            if not isinstance(item, dict):
                fail(422, "invalid_parts", "Invalid parts entry.")
            quantity = item.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or not 0 < quantity <= 1000000:
                fail(422, "invalid_parts", "Part quantity must be finite and positive.")
            result["parts"].append({"part": text(item.get("part"), "part"), "quantity": quantity})
        return result

    def update_work_order(self, principal, org_id, order_id, payload):
        permission = "authorize" if payload.get("status") in {"authorized", "cancelled"} else "write"
        def change():
            org = require_org_access(self.store, principal, org_id, permission)
            row = self._record("work_orders", org_id, order_id)
            self._version(row, payload)
            if row["status"] in {"completed", "cancelled"}:
                fail(409, "terminal_order", "Completed or cancelled work cannot be changed.")
            status = payload.get("status", row["status"])
            allowed = {"draft": {"draft", "authorized", "cancelled"},
                       "authorized": {"authorized", "in_progress", "cancelled"},
                       "in_progress": {"in_progress", "completed", "cancelled"}}
            if status not in allowed[row["status"]]:
                fail(409, "invalid_transition", "This maintenance status transition is not allowed.")
            if org["role"] == "technician" and (row["assignee"] != principal.subject
                    or any(key in payload for key in ("priority", "assignee", "due_date"))):
                fail(403, "permission_denied", "Technicians can progress only their own assigned work.")
            updates = {"status": status, "version": row["version"] + 1, "updated_at": now()}
            if any(key in payload for key in ("priority", "assignee", "due_date")):
                updates.update(self._schedule(org_id, {**row, **payload}))
                changed = any(updates[key] != row[key] for key in ("priority", "assignee", "due_date"))
                if changed and row["status"] == "in_progress":
                    fail(409, "work_in_progress", "Cancel and create a replacement to change work already in progress.")
                if changed and row["status"] == "authorized":
                    # Material scheduling changes need a new explicit decision.
                    updates.update(status="draft", authorized_by=None)
                    status = "draft"
            if status == "authorized" and row["status"] == "draft":
                updates["authorized_by"] = principal.subject
            if status == "completed":
                updates["completion_json"] = canonical(self._completion(payload.get("completion")))
            elif "completion" in payload:
                fail(422, "invalid_completion", "Completion evidence is accepted only when work is completed.")
            if all(value == row.get(key) for key, value in updates.items()
                   if key not in {"version", "updated_at"}):
                fail(422, "no_changes", "No maintenance change was supplied.")
            self.store.update("work_orders", order_id, updates)
            detail = {key: value for key, value in updates.items() if key not in {"completion_json", "updated_at"}}
            self._audit(org_id, order_id, principal.subject, "work_" + status,
                        updates["version"], detail)
            return self._order(self._record("work_orders", org_id, order_id))
        return self._mutate(principal, org_id, permission, "work_update:" + order_id, payload, change)

    def export(self, principal, org_id):
        result = self.overview(principal, org_id)
        result["work_orders"] = [self._order(row) for row in self.store._exec(
            "SELECT * FROM work_orders WHERE org_id = ? ORDER BY created_at, id", (org_id,))]
        result["work_orders_truncated"] = False
        return {"schema_version": 1, "exported_at": now(), "external_actions_performed": False, **result}


def operations_erasure_plan(store, subject):
    """Business records belong to the organization, not an individual actor."""
    memberships = store._exec("SELECT * FROM organization_members WHERE subject = ?", (subject,))
    remove_orgs, retained_orgs = [], []
    for member in memberships:
        rows = store._exec("SELECT subject, role FROM organization_members WHERE org_id = ?", (member["org_id"],))
        if len(rows) == 1:
            remove_orgs.append(member["org_id"])
        else:
            if member["role"] == "owner" and sum(row["role"] == "owner" for row in rows) == 1:
                fail(409, "transfer_ownership_required", "Transfer shared organization ownership before personal erasure.")
            if store._exec("SELECT id FROM work_orders WHERE org_id = ? AND assignee = ? "
                           "AND status NOT IN ('completed', 'cancelled') LIMIT 1", (member["org_id"], subject)):
                fail(409, "reassign_work_required", "Reassign or close your shared organization work before personal erasure.")
            retained_orgs.append(member["org_id"])
    return {"delete_organizations": remove_orgs, "retained_organizations": retained_orgs}


def operations_erasure_counts(store, subject, plan):
    counts = {table: 0 for table in OPERATION_DELETE_ORDER}
    removed = set(plan["delete_organizations"])
    for org_id in removed:
        for table in OPERATION_DELETE_ORDER:
            column = "id" if table == "organizations" else "org_id"
            counts[table] += store._exec(f"SELECT COUNT(*) AS n FROM {table} WHERE {column} = ?", (org_id,))[0]["n"]
    for table, column in (("organization_members", "subject"), ("operation_requests", "actor")):
        rows = store._exec(f"SELECT org_id FROM {table} WHERE {column} = ?", (subject,))
        counts[table] += sum(row["org_id"] not in removed for row in rows)
    return counts


def erase_operations(store, subject, plan):
    deleted = {table: 0 for table in OPERATION_DELETE_ORDER}
    for org_id in plan["delete_organizations"]:
        from server.rmd_schema import erase_org_rmd
        erase_org_rmd(store, org_id)
        for table in OPERATION_DELETE_ORDER:
            column = "id" if table == "organizations" else "org_id"
            deleted[table] += store._exec_rowcount(f"DELETE FROM {table} WHERE {column} = ?", (org_id,))
    deleted["organization_members"] += store._exec_rowcount(
        "DELETE FROM organization_members WHERE subject = ?", (subject,))
    # Remove replay receipts since they may duplicate private request responses.
    deleted["operation_requests"] += store._exec_rowcount("DELETE FROM operation_requests WHERE actor = ?", (subject,))
    return deleted
