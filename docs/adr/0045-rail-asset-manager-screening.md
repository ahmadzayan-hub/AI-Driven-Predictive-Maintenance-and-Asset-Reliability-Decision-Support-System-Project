# ADR 0045 — Railway Asset Manager decision-screening contract

*Renumbered from 0041 when this work was reconciled onto the project's main
history: 0041 and 0042 were already taken by the shipped-registry and
missing-value decisions. The decision itself is unchanged (ADR 0047).*

Status: Proposed implementation for review (2026-10-18).

## Context
The Team 3 academic railway contribution covers asset criticality, reliability,
and lifecycle cost. Agentic OS implementation is an additional proposed role,
not an official change to the course allocation. Existing Hermes orchestration,
custom stages, role trust and human approval must not be bypassed.

## Decision
Add a zero-dependency domain screening module with the proposed role tag
`TEAM3_RAIL_ASSET_MANAGER`. It operates on a **single synthetic observation**,
producing a structured advisory record. Its composite key is an analytic
segmentation key only: asset ID is reused across five classes in the supplied
data, so physical identity remains unverified.

Criticality category is retained as provided, not recomputed as a purported
ISO-compliant safety risk score. Economic exposure is the *sum of observed
maintenance cost and estimated service loss for the observation*, not whole-life
cost, cash saving or an optimized investment case. Condition and failure data
trigger a simple engineering review screen, not a predictive failure probability.
No automated maintenance action, asset replacement or release approval is granted.

`authorize` is a reusable, fail-closed domain policy helper. It is NOT an
API authentication integration: server enforcement, actor identity, tenancy
and audit-event persistence must be reviewed before any user-facing action
uses the helper.

## Decision evidence and limits
- ISO 55001:2024 and IEC 62402:2019 inform domain questions; this module does
  not assert compliance or reproduce proprietary requirements.
- End-of-support dates, OEM spare support, replacement CAPEX, residual value,
  cash-flow horizon and discount rate are absent from the educational dataset.
- Model training/evaluation, chronological splits, feature-timing leakage
  control and the integrated dashboard remain separate acceptance gates.
- Never submit actual course personal data or source tables to this public repo.
- Only deterministic synthetic unit fixtures are committed.

## Acceptance
`python -m unittest tests.test_rail_asset_decisions`

## Follow-up
1. Wire through a governed custom stage only after inspecting the current
   dataset/aggregation contracts and ensuring provenance through Hermes.
2. Integrate server-side identity/authorization and persistent audit trail
   under existing managed-auth conventions.
3. Add validated distinct-asset definitions, reviewed KPI denominators and
   chronological predictive-model evaluation; reconcile with Power BI.
4. Require domain-owner approval before any consequential maintenance action.
