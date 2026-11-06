# Hosted migration of 4 November 2026: reviews, videos and layout versions

Status: **applied** on 6 November 2026, with the owner's approval, to the hosted
Supabase project `asset-reliability-ai-saas` (every table then held 0 rows).
Checked after applying: row level security on, no grant to `PUBLIC`, `anon` or
`authenticated`. Supabase's advisor reports only the expected notice that RLS has
no policies, as for every backend-only table.

## What it changes

- `database/migrations/20261104_reviews_videos_layouts.sql` creates three tables:
  `public.export_reviews` (append-only review decisions, ADR
  `docs/adr/2026-11-04-shared-review.md`), `public.export_videos` (rendered or
  failed executive videos, ADR `docs/adr/2026-11-04-executive-video.md`) and
  `public.layout_versions` (designed-page layouts per reader and run, ADR
  `docs/adr/2026-11-04-layout-history.md`).
- Nothing existing is altered. Each table is backend-only like the others: row
  level security on, and every direct client grant revoked (`PUBLIC`, `anon`,
  `authenticated`). Running the file twice is safe.

## Why it must run before the application

The hosted server in verify mode checks the database against the schema it
expects, which now includes these tables. A revision deployed before they exist
will not start and names the missing table in its startup error. The server never
repairs a hosted schema.

## Steps for the operator

1. **Review** the file: three `CREATE TABLE` statements and the security block.
2. **Back up** the hosted database, or confirm a current backup exists.
3. **Apply** it through the Supabase SQL editor, or with `psql` over the session
   pooler (`docs/SUPABASE_SECURE_CONNECTION.md`). Never paste a password or
   connection string into a chat or the repository.
4. **Check** with the queries below.
5. **Deploy** the application revision that includes the tables.

## Read-only checks

```sql
-- Three rows, each with relrowsecurity = true.
SELECT c.relname, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN ('export_reviews', 'export_videos', 'layout_versions');
-- No rows: no direct grant to client roles.
SELECT table_name, grantee, privilege_type FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND table_name IN ('export_reviews', 'export_videos', 'layout_versions')
  AND grantee IN ('PUBLIC', 'anon', 'authenticated');
```

## Video files

Video files are written to `AGENTIC_OS_EXPORT_DIR` (default `data/exports/`) on the
host that renders them, which needs ffmpeg, ffprobe, espeak-ng and Pillow with
libraqm. The Vercel functions have none of these, so they render nothing and say so.
