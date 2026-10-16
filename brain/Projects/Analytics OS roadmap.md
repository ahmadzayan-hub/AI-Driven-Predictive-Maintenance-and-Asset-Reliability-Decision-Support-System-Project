---
type: project
aliases: [Analytics roadmap, Dashboard roadmap]
tags: [project, roadmap]
status: active
updated: 2026-10-16
review_every_days: 14
sources: [project-progress.md, server/analytics.py, server/runs.py, frontend/src/app/App.tsx, docs/UI_PLAN.md]
---

# Analytics OS roadmap

The [[User]]'s goal for [[Agentic OS]]: a system that digests several datasets with dynamic inputs and carries them through preparation, cleaning and modelling to a multi-page interactive dashboard with live data. The milestone board and status live in `project-progress.md`; this note keeps the reasoning.

## Where it stands (code audit, 2026-10-16)

| Capability | Today | Gap |
| --- | --- | --- |
| Ingestion | Done as A1 (ADR 0024): CSV, TSV, Excel, JSON and JSON Lines through `POST /api/datasets`, 4 MB uploaded and 10 MB as CSV, 50,000 rows, stored once in any format; a stored-dataset picker in the Runs view | `.xls`, Parquet and connectors; choosing a sheet in the interface |
| Several datasets | Storage keeps many, but a run takes exactly one | No joins, merges or multi-table runs |
| Dynamic inputs | Done as A2 (ADR 0025): a [[Column mapping]] per dataset, with suggested roles, every-row validation and an error summary in the Datasets view; unmapped data still uses name heuristics | Weeks and fiscal years; derived columns; more than one breakdown |
| Preparation and cleaning | Trim, drop empty and duplicate rows, null non-numbers; mapped dates parsed into period labels | No imputation or outlier handling; cleaned data cannot be downloaded |
| Modelling | Linear trend forecast with backtest, anomalies, contributions, causal checks, sensitivity | No classification, regression, clustering or seasonality |
| Visualisation | Up to four bar or line charts per run, as SVG with zero-line bars, a marked forecast and a table of the numbers; an Overview of key figures | No dashboard pages, filters, slicers or drill-down |
| Live data | Runs advance while the Runs view is open, or through an optional worker | No connectors, scheduled refresh or push updates |

## Order of work

1. A dataset API and a dataset picker. Done on 2026-10-16.
2. Column mapping, so the user chooses measures, dimensions and the date. Done on 2026-10-16.
3. Several datasets per run, with declared join keys and a merge stage.
4. A cleaned-data download and an aggregates query endpoint.
5. Dashboard pages with filters and drill-down.
6. New modelling stages, built as [[Custom stages]].
7. Live data: connectors, scheduled re-runs and push updates.

The interface follows the same order in `docs/UI_PLAN.md`, built to the [[Design system]]: phases 0 and 1 (foundation, Overview and Datasets) shipped on 2026-10-16, and each later phase waits on its milestone.

Each step keeps the [[Governed pipeline]] and the [[Approval gate]], and each needs a decision record in the [[Decision log]] before it ships. Measures follow [[Weighted KPIs]].

## Related

- [[Team 3 Capstone]]: a real multi-page dashboard brief that shows what users will expect.
- [[Soul]]: no feature is presented as shipped before its tests pass.
