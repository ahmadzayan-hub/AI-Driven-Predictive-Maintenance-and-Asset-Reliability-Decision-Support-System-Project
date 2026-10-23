-- Miyaar hosted catch-up, pinned application base 1e9ccd039292796400f34ccada1c927762af6b6d.
-- REVIEW ONLY: does not authorize any hosted write. Back up and rehearse first.
-- No existing owner/data is rewritten. Non-matching legacy schema aborts.
BEGIN;
SET LOCAL search_path = pg_catalog, public;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
SELECT pg_catalog.pg_advisory_xact_lock(727001);
-- No schema/data rewrite precedes this drift check. Unexpected legacy ownership
-- or shapes need an explicit migration review, never automatic attribution.
DO $preflight$
DECLARE expected jsonb := '{"schema_migrations": {"columns": {"version": {"type": "integer", "not_null": true, "optional": false}, "applied_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["version"], "unique": [], "foreign": []}, "rate_windows": {"columns": {"key": {"type": "text", "not_null": true, "optional": false}, "window_start": {"type": "integer", "not_null": true, "optional": false}, "count": {"type": "integer", "not_null": true, "optional": false}}, "pk": ["key", "window_start"], "unique": [], "foreign": []}, "model_calls_daily": {"columns": {"owner": {"type": "text", "not_null": true, "optional": false}, "day": {"type": "text", "not_null": true, "optional": false}, "count": {"type": "integer", "not_null": true, "optional": false}}, "pk": ["owner", "day"], "unique": [], "foreign": []}, "runs": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "goal": {"type": "text", "not_null": true, "optional": false}, "dataset_name": {"type": "text", "not_null": true, "optional": false}, "dataset_text": {"type": "text", "not_null": true, "optional": false}, "state": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}, "error": {"type": "text", "not_null": false, "optional": false}, "owner": {"type": "text", "not_null": false, "optional": false}, "dataset_id": {"type": "text", "not_null": false, "optional": false}, "lease_owner": {"type": "text", "not_null": false, "optional": false}, "lease_expires_at": {"type": "text", "not_null": false, "optional": false}, "report_language": {"type": "text", "not_null": false, "optional": false}, "mapping_json": {"type": "text", "not_null": false, "optional": false}, "joins_json": {"type": "text", "not_null": false, "optional": false}, "connector_id": {"type": "text", "not_null": false, "optional": false}, "assumptions_json": {"type": "text", "not_null": false, "optional": true}, "idempotency_key": {"type": "text", "not_null": false, "optional": true}, "request_hash": {"type": "text", "not_null": false, "optional": true}, "paused": {"type": "integer", "not_null": false, "optional": false}}, "pk": ["id"], "unique": [], "foreign": []}, "tasks": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "run_id": {"type": "text", "not_null": true, "optional": false}, "idx": {"type": "integer", "not_null": true, "optional": false}, "role": {"type": "text", "not_null": true, "optional": false}, "title": {"type": "text", "not_null": true, "optional": false}, "state": {"type": "text", "not_null": true, "optional": false}, "summary": {"type": "text", "not_null": false, "optional": false}, "result_json": {"type": "text", "not_null": false, "optional": false}, "updated_at": {"type": "text", "not_null": false, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["run_id"], "target": "runs", "target_columns": ["id"]}]}, "approvals": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "run_id": {"type": "text", "not_null": true, "optional": false}, "action": {"type": "text", "not_null": true, "optional": false}, "target": {"type": "text", "not_null": true, "optional": false}, "risk": {"type": "text", "not_null": true, "optional": false}, "impact": {"type": "text", "not_null": true, "optional": false}, "reversibility": {"type": "text", "not_null": true, "optional": false}, "content_hash": {"type": "text", "not_null": true, "optional": false}, "state": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "decided_at": {"type": "text", "not_null": false, "optional": false}, "decided_by": {"type": "text", "not_null": false, "optional": true}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["run_id"], "target": "runs", "target_columns": ["id"]}]}, "artifacts": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "run_id": {"type": "text", "not_null": true, "optional": false}, "name": {"type": "text", "not_null": true, "optional": false}, "kind": {"type": "text", "not_null": true, "optional": false}, "version": {"type": "integer", "not_null": true, "optional": false}, "content": {"type": "text", "not_null": true, "optional": false}, "published_path": {"type": "text", "not_null": false, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["run_id"], "target": "runs", "target_columns": ["id"]}]}, "sessions": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}, "ended": {"type": "integer", "not_null": true, "optional": false}, "preferences_json": {"type": "text", "not_null": true, "optional": false}, "history_json": {"type": "text", "not_null": true, "optional": false}, "transcript_json": {"type": "text", "not_null": true, "optional": false}, "next_entry_id": {"type": "integer", "not_null": true, "optional": false}, "owner": {"type": "text", "not_null": false, "optional": false}}, "pk": ["id"], "unique": [], "foreign": []}, "memory_kv": {"columns": {"owner": {"type": "text", "not_null": true, "optional": false}, "key": {"type": "text", "not_null": true, "optional": false}, "text": {"type": "text", "not_null": true, "optional": false}, "category": {"type": "text", "not_null": true, "optional": false}, "updated": {"type": "text", "not_null": false, "optional": false}}, "pk": ["owner", "key"], "unique": [], "foreign": []}, "vault_notes": {"columns": {"path": {"type": "text", "not_null": true, "optional": false}, "run_id": {"type": "text", "not_null": true, "optional": false}, "content": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["path"], "unique": [], "foreign": []}, "datasets": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "sha256": {"type": "text", "not_null": true, "optional": false}, "name": {"type": "text", "not_null": true, "optional": false}, "content": {"type": "text", "not_null": true, "optional": false}, "byte_size": {"type": "integer", "not_null": true, "optional": false}, "owner": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "source_format": {"type": "text", "not_null": false, "optional": false}, "row_count": {"type": "integer", "not_null": false, "optional": false}, "column_count": {"type": "integer", "not_null": false, "optional": false}, "mapping_json": {"type": "text", "not_null": false, "optional": false}, "mapping_updated_at": {"type": "text", "not_null": false, "optional": false}}, "pk": ["id"], "unique": [], "foreign": []}, "connectors": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "owner": {"type": "text", "not_null": true, "optional": false}, "name": {"type": "text", "not_null": true, "optional": false}, "url": {"type": "text", "not_null": true, "optional": false}, "format": {"type": "text", "not_null": false, "optional": false}, "sheet": {"type": "text", "not_null": false, "optional": false}, "every_minutes": {"type": "integer", "not_null": false, "optional": false}, "goal": {"type": "text", "not_null": true, "optional": false}, "language": {"type": "text", "not_null": true, "optional": false}, "profile": {"type": "text", "not_null": false, "optional": false}, "enabled": {"type": "integer", "not_null": true, "optional": false}, "failures": {"type": "integer", "not_null": true, "optional": false}, "last_status": {"type": "text", "not_null": false, "optional": false}, "last_error": {"type": "text", "not_null": false, "optional": false}, "last_checked_at": {"type": "text", "not_null": false, "optional": false}, "last_dataset_id": {"type": "text", "not_null": false, "optional": false}, "last_sha256": {"type": "text", "not_null": false, "optional": false}, "last_run_id": {"type": "text", "not_null": false, "optional": false}, "next_due_at": {"type": "text", "not_null": false, "optional": false}, "lease_owner": {"type": "text", "not_null": false, "optional": false}, "lease_expires_at": {"type": "text", "not_null": false, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}, "credential_id": {"type": "text", "not_null": false, "optional": true}}, "pk": ["id"], "unique": [], "foreign": []}, "kpi_policies": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "run_id": {"type": "text", "not_null": true, "optional": false}, "version": {"type": "integer", "not_null": true, "optional": false}, "revision": {"type": "text", "not_null": true, "optional": false}, "rules_json": {"type": "text", "not_null": true, "optional": false}, "actor": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [["run_id", "version"]], "foreign": [{"columns": ["run_id"], "target": "runs", "target_columns": ["id"]}]}, "organizations": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "name": {"type": "text", "not_null": true, "optional": false}, "version": {"type": "integer", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": []}, "organization_members": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "org_id": {"type": "text", "not_null": true, "optional": false}, "subject": {"type": "text", "not_null": true, "optional": false}, "role": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [["org_id", "subject"]], "foreign": [{"columns": ["org_id"], "target": "organizations", "target_columns": ["id"]}]}, "operation_sites": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "org_id": {"type": "text", "not_null": true, "optional": false}, "code": {"type": "text", "not_null": true, "optional": false}, "name": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [["org_id", "code"]], "foreign": [{"columns": ["org_id"], "target": "organizations", "target_columns": ["id"]}]}, "operation_assets": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "org_id": {"type": "text", "not_null": true, "optional": false}, "site_id": {"type": "text", "not_null": true, "optional": false}, "external_id": {"type": "text", "not_null": true, "optional": false}, "source_system": {"type": "text", "not_null": true, "optional": false}, "name": {"type": "text", "not_null": true, "optional": false}, "criticality": {"type": "text", "not_null": true, "optional": false}, "version": {"type": "integer", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [["org_id", "source_system", "external_id"]], "foreign": [{"columns": ["site_id"], "target": "operation_sites", "target_columns": ["id"]}, {"columns": ["org_id"], "target": "organizations", "target_columns": ["id"]}]}, "work_orders": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "org_id": {"type": "text", "not_null": true, "optional": false}, "asset_id": {"type": "text", "not_null": true, "optional": false}, "title": {"type": "text", "not_null": true, "optional": false}, "rationale": {"type": "text", "not_null": true, "optional": false}, "status": {"type": "text", "not_null": true, "optional": false}, "priority": {"type": "text", "not_null": true, "optional": false}, "assignee": {"type": "text", "not_null": true, "optional": false}, "due_date": {"type": "text", "not_null": true, "optional": false}, "evidence_json": {"type": "text", "not_null": true, "optional": false}, "completion_json": {"type": "text", "not_null": true, "optional": false}, "version": {"type": "integer", "not_null": true, "optional": false}, "created_by": {"type": "text", "not_null": true, "optional": false}, "authorized_by": {"type": "text", "not_null": false, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["asset_id"], "target": "operation_assets", "target_columns": ["id"]}, {"columns": ["org_id"], "target": "organizations", "target_columns": ["id"]}]}, "operation_audit": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "org_id": {"type": "text", "not_null": true, "optional": false}, "entity_id": {"type": "text", "not_null": true, "optional": false}, "actor": {"type": "text", "not_null": true, "optional": false}, "action": {"type": "text", "not_null": true, "optional": false}, "version": {"type": "integer", "not_null": true, "optional": false}, "detail_json": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["org_id"], "target": "organizations", "target_columns": ["id"]}]}, "operation_requests": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "org_id": {"type": "text", "not_null": true, "optional": false}, "actor": {"type": "text", "not_null": true, "optional": false}, "request_key": {"type": "text", "not_null": true, "optional": false}, "payload_hash": {"type": "text", "not_null": true, "optional": false}, "response_json": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [["org_id", "actor", "request_key"]], "foreign": [{"columns": ["org_id"], "target": "organizations", "target_columns": ["id"]}]}, "worker_heartbeats": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "seen_at": {"type": "text", "not_null": true, "optional": false}, "state": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": []}, "reliability_trials": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "org_id": {"type": "text", "not_null": true, "optional": false}, "created_by": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}, "revision": {"type": "integer", "not_null": true, "optional": false}, "protocol_json": {"type": "text", "not_null": true, "optional": false}, "predictions_json": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["org_id"], "target": "organizations", "target_columns": ["id"]}]}, "rmd_packs": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "owner": {"type": "text", "not_null": true, "optional": false}, "organization_id": {"type": "text", "not_null": false, "optional": false}, "title": {"type": "text", "not_null": true, "optional": false}, "revision": {"type": "integer", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": []}, "rmd_sources": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": true, "optional": false}, "name": {"type": "text", "not_null": true, "optional": false}, "kind": {"type": "text", "not_null": true, "optional": false}, "sha256": {"type": "text", "not_null": true, "optional": false}, "revision": {"type": "integer", "not_null": true, "optional": false}, "metadata_json": {"type": "text", "not_null": true, "optional": false}, "mapping_json": {"type": "text", "not_null": true, "optional": false}, "original_base64": {"type": "text", "not_null": true, "optional": false}, "artifacts_json": {"type": "text", "not_null": true, "optional": false}, "applicability_json": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [["pack_id", "name", "kind", "sha256"]], "foreign": [{"columns": ["pack_id"], "target": "rmd_packs", "target_columns": ["id"]}]}, "rmd_analyses": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "pack_revision": {"type": "integer", "not_null": true, "optional": false}, "fingerprint": {"type": "text", "not_null": true, "optional": false}, "language": {"type": "text", "not_null": true, "optional": false}, "filters_json": {"type": "text", "not_null": true, "optional": false}, "result_json": {"type": "text", "not_null": true, "optional": false}, "records_json": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["pack_id"], "target": "rmd_packs", "target_columns": ["id"]}]}, "rmd_analysis_sources": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": true, "optional": false}, "analysis_id": {"type": "text", "not_null": true, "optional": false}, "sources_json": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["analysis_id"], "target": "rmd_analyses", "target_columns": ["id"]}, {"columns": ["pack_id"], "target": "rmd_packs", "target_columns": ["id"]}]}, "rmd_runs": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": true, "optional": false}, "analysis_id": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["analysis_id"], "target": "rmd_analyses", "target_columns": ["id"]}, {"columns": ["pack_id"], "target": "rmd_packs", "target_columns": ["id"]}]}, "rmd_links": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": true, "optional": false}, "analysis_id": {"type": "text", "not_null": true, "optional": false}, "left_record_id": {"type": "text", "not_null": true, "optional": false}, "right_record_id": {"type": "text", "not_null": true, "optional": false}, "method": {"type": "text", "not_null": true, "optional": false}, "state": {"type": "text", "not_null": true, "optional": false}, "revision": {"type": "integer", "not_null": true, "optional": false}, "detail_json": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["analysis_id"], "target": "rmd_analyses", "target_columns": ["id"]}, {"columns": ["pack_id"], "target": "rmd_packs", "target_columns": ["id"]}]}, "rmd_actions": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": true, "optional": false}, "analysis_id": {"type": "text", "not_null": true, "optional": false}, "priority_id": {"type": "text", "not_null": true, "optional": false}, "state": {"type": "text", "not_null": true, "optional": false}, "revision": {"type": "integer", "not_null": true, "optional": false}, "body_json": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}, "updated_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [["pack_id", "analysis_id", "priority_id"]], "foreign": [{"columns": ["analysis_id"], "target": "rmd_analyses", "target_columns": ["id"]}, {"columns": ["pack_id"], "target": "rmd_packs", "target_columns": ["id"]}]}, "rmd_incidents": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": true, "optional": false}, "title": {"type": "text", "not_null": true, "optional": false}, "record_ids_json": {"type": "text", "not_null": true, "optional": false}, "revision": {"type": "integer", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["pack_id"], "target": "rmd_packs", "target_columns": ["id"]}]}, "rmd_audit": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": true, "optional": false}, "actor": {"type": "text", "not_null": true, "optional": false}, "action": {"type": "text", "not_null": true, "optional": false}, "entity_id": {"type": "text", "not_null": true, "optional": false}, "revision": {"type": "integer", "not_null": true, "optional": false}, "detail_json": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [], "foreign": [{"columns": ["pack_id"], "target": "rmd_packs", "target_columns": ["id"]}]}, "rmd_requests": {"columns": {"id": {"type": "text", "not_null": true, "optional": false}, "owner": {"type": "text", "not_null": true, "optional": false}, "pack_id": {"type": "text", "not_null": false, "optional": false}, "operation": {"type": "text", "not_null": true, "optional": false}, "request_key": {"type": "text", "not_null": true, "optional": false}, "payload_hash": {"type": "text", "not_null": true, "optional": false}, "response_json": {"type": "text", "not_null": true, "optional": false}, "created_at": {"type": "text", "not_null": true, "optional": false}}, "pk": ["id"], "unique": [["owner", "operation", "request_key"]], "foreign": []}}'::jsonb;
  tab text; spec jsonb; col text; c jsonb; rel oid; actual record;
  keys text[]; wanted text[]; fk jsonb; target_cols text[];
