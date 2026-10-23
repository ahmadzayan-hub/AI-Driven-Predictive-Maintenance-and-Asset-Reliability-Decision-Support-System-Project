# Opt-in database-backed worker candidate

Status: proposed for hosted activation; code and isolated tests only.

## Decision

Keep the live `vercel.json` unchanged. Provide a separate zero-instance example
and an explicit-allowlist Dockerfile. The entrypoint refuses accidental startup,
SQLite fallback, filesystem publication/knowledge/evaluation ledgers and external
model providers by default. The separate
[specialist wiring](2026-10-23-specialist-runtime-wiring.md) adds an explicit,
single-recipient configuration gate without activating it. It requires managed identity and the same worker execution mode
as the API. The operational switch is not a substitute for authorization.

The worker handles SIGTERM: finish the current atomic stage, release its lease,
do not start another stage, connector refresh or evaluation, record stopped,
close the database, and restore the previous signal handler. Idle waits are
interruptible. The candidate polls every 15 seconds instead of once a second;
readiness still expires through the existing heartbeat policy. A forced kill
relies on existing transaction rollback, durable run state and lease recovery,
not an in-memory queue. It is not an exactly-once guarantee for arbitrary custom
stage side effects.

## Durable content boundary

Dataset canonical CSV, run/task state, report artifacts, published notes,
owner-scoped sessions/memory and RMD source originals/extracted attachments are
database records. Tests reopen connections and launch a fresh Python process in
an empty working directory, verifying exact bytes, human-approved notes and
cross-owner denial. The PostgreSQL variant uses only the disposable CI database.
This does not prove an actual Vercel container restart or backup restoration.

Generic dataset imports preserve normalized CSV, not original Excel packaging.
Use RMD source ingestion when retaining the original workbook/document matters.
Runtime filesystem knowledge, a local evaluation ledger and legacy `.doc`
conversion without a configured sandbox are not supported by this candidate.

## Host constraints and acceptance

Vercel currently supports production-only Linux amd64 daemons with ephemeral
storage. Hobby has a shared five Active CPU-hour monthly quota and stops daemons
when it is exhausted. An existing project with a subfolder root cannot use this
beta. Actual team quota and root settings must be checked, not inferred from
code compatibility. [Official limits](https://vercel.com/docs/daemons/limits).

The example requests 1 GiB, zero instances and a 300-second shutdown grace period.
Dockerfile placement makes the repository root the build context; explicit COPY
and a Dockerfile-specific allowlist exclude private local data. No secret build
arguments are declared. [Configuration reference](https://vercel.com/docs/daemons/config-reference).

No Docker engine is available in the local preparation environment. Existing
public CI builds the candidate, checks its network-disabled activation guard,
then runs the durable-byte tests in a non-root, read-only container against only
disposable PostgreSQL. Check that run's outcome before claiming container support.
A reviewed base-image digest, resource measurement and actual hosted restart
acceptance remain release gates. See the [runbook](../implementation/DAEMON_RELEASE.md).
