# Scheduled refreshes use the API's resource policy

Date: 2026-10-20 · Status: Accepted

## Problem

The API passed configured per-owner limits to `RunEngine`; `build_worker`
left them unset. Scheduled source refreshes could therefore create datasets
and runs even when the operator set their allowances to zero. The worker
also ignored `AGENTIC_OS_CONFIG` when invoked directly, despite the documented
shared configuration contract.

## Decision

Load the same quota defaults and environment overrides in the production
worker as in the API. Select the configuration file from the explicit argument,
then `AGENTIC_OS_CONFIG`, then the default. Pass the same environment to vault
resolution and the model gateway. Retain the connector's existing recorded
failure and retry behavior when a resource limit refuses a refresh.

This does not introduce billing, change quota values, or prevent existing runs
from advancing at the limit. A snapshot can be retained when the subsequent
run allowance is exhausted, just as before.

## Validation

`tests/test_worker_limits.py` exercises scheduled refreshes with zero dataset
and run allowances, insufficient byte capacity, an allowed refresh, and
configuration precedence. The quota and configuration regressions failed
before the fix. Existing worker and connector tests cover leases, recovery,
and the approval boundary.

## Remaining boundary

Concurrent admission is covered by
[atomic operations](2026-10-20-atomic-run-operations.md). These controls bound
resource counts; they do not meter or enforce a monetary budget.