BEGIN
  FOR tab,spec IN SELECT * FROM jsonb_each(expected) LOOP
    SELECT pc.oid, pc.relkind INTO actual FROM pg_catalog.pg_class pc
      JOIN pg_catalog.pg_namespace ns ON ns.oid=pc.relnamespace
      WHERE ns.nspname='public' AND pc.relname=tab;
    IF NOT FOUND THEN CONTINUE; END IF;
    rel := actual.oid;
    IF EXISTS (SELECT 1 FROM pg_catalog.aclexplode(COALESCE((SELECT pc.relacl FROM pg_catalog.pg_class pc WHERE pc.oid=rel),pg_catalog.acldefault('r',(SELECT pc.relowner FROM pg_catalog.pg_class pc WHERE pc.oid=rel)))) acl WHERE acl.grantee=0 OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles role WHERE role.rolname IN ('anon','authenticated') AND CASE WHEN acl.grantee<>0 THEN pg_catalog.pg_has_role(role.oid,acl.grantee,'USAGE') ELSE false END))
       OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles role WHERE role.rolname IN ('anon','authenticated') AND pg_catalog.has_table_privilege(role.oid,rel,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')) THEN
      RAISE EXCEPTION 'Existing client access requires review: %',tab;
    END IF;
    IF actual.relkind <> 'r' THEN RAISE EXCEPTION 'Unexpected relation kind for %',tab; END IF;
    FOR col,c IN SELECT * FROM jsonb_each(spec->'columns') LOOP
      SELECT at.attname, pg_catalog.format_type(at.atttypid,at.atttypmod) AS kind, at.attnotnull
      INTO actual FROM pg_catalog.pg_attribute at WHERE at.attrelid=rel
        AND at.attname=col AND at.attnum>0 AND NOT at.attisdropped;
      IF NOT FOUND THEN
        IF NOT (c->>'optional')::boolean THEN RAISE EXCEPTION 'Required legacy column absent: %.%',tab,col; END IF;
      ELSIF actual.kind <> c->>'type' OR actual.attnotnull <> (c->>'not_null')::boolean THEN
        RAISE EXCEPTION 'Unexpected column type/nullability: %.%',tab,col;
      END IF;
    END LOOP;
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_attribute at WHERE at.attrelid=rel AND at.attnum>0 AND NOT at.attisdropped AND NOT (spec->'columns' ? at.attname)) THEN
      RAISE EXCEPTION 'Unreviewed additional column in %',tab;
    END IF;
    SELECT array_agg(at.attname::text ORDER BY k.ord) INTO keys
      FROM pg_catalog.pg_constraint co CROSS JOIN LATERAL unnest(co.conkey) WITH ORDINALITY k(attnum,ord)
      JOIN pg_catalog.pg_attribute at ON at.attrelid=co.conrelid AND at.attnum=k.attnum
      WHERE co.conrelid=rel AND co.contype='p' AND NOT co.condeferrable;
    SELECT array_agg(value) INTO wanted FROM jsonb_array_elements_text(spec->'pk');
    IF keys IS DISTINCT FROM wanted THEN RAISE EXCEPTION 'Unexpected primary key: %',tab; END IF;
    FOR c IN SELECT * FROM jsonb_array_elements(spec->'unique') LOOP
      SELECT array_agg(value) INTO wanted FROM jsonb_array_elements_text(c);
      IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint co WHERE co.conrelid=rel AND co.contype='u' AND NOT co.condeferrable
        AND ARRAY(SELECT at.attname::text FROM unnest(co.conkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute at ON at.attrelid=rel AND at.attnum=k.attnum ORDER BY k.ord)=wanted) THEN
        RAISE EXCEPTION 'Missing unique key: %',tab;
      END IF;
    END LOOP;
    FOR fk IN SELECT * FROM jsonb_array_elements(spec->'foreign') LOOP
      SELECT array_agg(value) INTO wanted FROM jsonb_array_elements_text(fk->'columns');
      SELECT array_agg(value) INTO target_cols FROM jsonb_array_elements_text(fk->'target_columns');
      IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint co JOIN pg_catalog.pg_class rt ON rt.oid=co.confrelid JOIN pg_catalog.pg_namespace rn ON rn.oid=rt.relnamespace
        WHERE co.conrelid=rel AND co.contype='f' AND co.convalidated AND NOT co.condeferrable AND co.confdeltype='a' AND co.confupdtype='a'
        AND rn.nspname='public' AND rt.relname=fk->>'target'
        AND ARRAY(SELECT at.attname::text FROM unnest(co.conkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute at ON at.attrelid=rel AND at.attnum=k.attnum ORDER BY k.ord)=wanted
        AND ARRAY(SELECT at.attname::text FROM unnest(co.confkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute at ON at.attrelid=co.confrelid AND at.attnum=k.attnum ORDER BY k.ord)=target_cols) THEN
        RAISE EXCEPTION 'Unexpected foreign key: %',tab;
      END IF;
    END LOOP;
  END LOOP;
  IF pg_catalog.to_regclass('public.runs') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM public.runs WHERE owner IS NULL OR btrim(owner)='') THEN RAISE EXCEPTION 'Ownerless historical runs require owner review'; END IF;
  END IF;
  IF pg_catalog.to_regclass('public.sessions') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM public.sessions WHERE owner IS NULL OR btrim(owner)='') THEN RAISE EXCEPTION 'Ownerless historical sessions require owner review'; END IF;
  END IF;
  IF pg_catalog.to_regclass('public.schema_migrations') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM public.schema_migrations WHERE version > 1) THEN RAISE EXCEPTION 'Database is newer than this release'; END IF;
  END IF;
