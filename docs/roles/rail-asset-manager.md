# Railway Asset Manager | Agentic OS domain role

**Status:** Proposed domain role / implementation in progress. **Updated:** 2026-10-18.

## Purpose and boundaries

Provide traceable, risk-informed decision support for railway asset criticality,
reliability, observed economic exposure, lifecycle planning and potential
obsolescence. This is an educational role built against synthetic observations,
not a live railway safety, maintenance control or certified asset-management system.

The MBA Team 3 publication assigns railway asset criticality, reliability and
lifecycle cost as the domain contribution. Agentic OS architecture and AI
decision support are an additional proposed development responsibility, not
an amended academic allocation.

## Identifiers

- Permission tag: `TEAM3_RAIL_ASSET_MANAGER`
- Future specialist stage role: `rail_asset_manager`
- Existing orchestrator: Hermes, **reuse**, do not duplicate.
- Reviewer: authenticated authorized human, distinct from the agent.
- Authorization: enforced by existing server identity and tenant scopes,
  not by a role string supplied in the HTTP request or model-generated output.

## Repository mapping

| Component | Evidence | Current boundary |
| --- | --- | --- |
| Governed orchestration | `server/analytics.py`, `server/stages.py` | Existing custom stage registry |
| Role-specific screening | `server/rail_asset_decisions.py` | Deterministic library, not an API endpoint or registered stage |
| Screening contract tests | `tests/test_rail_asset_decisions.py` | Must be executed and reported |
| Decision rationale | `docs/adr/0045-rail-asset-manager-screening.md` | Proposed, not corporate policy |
| Human review | `server/runs.py` | Existing publication gate does not authorize railway work |
| Modelling | `server/modelling.py` | Generic baseline evaluation; no validated railway failure prediction |
| UI | `frontend/` | Domain-specific integrated dashboard remains to be verified |

## Academic data contract

Source data: synthetic Team 3 enterprise panel. The railway subset contains
969 observations. Do not commit course source data, student registration
numbers or team personal information to this public repository.

Required source columns for the initial screen:
`Industry_Context`, `Asset_Class`, `Asset_ID`, `Criticality`,
`Condition_Score`, `Failure_Count`, `Downtime_Hours`,
`Maintenance_Cost_USD`, `Production_Loss_USD`.

`Asset_ID` is reused across asset classes. Construct a **provisional analytic**
key from industry context, asset class and asset ID, while retaining
`UNVERIFIED_PHYSICAL_IDENTITY`. Do not treat this key as a certified asset
register ID or aggregate temporal observations into physical-asset history.

The initial observed economic exposure is maintenance cost plus supplied
service-loss estimate for an observation, **not** discounted lifecycle cost,
cash benefit, avoidable loss or replacement investment justification.
Avoid double counting included spare and labour cost components.

## Standards and decision controls

ISO 55001:2024 supports lifecycle value, risk-informed decision-making and
evidence governance. IEC 62402:2019 informs obsolescence evidence collection.
Railway RAMS and cyber assurance requirements remain project-specific. No
standard clause compliance is certified here.

No OEM support date, end-of-life notice, replacement CAPEX, residual value,
discount rate, certification, predicted remaining useful life or achieved
saving may be generated or implied from absent data.

## Functional decomposition

1. **Asset-data validator**: grain, units, temporal provenance, missing
   fields, approved KPI calculation scope and identity ambiguity.
2. **Railway criticality analyst**: source-provided criticality and observed
   safety/service consequences; explain evidence and data gaps.
3. **Reliability analyst**: failures, MTBF, MTTR, availability, repair
   recurrence and downtime with reviewed denominators.
4. **Lifecycle analyst**: observable costs vs unsupported whole-life claims;
   request additional data for investment case.
5. **Obsolescence assessor**: request verifiable OEM evidence and maintain
   `INSUFFICIENT_OEM_EVIDENCE` until independently supported.
6. **Predictive analyst**: supervised outcome only if timing and identity
   constraints permit; chronological validation, leakage checks, appropriate
   baseline, calibrated model metrics and recorded limitations.
7. **Decision agent**: evidence-linked recommendations under bounded authority;
   no work-order execution or live asset state change.

## Enforcement and human-in-the-loop

- Deny access by default. Add tenant/owner scoping to authenticated
  endpoint enforcement before exposing any new route.
- Agent can prepare proposed interventions, not approve safety-critical
  changes, alter an interlocking, or bypass engineering governance.
- Persist actor, timestamps, dataset and model versions, thresholds,
  traceable calculations, reviewer identity, approval status and reasons.
- Use existing Hermes provenance, validation and approval-gated publication.
- Only verified aggregate facts may reach an optional language model;
  never raw dataset rows, secrets or source instructions.

## Required acceptance and testing

- Safe handling of missing/negative/nonfinite inputs, unknown criticality,
  reused asset identifiers, unsupported obsolescence and denied actions.
- Verify role-scope denial and multi-tenant isolation through **API tests**,
  not merely the current domain helper.
- Register a governed stage and prove that it cannot bypass validation.
- Train and compare a domain model against a valid baseline, or explicitly
  explain why the available dataset cannot support the target.
- Reconcile any role-specific views with the submitted Power BI dashboard,
  executive presentation and academic report.
- Record `python -m unittest tests.test_rail_asset_decisions` and
  `python scripts/verify.py` outputs. Never claim passing tests without
  execution evidence.

## Delivery status

**Implemented in this branch:** initial deterministic screening helper,
synthetic unit tests and ADR 0045.

**Not implemented yet:** authenticated API authorization, persisted audit
events for this role, registered railway specialist stage, validated
railway-specific predictive failure model, domain dashboard and lifecycle
investment optimizer.

This file is a development specification, not proof of operational acceptance.
