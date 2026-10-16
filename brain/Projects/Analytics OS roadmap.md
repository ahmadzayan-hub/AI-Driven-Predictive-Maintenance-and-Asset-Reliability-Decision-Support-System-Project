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
| Ingestion | CSV only, up to 2 MB and 50,000 rows, sent inside the run request | No upload endpoint, XLSX or JSON. Since `dea3b38` the Datasets view lists stored datasets and analyses one by id |
| Several datasets | Storage keeps many, but a run takes exactly one | No joins, merges or multi-table runs |
| Dynamic inputs | Columns typed by heuristics; the measure picked from the glossary or by name hints | No column mapping in the UI; dates need fixed column names |
| Preparation and cleaning | Trim, drop empty and duplicate rows, null non-numbers | No imputation, outlier handling or date parsing; cleaned data cannot be downloaded |
| Modelling | Linear trend forecast with backtest, anomalies, contributions, causal checks, sensitivity | No classification, regression, clustering or seasonality |
| Visualisation | Up to four bar or line charts per run, as SVG with zero-line bars, a marked forecast and a table of the numbers; an Overview of key figures | No dashboard pages, filters, slicers or drill-down |
| Live data | Runs advance while the Runs view is open, or through an optional worker | No connectors, scheduled refresh or push updates |

## Order of work

1. A dataset API and a dataset picker.
2. Column mapping, so the user chooses measures, dimensions and the date.
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
