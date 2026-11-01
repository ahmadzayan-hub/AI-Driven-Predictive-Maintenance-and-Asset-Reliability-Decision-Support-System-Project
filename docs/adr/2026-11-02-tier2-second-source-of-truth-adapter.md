# Tier 2 release gate: second source-of-truth adapter beyond MaintainX

Date: 2026-11-02 · Status: **Proposed, awaiting the owner's decision.** No
adapter code ships with this record.

## Context

The MaintainX read path is the only implemented source-of-truth adapter. It
reads assets and work orders into private snapshots and prepares reviewed
initial asset imports; it does not reconcile bidirectional CMMS work orders
or prove a live vendor contract (`KNOWN_LIMITATIONS.md`, pilot boundaries).

The portfolio review calls a "second source-of-truth adapter beyond the
MaintainX read path" a Tier 2 item needing an ADR plus a release gate, so
the product is not single-vendor dependent.

## Release gate (all must hold before a second adapter is called supported)

1. **Interface.** The adapter implements the same read snapshot contract as
   MaintainX: assets, work orders, and the reviewable import preview. No
   adapter-specific shortcuts in the UI.
2. **No bidirectional claims.** Until write-back is implemented and tested,
   the adapter is read-only and labelled as such in `KNOWN_LIMITATIONS.md`.
3. **Private data.** Raw source rows never reach a model; only reviewed
   summaries do (ADR 0010 and the raw-data rule in `AGENTS.md`).
4. **Evidence.** A test proves the adapter produces the same downstream
   analysis as MaintainX on a synthetic fixture, or documents the delta.
5. **Credentials.** Secrets come from a managed store, never from the repo
   (no secrets in Git rule).
6. **Rollback.** Disabling the adapter returns the product to the MaintainX
   path without data loss.

## Decision requested

Approve scoping a second adapter (candidate: a CSV/file import that mirrors
the MaintainX snapshot shape, no vendor contract required), or keep the
product single-adapter and say so in the README.

## Consequences if approved

- The CSV-mirror option needs no vendor contract and can be built and tested
  locally; a live vendor adapter needs credentials and a contract, which is
  the owner's call.
- Work lands on a branch; merges only when all six gate items are evidenced.
