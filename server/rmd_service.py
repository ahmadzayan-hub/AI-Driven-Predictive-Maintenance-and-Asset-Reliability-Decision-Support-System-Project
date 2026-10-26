"""Durable, permission-scoped evidence workspaces. No model consumes these rows.

All source bytes, extracted text, mappings and snapshots live in the existing
SQL store. User-facing exports are narrow snapshot exports, never operator
backups. Authority, relationship review and maintenance execution stay separate.
"""

import base64
from copy import deepcopy
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import os
from pathlib import PurePath
import re
import uuid

from server import executive_export, rmd_analytics, rmd_ingestion
from server.operations import OperationsError, require_org_access
from server.rmd_schema import ensure_schema, erase_pack_rmd

MAX_SOURCES = 50
MAX_ANALYSES = 100
MAX_RECORDS = 100_000
MAX_SOURCE_BYTES = 4_000_000
MAX_METADATA_BYTES = 32_000_000
MAX_ARTIFACT_BYTES = 32_000_000
MAX_PACK_BYTES = 200_000_000
FIELDS = frozenset(("sr_id", "wo_id", "wo_status", "event_date", "location", "category",
                    "symptom", "assessment", "recovery_action", "suspected_cause",
                    "verified_root_cause", "rca_evidence", "source_reconciliation_label",
                    "comparison_source", "due_date", "outstanding_status"))
GRAINS = frozenset(("mms_work_order", "occ_event", "sr_reconciliation", "summary", "other"))
VALUE_STATES = frozenset(("unknown", "not_applicable", "not_measured", "blank",
                          "unresolved_placeholder", "recorded", "measured_zero"))


class RmdError(ValueError):
    def __init__(self, status, code, message, arabic="تعذّر تنفيذ إجراء الأدلة. راجع النطاق والصلاحيات والمدخلات."):
        super().__init__(message)
        self.status, self.code, self.message, self.arabic = status, code, message, arabic


def fail(code, message, status=422, arabic=None):
    raise RmdError(status, code, message, arabic or "تعذّر تنفيذ إجراء الأدلة. راجع النطاق والصلاحيات والمدخلات.")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex


def text(value, field, maximum=200, required=True):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        fail("invalid_field", f"Invalid {field}.")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        fail("invalid_field", f"Invalid {field}.")
    return value.strip()


def bi(value, language="en"):
    if isinstance(value, dict):
        return str(value.get(language) or value.get("en") or "")
    return "" if value is None else str(value)


def digest_candidates(digest, field):
    """Candidate identifiers are labelled as candidates, never approved facts."""
    candidate = digest.get(field)
    if not isinstance(candidate, dict):
        return candidate if isinstance(candidate, str) else None
    values = list(dict.fromkeys(str(x["text"]) for x in candidate.get("items", [])
                                if isinstance(x, dict) and x.get("text")))
    return "; ".join(values) or None


def _version(payload, actual):
    value = payload.get("expected_revision", payload.get("expected_version"))
    if not isinstance(value, int) or isinstance(value, bool) or value != actual:
        fail("stale_revision", "Refresh the evidence before changing it.", 409,
             "حدّث الأدلة قبل تعديلها.")


