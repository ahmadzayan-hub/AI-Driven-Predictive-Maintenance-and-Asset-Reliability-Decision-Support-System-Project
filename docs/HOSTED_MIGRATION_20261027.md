# Hosted migration of 27 October 2026: the saved dashboard view table

Status: ready for operator review. **Not applied** to any hosted database by
this repository. Applying it is the database operator's step, after review.

## What it changes

- `database/migrations/20261027_dashboard_views.sql` creates one table,
  `public.dashboard_views`, which holds one saved dashboard view per owner and
  dataset (ADR `docs/adr/2026-10-27-interactive-dashboard.md`).
- Nothing existing is altered. The table is backend-only like the others:
  row level security on, and every direct client grant revoked (`PUBLIC`,
  `anon`, `authenticated`).
- The file refuses to run if a `dashboard_views` table of another shape
  already exists. Running it twice is safe.

## Why it must run before the application

The hosted server in verify mode checks the database against the schema it
expects, and that expectation now includes `dashboard_views`. A revision
deployed before the table exists will not start, and it will say
`dashboard_views:missing_table` in its startup error. This is intended: the
server never repairs a hosted schema.

## Steps for the operator

1. **Review** `database/migrations/20261027_dashboard_views.sql`. It contains
   one `CREATE TABLE`, one `CREATE UNIQUE INDEX`, and the security block. There
   are no other statements.
2. **Back up** the hosted database, or confirm that a current backup exists.
3. **Apply** it through the Supabase SQL editor, or with `psql` over the session
   pooler as described in `docs/SUPABASE_SECURE_CONNECTION.md`. Do not paste a
   password or connection string into a chat or into the repository.
4. **Check** with the read-only queries below. Each should return the stated
   value.
5. **Deploy** the application revision that includes the table.

## Read-only checks

```sql
-- 1. The table exists with the seven columns, in this order.
SELECT column_name FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'dashboard_views'
 ORDER BY ordinal_position;
-- expect: id, owner, dataset_key, run_id, page, query, updated_at

-- 2. Row level security is on.
SELECT c.relrowsecurity FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relname = 'dashboard_views';
-- expect: true

-- 3. Direct client roles have no access.
SELECT has_table_privilege('anon', 'public.dashboard_views', 'SELECT') AS anon_read,
       has_table_privilege('authenticated', 'public.dashboard_views', 'SELECT') AS authed_read;
-- expect: false, false
```

If a role named `anon` or `authenticated` does not exist on the project, the
third query errors. That is expected, and it means there is no such role to
grant access.

## Rollback

1. **Roll back the application first**, to the revision before the table was
   listed. That revision does not read the table, so it starts without it.
2. Only then, if the table must go, run `DROP TABLE public.dashboard_views;`.
   This deletes every saved dashboard view. It does not touch runs, datasets
   or any other table.

Rolling back the migration while the new revision is still deployed stops that
revision from starting, so do the application step first.

## Record

When applied, the operator records the date, the operator's name, and the
result of each check above in the hosted-operations log. This repository does
not record the hosted project's identifiers beyond what
`docs/SUPABASE_SECURE_CONNECTION.md` already states.
