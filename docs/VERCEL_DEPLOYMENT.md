# Vercel Deployment

The repository includes a **full-stack Vercel configuration**: the React
frontend as static assets and the FastAPI backend as a Python serverless
function. Configuration is not hosted acceptance.

**Current release policy, 2026-10-20:** `main` is the integration branch.
`git.deploymentEnabled.main=false` prevents Git pushes from deploying it.
GitHub Actions still runs. Production requires explicit owner approval and a
separate deployment of the reviewed commit
([decision](adr/2026-10-20-production-release-approval.md)).
Read-only hosting metadata identifies production commit `42e53d00` and Vercel
Authentication protection. It does not establish current application identity,
database durability or worker readiness. The historical observations below
apply only to the deployment and date they name.

## Why this is possible now

The original blocker was state, not the platform. The backend used to
require local disk (SQLite file, `data/memory.json`, vault folder).
Since ADR 0001 and its amendment, all durable state lives behind the
storage adapter, so the backend can run on an ephemeral filesystem.

## What is configured

| File | Purpose |
| --- | --- |
| `api/index.py` | ASGI entry point Vercel serves for `/api/*`; adds the repo root to `sys.path` and re-exports the unchanged FastAPI `app` |
| `vercel.json` | Builds the frontend, routes `/api/*` to the function, rewrites everything else to the SPA, sets security headers, `no-store` on the API and immutable caching on hashed assets |
| `requirements.in` | Direct server dependency declarations and optional-integration rationale |
| `requirements.txt` | Exact transitive function dependencies with platform markers and artifact hashes |
| `.python-version` | Pins the interpreter to 3.12 so the runtime cannot drift under the deployment |

**No custom runtime is pinned.** Vercel's Python support is native: a
`.py` file under `api/` exporting an ASGI `app` is a function, with
dependencies from `requirements.txt` and the interpreter from
`.python-version`. An earlier version of this file pinned
`@vercel/python@4.3.0` — legacy custom-runtime syntax whose version was
written from memory and never verified. A version that does not resolve
fails the build before anything else runs, so the pin was removed rather
than left as a trap for the first deploy.

Serverless hardening already in place:

- `PostgresStore` reconnects once outside an atomic operation when a pooler
  or cold start drops an idle connection. It never replays a statement inside
  a lost transaction; the caller must retry the complete operation.
- `SQLiteStore` relocates to a writable temp directory when its target
  directory is read-only, instead of crashing at import (tested).

## Deploy it

1. After release approval, use the existing Vercel project, or import
   `ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project`
   if setting up a new environment.
   `vercel.json` supplies every build setting; if a framework preset is
   offered, "Other" is correct. Deploy the approved `main` commit explicitly;
   do not enable automatic production publishing as a synchronization shortcut.
2. Add environment variables (Project → Settings → Environment
   Variables). Secrets remain server-side; only provider publishable settings
   are returned to the browser. Real hosted use requires durable storage and
   managed identity. A single-owner ephemeral configuration is a local demo,
   not a production setup:

   | Variable | Needed for |
   | --- | --- |
   | `DATABASE_URL` | **Durable state.** Supabase → Connect → *Transaction pooler* (port 6543, built for serverless), with your database password |
   | `AGENTIC_OS_ENV=production` | Fail closed unless auth is configured |
   | `SUPABASE_JWT_SECRET` *or* `AGENTIC_OS_JWKS_URL` | Token verification |
   | `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Browser sign-in (publishable) |
   | `ANTHROPIC_API_KEY` or `GROQ_API_KEY` | Optional model-phrased summaries. `OLLAMA_MODEL` is **not** useful here: a model on a laptop is unreachable from a serverless function |

3. Check `/api/health`, sign-in and cross-owner isolation using test accounts,
   then a synthetic run through approval and publication. Verify state after
   a restart and execute a restore drill on an isolated database.
4. Run `python scripts/worker.py` on an approved persistent worker host with the same
   database, configuration and resource-limit environment. A serverless HTTP
   function does not provide the continuous worker loop. Exercise a scheduled
   synthetic refresh against an allowed public host with direct egress.
5. Fit provider deadlines and measured stage duration within the function
   budget (`maxDuration` in `vercel.json`), including database/transaction time.
   Record errors, timeouts, alert ownership and backup ownership. Do not infer
   successful operation from the build status.

Earlier sessions applied initial Supabase migrations. Current bootstrap schema
and policy changes in source are not proof that a hosted database has received
them; inspect and validate the intended environment before release.

## Browser connection origins

The static shell CSP in `vercel.json` allows same-origin API requests and
`https://*.supabase.co` managed sign-in. Vercel does not substitute runtime
`SUPABASE_URL` or `VITE_API_BASE` values into this checked-in header. For a custom
auth domain or external API, add the exact HTTPS origin to `connect-src` in the
non-API `Content-Security-Policy` rule before building and deploying. Prefer the
exact Supabase project origin in place of the wildcard when it is known. Keep
`script-src` unchanged; model providers run on the server. The external API must
also allow the frontend origin through its CORS configuration. Verify sign-in
and a synthetic API action after an approved release. See the
[browser policy decision](adr/2026-10-20-browser-content-security-policy.md).

