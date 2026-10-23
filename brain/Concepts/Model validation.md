---
type: concept
aliases: []
tags: [data]
status: active
updated: 2026-10-23
review_every_days: 30
sources: [server/modelling.py, server/maintenance/targets.py, docs/adr/2026-10-20-maintenance-model-comparison-and-recommendations.md, docs/adr/2026-10-23-p2-slice-one.md, docs/analytics/PREDICTIVE_MODEL_VALIDATION.md]
---

# Model validation

Model validation tests whether a fitted model improves on an appropriate baseline for the intended decision.

## Interpretation

- Compare model and baseline on the same eligible held-out observations.
- Input availability and target timing matter; values learned after a decision cannot justify an earlier prediction.
- A missing or unsupported target should produce a limitation, not an invented score.
- Weak maintenance results withhold intervention advice. Relative improvement alone is not operational acceptance.
- A useful maintenance-risk verdict needs three tests since 23 October 2026: five points over the baseline, 55% balanced accuracy, and the one-sided 95% Wilson lower bound of that accuracy above 50%. Twelve seeded noise panels yield no useful verdict (A9 in the platform assessment).
- The train and test split is never silently random: the card records why a split is not chronological, and a dated maintenance target with fewer than five periods is not scored at all (A10). Without any date column the every-fifth split is declared.
- A model card without the 23 October fields (`balanced_accuracy_lower_bound`, `held_out_records`) was scored before the bound existed; read its verdict with that in mind.
- Dashboard filters do not retrain a stored model or redefine its evaluation population.

## Related

- [[Maintenance decision support]] defines the intended decision and horizon.
- [[Data quality contracts]] constrains usable features.
- [[Scoped dashboards]] labels whole-run model evidence.
- [[Agent evaluation]] measures specialist classifiers, a different evaluation object.
- [[Home]] indexes modelling knowledge.
