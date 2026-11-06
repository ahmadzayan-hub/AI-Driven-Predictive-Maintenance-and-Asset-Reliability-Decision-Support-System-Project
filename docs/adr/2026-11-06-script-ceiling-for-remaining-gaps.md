# Script ceiling raised to 292 KB for the remaining interface gaps

Date: 2026-11-06 · Status: Accepted · Owner decision: "Raise to 292 KB", asked with the platform at 285.6 of 286 KB

## Decision

All scripts may total 292 KB gzipped, up from 286 KB, for the interface the remaining gaps
need: confirming typo corrections in the join builder, deleting a run, several named views
and clickable scatter points. The first load stays capped at 100 KB and each view's chunk
at 30 KB, so the raise lands in chunks loaded on demand. Each slice that spends it records
what it cost.
