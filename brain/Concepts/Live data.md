---
type: concept
aliases: []
tags: [data]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/connectors.py, docs/adr/0034-live-data.md]
---

# Live data

Live data uses owned connectors to create versioned dataset snapshots from changing external sources.

## Refresh behavior

- Unchanged content does not create another analysis. New content becomes a new snapshot and governed run.
- Network fetching is restricted, bounded and checked against private-address access; a saved source is not unrestricted browsing.
- Scheduled refresh requires the worker. Manual refresh remains a separate operation.
- The owner-scoped update stream signals changes in runs and connectors; it is not an agent-message transcript.
- A dashboard should offer the newer snapshot without silently replacing the figures under review.

## Related

- [[Run lifecycle]] governs analyses created by refresh.
- [[Data quality contracts]] must still hold for each new snapshot.
- [[Scoped dashboards]] distinguishes the selected snapshot from a newer one.
- [[Approval gate]] still controls publication.
- [[Home]] connects live inputs to the rest of the system.
