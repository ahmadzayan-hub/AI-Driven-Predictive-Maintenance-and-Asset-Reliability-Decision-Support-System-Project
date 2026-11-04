-- Additive hosted migration (ADRs 2026-11-04-shared-review, -executive-video, -layout-history).
--
-- Creates three backend-only tables: export_reviews (append-only review
-- decisions), export_videos (rendered or failed executive videos) and
-- layout_versions (designed-page layouts per reader and run). Nothing existing
-- is altered. Row level security is on and every direct client grant is
-- revoked, as for the other application tables.
--
-- Apply only through the database operator, after review and with a current
-- backup, and BEFORE deploying the application revision that lists these tables
-- in its schema contract: the hosted server in verify mode refuses to start
-- without them. Re-running this file is safe.
-- See docs/HOSTED_MIGRATION_20261104.md for the steps and checks.
BEGIN;
CREATE TABLE IF NOT EXISTS public.export_reviews (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL, snapshot_id TEXT NOT NULL,
      format TEXT NOT NULL, language TEXT NOT NULL, artifact_sha256 TEXT NOT NULL,
      decision TEXT NOT NULL, comment TEXT NOT NULL, reviewer TEXT NOT NULL,
      created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.export_videos (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL, owner TEXT NOT NULL,
      snapshot_id TEXT NOT NULL, language TEXT NOT NULL, state TEXT NOT NULL,
      error TEXT, manifest_json TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public.layout_versions (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, run_id TEXT NOT NULL,
      version INTEGER NOT NULL, action TEXT NOT NULL, fingerprint TEXT NOT NULL,
      result_json TEXT NOT NULL, pinned_json TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE (owner, run_id, version));
DO $security$ DECLARE grantee text; tbl text; BEGIN
 FOREACH tbl IN ARRAY ARRAY['export_reviews','export_videos','layout_versions'] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
  EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC', tbl);
  FOR grantee IN SELECT rolname FROM pg_catalog.pg_roles WHERE rolname IN ('anon','authenticated') LOOP
   EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I', tbl, grantee);
  END LOOP;
 END LOOP; END $security$;
COMMIT;