END $preflight$;
DO $indexes$ BEGIN
IF pg_catalog.to_regclass('public.runs_idempotency') IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class ix ON ix.oid=i.indexrelid JOIN pg_catalog.pg_namespace ns ON ns.oid=ix.relnamespace JOIN pg_catalog.pg_class tb ON tb.oid=i.indrelid JOIN pg_catalog.pg_namespace tn ON tn.oid=tb.relnamespace
 WHERE ns.nspname='public' AND ix.relname='runs_idempotency' AND tn.nspname='public' AND tb.relname='runs' AND i.indisvalid AND i.indisready AND i.indimmediate AND i.indisunique=true AND i.indpred IS NULL AND i.indexprs IS NULL
 AND ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum ORDER BY k.ord)=ARRAY['owner','idempotency_key']) THEN RAISE EXCEPTION 'Unexpected index: runs_idempotency'; END IF;
IF pg_catalog.to_regclass('public.tasks_role_state_run') IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class ix ON ix.oid=i.indexrelid JOIN pg_catalog.pg_namespace ns ON ns.oid=ix.relnamespace JOIN pg_catalog.pg_class tb ON tb.oid=i.indrelid JOIN pg_catalog.pg_namespace tn ON tn.oid=tb.relnamespace
 WHERE ns.nspname='public' AND ix.relname='tasks_role_state_run' AND tn.nspname='public' AND tb.relname='tasks' AND i.indisvalid AND i.indisready AND i.indimmediate AND i.indisunique=false AND i.indpred IS NULL AND i.indexprs IS NULL
 AND ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum ORDER BY k.ord)=ARRAY['role','state','run_id']) THEN RAISE EXCEPTION 'Unexpected index: tasks_role_state_run'; END IF;
