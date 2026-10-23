---
type: concept
aliases: []
tags: [agents]
status: active
updated: 2026-10-23
review_every_days: 30
sources: [server/runs.py, server/deadline.py, frontend/src/features/runs/runStore.ts, docs/adr/2026-10-20-atomic-run-operations.md, docs/adr/2026-10-23-p2-slice-one.md]
---

# Run lifecycle

A run lifecycle is the durable execution state of an analysis, distinct from a chat session or a paused visual panel.

## State and recovery

- Run creation, stage advancement, approval and cancellation use atomic database operations.
- The completed stage is the durable checkpoint. Interrupted in-progress work rolls back; recovery must not execute the same live stage twice.
- The browser shares one scheduler per run. Reading a result card does not itself advance the analysis.
- Awaiting approval, a paused analysis, a disconnected browser and a terminal outcome are different states.
- A retried creation with the same `Idempotency-Key` returns the run already made (a 200 marked `idempotent_replay`), per owner, backed by a unique index; a creation without a key is never matched (23 October 2026).
- A [[Custom stages|custom stage]] runs under `AGENTIC_OS_STAGE_TIMEOUT` (default 120 s) and an [[Agent runtimes and MCP|agent runtime]] under `AGENTIC_OS_RUNTIME_TIMEOUT` (default 60 s). An overrun is abandoned on its thread and its task fails with the time stated; the run fails only if the stage declared `can_fail_run`. Python cannot stop the thread, so this is a limit, not a sandbox.
- Since the third release-gate slice, a run may carry decision inputs (an uplift and a cost per target, and the explored range) and ends with a decision record the [[Approval gate]] completes with who decided and when.

## Related

- [[Hermes orchestrator]] sequences the work.
- [[Agent collaboration]] presents observed state without adding execution.
- [[Approval gate]] controls publication.
- [[Backup and restore]] preserves durable work after loss.
- [[Home]] is the vault index.
