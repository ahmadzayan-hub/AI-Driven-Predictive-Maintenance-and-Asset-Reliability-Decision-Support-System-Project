# ADR 0046: Dedicated Supabase data plane and managed Auth bootstrap

Date: 2026-10-18 · Status: Database applied; Auth integration staged, not activated.

## Context
Team 3's Vercel application previously ran without `DATABASE_URL`, falling back to
ephemeral SQLite and local single-owner identity. The user approved creating an
isolated project `asset-reliability-ai-saas` under the existing Supabase organization
in `ap-south-1` (creation quoted at $0/month). The legacy `agentic-os` project is
unrelated and must remain unchanged.

## Database decision
Use `server/storage.py` as the source of truth. Migration
`database/migrations/20261018_asset_reliability_ai_initial.sql` provisions its
nine tables plus additive columns and query indexes. It is applied as
`asset_reliability_ai_initial_schema_20261018` via Supabase management API.

Tables reside in `public` because the existing PostgresStore uses unqualified
SQL names. Every table is RLS enabled, has no permissive policies, and explicitly
revokes table access from PUBLIC, anon and authenticated. Supabase's REST data API
cannot access their contents. The backend must connect using an appropriately
protected Postgres wire-protocol credential and enforce per-owner permissions.

RLS-without-policy warnings from Supabase security advisors are **expected
deny-by-default behavior** for this backend-only database architecture.

## Auth decision
Reuse `server/auth.py` and Supabase managed Auth; do not build passwords or
custom JWTs. The browser may receive a modern publishable key, but it must not
put `sb_publishable_...` into `Authorization: Bearer`; the `apikey` header is
sufficient before user authentication. Password sign-in is implemented.
Magic-link sign-in is not advertised until callbacks and redirects work.

Persist the provider URL, publishable key, expected JWT issuer/audience and
least-privilege `viewer` default in Vercel's encrypted variables.
Do not activate `AGENTIC_OS_JWKS_URL` or `AGENTIC_OS_ENV=production` until the
signing algorithm and database connection are verified. JWT verification
must use asymmetrically signed RS256/ES256 tokens through JWKS, with `sub`,
`iss`, `aud` and expiry checks, and forbid user_metadata role escalation.
Never publish an HS256 secret, service_role key or `DATABASE_URL`.

## State of delivery
- Confirmed: Supabase project active, 9 tables present, all RLS, direct
  anon/authenticated table SELECT and INSERT denied.
- Confirmed: Vercel has five encrypted non-activating Auth configuration variables.
- Pending: Secure `DATABASE_URL` transfer via Supabase Connect/Vercel Settings,
  project JWT signing key mode, invited user account, assignment of approved
  engineer/analyst role, restricted email redirects and real-user session QA.
- Pending: Vercel redeployment with both secure DB and a valid signing verifier.
- Pending: browser, role isolation and cold-start persistence acceptance tests.

**Release must not be represented as complete enterprise authentication until
the pending gates pass.**

## Verification
The snapshot test `tests/test_supabase_schema_snapshot.py` checks table parity,
RLS and revocations. After protected env activation, verify anonymous API
denial, password login, persistent upload/runs after cold start, and cross-user
404 isolation, including browser language parity.
