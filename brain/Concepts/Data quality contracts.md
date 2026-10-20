---
type: concept
aliases: []
tags: [data]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [server/analytics.py, server/maintenance/contract.py, server/maintenance/governance.py, docs/PROJECT_CHARTER.md]
---

# Data quality contracts

Data quality contracts specify what an input means before a calculation or model can use it.

## Questions to settle

- Record grain, units, missingness, field scale and when a value becomes known affect valid analysis.
- Structural validity, privacy findings and domain plausibility are separate checks.
- A maintenance field's semantic type must not be inferred merely because its stored values are numeric.
- A passed automated check does not establish an accepted source definition or domain threshold.

## Related

- [[Column mapping]] records declared presentation roles.
- [[Dataset joins]] preserves the intended row population across files.
- [[Maintenance decision support]] needs a decision-specific contract.
- [[Model validation]] depends on usable and correctly timed inputs.
- [[Home]] connects these data concepts.
