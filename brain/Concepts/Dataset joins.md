---
type: concept
aliases: []
tags: [data]
status: active
updated: 2026-10-27
review_every_days: 30
sources: [server/joins.py, docs/adr/0030-several-datasets-per-run.md, docs/adr/2026-10-27-stacked-datasets.md]
---

# Dataset joins

Dataset joins combine declared, owner-accessible tables without silently multiplying the analysis population.

## Join contract

- A run snapshots its join declaration and mappings; later mapping edits do not rewrite that run.
- The merge stage follows cleaning and runs only when joins are declared.
- Left and inner joins have different population meanings, which must remain visible.
- Repeated lookup keys are refused when they would multiply main-table rows.
- Matched, unmatched and renamed-column information supports review of the result.
- A stack (27 October 2026) appends an export with exactly the same columns under the main table, read with the main mapping; repeats of rows already present are dropped and counted, and a `source` column names each row's dataset so totals can be broken down by export.

## Related

- [[Column mapping]] defines the roles used before and after merging.
- [[Data quality contracts]] explains keys, grain and units.
- [[Weighted KPIs]] requires the correct denominator after a join.
- [[Tenant isolation]] limits access to contributing datasets.
- [[Home]] indexes data preparation.
