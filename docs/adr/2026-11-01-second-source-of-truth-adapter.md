# Second source-of-truth adapter beyond the MaintainX read path

Date: 2026-11-01. Status: proposed (Tier 2 item 3).

## Decision

The flagship's evidence layer reads from MaintainX today. Add a second
source-of-truth adapter so the platform is not single-source, following the
existing port/adapter pattern (read-only in P0).

Concretely:

- Implement a new adapter behind the existing read port, mirroring the
  MaintainX adapter's contract (entities, provenance, observed timestamps).
- The adapter is read-only in P0: GET only. No POST/PATCH/DELETE paths.
  A future write needs a separate proposal/approval port.
- Every record carries an `EvidenceRef` (source system, entity type, entity
  id, observed timestamp) so the two sources are distinguishable in reports.
- The second source is registered as a provider with provenance; production
  mode never falls back to synthetic data.

## Why

A single source of truth is a single point of failure and a single point of
dispute. The Tier-2 plan calls for a second adapter as one of three ADRs
needed before the hosted pilot is defensible to an asset owner.

## Validation and reversibility

- Contract tests assert the new adapter satisfies the same read-port
  interface as MaintainX.
- A Control Tower smoke run against both sources produces a DTO with evidence
  refs from both.
- Reversible: the adapter is optional; if the second source is unavailable,
  the pilot continues on MaintainX alone and the gap is recorded in the deploy
  note. No silent fallback.
