---
type: concept
aliases: []
tags: [agents]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/analytics.py, frontend/src/features/runs/EvidencePanel.tsx, frontend/src/features/runs/evidence.ts]
---

# Evidence and claims

Evidence and claims connect a reported statement to its calculation, quality checks and stated limitations.

## Review model

- A stage returns typed claims, calculations, checks and a result summary. Calculation references allow validation and inspection.
- The evidence dialog exposes the returned checks and claims; a colored status or animated connection is not evidence by itself.
- Validation of arithmetic does not prove a causal explanation, a useful predictor or an accepted maintenance intervention.
- Missing observations and weak results must remain visible rather than becoming confident prose.

## Related

- [[Governed pipeline]] produces the typed results.
- [[Weighted KPIs]] defines population-aware arithmetic.
- [[Scoped dashboards]] preserves the scope of each claim.
- [[Approval gate]] requires human review of the exact artifact.
- [[Home]] maps the wider context.