END $indexes$;
CREATE TABLE IF NOT EXISTS public.organizations (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.organization_members (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES public.organizations(id),
      subject TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, subject));
CREATE TABLE IF NOT EXISTS public.operation_sites (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES public.organizations(id),
      code TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, code));
CREATE TABLE IF NOT EXISTS public.operation_assets (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES public.organizations(id),
      site_id TEXT NOT NULL REFERENCES public.operation_sites(id),
      external_id TEXT NOT NULL, source_system TEXT NOT NULL, name TEXT NOT NULL,
      criticality TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, source_system, external_id));
CREATE TABLE IF NOT EXISTS public.work_orders (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES public.organizations(id),
      asset_id TEXT NOT NULL REFERENCES public.operation_assets(id), title TEXT NOT NULL,
      rationale TEXT NOT NULL, status TEXT NOT NULL, priority TEXT NOT NULL,
      assignee TEXT NOT NULL, due_date TEXT NOT NULL, evidence_json TEXT NOT NULL,
      completion_json TEXT NOT NULL, version INTEGER NOT NULL,
      created_by TEXT NOT NULL, authorized_by TEXT, created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.operation_audit (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES public.organizations(id),
      entity_id TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
      version INTEGER NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.operation_requests (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES public.organizations(id),
      actor TEXT NOT NULL, request_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
      response_json TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, actor, request_key));
CREATE TABLE IF NOT EXISTS public.rate_windows (
      key TEXT NOT NULL, window_start INTEGER NOT NULL, count INTEGER NOT NULL,
      PRIMARY KEY (key, window_start));
CREATE TABLE IF NOT EXISTS public.model_calls_daily (
      owner TEXT NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL,
      PRIMARY KEY (owner, day));
CREATE TABLE IF NOT EXISTS public.schema_migrations (
      version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.worker_heartbeats (
      id TEXT PRIMARY KEY, seen_at TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.reliability_trials (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES public.organizations(id),
      created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      revision INTEGER NOT NULL, protocol_json TEXT NOT NULL, predictions_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.runs (
      id TEXT PRIMARY KEY, goal TEXT NOT NULL, dataset_name TEXT NOT NULL,
      dataset_text TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error TEXT,
      owner TEXT, dataset_id TEXT, lease_owner TEXT, lease_expires_at TEXT,
      report_language TEXT, mapping_json TEXT, joins_json TEXT,
      connector_id TEXT, assumptions_json TEXT, idempotency_key TEXT, request_hash TEXT,
      paused INTEGER);
CREATE TABLE IF NOT EXISTS public.tasks (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES public.runs(id),
      idx INTEGER NOT NULL, role TEXT NOT NULL, title TEXT NOT NULL,
      state TEXT NOT NULL, summary TEXT, result_json TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS public.kpi_policies (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES public.runs(id),
      version INTEGER NOT NULL, revision TEXT NOT NULL, rules_json TEXT NOT NULL,
      actor TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE (run_id, version));
CREATE TABLE IF NOT EXISTS public.approvals (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES public.runs(id),
      action TEXT NOT NULL, target TEXT NOT NULL, risk TEXT NOT NULL,
      impact TEXT NOT NULL, reversibility TEXT NOT NULL,
      content_hash TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, decided_at TEXT, decided_by TEXT);
CREATE TABLE IF NOT EXISTS public.artifacts (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES public.runs(id),
      name TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
      content TEXT NOT NULL, published_path TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.sessions (
      id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      ended INTEGER NOT NULL, preferences_json TEXT NOT NULL,
      history_json TEXT NOT NULL, transcript_json TEXT NOT NULL,
      next_entry_id INTEGER NOT NULL, owner TEXT);
CREATE TABLE IF NOT EXISTS public.memory_kv (
      owner TEXT NOT NULL, key TEXT NOT NULL, text TEXT NOT NULL,
      category TEXT NOT NULL, updated TEXT,
      PRIMARY KEY (owner, key));
CREATE TABLE IF NOT EXISTS public.vault_notes (
      path TEXT PRIMARY KEY, run_id TEXT NOT NULL,
      content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.datasets (
      id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, name TEXT NOT NULL,
      content TEXT NOT NULL, byte_size INTEGER NOT NULL,
      owner TEXT NOT NULL, created_at TEXT NOT NULL,
      source_format TEXT, row_count INTEGER, column_count INTEGER,
      mapping_json TEXT, mapping_updated_at TEXT);
CREATE TABLE IF NOT EXISTS public.connectors (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
      url TEXT NOT NULL, format TEXT, sheet TEXT, every_minutes INTEGER,
      goal TEXT NOT NULL, language TEXT NOT NULL, profile TEXT,
      enabled INTEGER NOT NULL, failures INTEGER NOT NULL,
      last_status TEXT, last_error TEXT, last_checked_at TEXT,
      last_dataset_id TEXT, last_sha256 TEXT, last_run_id TEXT,
      next_due_at TEXT, lease_owner TEXT, lease_expires_at TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, credential_id TEXT);
CREATE TABLE IF NOT EXISTS public.rmd_packs (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, organization_id TEXT,
      title TEXT NOT NULL, revision INTEGER NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.rmd_sources (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES public.rmd_packs(id),
      name TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL,
      revision INTEGER NOT NULL, metadata_json TEXT NOT NULL,
      mapping_json TEXT NOT NULL, original_base64 TEXT NOT NULL,
      artifacts_json TEXT NOT NULL, applicability_json TEXT NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(pack_id, name, kind, sha256));
CREATE TABLE IF NOT EXISTS public.rmd_analyses (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES public.rmd_packs(id),
      created_at TEXT NOT NULL, pack_revision INTEGER NOT NULL,
      fingerprint TEXT NOT NULL, language TEXT NOT NULL,
      filters_json TEXT NOT NULL, result_json TEXT NOT NULL,
      records_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.rmd_links (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES public.rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES public.rmd_analyses(id),
      left_record_id TEXT NOT NULL, right_record_id TEXT NOT NULL,
      method TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
      detail_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.rmd_analysis_sources (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES public.rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES public.rmd_analyses(id),
      sources_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.rmd_runs (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES public.rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES public.rmd_analyses(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.rmd_actions (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES public.rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES public.rmd_analyses(id),
      priority_id TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
      body_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(pack_id, analysis_id, priority_id));
CREATE TABLE IF NOT EXISTS public.rmd_incidents (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES public.rmd_packs(id),
      title TEXT NOT NULL, record_ids_json TEXT NOT NULL,
      revision INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.rmd_audit (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES public.rmd_packs(id),
      actor TEXT NOT NULL, action TEXT NOT NULL, entity_id TEXT NOT NULL,
      revision INTEGER NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.rmd_requests (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, pack_id TEXT,
      operation TEXT NOT NULL, request_key TEXT NOT NULL,
      payload_hash TEXT NOT NULL, response_json TEXT NOT NULL,
      created_at TEXT NOT NULL, UNIQUE(owner, operation, request_key));
ALTER TABLE public.runs ADD COLUMN IF NOT EXISTS assumptions_json TEXT;
ALTER TABLE public.runs ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE public.runs ADD COLUMN IF NOT EXISTS request_hash TEXT;
ALTER TABLE public.approvals ADD COLUMN IF NOT EXISTS decided_by TEXT;
ALTER TABLE public.connectors ADD COLUMN IF NOT EXISTS credential_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS runs_idempotency ON public.runs (owner, idempotency_key);
CREATE INDEX IF NOT EXISTS tasks_role_state_run ON public.tasks (role, state, run_id);
DO $security$ DECLARE tab text; grantee text; BEGIN
 FOR tab IN SELECT unnest(ARRAY['schema_migrations','rate_windows','model_calls_daily','runs','tasks','approvals','artifacts','sessions','memory_kv','vault_notes','datasets','connectors','kpi_policies','organizations','organization_members','operation_sites','operation_assets','work_orders','operation_audit','operation_requests','worker_heartbeats','reliability_trials','rmd_packs','rmd_sources','rmd_analyses','rmd_analysis_sources','rmd_runs','rmd_links','rmd_actions','rmd_incidents','rmd_audit','rmd_requests']) LOOP
 EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',tab);
 EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC',tab);
 FOR grantee IN SELECT rolname FROM pg_catalog.pg_roles WHERE rolname IN ('anon','authenticated') LOOP
 EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I',tab,grantee);
 END LOOP; END LOOP; END $security$;
INSERT INTO public.schema_migrations(version,applied_at) VALUES (1,to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS"Z"')) ON CONFLICT(version) DO NOTHING;
COMMIT;
