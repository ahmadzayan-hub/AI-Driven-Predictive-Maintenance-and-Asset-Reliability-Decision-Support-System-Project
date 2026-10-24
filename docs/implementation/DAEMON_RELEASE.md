# Non-activating Vercel worker release candidate

This is not a deployed service or a claim of production readiness. The existing
application deployment and disabled main-branch Git deployment remain unchanged.
`deploy/vercel.daemons.example.json` is an example, not the deployment manifest.
Its only daemon has zero instances; do not copy it into production automatically.

## Before any production write

1. Confirm the intended existing Supabase project and exact database target.
   Follow [HOSTED_SCHEMA_RELEASE.md](HOSTED_SCHEMA_RELEASE.md): private backup,
   isolated restore, approved SQL hash, migration and read-only schema validation.
   API and worker startup verify schema only; they must never run production DDL.
2. Obtain per-action approval to configure the existing database credential only
   in the intended Vercel project's Production environment. Use the secure
   secret-entry UI, never chat, Git, logs, frontend variables or build arguments.
   Review least privilege, TLS, connection count and revocation/rotation ownership.
3. Confirm Hobby account eligibility, remaining shared daemon CPU allowance,
   project root at repository root, region, and current instance-count overrides.
   Do not upgrade, enable paid models, increase budget or assume free unlimited
   operation. Fifteen-second polling reduces idle database/TLS work but does not
   prove a monthly CPU bound. Measure before claiming sustained free operation.
4. Build the official Python image for Linux amd64 in an isolated environment;
   record and pin its reviewed digest. Install the existing hash-locked packages.
   Inspect image layers for secrets, test as the non-root user, measure memory,
   test SIGTERM and forced termination with disposable PostgreSQL. Existing CI
   builds and exercises the non-root, read-only candidate against its disposable
   PostgreSQL service; inspect its actual result and printed base-image digest.
   Source-only checks do not establish Docker or hosted restart acceptance.

## Exact candidate runtime settings

- `AGENTIC_OS_DAEMON_ACTIVATION=reviewed`, only after the release gates are approved.
- `DATABASE_URL`: approved existing PostgreSQL credential, entered securely.
- `AGENTIC_OS_PUBLISH_TARGET=database`.
- `AGENTIC_OS_RUN_EXECUTION=worker`, also on the API.
- `AGENTIC_OS_REQUIRE_AUTH=1`, plus approved managed JWKS/issuer/audience settings.
- `AGENTIC_OS_EVAL_INTERVAL_SECONDS=0`; no filesystem knowledge directory.
- No external model configuration, role-to-provider map or model router. Built-in
  calculations, maintenance rules and governed reports work without paid models;
  they are labelled built-in, not represented as a live external LLM.

Optional specialist activation is a separate reviewed mode, never the default:
`AGENTIC_OS_SPECIALISTS_ENABLED=1`, an explicit matching
`AGENTIC_OS_SPECIALIST_MODEL=provider:model`, and an explicit positive existing
`AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY` are additionally required on API and worker.
The selected provider must already be configured and separately approved for
the exact recipient, cost and data scope. No router, role-to-provider map or
cross-provider fallback is accepted for this mode. A matching worker heartbeat
is only recent configuration activity; live-model verification is still pending.
See the [wiring decision](../adr/2026-10-23-specialist-runtime-wiring.md).

Configuring these settings is a separate approved action. The activation string
is only an accidental-start guard and does not grant permissions. The container
starts `python -m server.daemon`; it does not run migrations, publish automatically
or decide human approvals. Both API and worker must use identical approved stage
configuration and database publication target.

## Hosted acceptance and rollback

After approved setup, start one instance only. Prove a new authenticated owner can
upload synthetic data, start a run, close the browser, and return to a genuine
approval-pending result. Verify viewer isolation and denial for another account.
Approve only the synthetic report explicitly. Retrieve its exact database content.
Upload synthetic RMD DOCX/XLSX sources and retrieve original bytes and attachments.
Restart/replace the worker and API instance, retrieve them again, and compare hashes.
Test termination during a stage and lease recovery with no duplicated committed
tasks. Check readiness heartbeat, error logs, memory and CPU use. A 200 response,
a ready deployment or a live process alone is not acceptance.

If acceptance fails, stop the daemon by setting all instance counts to zero,
verify no claims continue, and restore the prior application deployment/config.
Do not delete branches, source data or migration records. Database rollback must
follow the separately reviewed backup/restore plan, not unreviewed reverse SQL.
Do not expose a writable demo as a substitute while authentication is unavailable.

## Content retained and limits

RMD stores original uploaded source bytes and extracted attachment bytes in
PostgreSQL. Canonical dataset CSV, reports, published notes, runs/tasks, sessions
and owner-scoped memory are also database-backed. Temporary document conversion
files are intermediates, not authoritative storage. Generic dataset imports do
not preserve original workbook packaging. Filesystem knowledge collections and
evaluation ledgers are not durable here and are rejected by this candidate.
Legacy `.doc` conversion still needs its separately configured sandbox.

Passwordless email onboarding still depends on the approved callback allowlist,
managed identity verification, actual mail delivery and an explicit owner role.
Default Supabase mail may serve only authorized team addresses at low rate;
general-user delivery is not promised without verified SMTP configuration.
Google/Apple remain unavailable unless the provider reports them enabled through
separately approved configuration. See the [auth ADR](../adr/2026-10-23-managed-auth-onboarding.md).

References: [Vercel daemons](https://vercel.com/docs/daemons),
[limits](https://vercel.com/docs/daemons/limits),
[configuration](https://vercel.com/docs/daemons/config-reference).
