-- Additive private evidence schema; apply through the approved database migration workflow.
-- No original documents, operational records or credentials.
BEGIN;
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
