-- Asset Reliability AI: secure initial application schema
-- Mirrors server/storage.py SCHEMA_STATEMENTS and additive _migrate columns.
-- PostgREST / anon / authenticated are intentionally NOT granted table access.
-- Backend uses managed PostgreSQL (psycopg2) with server-side owner checks.
-- No secrets, user records, customer data, or privileged credentials in this file.
-- Migration generated 2026-10-18; apply only to dedicated Team 3 Supabase project.
BEGIN;
CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY, goal TEXT NOT NULL, dataset_name TEXT NOT NULL,
      dataset_text TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error TEXT,
      owner TEXT,
      dataset_id TEXT,
      lease_owner TEXT,
      lease_expires_at TEXT,
      report_language TEXT,
      mapping_json TEXT,
      joins_json TEXT,
      connector_id TEXT,
      paused INTEGER);

CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      idx INTEGER NOT NULL, role TEXT NOT NULL, title TEXT NOT NULL,
      state TEXT NOT NULL, summary TEXT, result_json TEXT, updated_at TEXT);

CREATE TABLE IF NOT EXISTS approvals (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      action TEXT NOT NULL, target TEXT NOT NULL, risk TEXT NOT NULL,
      impact TEXT NOT NULL, reversibility TEXT NOT NULL,
      content_hash TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, decided_at TEXT);

CREATE TABLE IF NOT EXISTS artifacts (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      name TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
      content TEXT NOT NULL, published_path TEXT, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      ended INTEGER NOT NULL, preferences_json TEXT NOT NULL,
      history_json TEXT NOT NULL, transcript_json TEXT NOT NULL,
      next_entry_id INTEGER NOT NULL,
      owner TEXT);

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
      source_format TEXT,
      row_count INTEGER,
      column_count INTEGER,
      mapping_json TEXT,
      mapping_updated_at TEXT);

CREATE TABLE IF NOT EXISTS connectors (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
      url TEXT NOT NULL, format TEXT, sheet TEXT, every_minutes INTEGER,
      goal TEXT NOT NULL, language TEXT NOT NULL, profile TEXT,
      enabled INTEGER NOT NULL, failures INTEGER NOT NULL,
      last_status TEXT, last_error TEXT, last_checked_at TEXT,
      last_dataset_id TEXT, last_sha256 TEXT, last_run_id TEXT,
      next_due_at TEXT, lease_owner TEXT, lease_expires_at TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE INDEX IF NOT EXISTS ar_ai_runs_owner_created_idx ON runs (owner, created_at);
CREATE INDEX IF NOT EXISTS ar_ai_runs_owner_updated_idx ON runs (owner, updated_at);
CREATE INDEX IF NOT EXISTS ar_ai_datasets_owner_created_idx ON datasets (owner, created_at);
CREATE INDEX IF NOT EXISTS ar_ai_connectors_owner_created_idx ON connectors (owner, created_at);
CREATE INDEX IF NOT EXISTS ar_ai_tasks_run_idx ON tasks (run_id);
CREATE INDEX IF NOT EXISTS ar_ai_approvals_run_idx ON approvals (run_id);
CREATE INDEX IF NOT EXISTS ar_ai_artifacts_run_idx ON artifacts (run_id);
ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.runs FROM PUBLIC, anon, authenticated;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.tasks FROM PUBLIC, anon, authenticated;
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
COMMIT;
