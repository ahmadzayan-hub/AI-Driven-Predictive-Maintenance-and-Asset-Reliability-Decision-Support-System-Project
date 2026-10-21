# Separate durable execution from HTTP and scope source credentials

Date: 2026-10-21 · Status: Accepted

## Problem

The competitive assessment identified two implemented foundations that were
not yet complete customer workflows. A background worker existed, but browser
drivers still executed stages inside HTTP requests. A slow model could outlive
the hosting request budget. Source snapshots were restricted to public files,
which excluded authenticated maintenance exports.

## Decisions

### Configurable execution ownership

`AGENTIC_OS_RUN_EXECUTION=worker` on the API advertises server execution in
every run detail. The run row and its tasks remain the durable queue. An
advance request returns the durable snapshot with HTTP 202 before entering
the stage transaction; repeating it creates no extra task. The browser polls
GET rather than sending advance POSTs. Missing configuration retains `client`
mode for existing local installations. An invalid mode fails startup.

Run a **separate supervised process**, `python -m server.worker`, against the
same database and vault configuration. API threads must not host this worker:
one store connection's operation lock deliberately serializes its transactions
and reads. The worker reuses existing atomic stages, conditional claims,
leases and crash recovery. It stops at human approval. Closing the browser
does not stop server work. A missing worker leaves a durable queued run; the
API never silently falls back to expensive request-thread execution.

Heartbeats are persisted before and after bounded work and during idle loops.
`/api/health` exposes execution mode, whether a recent non-stopped heartbeat
exists, last observation time and age. It does not expose worker identifiers,
source configurations, account names or goals. A heartbeat is recent for
120 seconds; a graceful stop becomes unready immediately. This is observed
activity, not proof of a live process, capacity, an uptime guarantee or a
successful hosted deployment. Long custom stages can exceed the heartbeat
window and must have their own bounded execution policy. Worker exception
logging includes exception classes, not upstream exception contents.

### Operator-managed credentials, persisted aliases only

A connector may carry a `credential_id`. It is a non-secret alias supplied by
the operator to the authorized owner. An operator registry in
`AGENTIC_OS_CONNECTOR_CREDENTIALS` maps each alias to an exact owner, lowercase
hostname, port (default 443), header kind and secret environment-variable name.
The hostname must also occur explicitly in `AGENTIC_OS_CONNECTOR_HOSTS`.
Supported authentication is a Bearer token or an `X-API-Key` header. Arbitrary
headers, wildcard owners/hosts, whitespace/control characters in tokens and
authenticated fixture-host fetches are refused.

Illustrative metadata, with no credential value:

```json
{
  "maintenance-export": {
    "owner": "managed-provider-subject",
    "host": "data.example.com",
    "port": 443,
    "header": "Authorization",
    "token_env": "MAINTENANCE_SOURCE_TOKEN"
  }
}
```

The actual token is installed through the operator's secret manager as
`MAINTENANCE_SOURCE_TOKEN` in the API and worker environments. Never put it in
the registry JSON, a connector URL, frontend configuration, logs or Git.
The request body supplies only the alias:

```json
{
  "name": "Maintenance export",
  "url": "https://data.example.com/export.csv",
  "goal": "Review maintenance evidence",
  "credential_id": "maintenance-export"
}
```

The alias is checked when saved and resolved again for every fetch. Rotation
or revocation therefore takes effect on subsequent requests without editing
connector records. The raw token and secret environment-variable name are
never copied into connector storage or returned by the API. Removing the
alias or token causes a recorded, generic refresh refusal; public connectors
retain their existing behavior.

Connector admission counts and inserts under one owner-scoped database
transaction. Independent API instances therefore cannot both consume the
last available connector slot. An in-process application lock alone cannot
enforce this limit across instances.

Authentication does not relax the HTTPS fence: all resolved addresses must
be public, the socket connects to the checked address with hostname-verified
TLS, size/time limits remain, and redirects are never followed. Authenticated
redirect locations are not echoed because an upstream server could reflect
a credential in that location. Failures do not include credential values.

## Validation and remaining acceptance

`tests/test_durable_execution.py` covers queued read-only advances, a snapshot
read while another store connection holds a blocked stage transaction,
restart checkpoints, readiness expiry/shutdown, exception-log redaction and
the actual HTTP 202 contract. Existing worker/recovery/atomic suites retain
duplicate-claim, crash and approval-boundary coverage. The shared frontend
scheduler tests verify GET polling and no advance POSTs in worker mode.

`tests/test_connector_credentials.py` covers owner/origin/allowlist binding,
secret rotation and revocation, private-address refusal, redirects, invalid
headers/tokens, public compatibility and alias-only persistence.
The separate-store admission regression also detects removal of the atomic
boundary, preventing a race from passing through sequential-only coverage.

This change enables authenticated **whole-file snapshots**. It does not claim
an incremental CMMS/ERP adapter, OAuth refresh flow, industrial streaming,
automatic work-order writeback or a successful live customer integration.
Supervision, shared PostgreSQL configuration, hosted restart and concurrent
load drills, alert delivery, and a real source owner's acceptance remain
deployment gates. SQLite still serializes writers during a bounded stage;
HTTP separation does not remove that documented throughput limitation.
