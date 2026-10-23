# Bounded, durable model admission outside run transactions

Date: 2026-10-23 · Status: Proposed for owner review

## Why a check followed by charge is insufficient

Concurrent requests could read the same remaining daily slot before either
charged it. The worker builder did not attach the API's model budget. Merely
moving the charge before a call inside RunEngine.advance is also wrong: advance
holds a run transaction, nested atomic blocks do not take a second owner lock,
and rollback after an external attempt would erase its charge. Consultant
threads did not inherit tenant ContextVars and could charge the local owner.

## Decision

Keep the existing run transaction and state/lease checks. Before acquiring it,
commit a bounded block of admission credits in the existing model_calls_daily
table under the existing per-owner transaction lock. Inside the run transaction,
provider attempts consume only the shared, locked in-memory token. Each parallel
consultant gets its own copied context containing the same token and tenant.
Provider/model variants and routed gateways share that budget. The worker uses
the same budget as the API. A standalone call atomically reserves one credit.

The conservative built-in-stage envelope is two narration attempts, two for an
external Hermes, two for an external agent, and six per external consultant
(structured attempt/failover, compatibility retry, then text fallback). It is
clamped to the remaining daily allowance, not the entire allowance. The bound
covers configured roles rather than a stale pre-lock stage observation. Custom
stages exceeding the envelope fall back rather than top up inside a transaction.
Revisit and test this bound when the model call graph changes.

After the run transaction commits or rolls back, close the token and return only
unused credits in a separate owner transaction. Provider failure stays spent.
Never retry an uncertain settlement. Reservation-store failure creates an active
zero-credit token, preventing accidental fallthrough to a database call inside
the run transaction. An expired UTC-day token is denied; its unused credits are
returned only to its original day. Closed tokens deny delayed work.

## Meaning and tradeoffs

The API's historical model_calls counter now means admission credits consumed or
reserved, including in-flight reservations and unreclaimed credits after crash
or uncertain settlement. It is NOT observed provider calls, tokens, currency or
a bill. model_budget_basis makes the distinction explicit. The separate process
provider ledger reports observed attempts and may itself be lost on process
failure. No pricing claim is introduced.

Concurrent work for the same owner sees in-flight credits as unavailable. A
crash can consume the unused portion of that stage's bounded reservation until
the UTC reset. This is conservative financial protection, not proof those calls
occurred. Other owners retain separate allowances. Low remaining allowance can
make optional role notes fall back; the application must not relabel fallback
as a successful model response. No production activation is approved here.

## Verification

Synthetic regressions cover parallel SQLite connections and copied contexts,
provider failure, rollback after an attempt, restart persistence, scoped tenant
isolation, deadline rollover, nested scopes, zero admission, cancellation,
paused runs, an uncertain reservation commit, and settlement acknowledgement
loss without duplicate refund. Existing worker role tests must still produce
configured synthetic model answers and stop for human approval. PostgreSQL
concurrency and rollback tests run only against the disposable CI test database;
a skipped local database test is not PostgreSQL acceptance.

## Migration, release and rollback

No schema migration, new provider, credential, database or dependency is added.
The target database must already have the current reviewed schema, including
model_calls_daily. The older nine-table hosted schema is not automatically
accepted: review the full current schema gap, backup and isolated restore before
an approved hosted release. Startup's schema creation is a production write,
not a harmless health check.

This PR is stacked after the shared-limiter repair. Main merge, production
configuration and deployment require owner approval. For rollback use a new
revert commit; preserve all rows and backups. Reverting to check-then-charge
restores the overspend race, so paid-provider work must remain paused pending a
safe approved release. Local deterministic operation and human publication
approval remain available; no live maintenance decisions are authorized.
