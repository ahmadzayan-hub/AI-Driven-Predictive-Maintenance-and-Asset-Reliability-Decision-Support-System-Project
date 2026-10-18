# Connecting Asset Reliability AI to its dedicated Supabase backend

## Already provisioned (18 October 2026)
- Project ID: `uiommvpyzutkkurjoajw` (`asset-reliability-ai-saas`).
- Region: `ap-south-1`. Created at quoted $0/month.
- Applied migration `asset_reliability_ai_initial_schema_20261018`.
- Nine backend-only application tables; RLS enabled and direct client grants removed.
- Vercel project `asset-reliability-team3-saas` has five encrypted,
  **non-secret** auth settings: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
  `AGENTIC_OS_JWT_ISSUER`, `AGENTIC_OS_JWT_AUDIENCE`,
  `AGENTIC_OS_DEFAULT_ROLE=viewer`.

## Protected credential transfer — perform in platform dashboards
1. Open [Supabase project](https://supabase.com/dashboard/project/uiommvpyzutkkurjoajw)
   → **Connect** → select the **Session pooler** (IPv4 compatible) and copy the
   URI to a password manager, entering its DB password there if prompted.
   Prefer port 5432 initially; never paste the password or URI into a chat
   or public repository. Avoid sharing a DB password with the browser.
2. Open [Vercel environment settings](https://vercel.com/celia2026-3923s-projects/asset-reliability-team3-saas/settings/environment-variables),
   create `DATABASE_URL` with the pooler URI as a **Sensitive** or
   **Encrypted** variable, scoped to a controlled preview first.
3. In Supabase **Authentication → JWT Signing Keys**, confirm that issued
   user tokens are RS256 or ES256, and that the public JWKS endpoint
   contains an active public key. If not, configure/rotate an asymmetric
   signing key in Supabase before enabling JWT verification.
4. In Vercel, configure `AGENTIC_OS_JWKS_URL` to
   `https://uiommvpyzutkkurjoajw.supabase.co/auth/v1/.well-known/jwks.json`.
   Set `AGENTIC_OS_REQUIRE_AUTH=1` for the same preview target;
   only then activate `AGENTIC_OS_ENV=production` for the final,
   production-scoped release after successful validation.
5. In Supabase **Authentication → URL Configuration**, set the correct
   SaaS Site URL and explicit allowed redirect domains, after assessing
   which host is actually used. Enable a production SMTP provider before
   relying on email invitations. Invite a known test account through
   Supabase Auth, verify its email, and test password login.
6. By default every valid user has a read-only `viewer` role. Assign a
   single approved user ID to an `analyst` or `owner` role via the
   server-only `AGENTIC_OS_ROLE_ASSIGNMENTS` env variable, e.g.
   `<verified-user-uuid>:analyst`. Never grant platform `admin` by
   user-controlled claims, and don't disable authorization for testing.
7. Test authenticated requests, denied unauthorized requests,
   tenant isolation, dataset persistence over cold starts and
   report approval. Only after success, repeat the secure settings
   for production and redeploy.

## Why activation is gated
The current Vercel app cannot be switched to full JWT production until
the DB credential is supplied securely. Configuring JWT verification
without confirming asymmetric signing or a role assignment can lock users
out; setting `AGENTIC_OS_ENV=production` without a durable database
can leave data on ephemeral SQLite. Neither is a valid SaaS release.

This is a privileged backend-only SQL architecture, **not** a generic
PostgREST/RLS-per-tenant product. Tenant isolation depends on
`server/auth.py` plus API owner authorization and needs separate
pen-test/acceptance evidence.
