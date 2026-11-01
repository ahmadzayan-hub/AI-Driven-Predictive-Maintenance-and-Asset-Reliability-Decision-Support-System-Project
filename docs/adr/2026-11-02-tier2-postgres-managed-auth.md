# Tier 2 release gate: persistent PostgreSQL and managed authentication

Date: 2026-11-02 · Status: **Proposed, awaiting the owner's decision.** No
schema or auth change is shipped by this record alone.

## Context

The pilot runs on SQLite with a single shared database file and no managed
identity. `KNOWN_LIMITATIONS.md` and issue #13 list persistent PostgreSQL plus
managed authentication as a P0 SaaS launch blocker. The portfolio review
records this as a Tier 2 "Production MVP" item that needs an ADR and a
release gate before it can be called shipped.

The code already supports both backends: `PG_TEST_URL` gates the PostgreSQL
test path, `scripts/verify.py` runs the SQLite path by default, and
`docs/SUPABASE_SECURE_CONNECTION.md` documents the Supabase bootstrap. What
is missing is a documented, testable gate that says "this configuration is
approved to host real tenants".

## Release gate (all must hold before merge to main)

1. **Schema parity.** `tests/test_runs.py` PostgreSQL path passes against a
   fresh database created from the tracked migration scripts, with zero
   manual steps. No SQLite-only behaviour leaks into the hosted path.
2. **Managed identity.** Sign-in comes from a managed provider (ADR 0002);
   no custom password system. PKCE onboarding and passwordless recovery
   (ADR 2026-10-23-managed-auth-onboarding) are exercised end to end in the
   hosted environment.
3. **Tenant isolation.** Cross-tenant reads are covered by the platform
   contract tests; a run created by tenant A is never visible to tenant B.
4. **Backup and restore.** A documented restore procedure from a nightly
   backup is tested once against a non-production database.
5. **Rollback.** Promoting the previous deployment is documented and does
   not lose data.
6. **Env vars.** `DATABASE_URL`, the sign-in provider keys and
   `NEXT_PUBLIC_APP_URL` are listed in `docs/VERCEL_DEPLOYMENT.md` with
   their source of truth.

## Decision requested

Approve starting the PostgreSQL migration slice, or keep the pilot on SQLite
and relabel the product "single-tenant pilot" in the README.

## Consequences if approved

- New work lands on a branch and merges only when all six gate items are
  evidenced in CI. No partial "production" claim may appear in
  `KNOWN_LIMITATIONS.md` until then.
- SQLite stays the default for local development and tests.
