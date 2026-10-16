# Project progress

Last updated: 2026-10-16, session `7ba0117d`. The session-end skill keeps this file current; the SessionStart hook reads the *Now* section into every new session.

**Vision.** Agentic OS becomes an analytics OS. It digests several datasets with dynamic inputs, then carries them through preparation, cleaning and modelling to a multi-page interactive dashboard with live data, with insights and key findings that are always traceable to a calculation. The reasoning behind it is in `brain/Projects/Analytics OS roadmap.md`.

## Now

- **Capstone, due 22 Oct (upload 21 Oct):**
    - The report and the 15-slide deck carry figures computed from the final dataset on 16 Oct, and a Power BI kit is delivered.
    - Still open: build the `.pbix` from the kit; the team-owned `[Add]` items (screenshots, notebook names, the instructor email); owners rerunning their own figures; rehearsals on 20, 23 and 24 Oct.
    - The drafts are private documents shared with the team.
- **Operating system for this repository: done 2026-10-16.** CLAUDE.md, Memory.md, this board, session-logs.md, the second brain in `brain/`, and session hooks and skills in `.claude/`. Next: confirm the hooks fire in a fresh session.
- **Interface, phases 0 and 1: done 2026-10-16** (`dea3b38`, ADR 0023, plan in `docs/UI_PLAN.md`). Design system v2 generated with the vendored ui-ux-pro-max skill, bundled Fira fonts, chart fixes, and the Overview and Datasets views.
- **Next build: A1, dataset API (ADR 0024).** It unlocks interface phase 2, adding data in several formats.

## Next

1. A1: dataset API and upload formats, with ADR 0024 (see the milestones). Then interface phase 2: upload, preview, column mapping and deep links.
2. A2: column mapping in the UI, used by governance and preparation.
3. Invite the team as collaborators and protect the default branch (owner action, on GitHub).

## Analytics OS milestones

Status values: Not started, In progress, Done (date, evidence).

| # | Milestone | Status | Gate to call it done |
| --- | --- | --- | --- |
| A1 | Dataset API: `POST /api/datasets` (multipart), CSV, XLSX and JSON parsers, larger limit, picker in the Runs view | In progress: the picker for stored datasets shipped in `dea3b38`; the API and parsers are not started | ADR; API and parser tests; e2e upload of each format |
| A2 | Column mapping: choose measures, dimensions and the date column; date parsing; replaces name heuristics | Not started | ADR; tests on mapped and unmapped data; Arabic and English UI |
| A3 | Several datasets per run: dataset list, declared join keys, merge stage after cleaning | Not started | ADR; join-correctness tests (row counts, key coverage) |
| A4 | Cleaned-data download and an aggregates query endpoint (filter and group-by) | Not started | Tests; tenant isolation tests on the new endpoints |
| A5 | Dashboard: router, pages, global filters, drill-down, richer chart types | Not started | ADR; axe and e2e on every page; desktop and mobile |
| A6 | Modelling stages: regression, classification, clustering, seasonal forecast, each against a baseline | Not started | ADR 0020 plugins; every model reports its baseline |
| A7 | Live data: connectors that snapshot into datasets, scheduled re-runs, push updates (SSE) | Not started | ADR; worker tests; reconnect behaviour |

## Gap analysis (code audit, 2026-10-16)

| Area | Today | Missing |
| --- | --- | --- |
| Ingestion | CSV only, inside `POST /api/runs` (`server/app.py`); 2 MB and 50,000 rows (`server/analytics.py`); stored content-addressed (`server/runs.py`) | Upload endpoint, XLSX and JSON. The Datasets view lists stored datasets and analyses one by id (`dea3b38`) |
| Several datasets | Storage keeps many; one `dataset_id` per run | Multi-dataset runs, joins |
| Dynamic inputs | Numeric typing at 50% and 90% parse rates; measure from the glossary or name hints (`server/metrics.py`); date column must be named month, date, period, week or year | User column mapping; date and category typing; currency and percent parsing |
| Prep and cleaning | Trim, drop empty and duplicate rows, null non-numbers; periods sorted as strings | Imputation, outlier treatment, date parsing; cleaned data not downloadable |
| Modelling | Linear trend with backtest, anomalies, contributions and correlations, causal checks, concentration, sensitivity | Classification, multivariate regression, clustering, seasonality |
| Visualisation | Up to four bar or line `ChartSpec`s per run, as hand-written SVG (`RunsView.tsx`): bars from a zero line, a marked forecast boundary, a table of the numbers under each chart. The Overview shows key figures and the latest headlines | Dashboard pages, filters, slicers, drill-down, tooltips |
| Live data | A run advances while the Runs view is open (350 ms ticks) or through `server/worker.py` | Connectors, scheduled refresh, SSE or websockets |

Reusable foundations: the metric glossary (`metrics.json`), custom stages (ADR 0020), agent runtimes and the MCP server (ADR 0021), and durable runs with database leases (ADR 0006).

## Shipped

| Date | What | Evidence |
| --- | --- | --- |
| 2026-10-16 | Interface phases 0 and 1: design system v2, bundled fonts, chart fixes, Overview and Datasets views (ADR 0023) | `dea3b38`; 646 Python tests with PostgreSQL; 52 frontend unit tests; 57 of 60 end-to-end checks run and pass, 3 skipped by design |
| 2026-10-16 | Operating system for the repository: tracking files, second brain, hooks and skills | 646 Python tests with PostgreSQL, 30 of them new; brain check strict-clean |
| 2026-10-16 | Repository opened to the team: CONTRIBUTING.md, PR template, `private/` ignored | `7091b76`; CI run 43 green |
| 2026-10-16 | `main` merged into the working branch; source-map-js advisory cleared | `253ea07`, `8a8b376`; 616 Python tests with PostgreSQL |
| 2026-10-02 | Vercel production deployment, verified for a signed-in owner | `2aeb9fd`, `7869546` |
| 2026-10-02 | Frontend audit cleared (vitest, undici) | `92cf174`; CI run 42 green |
| 2026-09-25 | Reports in the reader's language (ADR 0022) | `877713c` |
| 2026-09-23 | Agent runtimes and MCP (ADR 0021); custom stages (ADR 0020) | `de59a02`, `c09e8b3` |

The earlier history is in `docs/ROADMAP.md` (tiers and gates) and `docs/adr/`.

## Risks and blockers

- **Capstone time:** six days to submission, with the dashboard not yet built. Cut optional scope first, as the plan says.
- **Data upload limit:** the capstone dataset is 2.1 MB, over the app's 2 MB limit, until A1 lands.
- **Production checks:** auth, the database and the model provider are unverified on Vercel; see `docs/KNOWN_LIMITATIONS.md`.
- **Hooks:** they need `python3`, and they run only after a person trusts the folder in Claude Code.
