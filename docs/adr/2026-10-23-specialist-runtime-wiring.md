# Default-off evidence-specialist API and worker wiring

Status: code candidate. Synthetic transports only; no production activation or
live-model acceptance is implied.

## Decision

Use the existing API `profile` contract and background `RunWorker`, not a second
queue or a scripted production agent. `AGENTIC_OS_SPECIALISTS_ENABLED=1` and an
explicit `AGENTIC_OS_SPECIALIST_MODEL=provider:model` select the same
`GatewayDecisions` factory on both sides. Absent configuration leaves the normal
governed analytics workflow unchanged. The first specialist workflow accepts one
authorized ordinary dataset, not joined tables, RMD packs or arbitrary files.

The factory requires managed JWT identity, worker execution, database publication,
and the actual shared durable model budget. Hosted mode also requires PostgreSQL.
A router, unavailable/model-mismatched provider or a cross-provider fallback is
not an accepted decision driver. Existing per-owner admission limits remain
authoritative. No credentials, permissions, environment values or budget limits
are changed by this code. A selected provider is not proof of quota, cost or
entitlement; there is no absolute free-service claim.

Configuration and activity are distinct. Authenticated health reports configured,
matching-worker-capable and live-model-verified separately. A worker advertises a
non-secret protocol/model/recipient/budget digest in its existing heartbeat ID.
Only a fresh matching heartbeat establishes observed worker capability, not a
generic worker or a stale/stopped one. `live_model_verified` stays false: code
configuration and synthetic tests cannot establish live acceptance. This is not
a new access-control grant, and no heartbeat/schema migration is introduced.

Persisted specialist model identity also binds a custom endpoint and effective
admission-limit digest; changing the endpoint or raising a worker's budget cannot
silently resume an API-created checkpoint with weaker limits or a new recipient.
Embedded credentials in endpoint URLs are rejected. Only the hash is persisted,
not a secret or URL. Configuration mismatch preserves the checkpoint rather than
dispatching work to another model. Workers without a specialist driver exclude
specialist tasks at lease selection. Configured workers filter incompatible
checkpoint bindings before the candidate limit and conditional lease update, so
old model/budget work cannot repeatedly take the lease or starve ordinary work.
The optional PostgreSQL selection uses PostgreSQL 16+ JSON validation (the CI
service and current intended managed target meet this version); malformed
checkpoint JSON is excluded and preserved, not cast blindly or overwritten.
The opt-in limit parser requires an explicit unsigned decimal integer greater
than zero; blank, negative, nonfinite or malformed values never inherit the
ordinary legacy default. Ordinary workflow quota defaults remain unchanged.

Creation retains existing write permission, selected-source ownership, quota and
idempotency checks. Client advancement is still blocked in worker mode. Human
publication uses the existing owner/read/authorize path and exact report/source
verification; a model never approves or sends a report. Existing Motion access,
review and transactional terminal-state fences are preserved.

## Honest interface and payload bounds

`/api/pipelines` adds `explicit_plans` for standalone workflows. The selector and
timeline show four bounded specialist identities plus the publication gate,
not the normal deterministic stages pretending to be independent model agents.
The optional profile is not advertised when configuration is unavailable. Both
languages disclose one source, a configured model, a worker and human review.

Decision and tool argument/output bounds count UTF-8 bytes, including Arabic.
No raw rows are sent to the model; the existing privacy and canonical-claim
verification contracts remain in force. Reports in this wave assemble accepted
evidence, rather than promising creative narrative or predictive accuracy.
Accepted claims, exact calculation IDs/values/methods and source-version
provenance are projected into the existing authorized report/evidence panel.
The verifier's actual replay result is visible and explicitly is not human
publication approval. Raw checkpoints, pending operations and model context are
not exported. Model transport omits only duplicate generated human markdown;
its text, claims and calculations remain privacy-scanned. This avoids treating
a legitimate digit-heavy SHA as a telephone number without exempting user text.
Standalone report tabs select an available section instead of assuming a
`descriptive` section exists.

## Container and verification

The explicit worker image allowlist additionally includes root `assistant.py`,
which the real tool catalogue imports. The live Vercel file remains unchanged;
the example still has zero instances. The candidate daemon accepts a separately
reviewed specialist selection only with explicit positive admission, no routing
or role map, plus all existing identity/PostgreSQL/publication activation guards.
Configuration validation is network-free and runtime startup stays verify-only.

Synthetic acceptance uses the real HTTP API, configured gateway adapter and
mocked provider transport. A separate connection commits a decision, a fresh
Python interpreter resumes it, and the API reads the resulting verified draft
before a human-role approval publishes it. Tests cover owner/viewer isolation,
configuration/recipient mismatch, disabled queue selection, admission accounting,
matching versus generic worker heartbeats, and UTF-8 limits. Fresh-process
mismatched-budget selection is checked separately from matching-worker restart.
A dedicated disposable browser fixture creates English/Arabic reports through
the real API and worker with scripted model transport; desktop/mobile checks
inspect accepted claims, calculations and verification before human approval.
That fixture is not reachable from the production factory and cannot call a
live provider. PostgreSQL mirrors
run only against the caller's disposable test database. None of these tests
proves actual owner email delivery, provider quality, production restart or
hosted permission/backup correctness.

## Remaining activation gates

The [schema runbook](../implementation/HOSTED_SCHEMA_RELEASE.md) retains its exact
reviewed SQL and private backup/restore gates. The
[daemon runbook](../implementation/DAEMON_RELEASE.md) retains secure credential
configuration, actual host eligibility/quota, resource measurement and restart
acceptance. Production identity requires the canonical callback, verified mail
delivery, an actual owner session and a separately authorized minimum role.
Actual selected-model entitlement/no-spend eligibility and a bounded live-model
acceptance remain unverified. Local Motion media storage/rendering is still not
a durable hosted renderer. Turning off a demo label does not close these gates.

Metric clarification is a separate append-only contract under review, not a
fake-save UI. Post-report voice, creative Motion specialists, action ownership
and effect follow-up remain incremental journeys with their own evidence and
human gates; this runtime is not a replacement for a CMMS or autonomous safety
decision authority.
