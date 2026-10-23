---
type: concept
aliases: []
tags: [agents]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/runs.py, frontend/src/features/runs/runStore.ts, docs/adr/2026-10-20-atomic-run-operations.md]
---

# Run lifecycle

A run lifecycle is the durable execution state of an analysis, distinct from a chat session or a paused visual panel.

## State and recovery

- Run creation, stage advancement, approval and cancellation use atomic database operations.
- The completed stage is the durable checkpoint. Interrupted in-progress work rolls back; recovery must not execute the same live stage twice.
- The browser shares one scheduler per run. Reading a result card does not itself advance the analysis.
- Awaiting approval, a paused analysis, a disconnected browser and a terminal outcome are different states.

## Related

- [[Hermes orchestrator]] sequences the work.
- [[Agent collaboration]] presents observed state without adding execution.
- [[Approval gate]] controls publication.
- [[Backup and restore]] preserves durable work after loss.
- [[Home]] is the vault index.
