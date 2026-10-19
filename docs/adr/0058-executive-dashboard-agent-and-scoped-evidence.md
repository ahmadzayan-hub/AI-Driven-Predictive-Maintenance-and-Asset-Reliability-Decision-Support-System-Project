# 0058 — Executive dashboard agent and scoped evidence

Date: 2026-10-19

## Context

The owner requested a deep dashboard redesign, an executive dashboard agent,
and integration of Claude Code dashboard/Artifacts skills. The existing product
already has governed runs, a controlled maintenance KPI register, filtered table
queries and accessible SVG charts. Its overview does not bring these together
for an executive decision. Maintenance model cards are computed as a collection
but the run response exposes only singular model cards.

Claude-hosted Artifacts and Dashboards are separate platform capabilities. Their
availability and account permissions cannot be inferred from a local skill file.
Importing a prototype scaffold would also replace this application's established
React, SVG, localization and dependency contracts.

## Decision

- Add a read-only `ExecutiveDashboardAgent` and a run-owned
  `GET /api/runs/{id}/executive` endpoint. Reuse the query layer's validated
  filters and the maintenance register's calculations. No model receives raw
  rows, and preparing a brief neither advances nor approves a run.
- Return the exact selected and total record counts, supported KPIs, missing
  evidence, observed-work review priorities, follow-up questions, resolvable
  calculation references and drilldowns. Bound every returned collection.
  The source is explicitly `engine`; this is a deterministic evidence briefing,
  not a claim that an LLM generated prose or an asset diagnosis.
- Recompute KPI values and priorities over the selected records. Stored run
  findings and model evaluations retain their whole-run scope and are labelled
  accordingly; filtering a dashboard does not retrain a model or rewrite a claim.
  Empty or unsupported inputs produce named limitations rather than zero scores.
- Redesign the existing dashboard overview, retaining its other pages, shareable
  filter state, authorized record drill-through and chart data tables. English
  and Arabic RTL have the same interactions. A brief can be refreshed, inspected
  and exported as sourced JSON; export does not publish or approve a report.
- Keep requests owned by their run/filter/language context. Ignore cancelled or
  obsolete results and remove the module-global private-response cache so account
  changes do not retain another principal's displayed snapshot.
- Preserve both fitted and unsupported maintenance model cards in run
  serialization. Render an unsupported target without a score or sample count.
  Honour the maintenance acceptance verdict even if relative baseline improvement
  alone passed. Preserve each model's horizon and decision context.
- Let explicit maintenance upload links select the existing maintenance profile,
  with a validated route/preset. Ordinary uploads retain their existing default;
  no arbitrary profile is accepted from a URL.
- Extend the existing `.claude/skills/dashboards` workflow and
  `dashboard-analyst` agent for run-scoped SaaS work, executive information design,
  provenance, both languages and verification. Keep the working offline renderer.
  Hosted Artifact publication is conditional on actual tool/account capabilities,
  never a fabricated SDK or automatic upload of private data.
- Reuse design tokens, bundled fonts and SVG charts; add no browser runtime
  dependency or CDN. Initial-load, chunk and font budgets stay unchanged.
  Allow total cross-view JavaScript up to 175 KB gzip (previously 170) and
  total CSS up to 21 KB gzip (previously 20). The measured increment supplies
  the lazy executive view, its bilingual packs, evidence interactions and model
  boundary handling; it adds no first-load view or external dependency. This
  explicit allowance is not a claim that the dashboard costs no bytes.

## Verification and consequences

API tests cover filters, missing/empty evidence, reference integrity, ownership
and readiness. UI tests cover scope changes, stale responses, recoverable errors,
Arabic rendering, model boundaries and exports. Browser checks exercise the real
API, filtering/drill-through, responsive layouts and accessibility.

This creates a reviewable executive workspace over recorded evidence. It does
not prove future failure prediction, replace an engineer's decision, install a
Claude-hosted service or authorize production deployment. Actual results and
budgets are maintained in `README.md`; research and capability boundaries are
recorded in `docs/design/EXECUTIVE_DASHBOARD_RESEARCH.md`.
