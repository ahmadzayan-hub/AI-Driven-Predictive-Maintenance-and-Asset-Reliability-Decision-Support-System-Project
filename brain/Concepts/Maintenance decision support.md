---
type: concept
aliases: []
tags: [data]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [docs/PROJECT_CHARTER.md, server/maintenance/contract.py, server/maintenance/kpis.py, server/maintenance/targets.py]
---

# Maintenance decision support

Maintenance decision support turns recorded operational evidence into questions and priorities that a responsible person can review.

## Decision boundaries

- Downtime, repair workload, condition and cost require named populations, units and source definitions.
- Validate an entity key before treating records as a physical asset's history.
- Cross-sectional screening is not a demonstrated next-period failure predictor.
- Product naming does not establish achieved savings, an optimal maintenance plan or production readiness.
- Independent domain acceptance remains necessary before recommendations guide real interventions.

## Related

- [[Weighted KPIs]] defines controlled measures.
- [[Data quality contracts]] defines record and field meaning.
- [[Model validation]] checks predictive usefulness.
- [[Scoped dashboards]] exposes the evidence and its limits.
- [[Home]] connects domain work to the product.
