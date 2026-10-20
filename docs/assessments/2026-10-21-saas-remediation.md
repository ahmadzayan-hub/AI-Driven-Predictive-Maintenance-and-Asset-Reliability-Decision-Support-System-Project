# SaaS assessment remediation

Date: 2026-10-21

The owner asked to implement the [competitive assessment](2026-10-21-saas-competitive-benchmark.md)
and delegated the first-source recommendation. The suggested pilot is **MaintainX,
with reviewed pumps and motors at one facility**. No customer account, live source
authorization or independent field outcomes have been supplied.

## Implemented changes

| Assessment gap | Implemented response | Remaining acceptance boundary |
| --- | --- | --- |
| Work stops or waits on a long browser request | Explicit worker execution, persisted progress, prompt advance acknowledgement, browser status polling and bounded heartbeat readiness | Representative hosted concurrency, restart, queue latency and recovery objectives need deployment evidence. |
| No shared maintenance workspace | Organizations, memberships, site/asset registry, organization roles combined with managed identity permissions | Customer identity provisioning and hosted cross-tenant negatives must be accepted on the actual deployment. |
| Findings do not lead to recorded work | Evidence-linked drafts, separate maintenance authorization, assignment, progression, completion, labor/parts and audit | A real technician outcome and external CMMS reconciliation are still required. Report approval never authorizes a repair. |
| Sources cannot use operator credentials | Owner/host/port-scoped aliases, secret values held only by the operator, and bounded read-only MaintainX asset/work-order snapshots | Real account entitlement, source contract tests, scheduling and deletion reconciliation are not established by synthetic fixtures. |
| Predictive value has no prospective record | Immutable protocols, server-stamped model/baseline predictions, mature outcomes, explicit denominators, uncertainty and calibration | Independent domain review, adequate unseen exposure and useful customer decision thresholds remain unmeasured. |
| Planner workflow exposes too much implementation detail | Bilingual Operations navigation, role-specific controls, explicit confirmations, evidence details, imports/exports and readiness observations | Actual planner/technician task completion and assistive-technology use need observation. Existing restrained agent motion is preserved. |
| Confidential course artifacts remain tracked | Removed the two identified dashboard artifacts from the current source tree while preserving local copies and ignore rules | Historical and external copies remain under the owner's private-data remediation; no history was rewritten and the repository stays private. |

The [pilot runbook](../PILOT_RUNBOOK.md) gives configuration, supported source
commands, permissions, work-order flow, validation definitions and acceptance
evidence. [Maintenance operations](../MAINTENANCE_OPERATIONS.md) documents the
domain/API contract. The database bootstrap snapshot includes the new tables
with the existing deny-by-default grants; it has not been applied to a hosted
database in this session.

## Evidence and limits

Actual executed checks, counts, skips and build measurements are maintained in
[README Testing](../../README.md#testing). Review evidence is retained outside
Git. The initial full run exposed an outdated worker test double, compound
browser journeys exceeding their total deadline, shared fixture assumptions and
a stale phone-navigation expectation. The fixes preserve individual assertions,
accessibility rules, human approval and exact record identity; the
[browser decision](../adr/2026-10-21-browser-journey-isolation.md) records why.

Software regression results establish the behavior exercised by those checks.
They do not establish hosted availability, failure-prediction accuracy, avoided
downtime, causal savings, commercial adoption or parity with the benchmark
vendors. The prospective ledger excludes pending outcomes and measures only
registered windows; different actor IDs do not prove independent adjudication.

## Still open

| Gate owner | Evidence needed |
| --- | --- |
| Deployment operator | Explicit release authorization, hosted identity/isolation, representative load, worker recovery, fresh-backup restore, erasure/retention and freshness monitoring acceptance. |
| Customer source administrator | Authorized MaintainX test account and observed real API/import/reconciliation behavior for the selected facility. |
| Maintenance domain reviewer | Accepted asset/failure definitions, no leakage, sufficient later observations, independently reviewed outcomes and agreed error costs. |
| Product/service owner and customer | Buyer and support ownership, onboarding, package/usage terms, observed repeat use, support effort and a purchase/renewal decision. |

No external gate is accepted without its owner's evidence. No overall SaaS
readiness percentage is inferred from the review gate count.

Outbound CMMS writes, continuous sensor ingestion, durable offline work edits,
automatic billing and enterprise provisioning remain separate capabilities,
to be justified by the chosen customer workflow. The current agent connection
view shows observed workflow state; it does not invent a durable inter-agent
message transcript. No production deployment or external work-order write was
performed.
