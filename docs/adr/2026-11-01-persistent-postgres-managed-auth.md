# Persistent PostgreSQL and managed auth for the pilot

Date: 2026-11-01. Status: proposed (Tier 2 item 1).

## Decision

The public RMD flagship runs its pilot on SQLite with a local admin account.
That is acceptable for a single-user demo and unacceptable for a hosted pilot
with more than one user. Move the pilot to PostgreSQL with managed
authentication before any external user is invited.

Concretely:

- Database: PostgreSQL (Supabase or equivalent managed Postgres). The schema
  already targets Postgres for the hosted path; SQLite stays for local dev.
- Auth: a managed provider (Supabase Auth or equivalent) instead of the
  local hashed-token directory. Identity comes from the provider; no custom
  password system is built.
- Migrations: run `supabase/migrations/0001_init.sql` (or the repo's
  equivalent) once per environment and record the applied version in the
  deploy note.
- Env vars required: `DATABASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`,
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
  `NEXT_PUBLIC_APP_URL`. Each must be set in the hosting provider and listed
  in the deploy note.

## Why

KNOWN_LIMITATIONS already states the honest version: the pilot runs on SQLite
and local auth. A hosted pilot needs persistent state and named users. This is
the single biggest blocker to a real external pilot and it is infra, not code.

## Validation and reversibility

- CI stays green on main before and after.
- A smoke test signs up a new account, creates a project, uploads a document,
  extracts it and publishes a report, against the Postgres-backed deployment.
- Reversible: keep SQLite as the local dev default; the hosted path is selected
  by `DATABASE_URL`. Roll back by pointing the deployment at the previous
  build; no data migration is required until the first real pilot user exists.

## Open items

- Supabase URL + keys and Vercel access are needed from the owner (parallel
  track). No code change proceeds past the env-var inventory without them.
