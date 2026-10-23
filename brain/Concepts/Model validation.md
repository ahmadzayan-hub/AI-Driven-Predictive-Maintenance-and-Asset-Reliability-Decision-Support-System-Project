---
type: concept
aliases: []
tags: [data]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/modelling.py, server/maintenance/targets.py, docs/adr/2026-10-20-maintenance-model-comparison-and-recommendations.md]
---

# Model validation

Model validation tests whether a fitted model improves on an appropriate baseline for the intended decision.

## Interpretation

- Compare model and baseline on the same eligible held-out observations.
- Input availability and target timing matter; values learned after a decision cannot justify an earlier prediction.
- A missing or unsupported target should produce a limitation, not an invented score.
- Weak maintenance results withhold intervention advice. Relative improvement alone is not operational acceptance.
- Dashboard filters do not retrain a stored model or redefine its evaluation population.

## Related

- [[Maintenance decision support]] defines the intended decision and horizon.
- [[Data quality contracts]] constrains usable features.
- [[Scoped dashboards]] labels whole-run model evidence.
- [[Agent evaluation]] measures specialist classifiers, a different evaluation object.
- [[Home]] indexes modelling knowledge.
