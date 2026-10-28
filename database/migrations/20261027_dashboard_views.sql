-- Additive hosted migration (ADR 2026-10-27-interactive-dashboard).
--
-- Creates one backend-only table, dashboard_views: a saved dashboard view per
-- owner and dataset. Nothing existing is altered. Row level security is on and
-- every direct client grant is revoked, as for the other application tables.
--
-- Apply only through the database operator, after review and with a current
-- backup, and BEFORE deploying the application revision that lists this table
-- in its schema contract: the hosted server in verify mode refuses to start
-- without it. Re-running this file is safe; it refuses a table of another shape.
-- See docs/HOSTED_MIGRATION_20261027.md for the steps and checks.
BEGIN;
DO $preflight$
DECLARE found integer;
BEGIN
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_class c
             JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND c.relname = 'dashboard_views') THEN
    SELECT count(*) INTO found FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'dashboard_views'
        AND column_name IN ('id', 'owner', 'dataset_key', 'run_id', 'page', 'query', 'updated_at');
    IF found <> 7 THEN
      RAISE EXCEPTION 'public.dashboard_views exists with a different shape; review before applying';
    END IF;
  END IF;
END $preflight$;
CREATE TABLE IF NOT EXISTS public.dashboard_views (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, dataset_key TEXT NOT NULL,
      run_id TEXT NOT NULL, page TEXT NOT NULL, query TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE (owner, dataset_key));
CREATE UNIQUE INDEX IF NOT EXISTS dashboard_views_owner_dataset
      ON public.dashboard_views (owner, dataset_key);
DO $security$ DECLARE grantee text; BEGIN
 ALTER TABLE public.dashboard_views ENABLE ROW LEVEL SECURITY;
 REVOKE ALL ON TABLE public.dashboard_views FROM PUBLIC;
 FOR grantee IN SELECT rolname FROM pg_catalog.pg_roles WHERE rolname IN ('anon','authenticated') LOOP
 EXECUTE format('REVOKE ALL ON TABLE public.dashboard_views FROM %I',grantee);
 END LOOP; END $security$;
COMMIT;
