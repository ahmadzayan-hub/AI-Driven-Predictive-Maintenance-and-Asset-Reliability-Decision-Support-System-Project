-- Asset Reliability AI: secure initial application schema
-- Mirrors server/storage.py SCHEMA_STATEMENTS, which since 23 October carry
-- every column the additive _migrate pass adds to older databases.
-- PostgREST / anon / authenticated are intentionally NOT granted table access.
-- Backend uses managed PostgreSQL (psycopg2) with server-side owner checks.
-- No secrets, user records, customer data, or privileged credentials in this file.
-- Migration generated 2026-10-18; apply only to dedicated Team 3 Supabase project.
-- Snapshot refreshed 2026-10-22 for private evidence workspaces and governed review.
-- This is the initial-schema mirror; editing it does not apply a hosted migration.
BEGIN;
CREATE TABLE IF NOT EXISTS organizations (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS organization_members (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      subject TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, subject));

CREATE TABLE IF NOT EXISTS operation_sites (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      code TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, code));

CREATE TABLE IF NOT EXISTS operation_assets (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      site_id TEXT NOT NULL REFERENCES operation_sites(id),
      external_id TEXT NOT NULL, source_system TEXT NOT NULL, name TEXT NOT NULL,
      criticality TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, source_system, external_id));

CREATE TABLE IF NOT EXISTS work_orders (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      asset_id TEXT NOT NULL REFERENCES operation_assets(id), title TEXT NOT NULL,
      rationale TEXT NOT NULL, status TEXT NOT NULL, priority TEXT NOT NULL,
      assignee TEXT NOT NULL, due_date TEXT NOT NULL, evidence_json TEXT NOT NULL,
      completion_json TEXT NOT NULL, version INTEGER NOT NULL,
      created_by TEXT NOT NULL, authorized_by TEXT, created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS operation_audit (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      entity_id TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
      version INTEGER NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS operation_requests (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      actor TEXT NOT NULL, request_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
      response_json TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, actor, request_key));

CREATE TABLE IF NOT EXISTS worker_heartbeats (
      id TEXT PRIMARY KEY, seen_at TEXT NOT NULL, state TEXT NOT NULL);

-- Which migration pass the store has applied (P2 slice two, B12).
CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS reliability_trials (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      revision INTEGER NOT NULL, protocol_json TEXT NOT NULL, predictions_json TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY, goal TEXT NOT NULL, dataset_name TEXT NOT NULL,
      dataset_text TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error TEXT,
      owner TEXT, dataset_id TEXT, lease_owner TEXT, lease_expires_at TEXT,
      report_language TEXT, mapping_json TEXT, joins_json TEXT,
      connector_id TEXT, assumptions_json TEXT, idempotency_key TEXT,
      paused INTEGER);

CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      idx INTEGER NOT NULL, role TEXT NOT NULL, title TEXT NOT NULL,
      state TEXT NOT NULL, summary TEXT, result_json TEXT, updated_at TEXT);

CREATE TABLE IF NOT EXISTS kpi_policies (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      version INTEGER NOT NULL, revision TEXT NOT NULL, rules_json TEXT NOT NULL,
      actor TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE (run_id, version));

CREATE TABLE IF NOT EXISTS approvals (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      action TEXT NOT NULL, target TEXT NOT NULL, risk TEXT NOT NULL,
      impact TEXT NOT NULL, reversibility TEXT NOT NULL,
      content_hash TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, decided_at TEXT, decided_by TEXT);

CREATE TABLE IF NOT EXISTS artifacts (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      name TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
      content TEXT NOT NULL, published_path TEXT, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      ended INTEGER NOT NULL, preferences_json TEXT NOT NULL,
      history_json TEXT NOT NULL, transcript_json TEXT NOT NULL,
      next_entry_id INTEGER NOT NULL, owner TEXT);

CREATE TABLE IF NOT EXISTS memory_kv (
      owner TEXT NOT NULL, key TEXT NOT NULL, text TEXT NOT NULL,
      category TEXT NOT NULL, updated TEXT,
      PRIMARY KEY (owner, key));

