---
type: concept
aliases: []
tags: [security]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/model_privacy.py, docs/adr/2026-10-20-personal-data-model-boundary.md]
---

# Model privacy

Model privacy screens outgoing context so detected identifying information does not cross a model or runtime boundary.

## Outgoing context

- Raw dataset rows remain on the server. Computed figures can still contain identifying group labels.
- Persisted privacy findings and the exact outgoing text are checked before supported model-facing handoffs.
- When the gate refuses narration, the deterministic result remains available with an explanation.
- Publication approval is not consent to send private labels to a model.
- Pattern detection is conservative and incomplete; it is not a guarantee of anonymization.

## Related

- [[Model gateway]] is a narration boundary.
- [[Knowledge retrieval]] supplies operator-managed reference text.
- [[Data quality contracts]] includes detection and validation limits.
- [[Soul]] states the raw-data rule.
- [[Home]] indexes related controls.
