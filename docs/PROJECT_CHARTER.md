# AI-Driven Predictive Maintenance and Asset Reliability Decision-Support System SaaS Project

The product helps maintenance and reliability teams turn operational data into
reviewable decisions about downtime, work orders, asset condition and cost.
It is being developed as software as a service. **Agentic OS** is the reusable
analytics engine and development operating system behind it.

The Arabic product title is **مشروع نظام الصيانة التنبؤية المدعوم بالذكاء الاصطناعي ودعم قرارات موثوقية الأصول كبرمجيات كخدمة**.
The compact interface labels are **Asset Reliability** and **موثوقية الأصول**.
The naming decision is recorded in [ADR 0036](adr/0036-maintenance-product-identity.md).

## Decisions the product should support

- Which maintenance observations need investigation, and what evidence supports that priority?
- Where are downtime, repair workload and economic exposure concentrated?
- Which indicators can be compared using consistent populations and denominators?
- Does a proposed predictive model improve on a suitable baseline using information available before the decision?
- What action should a person review, and which uncertainty or missing evidence could change it?

These are product objectives. A product title is not evidence of a useful failure
predictor, an optimal maintenance schedule, achieved savings or production readiness.

## What the repository provides

| Capability | Code evidence | Remaining domain work |
| --- | --- | --- |
| Ingestion, column mapping and joins | `server/datasets.py`, `server/mapping.py`, `server/joins.py` | A maintenance input contract with units, record grain and information timing |
| Governance and calculations | `server/analytics.py`, `server/metrics.py`, `server/detectors.py` | Connect the structural detectors to governed stage outputs and establish approved maintenance KPI definitions |
| Reusable model evaluation | `server/modelling.py` | Choose a decision target, exclude outcome leakage, validate chronologically and report weak results honestly |
| Interactive analysis | `server/query.py`, `frontend/src/features/dashboard/` | Domain views, approved measure selection and cross-filtering where justified |
| Human review and publishing | `server/runs.py`, approval views | A reproducible bundle linking each deliverable claim to its calculation and review |
| Hosted foundations | Managed identity, owner-scoped storage, quotas and workers described in ADRs 0002, 0006, 0008 and 0034 | Validate the intended customer tenancy model, operational monitoring, recovery, direct-egress refresh and service ownership |

The generic `models` profile does not itself establish predictive-maintenance
validity. Inputs must be selected by when they are known. An entity identifier must
also be validated before treating observations as a physical asset's history.

## Delivery sequence

| Priority | Work | Completion evidence |
| --- | --- | --- |
| P0 | Private requirements and source register | Each required deliverable maps to its source, owner, acceptance check and unresolved items |
| P1 | Maintenance data and KPI contract | Recorded grain, stable entity keys or an explicit observation-only scope, formula and denominator tests, source reconciliation |
| P2 | Governance stage integration | Detector findings become calculations and claims under the existing validator, with synthetic tests and bilingual reports |
| P3 | Decision-specific modelling | Feature timing register, chronological evaluation, informative baseline, error analysis and a clear useful/weak verdict |
| P4 | Maintenance dashboard and deliverable assembly | Consistent KPIs, working filters and drill-through, evidence register, human review and files opened in their intended applications |
| P5 | SaaS pilot | Managed sign-in, agreed organization/owner permissions, tested isolation, worker operation, restore drill and measured service behavior |

Each behavioral milestone needs its own decision record and tests. This naming
change implements none of P1–P5 by implication. Commercial billing, organization
administration and deployment choices require product decisions before implementation.

## Delivery boundaries

Course requirements, team identities, source files and private submission plans
stay in ignored workspaces. The product repository holds reusable software and
public documentation. An educational reference publication is source material,
not proof that the team's analysis or deliverables are finished.

The engine computes from source data locally or on the server. Only verified
aggregates and findings reach a model. People approve publishing and consequential
decisions. Synthetic results remain labelled synthetic, and proposed benefits
remain proposals until demonstrated.

The project display name is changed locally. Repository URLs, deployment URLs,
the workspace folder, engine configuration, storage keys and export filenames
retain their existing identifiers. Historical records retain the name used when
they were written.
