# ADR 0042: Opt-in maintenance decision profile

Date: 2026-10-18. Status: Proposed, awaiting PR review.

## Decision
Reuse the existing Hermes custom-stage contract; do not create another
orchestrator. Register the already-present `MaintenanceGovernance` and
`MaintenanceRisk` stages and a `RailAssetManagerStage` under a named
`maintenance` profile. Leave the default and models profiles unchanged.

The railway specialist performs deterministic per-observation screening and
reports only validated aggregate counts and observed economic exposure.
It does not estimate predictive failure risk, support end dates, remaining
useful life, or full lifecycle replacement cost. Asset_ID remains an analytic
identifier rather than a verified unique physical asset key.

No new API route, autonomous work-order action, external model disclosure,
tenant privilege, or production deployment is introduced. Existing human
approval of publication continues to apply.

## Verification gates
- `python -m unittest tests.test_rail_asset_stage tests.test_rail_asset_decisions`
- `python scripts/verify.py` and existing GitHub CI.
- A maintenance-profile synthetic run and human-reviewed report.
- Manual preview smoke test on Vercel, with authenticated data isolation
  before hosted use.

## SaaS rollout
The existing Vercel projects `agentic-os-final-project` and its frontend
are linked to the *old* `agentic-os-final-project` GitHub repository. A new
separate Vercel project `asset-reliability-team3-saas` is linked to
`AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project`.
Preview build status alone is not proof of functional production readiness.
Use durable PostgreSQL storage and managed authentication before inviting
real users. Longer model jobs need appropriately designed workers.

## Academic boundary
Phase 1 is the MBA capstone deliverable trio. This opt-in enhancement
belongs to the post-capstone SaaS bonus and cannot substitute for the
required PBIX, PPTX and PDF.
