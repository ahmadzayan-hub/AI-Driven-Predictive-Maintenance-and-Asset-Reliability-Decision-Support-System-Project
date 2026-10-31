---
type: operation
aliases: [Maintenance operations pilot]
tags: [operations, reliability, pilot]
status: active
updated: 2026-10-31
review_every_days: 14
sources: [docs/PILOT_RUNBOOK.md, docs/MAINTENANCE_OPERATIONS.md, docs/assessments/2026-10-21-saas-remediation.md, docs/adr/2026-10-21-prospective-maintenance-validation.md, docs/adr/2026-10-21-maintenance-operations.md, docs/adr/2026-10-21-operations-workspace.md, docs/adr/2026-10-31-reliability-model.md, docs/adr/2026-10-31-risk-ranking.md, docs/adr/2026-10-31-what-if-scenarios.md]
---

# Maintenance pilot

The first proposed source is MaintainX, with selected pumps and motors at one
facility. No customer, live credential or field outcome has been supplied.
[[Agentic OS]] now provides an organization-scoped operations queue with assets,
explicit maintenance authorization, assignments, observed completion and audit.
The [[Approval gate]] still controls report publication independently.

An operator-held alias enables bounded authenticated source reads. The private
adapter snapshot preserves source identity and successful synchronization time;
its reviewed asset import is explicit. [[Live data]] remains distinct from a
bidirectional CMMS contract. Outbound work and reconciliation need pilot evidence.

Prospective protocols fix the model, baseline, threshold and failure definition
before server-stamped predictions. Full-horizon outcomes and external evidence
references are required before scoring. Pending observations are not negatives;
registered-window recall is not fleet-wide recall. Different actor identifiers do not
prove independent review, and no causal savings are inferred.

[[Tenant isolation]], [[Backup and restore]] and [[Managed identity]] support
local correctness. Hosted load/restart/restore acceptance, independent domain
validation, a live source contract and customer/service terms remain open.
The [[Decision log]] records this boundary; [[Soul]] requires observed evidence
before calling the pilot production-ready.

Since 31 October the maintenance profile also fits a failure pattern per asset
class, ranks assets by expected failure cost and compares planned-replacement
intervals. They need dated failure records per asset over time; they are
advisory, issue no work order and weight no criticality without the owner's
numbers, so they do not change the boundary above.