## Without `DATABASE_URL`

The deployment still runs, but the store falls back to SQLite in the
function's temp directory: state survives only while an instance stays
warm and is lost on cold start. Acceptable for a first look, **not** for
real use. Set `DATABASE_URL` before treating the deployment as usable.

## Historical verification on 2026-10-02

**Deployed on 2026-10-02** to the Vercel project `agentic-os-final-project`
(team `celia2026-3923s-projects`), production domain
`https://agentic-os-final-project.vercel.app`, from commit `2aeb9fd` of
`claude/agentic-os-final-project-53j6ql`.

What the first import got wrong, and the fix: the import dialog
auto-detected the **FastAPI** preset. Under that preset, as the build log
warns, an internal rewrite routes the request *using the rewritten
destination path*, so every `/api/*` request reached the function as
`/api/index`, FastAPI had no such route, and its SPA fallback answered
`index.html`. The site rendered; every API call returned HTML.
`vercel.json` now carries `"framework": null` (the "Other" preset), which
Vercel's configuration reference documents as overriding the project
setting, and the next build routed correctly. Keep that line.

Verified against the live production domain, by HTTP:

- `GET /api/health` → JSON (`status: ok`, deterministic narrator, no
  router, no stages, no runtime).
- `GET /api/pipelines` → JSON.
- `GET /` and `GET /runs` → the SPA's `index.html` with the configured
  security headers.

Not verified, in each case because the implementation environment could
not reach it rather than because it failed:

- **Whether the production domain is public.** The project has Vercel
  Authentication set to *Standard Protection*
  (`all_except_custom_domains`); the checks above went through an
  authenticated bypass. Open the domain in a private window to confirm;
  Project → Settings → Deployment Protection changes it.
- **A browser session, a run and an approval** on the deployment. Only
  GET requests were exercised.
- **Environment variables.** The deploying token could not list them, so
  whether `DATABASE_URL` is set is unknown. The health response does not
  say. Without it, state is per-instance and lost on cold start, as the
  section above describes.
- **Sign-in.** No identity provider is configured, so the deployment runs
  in local mode: one owner, no login, same as a laptop.
- **The Python version.** The "Other" build installed dependencies under
  CPython 3.14 despite `.python-version` saying 3.12; the function
  served, but the pin is evidently not what selects the runtime under
  this preset.

Two observations from that historical deployment (recheck before acting):

- A second project, `agentic-os-final-project-frontend`, was created by
  the same import with `frontend` as its root directory. Its builds fail
  (`cd frontend` inside `frontend`) and served nothing then. Its current state
  and removal require a separate owner decision.
- A push to the branch produced a **preview** deployment, not a
  production one: the project's Production Branch is not this branch.
  The fixed build was promoted by creating a production deployment
  explicitly. Current policy keeps production deployment separate from Git
  synchronization; the earlier suggestion to make pushes publish is superseded.

## Rollback

After owner approval, select the retained known-good deployment and promote it.
Verify its compatibility with the current schema and stored artifacts first.
Additive migrations reduce rollback risk but do not prove every older build
can interpret newer data. Exercise the rollback/restore procedure in staging.
