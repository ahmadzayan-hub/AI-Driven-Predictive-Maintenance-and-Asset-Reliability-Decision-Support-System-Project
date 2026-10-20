# Checks and run mutations are one atomic database operation

Date: 2026-10-20 · Status: Accepted

## Reproduced failures

Independent connections could both read unused quota and then exceed it.
Interrupted run creation left a queued run with only part of its task plan.
Two API instances could both execute the collector: the second reclaimed the
first instance's live task as an orphan. The API's in-process lock protected
only one application instance.

## Decision

Add a store-level atomic operation with a reentrant connection lock. SQLite
uses `BEGIN IMMEDIATE`; PostgreSQL uses an explicit transaction and a
transaction-scoped advisory lock derived from a stable owner/run key.
Dataset deduplication and quota admission, complete run creation, advancing one
stage, approval decisions, pause/resume and cancellation use these operations.
Nested dataset creation shares the run-creation transaction.

An atomic operation either commits all its database changes or rolls them
back. PostgreSQL can reconnect before a transaction starts. It must not replay
an individual statement after a connection loss inside a transaction: doing
so would continue without its lock or preceding writes.

The completed stage is the durable checkpoint. A killed process rolls back its
in-progress stage; an older orphaned task is still recovered on the next advance.
Worker leases remain the scheduling mechanism. A run's row remains locked
during its stage, preventing a successor's lease claim from overtaking that
stage's commit. Competing approval decisions serialize on the same run.

## Tradeoffs and boundaries

Local SQLite serializes writers; its wait covers the gateway's bounded
60-second narration window. PostgreSQL serializes operations for the same
owner or run, permitting unrelated keys to proceed on independent connections.
A slow stage holds a transaction, so this is a correctness fix for the current
bounded workloads, not evidence of high-concurrency service capacity.

Vault file writes remain idempotent by run ID and occur only after a matching
human approval request. They are not part of a distributed filesystem/database
transaction; a failed publication must be retried using the same approved
artifact. No automatic approval is introduced.

## Evidence

The new concurrent-admission, interrupted-creation and duplicate-task regressions
all failed on both adapters before the fix. `tests/test_atomic_admission.py`
covers these cases through independent connections; the worker, quota and
recovery suites also run against the isolated PostgreSQL database, including
real worker-process termination.

The locking choices follow the
[PostgreSQL transaction lock contract](https://www.postgresql.org/docs/17/explicit-locking.html)
and [SQLite immediate transactions](https://www.sqlite.org/lang_transaction.html).