class RmdService:
    def __init__(self, store, identity_mode="local", env=None):
        self.store = store
        self.identity_mode = identity_mode
        self.env = os.environ if env is None else env
        self.vault_dir = None
        # Existing application storage registers this schema. Direct service
        # callers also receive additive, idempotent setup.
        ensure_schema(store)

    def _pack(self, principal, pack_id, permission="read"):
        if not principal.can("read"):
            fail("permission_denied", "Read permission required.", 403)
        rows = self.store._exec("SELECT * FROM rmd_packs WHERE id = ?", (pack_id,))
        if not rows:
            fail("pack_not_found", "Evidence pack not found.", 404)
        pack = rows[0]
        if pack["organization_id"]:
            try:
                require_org_access(self.store, principal, pack["organization_id"], permission)
            except OperationsError as error:
                if error.status == 404:
                    fail("pack_not_found", "Evidence pack not found.", 404)
                fail("permission_denied", "Your organization role cannot perform this action.", 403)
        else:
            if pack["owner"] != principal.subject:
                # Platform administration is not private-document ownership.
                fail("pack_not_found", "Evidence pack not found.", 404)
            platform = "approve" if permission == "authorize" else permission
            if not principal.can(platform):
                fail("permission_denied", "Your role cannot perform this evidence action.", 403)
        return pack

    def _source(self, principal, pack_id, source_id, permission="read"):
        self._pack(principal, pack_id, permission)
        rows = self.store._exec("SELECT * FROM rmd_sources WHERE id = ? AND pack_id = ?", (source_id, pack_id))
        if not rows:
            fail("source_not_found", "Evidence source not found.", 404)
        return rows[0]

    def _analysis(self, principal, pack_id, analysis_id):
        self._pack(principal, pack_id)
        rows = self.store._exec("SELECT * FROM rmd_analyses WHERE id = ? AND pack_id = ?", (analysis_id, pack_id))
        if not rows:
            fail("analysis_not_found", "Evidence analysis not found.", 404)
        return rows[0]

    def _audit(self, principal, pack_id, action, entity_id, revision, detail=None):
        self.store.insert("rmd_audit", {"id": uid(), "pack_id": pack_id, "actor": principal.subject,
            "action": action, "entity_id": entity_id, "revision": revision,
            "detail_json": canonical(detail or {}), "created_at": now()})

    def _bump(self, pack):
        self.store.update("rmd_packs", pack["id"], {"revision": pack["revision"] + 1, "updated_at": now()})

    def _request(self, principal, operation, payload, callback, pack_id=None):
        key = payload.get("idempotency_key")
        if key is None:
            return callback()
        key = text(key, "idempotency_key", 128)
        digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
        previous = self.store._exec("SELECT * FROM rmd_requests WHERE owner = ? AND operation = ? AND request_key = ?",
                                    (principal.subject, operation, key))
        if previous:
            if previous[0]["payload_hash"] != digest:
                fail("idempotency_conflict", "This request key was already used with different input.", 409)
            return json.loads(previous[0]["response_json"])
        count = self.store._exec("SELECT COUNT(*) AS n FROM rmd_requests WHERE owner = ?", (principal.subject,))[0]["n"]
        if count >= 50_000:
            fail("capacity_reached", "The request history limit has been reached.", 409)
        result = callback()
        self.store.insert("rmd_requests", {"id": uid(), "owner": principal.subject,
            "pack_id": pack_id or result.get("id"), "operation": operation, "request_key": key,
            "payload_hash": digest, "response_json": canonical(result), "created_at": now()})
        return result

    def list_packs(self, principal):
        if not principal.can("read"):
            fail("permission_denied", "Read permission required.", 403)
        rows = self.store._exec("SELECT DISTINCT p.* FROM rmd_packs p LEFT JOIN organization_members m "
            "ON m.org_id = p.organization_id AND m.subject = ? "
            "WHERE (p.organization_id IS NULL AND p.owner = ?) OR "
            "(p.organization_id IS NOT NULL AND m.role IN ('owner','manager','technician','viewer')) "
            "ORDER BY p.created_at DESC, p.id LIMIT 200", (principal.subject, principal.subject))
        return {"packs": [self.get_pack(principal, row["id"]) for row in rows]}

    def create_pack(self, principal, payload):
        if not principal.can("write"):
            fail("permission_denied", "Write permission required.", 403)
        if "owner" in payload or "owner_id" in payload:
            fail("invalid_owner", "Ownership comes from the authenticated caller.")
        title = text(payload.get("title"), "title", 200)
        org = payload.get("organization_id") or None
        with self.store.atomic("rmd-owner:" + principal.subject):
            if org:
                try:
                    require_org_access(self.store, principal, text(org, "organization_id", 128), "write")
                except OperationsError as error:
                    fail(error.code, error.message, error.status)
            def create():
                n = self.store._exec("SELECT COUNT(*) AS n FROM rmd_packs WHERE owner = ?", (principal.subject,))[0]["n"]
                if n >= 100:
                    fail("capacity_reached", "The evidence pack limit has been reached.", 409)
                key, stamp = uid(), now()
                self.store.insert("rmd_packs", {"id": key, "owner": principal.subject,
                    "organization_id": org, "title": title, "revision": 1,
                    "created_at": stamp, "updated_at": stamp})
                self._audit(principal, key, "pack_created", key, 1)
                return self.get_pack(principal, key)
            return self._request(principal, "pack:create", payload, create)

    def _source_summary(self, row):
        metadata = json.loads(row["metadata_json"])
        digest = metadata.get("document", {}).get("digest", {})
        return {"id": row["id"], "name": row["name"], "kind": row["kind"], "sha256": row["sha256"],
            "revision": row["revision"], "created_at": row["created_at"],
            "mapping_status": "confirmed" if json.loads(row["mapping_json"]).get("sheets") else "requires_confirmation" if row["kind"] == "workbook" else "not_applicable",
            "coverage": metadata.get("coverage", {}), "warnings": metadata.get("warnings", []),
            "document_code": digest_candidates(digest, "document_code"),
            "document_revision": digest_candidates(digest, "revision"),
            "document_identity_review_required": True,
            "applicability": json.loads(row["applicability_json"])}

    def get_pack(self, principal, pack_id):
        pack = self._pack(principal, pack_id)
        permissions = {"read": True}
        for permission, label in (("write", "write"), ("authorize", "review")):
            try:
                self._pack(principal, pack_id, permission)
                permissions[label] = True
            except RmdError:
                permissions[label] = False
        sources = self.store._exec("SELECT * FROM rmd_sources WHERE pack_id = ? ORDER BY created_at,id", (pack_id,))
        analyses = self.store._exec("SELECT id,created_at,pack_revision,fingerprint,language FROM rmd_analyses "
                                    "WHERE pack_id = ? ORDER BY created_at DESC,id DESC", (pack_id,))
        return {**pack, "sources": [self._source_summary(row) for row in sources], "analyses": analyses, "permissions": permissions,
                "data_mode": "private_evidence", "publication_state": "not_published"}

    def import_source(self, principal, pack_id, filename, data, kind):
        self._pack(principal, pack_id, "write")
        name = text(filename, "filename", 240)
        if name != PurePath(name).name or any(x in name for x in ("/", "\\", "\x00")):
            fail("invalid_filename", "Use a filename without a directory path.")
        if not isinstance(data, bytes) or not data or len(data) > MAX_SOURCE_BYTES:
            fail("invalid_source_size", "The source must contain at most 4 MB.", 413)
        if kind not in ("procedure", "workbook"):
            fail("invalid_source_kind", "Choose a procedure or workbook source.")
        digest = hashlib.sha256(data).hexdigest()
        previous = self.store._exec("SELECT id FROM rmd_sources WHERE pack_id = ? AND name = ? AND kind = ? AND sha256 = ?",
                                    (pack_id, name, kind, digest))
        if previous:
            return self.get_source(principal, pack_id, previous[0]["id"])
        converter = None
        if name.lower().endswith(".doc") and self.identity_mode != "local":
            converter = self.env.get("RMD_SANDBOXED_DOC_CONVERTER")
            if not converter:
                fail("conversion_not_configured", "Hosted legacy Word conversion needs an explicitly configured sandboxed converter.", 409)
        extraction = rmd_ingestion.ingest_source(name, data, kind, converter=converter)
        metadata = extraction["metadata"]
        metadata_json = canonical(metadata)
        if len(metadata_json.encode()) > MAX_METADATA_BYTES:
            fail("extraction_limit", "The extracted source is too large to retain safely.", 413)
        artifacts, total = [], 0
        for index, item in enumerate(extraction.get("artifacts", [])):
            binary = item["data"]
            total += len(binary)
            if total > MAX_ARTIFACT_BYTES:
                fail("extraction_limit", "The extracted artifacts exceed the retention limit.", 413)
            artifacts.append({"id": str(index), "name": item["name"], "content_type": item["content_type"],
                              "sha256": hashlib.sha256(binary).hexdigest(),
                              "data_base64": base64.b64encode(binary).decode("ascii")})
        with self.store.atomic("rmd-pack:" + pack_id):
            pack = self._pack(principal, pack_id, "write")
            previous = self.store._exec("SELECT id FROM rmd_sources WHERE pack_id = ? AND name = ? AND kind = ? AND sha256 = ?",
                                        (pack_id, name, kind, digest))
            if previous:
                return self.get_source(principal, pack_id, previous[0]["id"])
            sources = self.store._exec("SELECT metadata_json FROM rmd_sources WHERE pack_id = ?", (pack_id,))
            if len(sources) >= MAX_SOURCES:
                fail("capacity_reached", "The source limit has been reached.", 409)
            stored_bytes = sum(json.loads(s["metadata_json"]).get("bytes", 0) for s in sources)
            if stored_bytes + len(data) > MAX_PACK_BYTES:
                fail("capacity_reached", "The pack source-byte limit has been reached.", 409)
            key, stamp = uid(), now()
            self.store.insert("rmd_sources", {"id": key, "pack_id": pack_id, "name": name, "kind": kind,
                "sha256": digest, "revision": 1, "metadata_json": metadata_json,
                "mapping_json": "{}", "original_base64": base64.b64encode(data).decode("ascii"),
                "artifacts_json": canonical(artifacts), "applicability_json": canonical({"state": "unverified",
                    "reason": "Supplied reference copy; current applicability and supersession are unverified.",
                    "evidence": [], "decided_by": None}), "created_at": stamp, "updated_at": stamp})
            self._bump(pack)
            self._audit(principal, pack_id, "source_imported", key, 1, {"sha256": digest, "kind": kind})
            return self.get_source(principal, pack_id, key)

    def get_source(self, principal, pack_id, source_id):
        row = self._source(principal, pack_id, source_id)
        metadata = deepcopy(json.loads(row["metadata_json"]))
        for sheet in metadata.get("sheets", []):
            sheet["preview_total_rows"] = len(sheet.get("rows", []))
            sheet["rows"] = sheet.get("rows", [])[:20]
            sheet["preview_truncated"] = sheet["preview_total_rows"] > 20
        artifacts = [{k: v for k, v in item.items() if k != "data_base64"}
                     for item in json.loads(row["artifacts_json"])]
        return {**metadata, **self._source_summary(row), "mapping": json.loads(row["mapping_json"]),
                "artifacts": artifacts}

    def download_source(self, principal, pack_id, source_id, artifact_id=None):
        row = self._source(principal, pack_id, source_id)
        if artifact_id is not None:
            item = next((x for x in json.loads(row["artifacts_json"]) if x["id"] == artifact_id), None)
            if item is None:
                fail("artifact_not_found", "Evidence artifact not found.", 404)
            return base64.b64decode(item["data_base64"]), item["content_type"], item["name"]
        mimes = {".doc": "application/msword", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                 ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12"}
        return base64.b64decode(row["original_base64"]), mimes.get(PurePath(row["name"]).suffix.lower(), "application/octet-stream"), row["name"]

    def save_mapping(self, principal, pack_id, source_id, payload):
        with self.store.atomic("rmd-pack:" + pack_id):
            pack = self._pack(principal, pack_id, "write")
            source = self._source(principal, pack_id, source_id, "write")
            if source["kind"] != "workbook":
                fail("mapping_not_applicable", "Only workbook sources have sheet mappings.")
            if payload.get("expected_revision") is not None:
                _version(payload, source["revision"])
            elif json.loads(source["mapping_json"]).get("sheets"):
                fail("stale_revision", "A mapping update needs its current source revision.", 409)
            sheets = payload.get("sheets")
            if not isinstance(sheets, list) or not sheets or len(sheets) > 32:
                fail("invalid_mapping", "Confirm the sheet grain, header and columns.")
            metadata = json.loads(source["metadata_json"])
            originals = {s["name"]: s for s in metadata.get("sheets", [])}
            names, mappings = set(), []
            for mapping in sheets:
                if not isinstance(mapping, dict) or mapping.get("name") not in originals or mapping["name"] in names:
                    fail("invalid_mapping", "Each mapped sheet must identify one supplied worksheet.")
                names.add(mapping["name"])
                sheet, role = originals[mapping["name"]], mapping.get("role")
                header, columns = mapping.get("header_row"), mapping.get("columns")
                if not isinstance(role, str) or role not in GRAINS or not isinstance(header, int) or isinstance(header, bool) or header < 1:
                    fail("invalid_mapping", "The sheet needs a valid grain and source header row.")
                available = {c["letter"] for c in sheet.get("columns", [])}
                if not isinstance(columns, dict) or set(columns) - FIELDS or any(not isinstance(c, str) or c not in available for c in columns.values()):
                    fail("invalid_mapping", "Map fields using the source column letters.")
                if role not in {"summary", "other"} and not columns:
                    fail("invalid_mapping", "A detail sheet needs at least one mapped field.")
                if header not in {r["source_row"] for r in sheet.get("rows", [])}:
                    fail("invalid_mapping", "The header row must exist in the source.")
                fmt = mapping.get("date_format", "ISO")
                if not isinstance(fmt, str) or fmt not in {"ISO", "DMY", "MDY"}:
                    fail("invalid_mapping", "Choose an explicit source date format.")
                policies = mapping.get("value_states", {})
                if not isinstance(policies, dict) or set(policies) - FIELDS:
                    fail("invalid_mapping", "Invalid field-specific missing-value policy.")
                for values in policies.values():
                    if not isinstance(values, dict) or len(values) > 20 or any(not isinstance(v, str) or v not in VALUE_STATES for v in values.values()):
                        fail("invalid_mapping", "Missing-value meanings must be assigned field by field.")
                mappings.append({"name": mapping["name"], "role": role, "header_row": header,
                                 "columns": columns, "date_format": fmt, "value_states": policies})
            if names != set(originals):
                fail("unmapped_sheets", "Assign every worksheet a grain, including summary and other sheets.")
            revision = source["revision"] + 1
            value = {"sheets": mappings, "confirmed_by": principal.subject, "confirmed_at": now(), "revision": revision}
            self.store.update("rmd_sources", source_id, {"mapping_json": canonical(value), "revision": revision, "updated_at": now()})
            self._bump(pack)
            self._audit(principal, pack_id, "mapping_confirmed", source_id, revision)
            return self.get_source(principal, pack_id, source_id)

    @staticmethod
    def _mapped_date(value, fmt):
        if value in (None, ""):
            return value
        s = str(value).strip()
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", s):
                return (datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat() if "T" in s else date.fromisoformat(s).isoformat())
            if fmt in {"DMY", "MDY"}:
                for pattern in (("%d/%m/%Y", "%d-%m-%Y") if fmt == "DMY" else ("%m/%d/%Y", "%m-%d-%Y")):
                    try:
                        return datetime.strptime(s, pattern).date().isoformat()
                    except ValueError:
                        pass
        except ValueError:
            pass
        return value  # Preserved as unresolved; analytics never guesses it.

    def _records(self, sources):
        records, versions = [], []
        for source in sources:
            metadata, mapping = json.loads(source["metadata_json"]), json.loads(source["mapping_json"])
            versions.append({"source_id": source["id"], "filename": source["name"], "sha256": source["sha256"],
                             "version": source["revision"], "mapping_revision": mapping.get("revision"),
                             "kind": source["kind"]})
            if source["kind"] != "workbook":
                continue
            if not mapping.get("sheets"):
                fail("mapping_required", "Confirm each workbook sheet and its columns before analysis.", 409)
            by_name = {s["name"]: s for s in metadata["sheets"]}
            for spec in mapping["sheets"]:
                sheet = by_name[spec["name"]]
                for row in sheet["rows"]:
                    if row["source_row"] <= spec["header_row"]:
                        continue
                    cells = row.get("cells", {})
                    if not any(c.get("raw_value") not in (None, "") or c.get("formula") for c in cells.values()):
                        continue
                    fields, states = {}, {}
                    for field, column in spec["columns"].items():
                        cell = cells.get(column, {})
                        value = cell.get("cached_value") if cell.get("formula") else cell.get("value")
                        if value is None and not cell.get("formula"):
                            value = ""  # A supplied blank cell, never a measured zero.
                        if field in {"event_date", "due_date"}:
                            value = self._mapped_date(value, spec["date_format"])
                        fields[field] = value
                        policy = spec.get("value_states", {}).get(field, {})
                        if str(value) in policy:
                            states[field] = policy[str(value)]
                    key = hashlib.sha256(canonical([source["id"], source["sha256"], spec["name"], row["source_row"]]).encode()).hexdigest()[:32]
                    records.append({"id": key, "source_id": source["id"], "source_sha": source["sha256"],
                        "sheet": spec["name"], "source_row": row["source_row"], "locator": row["locator"],
                        "grain": spec["role"], "fields": fields, "field_states": states,
                        "raw_fields": cells, "hidden_row": row.get("hidden", False)})
                    if len(records) > MAX_RECORDS:
                        fail("record_limit", "The pack exceeds its analysis record limit.", 413)
        return records, versions

    def create_analysis(self, principal, pack_id, payload):
        with self.store.atomic("rmd-pack:" + pack_id):
            pack = self._pack(principal, pack_id, "write")
            def create():
                n = self.store._exec("SELECT COUNT(*) AS n FROM rmd_analyses WHERE pack_id = ?", (pack_id,))[0]["n"]
                if n >= MAX_ANALYSES:
                    fail("capacity_reached", "The analysis snapshot limit has been reached.", 409)
                sources = self.store._exec("SELECT * FROM rmd_sources WHERE pack_id = ? ORDER BY id", (pack_id,))
                records, versions = self._records(sources)
                if not records:
                    fail("records_required", "Import and map an operational workbook before calculating insights.", 409)
                filters = payload.get("filters") or {}
                if not isinstance(filters, dict) or len(canonical(filters)) > 20_000:
                    fail("invalid_filters", "Filters must be a bounded object.")
                allowed_filters = {"from", "to", "date_from", "date_to", "period", "location", "category", "status", "source_ids", "sources", "grains", "roles", "grain", "chart_grain", "comparison_source_ids"}
                if set(filters) - allowed_filters:
                    fail("invalid_filters", "An unsupported filter was requested.")
                if filters.get("grain") is not None:
                    if not isinstance(filters["grain"], str) or filters["grain"] not in GRAINS:
                        fail("invalid_filters", "An unsupported grain was requested.")
                    filters = {**filters, "grains": [filters["grain"]]}
                    del filters["grain"]
                language = "ar" if payload.get("language") == "ar" else "en"
                stamp, key = now(), uid()
                try:
                    result = rmd_analytics.analyse_records(records, source_versions=versions, filters=filters,
                                                          language=language, calculated_at=stamp)
                except ValueError as error:
                    fail("invalid_analysis", str(error))
                fingerprint = hashlib.sha256(canonical([versions, filters, result["calculation_version"]]).encode()).hexdigest()
                result.update({"id": key, "pack_id": pack_id, "pack_revision": pack["revision"],
                               "created_at": stamp, "fingerprint": fingerprint, "run_id": None,
                               "publication_state": "not_published", "data_mode": "private_evidence"})
                self.store.insert("rmd_analyses", {"id": key, "pack_id": pack_id, "created_at": stamp,
                    "pack_revision": pack["revision"], "fingerprint": fingerprint, "language": language,
                    "filters_json": canonical(filters), "result_json": canonical(result), "records_json": canonical(records)})
                snapshots = []
                for source in sources:
                    metadata = json.loads(source["metadata_json"])
                    snapshots.append({"source_id": source["id"], "name": source["name"],
                        "sha256": source["sha256"], "revision": source["revision"],
                        "mapping": json.loads(source["mapping_json"]),
                        "extraction": metadata.get("extraction"), "coverage": metadata.get("coverage"),
                        "document_digest": metadata.get("document", {}).get("digest"),
                        "applicability": json.loads(source["applicability_json"])})
                self.store.insert("rmd_analysis_sources", {"id": key, "pack_id": pack_id,
                    "analysis_id": key, "sources_json": canonical(snapshots)})
                for proposal in result.get("proposed_links", []):
                    link_id = key + "-" + proposal["id"]
                    self.store.insert("rmd_links", {"id": link_id, "pack_id": pack_id, "analysis_id": key,
                        "left_record_id": proposal["left_record_id"], "right_record_id": proposal["right_record_id"],
                        "method": proposal["method"], "state": "proposed", "revision": 1,
                        "detail_json": canonical(proposal), "created_at": stamp, "updated_at": stamp})
                self._audit(principal, pack_id, "analysis_calculated", key, 1,
                            {"fingerprint": fingerprint, "pack_revision": pack["revision"]})
                return self.get_analysis(principal, pack_id, key)
            return self._request(principal, "analysis:create:" + pack_id, payload, create, pack_id)

    def get_analysis(self, principal, pack_id, analysis_id):
        row = self._analysis(principal, pack_id, analysis_id)
        result = json.loads(row["result_json"])
        # Human decisions are a separate overlay, never recalculated source facts.
        result["proposed_links"] = self.list_links(principal, pack_id, analysis_id)["links"]
        run = self.store._exec("SELECT id FROM rmd_runs WHERE pack_id = ? AND analysis_id = ? ORDER BY created_at LIMIT 1", (pack_id, analysis_id))
        if run:
            result["run_id"] = run[0]["id"]
            state = self.store.get_run(run[0]["id"])
            artifact = self.store.latest_artifact(run[0]["id"])
            result["run_state"] = state["state"] if state else None
            result["published_path"] = artifact.get("published_path") if artifact else None
            result["publication_state"] = ("published" if result["published_path"] else
                                           "awaiting_approval" if result["run_state"] == "awaiting_approval" else "not_published")
        return result

    def records(self, principal, pack_id, analysis_id, query=None):
        row = self._analysis(principal, pack_id, analysis_id)
        query = query or {}
        result = json.loads(row["result_json"])
        ids = set(result.get("scope", {}).get("record_ids", []))
        # Cited comparison records may be outside a display-period filter. They
        # remain explicitly comparison evidence, not extra dashboard population.
        for link in result.get("proposed_links", []):
            ids.update((link["left_record_id"], link["right_record_id"]))
        for item in result.get("reconciliation", {}).get("records", []):
            ids.update(item.get("matched_record_ids", []))
        wanted = query.get("record_ids")
        if wanted is not None:
            if not isinstance(wanted, list) or len(wanted) > MAX_RECORDS or any(not isinstance(i, str) for i in wanted):
                fail("invalid_record_query", "Invalid evidence record selection.")
            if not set(wanted).issubset(ids):
                fail("record_not_found", "A requested record is outside this snapshot's evidence scope.", 404)
            ids.intersection_update(wanted)
        grain = query.get("grain")
        if grain is not None and (not isinstance(grain, str) or grain not in GRAINS):
            fail("invalid_record_query", "Invalid record grain.")
        records = [r for r in json.loads(row["records_json"]) if r["id"] in ids and (not grain or r["grain"] == grain)]
        try:
            offset, limit = int(query.get("offset", 0)), int(query.get("limit", 50))
        except (ValueError, TypeError):
            fail("invalid_record_query", "Invalid evidence page.")
        if offset < 0 or not 1 <= limit <= 200:
            fail("invalid_record_query", "Evidence pages contain at most 200 records.")
        return {"records": records[offset:offset + limit], "total": len(records), "offset": offset, "limit": limit,
                "analysis_id": analysis_id, "fingerprint": row["fingerprint"],
                "comparison_records_may_be_outside_display_period": True}

    def search_knowledge(self, principal, pack_id, query="", source_id=None, limit=20):
        self._pack(principal, pack_id)
        query = text(query, "query", 500, required=False)
        wanted = set(re.findall(r"[\w\u0600-\u06ff]+", query.casefold()))
        sources = self.store._exec("SELECT * FROM rmd_sources WHERE pack_id = ? AND kind = 'procedure' ORDER BY id", (pack_id,))
        if source_id is not None:
            self._source(principal, pack_id, source_id)
            sources = [s for s in sources if s["id"] == source_id]
        hits = []
        for source in sources:
            meta = json.loads(source["metadata_json"])
            doc = meta.get("document", {})
            digest = doc.get("digest", {})
            for clause in doc.get("clauses", []):
                searchable = " ".join((source["name"], digest_candidates(digest, "document_code") or "",
                                       clause.get("section") or "", clause.get("text", "")))
                words = set(re.findall(r"[\w\u0600-\u06ff]+", searchable.casefold()))
                matched = wanted & words
                if wanted and not matched:
                    continue
                passage_sha = hashlib.sha256(clause.get("text", "").encode()).hexdigest()
                hits.append({"id": source["id"] + ":" + clause["id"], "clause_id": clause["id"],
                    "source_id": source["id"], "source_name": source["name"], "source_sha256": source["sha256"],
                    "document_code": digest_candidates(digest, "document_code"), "revision": source["revision"],
                    "document_revision": digest_candidates(digest, "revision"), "passage_sha256": passage_sha,
                    "document_identity_review_required": True,
                    "locator": clause["locator"], "section": clause.get("section"), "text": clause["text"],
                    "applicability": json.loads(source["applicability_json"]), "coverage": meta.get("coverage", {}),
                    "classification": "private_reference", "model_use": "not_permitted_by_default",
                    "matched_terms": sorted(matched), "score": len(matched)})
        hits.sort(key=lambda hit: (-hit["score"], hit["source_id"], hit["clause_id"]))
        return {"hits": hits[:max(1, min(int(limit), 100))], "total": len(hits), "query": query,
                "applicability_default": "unverified", "classification": "private_reference"}

    def update_applicability(self, principal, pack_id, source_id, payload):
        with self.store.atomic("rmd-pack:" + pack_id):
            pack = self._pack(principal, pack_id, "authorize")
            source = self._source(principal, pack_id, source_id, "authorize")
            _version(payload, source["revision"])
            state = payload.get("state")
            if not isinstance(state, str) or state not in {"unverified", "confirmed_current", "superseded", "not_applicable"}:
                fail("invalid_applicability", "Choose an explicit applicability decision.")
            evidence = payload.get("evidence")
            if not isinstance(evidence, list) or not evidence or len(evidence) > 30 or any(not isinstance(e, str) or not e.strip() or len(e) > 1000 for e in evidence):
                fail("evidence_required", "An applicability decision needs review evidence.")
            decision = {"state": state, "reason": text(payload.get("reason"), "reason", 2000),
                        "evidence": evidence, "decided_by": principal.subject, "decided_at": now()}
            rev = source["revision"] + 1
            self.store.update("rmd_sources", source_id, {"revision": rev, "applicability_json": canonical(decision), "updated_at": now()})
            self._bump(pack)
            self._audit(principal, pack_id, "applicability_decided", source_id, rev, decision)
            return self.get_source(principal, pack_id, source_id)

    def list_links(self, principal, pack_id, analysis_id=None):
        self._pack(principal, pack_id)
        sql, params = "SELECT * FROM rmd_links WHERE pack_id = ?", [pack_id]
        if analysis_id:
            self._analysis(principal, pack_id, analysis_id)
            sql += " AND analysis_id = ?"; params.append(analysis_id)
        rows = self.store._exec(sql + " ORDER BY created_at,id", tuple(params))
        return {"links": [{**json.loads(r["detail_json"]), **{k: v for k, v in r.items() if k != "detail_json"}} for r in rows]}

    def review_link(self, principal, pack_id, link_id, payload):
        with self.store.atomic("rmd-pack:" + pack_id):
            self._pack(principal, pack_id, "authorize")
            rows = self.store._exec("SELECT * FROM rmd_links WHERE id = ? AND pack_id = ?", (link_id, pack_id))
            if not rows:
                fail("link_not_found", "Evidence link not found.", 404)
            link = rows[0]; _version(payload, link["revision"])
            if not isinstance(payload.get("decision"), str) or payload.get("decision") not in {"confirmed", "rejected"}:
                fail("invalid_link_decision", "Confirm or reject the proposed relationship.")
            note = text(payload.get("note"), "review note", 2000)
            revision = link["revision"] + 1
            self.store.update("rmd_links", link_id, {"state": payload["decision"], "revision": revision, "updated_at": now()})
            self._audit(principal, pack_id, "link_" + payload["decision"], link_id, revision, {"note": note})
            return next(x for x in self.list_links(principal, pack_id)["links"] if x["id"] == link_id)

    def create_incident(self, principal, pack_id, payload):
        with self.store.atomic("rmd-pack:" + pack_id):
            self._pack(principal, pack_id, "authorize")
            analysis_id = text(payload.get("analysis_id"), "analysis_id", 128)
            selected = payload.get("record_ids")
            if (not isinstance(selected, list) or not selected or len(selected) > MAX_RECORDS
                    or any(not isinstance(x, str) for x in selected) or len(selected) != len(set(selected))):
                fail("invalid_incident", "Select distinct reviewed evidence records.")
            self.records(principal, pack_id, analysis_id, {"record_ids": selected, "limit": 1})
            # This is a deliberate human grouping. Link confirmation by itself
            # never creates an incident or rewrites original source entities.
            key, stamp = uid(), now()
            row = {"id": key, "pack_id": pack_id, "title": text(payload.get("title"), "title", 200),
                   "record_ids_json": canonical(selected), "revision": 1, "created_at": stamp}
            self.store.insert("rmd_incidents", row)
            self._audit(principal, pack_id, "incident_group_created", key, 1,
                        {"analysis_id": analysis_id, "record_ids": selected, "reason": text(payload.get("reason"), "reason", 2000)})
            return {k: v for k, v in row.items() if k != "record_ids_json"} | {"record_ids": selected, "classification": "human_confirmed_group"}

    def list_actions(self, principal, pack_id):
        self._pack(principal, pack_id)
        rows = self.store._exec("SELECT * FROM rmd_actions WHERE pack_id = ? ORDER BY created_at,id", (pack_id,))
        return {"actions": [{**json.loads(row["body_json"]), **{k: v for k, v in row.items() if k != "body_json"}} for row in rows]}

    def create_action(self, principal, pack_id, payload):
        with self.store.atomic("rmd-pack:" + pack_id):
            self._pack(principal, pack_id, "write")
            def create():
                analysis_id = text(payload.get("analysis_id"), "analysis_id", 128)
                analysis = self.get_analysis(principal, pack_id, analysis_id)
                priority_id = text(payload.get("priority_id"), "priority_id", 128)
                priority = next((p for p in analysis.get("priorities", []) if p["id"] == priority_id), None)
                if priority is None:
                    fail("priority_not_found", "The proposed action must cite an existing priority.", 404)
                previous = self.store._exec("SELECT id FROM rmd_actions WHERE pack_id = ? AND analysis_id = ? AND priority_id = ?",
                                            (pack_id, analysis_id, priority_id))
                if previous:
                    return next(x for x in self.list_actions(principal, pack_id)["actions"] if x["id"] == previous[0]["id"])
                key, stamp = uid(), now()
                body = {"proposed_action": priority.get("proposed_action"), "owner_role": priority.get("owner_role"),
                        "owner_is_suggested": True, "due_date": None, "due_date_basis": priority.get("due_date_basis"),
                        "closure_evidence": [], "evidence_required_for_closure": priority.get("closure_evidence"),
                        "evidence": priority.get("evidence", {}), "maintenance_authorization": False}
                self.store.insert("rmd_actions", {"id": key, "pack_id": pack_id, "analysis_id": analysis_id,
                    "priority_id": priority_id, "state": "proposed", "revision": 1, "body_json": canonical(body),
                    "created_at": stamp, "updated_at": stamp})
                self._audit(principal, pack_id, "action_proposed", key, 1)
                return next(x for x in self.list_actions(principal, pack_id)["actions"] if x["id"] == key)
            return self._request(principal, "action:create:" + pack_id, payload, create, pack_id)

    def update_action(self, principal, pack_id, action_id, payload):
        with self.store.atomic("rmd-pack:" + pack_id):
            self._pack(principal, pack_id, "authorize")
            rows = self.store._exec("SELECT * FROM rmd_actions WHERE id = ? AND pack_id = ?", (action_id, pack_id))
            if not rows:
                fail("action_not_found", "Action not found.", 404)
            row = rows[0]; _version(payload, row["revision"])
            state = payload.get("state")
            if not isinstance(state, str) or state not in {"proposed", "accepted", "in_review", "closed", "rejected"}:
                fail("invalid_action_state", "Choose a recorded management-action state.")
            body = json.loads(row["body_json"])
            evidence = payload.get("closure_evidence", body["closure_evidence"])
            if not isinstance(evidence, list) or len(evidence) > 30 or any(not isinstance(x, str) or not x.strip() or len(x) > 1000 for x in evidence):
                fail("invalid_evidence", "Invalid closure evidence.")
            if state == "closed" and not evidence:
                fail("closure_evidence_required", "Closing an action requires supporting evidence.")
            body["closure_evidence"] = evidence
            revision = row["revision"] + 1
            self.store.update("rmd_actions", action_id, {"state": state, "revision": revision, "body_json": canonical(body), "updated_at": now()})
            self._audit(principal, pack_id, "action_" + state, action_id, revision, {"note": text(payload.get("note", ""), "note", 2000, False), "closure_evidence": evidence})
            return next(x for x in self.list_actions(principal, pack_id)["actions"] if x["id"] == action_id)

    def audit(self, principal, pack_id):
        self._pack(principal, pack_id)
        rows = self.store._exec("SELECT * FROM rmd_audit WHERE pack_id = ? ORDER BY created_at,id", (pack_id,))
        return {"events": [{**{k: v for k, v in r.items() if k != "detail_json"}, "detail": json.loads(r["detail_json"])} for r in rows]}

    def delete_pack(self, principal, pack_id):
        with self.store.atomic("rmd-pack:" + pack_id):
            self._pack(principal, pack_id, "authorize")
            notes = [row["path"] for row in self.store._exec(
                "SELECT n.path FROM vault_notes n JOIN rmd_runs r ON r.id=n.run_id WHERE r.pack_id = ?", (pack_id,))]
            erase_pack_rmd(self.store, pack_id)
        from server.erasure import erase_vault_paths, not_reached
        removed, missing = erase_vault_paths(self.vault_dir, notes)
        return {"deleted": True, "vault_files_deleted": removed,
                "vault_files_not_found": missing, "not_reached": not_reached()}

    def export(self, principal, pack_id, analysis_id, format="html", language=None, fingerprint=None):
        row = self._analysis(principal, pack_id, analysis_id)
        if fingerprint is not None and fingerprint != row["fingerprint"]:
            fail("stale_snapshot", "Prepare the exact snapshot again before exporting.", 409)
        result = json.loads(row["result_json"])
        language = "ar" if (language or row["language"]) == "ar" else "en"
        tr = lambda en, ar: ar if language == "ar" else en
        actions = [a for a in self.list_actions(principal, pack_id)["actions"] if a["analysis_id"] == analysis_id]
        calculations = result.get("calculations", result.get("kpis", []))
        if format == "csv":
            out = io.StringIO(newline="")
            writer = csv.writer(out)
            columns = ["analysis_id", "fingerprint", "filters", "kind", "calculation_id", "label", "value", "unit", "grain", "formula", "numerator", "denominator", "period", "source_versions", "record_ids", "owner_role", "due_date", "due_date_basis", "state", "closure_evidence"]
            writer.writerow(columns)
            def safe(value):
                if isinstance(value, dict) and {"en", "ar"} & value.keys():
                    value = bi(value, language)
                elif isinstance(value, (list, dict)):
                    value = canonical(value)
                else:
                    value = bi(value, language)
                return "'" + value if value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@")) else value
            def write(values):
                shared = {"analysis_id": analysis_id, "fingerprint": row["fingerprint"],
                    "filters": result.get("filters", {}), "period": result.get("period", {}),
                    "source_versions": result.get("source_versions", [])}
                writer.writerow([safe({**shared, **values}.get(c)) for c in columns])
            for calculation in calculations:
                population = calculation.get("population", {})
                write({"kind": "chart_definition" if "table" in calculation else "calculation",
                    "calculation_id": calculation.get("calculation_id", calculation.get("id")),
                    "label": calculation.get("title", calculation.get("question", calculation.get("id"))),
                    "value": calculation.get("value"), "unit": calculation.get("unit"),
                    "grain": calculation.get("grain", population.get("grain")),
                    "formula": calculation.get("formula"), "numerator": calculation.get("numerator"),
                    "denominator": calculation.get("denominator"),
                    "record_ids": calculation.get("evidence_record_ids", population.get("record_ids", []))})
            for chart in result.get("charts", []):
                for point in chart.get("table", []):
                    write({"kind": "chart_value", "calculation_id": chart.get("calculation_id"),
                        "label": point.get("label"), "value": point.get("value"), "unit": chart.get("unit"),
                        "grain": chart.get("grain"), "formula": chart.get("formula"),
                        "record_ids": point.get("record_ids", [])})
            for action in actions:
                write({"kind": "action", "label": action.get("proposed_action"),
                    "record_ids": action.get("evidence", {}).get("record_ids", []),
                    "owner_role": action.get("owner_role"), "due_date": action.get("due_date"),
                    "due_date_basis": action.get("due_date_basis"), "state": action["state"],
                    "closure_evidence": action.get("closure_evidence")})
            return out.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", f"evidence-{analysis_id}-{language}.csv"
        if format != "html":
            fail("invalid_export_format", "Choose HTML or CSV.")
        sections = [executive_export.Section(tr("Snapshot and scope", "اللقطة والنطاق"), paragraphs=[
            tr("Draft for qualified human review. Exporting does not approve, publish or authorize maintenance.", "مسودة للمراجعة البشرية المؤهلة. لا يعني التصدير الاعتماد أو النشر أو الإذن بتنفيذ الصيانة."),
            tr("Snapshot", "اللقطة") + f": {analysis_id}", tr("Source revision", "إصدار المصدر") + f": {row['fingerprint']}",
            tr("Filters", "المرشحات") + ": " + canonical(result.get("filters", {})),
            tr("Period", "الفترة") + ": " + canonical(result.get("period", {})),
            tr("Sources", "المصادر") + ": " + canonical(result.get("source_versions", [])),
            tr("Calculation version", "إصدار الحساب") + ": " + str(result.get("calculation_version")),
            tr("Coverage", "التغطية") + ": " + canonical(result.get("coverage", {}))])]
        sections.append(executive_export.Section(tr("Recorded figures", "الأرقام المسجلة"), tables=[executive_export.Table(
            (tr("Measure", "المقياس"), tr("Value", "القيمة"), tr("Unit", "الوحدة"), tr("Calculation", "الحساب")),
            [(bi(k.get("title"), language), str(k.get("value")), bi(k.get("unit"), language), k.get("id", "")) for k in result.get("kpis", [])])]))
        for calculation in calculations:
            population = calculation.get("population", {})
            sections.append(executive_export.Section(
                bi(calculation.get("title", calculation.get("question", calculation.get("id"))), language),
                paragraphs=[str(calculation.get("calculation_id", calculation.get("id", ""))),
                    tr("Formula", "الصيغة") + ": " + str(calculation.get("formula", "")),
                    tr("Population", "المجتمع") + ": " + canonical(population),
                    tr("Numerator / denominator", "البسط / المقام") + ": " + canonical([calculation.get("numerator"), calculation.get("denominator")]),
                    tr("Missing-data treatment", "معالجة البيانات الناقصة") + ": " + bi(calculation.get("missing_policy"), language),
                    tr("Exclusions", "الاستبعادات") + ": " + canonical(calculation.get("exclusions", {}))]))
        for chart in result.get("charts", []):
            sections.append(executive_export.Section(bi(chart.get("title"), language),
                paragraphs=[tr("Grain", "مستوى السجل") + ": " + str(chart.get("grain")),
                    tr("Unit", "الوحدة") + ": " + str(chart.get("unit")),
                    tr("Calculation", "الحساب") + ": " + str(chart.get("calculation_id"))],
                tables=[executive_export.Table((tr("Recorded category", "الفئة المسجلة"), tr("Value", "القيمة"),
                    tr("Supporting record identifiers", "معرفات السجلات الداعمة")),
                    [(str(point.get("label")), str(point.get("value")), ", ".join(point.get("record_ids", [])))
                     for point in chart.get("table", [])])]))
        for priority in result.get("priorities", []):
            sections.append(executive_export.Section(bi(priority.get("finding"), language), paragraphs=[
                bi(priority.get(key), language) for key in ("management_implication", "uncertainty", "proposed_action", "closure_evidence")]))
        sections.append(executive_export.Section(tr("Action register", "سجل الإجراءات"), tables=[executive_export.Table(
            (tr("Proposed action", "الإجراء المقترح"), tr("Suggested role", "الدور المقترح"), tr("Due-date basis", "أساس الموعد"), tr("State", "الحالة")),
            [(bi(a.get("proposed_action"), language), bi(a.get("owner_role"), language), bi(a.get("due_date_basis"), language), a["state"]) for a in actions])]))
        sections.append(executive_export.Section(tr("Limitations", "القيود"), paragraphs=[bi(x, language) for x in result.get("limitations", [])]))
        synopsis = executive_export._synopsis
        front = executive_export.Section(tr("Executive summary", "الملخص التنفيذي"), compact=True,
            paragraphs=[tr("Draft for qualified human review. Recorded evidence only; no maintenance instruction or achieved saving is approved.",
                "مسودة للمراجعة البشرية المؤهلة. أدلة مسجلة فقط؛ لم تُعتمد تعليمات صيانة أو وفورات محققة."),
                tr("Snapshot", "اللقطة") + ": " + analysis_id,
                tr("Exact scope, filters, source revisions and limitations follow.", "يلي ذلك النطاق الدقيق والمرشحات وإصدارات المصادر والقيود.")])
        front.tables = [executive_export.Table(
            (tr("Observed measure", "المؤشر المرصود"), tr("Value / unit", "القيمة / الوحدة")),
            [(synopsis(bi(k.get("title"), language), 85), str(k.get("value")) + " " + bi(k.get("unit"), language))
             for k in result.get("kpis", [])[:3]], (55, 45))]
        front.after_title = tr("Review priorities", "أولويات المراجعة")
        front.after_paragraphs = [synopsis(bi(p.get("proposed_action"), language), 120) for p in result.get("priorities", [])[:3]]
        front.after_paragraphs.append(tr("Associations do not establish causal effects or future failure. Review the full evidence and limitations before acting.",
            "لا تثبت الارتباطات آثاراً سببية أو أعطالاً مستقبلية. راجع الأدلة والقيود الكاملة قبل التصرف."))
        page = executive_export.render_sections_html(tr("RMD Evidence and Insights", "أدلة ورؤى الصيانة"), [front, *sections], language)
        return page, "text/html; charset=utf-8", f"evidence-{analysis_id}-{language}.html"
