---
type: concept
aliases: []
tags: [interface]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [docs/adr/0058-executive-dashboard-agent-and-scoped-evidence.md, docs/adr/2026-10-20-asset-evidence-scope.md, server/query.py]
---

# Scoped dashboards

Scoped dashboards keep each displayed measure bound to its selected run, filters, population and language.

## Evidence scope

- Selected-record KPIs can be recomputed while stored findings and model evaluations remain whole-run evidence.
- Stale responses from an earlier run or filter must not replace the current view.
- Empty input and unsupported measures carry explicit limitations rather than zero-valued success.
- Truncated trends and bounded evidence searches disclose their scope.
- The executive briefing is read-only; preparing it does not advance or approve an analysis.

## Related

- [[Weighted KPIs]] provides consistent arithmetic.
- [[Evidence and claims]] makes findings inspectable.
- [[Business report exports]] preserves the selected scope in files.
- [[Tenant isolation]] protects the underlying resources.
- [[Home]] indexes the interface concepts.