CREATE TABLE IF NOT EXISTS vault_notes (
      path TEXT PRIMARY KEY, run_id TEXT NOT NULL,
      content TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS datasets (
      id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, name TEXT NOT NULL,
      content TEXT NOT NULL, byte_size INTEGER NOT NULL,
      owner TEXT NOT NULL, created_at TEXT NOT NULL,
      source_format TEXT, row_count INTEGER, column_count INTEGER,
      mapping_json TEXT, mapping_updated_at TEXT);

CREATE TABLE IF NOT EXISTS connectors (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
      url TEXT NOT NULL, format TEXT, sheet TEXT, every_minutes INTEGER,
      goal TEXT NOT NULL, language TEXT NOT NULL, profile TEXT,
      enabled INTEGER NOT NULL, failures INTEGER NOT NULL,
      last_status TEXT, last_error TEXT, last_checked_at TEXT,
      last_dataset_id TEXT, last_sha256 TEXT, last_run_id TEXT,
      next_due_at TEXT, lease_owner TEXT, lease_expires_at TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, credential_id TEXT);

CREATE TABLE IF NOT EXISTS rmd_packs (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, organization_id TEXT,
      title TEXT NOT NULL, revision INTEGER NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rmd_sources (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      name TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL,
      revision INTEGER NOT NULL, metadata_json TEXT NOT NULL,
      mapping_json TEXT NOT NULL, original_base64 TEXT NOT NULL,
      artifacts_json TEXT NOT NULL, applicability_json TEXT NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(pack_id, name, kind, sha256));

CREATE TABLE IF NOT EXISTS rmd_analyses (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      created_at TEXT NOT NULL, pack_revision INTEGER NOT NULL,
      fingerprint TEXT NOT NULL, language TEXT NOT NULL,
      filters_json TEXT NOT NULL, result_json TEXT NOT NULL,
      records_json TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rmd_links (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES rmd_analyses(id),
      left_record_id TEXT NOT NULL, right_record_id TEXT NOT NULL,
      method TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
      detail_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rmd_analysis_sources (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES rmd_analyses(id),
      sources_json TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rmd_runs (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES rmd_analyses(id), created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rmd_actions (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES rmd_analyses(id),
      priority_id TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
      body_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(pack_id, analysis_id, priority_id));

CREATE TABLE IF NOT EXISTS rmd_incidents (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      title TEXT NOT NULL, record_ids_json TEXT NOT NULL,
      revision INTEGER NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rmd_audit (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      actor TEXT NOT NULL, action TEXT NOT NULL, entity_id TEXT NOT NULL,
      revision INTEGER NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS rmd_requests (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, pack_id TEXT,
      operation TEXT NOT NULL, request_key TEXT NOT NULL,
      payload_hash TEXT NOT NULL, response_json TEXT NOT NULL,
      created_at TEXT NOT NULL, UNIQUE(owner, operation, request_key));

CREATE INDEX IF NOT EXISTS ar_ai_runs_owner_created_idx ON runs (owner, created_at);
CREATE INDEX IF NOT EXISTS ar_ai_runs_owner_updated_idx ON runs (owner, updated_at);
CREATE INDEX IF NOT EXISTS ar_ai_datasets_owner_created_idx ON datasets (owner, created_at);
CREATE INDEX IF NOT EXISTS ar_ai_connectors_owner_created_idx ON connectors (owner, created_at);
CREATE INDEX IF NOT EXISTS ar_ai_tasks_run_idx ON tasks (run_id);
CREATE INDEX IF NOT EXISTS ar_ai_approvals_run_idx ON approvals (run_id);
CREATE INDEX IF NOT EXISTS ar_ai_artifacts_run_idx ON artifacts (run_id);
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.organizations FROM PUBLIC, anon, authenticated;
ALTER TABLE public.organization_members ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.organization_members FROM PUBLIC, anon, authenticated;
ALTER TABLE public.operation_sites ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.operation_sites FROM PUBLIC, anon, authenticated;
ALTER TABLE public.operation_assets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.operation_assets FROM PUBLIC, anon, authenticated;
ALTER TABLE public.work_orders ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.work_orders FROM PUBLIC, anon, authenticated;
ALTER TABLE public.operation_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.operation_audit FROM PUBLIC, anon, authenticated;
ALTER TABLE public.operation_requests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.operation_requests FROM PUBLIC, anon, authenticated;
ALTER TABLE public.worker_heartbeats ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.worker_heartbeats FROM PUBLIC, anon, authenticated;
ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.schema_migrations FROM PUBLIC, anon, authenticated;
ALTER TABLE public.reliability_trials ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.reliability_trials FROM PUBLIC, anon, authenticated;
ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.runs FROM PUBLIC, anon, authenticated;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.tasks FROM PUBLIC, anon, authenticated;
ALTER TABLE public.kpi_policies ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.kpi_policies FROM PUBLIC, anon, authenticated;
ALTER TABLE public.approvals ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.approvals FROM PUBLIC, anon, authenticated;
ALTER TABLE public.artifacts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.artifacts FROM PUBLIC, anon, authenticated;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.sessions FROM PUBLIC, anon, authenticated;
ALTER TABLE public.memory_kv ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.memory_kv FROM PUBLIC, anon, authenticated;
ALTER TABLE public.vault_notes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.vault_notes FROM PUBLIC, anon, authenticated;
ALTER TABLE public.datasets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.datasets FROM PUBLIC, anon, authenticated;
ALTER TABLE public.connectors ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.connectors FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_packs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_packs FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_sources ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_sources FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_analyses ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_analyses FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_analysis_sources ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_analysis_sources FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_runs FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_links ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_links FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_actions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_actions FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_incidents ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_incidents FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_audit ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_audit FROM PUBLIC, anon, authenticated;
ALTER TABLE public.rmd_requests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.rmd_requests FROM PUBLIC, anon, authenticated;
COMMIT;

