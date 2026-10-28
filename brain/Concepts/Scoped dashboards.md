---
type: concept
aliases: []
tags: [interface]
status: active
updated: 2026-10-27
review_every_days: 30
sources: [docs/adr/0058-executive-dashboard-agent-and-scoped-evidence.md, docs/adr/2026-10-20-asset-evidence-scope.md, docs/adr/2026-10-27-interactive-dashboard.md, server/query.py, server/dashboard_views.py]
---

# Scoped dashboards

Scoped dashboards keep each displayed measure bound to its selected run, filters, population and language.

## Evidence scope

- Selected-record KPIs can be recomputed while stored findings and model evaluations remain whole-run evidence.
- Stale responses from an earlier run or filter must not replace the current view.
- Empty input and unsupported measures carry explicit limitations rather than zero-valued success.
- Truncated trends and bounded evidence searches disclose their scope.
- The executive briefing is read-only; preparing it does not advance or approve an analysis.

## Interaction (27 October 2026)

- A bar or a line point is a button: clicking it keeps that group alone on every figure, through the address like every other filter; clicking again releases it. The histogram and the scatter plot are not clickable.
- One dashboard view per owner and dataset is kept on the server (`dashboard_views`, keyed by the stored dataset's id or the dataset name) and applied when a run over that dataset opens from a bare address. The address is validated against the dashboard's own keys and bounded.
- The executive brief leaves sections with nothing to report out and names them once in the decision context; a section with content beside a missing part keeps its statement.

## Related

- [[Weighted KPIs]] provides consistent arithmetic.
- [[Evidence and claims]] makes findings inspectable.
- [[Business report exports]] preserves the selected scope in files.
- [[Tenant isolation]] protects the underlying resources.
- [[Home]] indexes the interface concepts.
