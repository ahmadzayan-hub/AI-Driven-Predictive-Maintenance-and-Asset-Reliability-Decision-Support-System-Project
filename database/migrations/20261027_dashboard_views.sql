-- Additive deployment migration (ADR 2026-10-27-interactive-dashboard).
-- Review/apply through the database operator; changing this file does not
-- apply it to any hosted database. The table is backend-only like the
-- others: row level security on, every direct-client grant revoked.
BEGIN;
CREATE TABLE IF NOT EXISTS public.dashboard_views (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, dataset_key TEXT NOT NULL,
      run_id TEXT NOT NULL, page TEXT NOT NULL, query TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE (owner, dataset_key));
DO $security$ DECLARE grantee text; BEGIN
 ALTER TABLE public.dashboard_views ENABLE ROW LEVEL SECURITY;
 REVOKE ALL ON TABLE public.dashboard_views FROM PUBLIC;
 FOR grantee IN SELECT rolname FROM pg_catalog.pg_roles WHERE rolname IN ('anon','authenticated') LOOP
 EXECUTE format('REVOKE ALL ON TABLE public.dashboard_views FROM %I',grantee);
 END LOOP; END $security$;
COMMIT;
