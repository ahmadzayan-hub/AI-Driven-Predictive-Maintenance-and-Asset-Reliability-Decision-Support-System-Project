# Project progress

Last updated: 2026-10-16, session `7ba0117d`. The session-end skill keeps this file current; the SessionStart hook reads the *Now* section into every new session.

**Vision.** Agentic OS becomes an analytics OS. It digests several datasets with dynamic inputs, then carries them through preparation, cleaning and modelling to a multi-page interactive dashboard with live data, with insights and key findings that are always traceable to a calculation. The reasoning behind it is in `brain/Projects/Analytics OS roadmap.md`.

## Now

- **Capstone, due 22 Oct (upload 21 Oct):**
    - Release candidates built on 16 Oct and sent to the user: `Group_9226_Team_3_Report.pdf` (24 A4 pages) and `Group_9226_Team_3_Presentation.pptx` (15 slides with notes), with the Power BI kit, a submission checklist and the build scripts. Report, deck and the kit's 30 expected values reconcile.
    - Still open: build the `.pbix` in Power BI Desktop from the kit; the team-owned items highlighted in the PDF (registration numbers, screenshots, notebook names, the instructor email); owners rerunning their own figures; rehearsals on 20, 23 and 24 Oct.
    - The drafts are private documents shared with the team.
- **Operating system for this repository: done 2026-10-16.** CLAUDE.md, `AGENTS.md` for other coding agents, Memory.md, this board, session-logs.md, the second brain in `brain/`, session hooks and skills in `.claude/`, and `scripts/verify.py` with its `verify` skill. The SessionStart hook fired live in this session, at its start and after each compaction.
- **Interface, phases 0 and 1: done 2026-10-16** (`dea3b38`, ADR 0023, plan in `docs/UI_PLAN.md`). Design system v2 generated with the vendored ui-ux-pro-max skill, bundled Fira fonts, chart fixes, and the Overview and Datasets views.
- **A1, the dataset API: done 2026-10-16** (ADR 0024). `POST /api/datasets` reads CSV, TSV, Excel, JSON and JSON Lines into one canonical table with the standard library. Uploads go up to 4 MB, the platform's limit, and 10 MB as CSV. The Runs view has a stored-dataset picker, and the Datasets view adds files.
- **A2, column mapping: done 2026-10-16** (ADR 0025). The owner gives each column a role (measure, dimension, date, ignore), chooses the measure, breakdown, date order and grain, and saves it with the dataset after every-row validation. Runs copy the mapping; unmapped data runs as before. The Datasets view has a *Columns* panel with preview, suggestions and an error summary.
- **Next build: A3, several datasets per run (ADR 0026)**, and the rest of interface phase 2: deep links and the sheet picker. Code-split the views first: JavaScript is at 96.7 of 100 KB.

## Next

1. Code-split the interface views, to recover budget before phase 3.
2. A3: several datasets per run, with declared join keys (ADR 0026); deep links and the sheet picker (phase 2).
3. Invite the team as collaborators and protect the default branch (owner action, on GitHub).

## Analytics OS milestones

Status values: Not started, In progress, Done (date, evidence).

| # | Milestone | Status | Gate to call it done |
| --- | --- | --- | --- |
| A1 | Dataset API: `POST /api/datasets`, CSV, XLSX and JSON parsers, larger limit, picker in the Runs view | Done 2026-10-16: ADR 0024; 53 reader and API tests on SQLite and PostgreSQL; end-to-end upload of CSV, XLSX and JSON | ADR; API and parser tests; e2e upload of each format |
| A2 | Column mapping: choose measures, dimensions and the date column; date parsing; replaces name heuristics | Done 2026-10-16: ADR 0025; 50 mapping tests on SQLite and PostgreSQL; e2e mapping in English and Arabic, desktop and phone | ADR; tests on mapped and unmapped data; Arabic and English UI |
| A3 | Several datasets per run: dataset list, declared join keys, merge stage after cleaning | Not started | ADR; join-correctness tests (row counts, key coverage) |
| A4 | Cleaned-data download and an aggregates query endpoint (filter and group-by) | Not started | Tests; tenant isolation tests on the new endpoints |
| A5 | Dashboard: router, pages, global filters, drill-down, richer chart types | Not started | ADR; axe and e2e on every page; desktop and mobile |
| A6 | Modelling stages: regression, classification, clustering, seasonal forecast, each against a baseline | Not started | ADR 0020 plugins; every model reports its baseline |
| A7 | Live data: connectors that snapshot into datasets, scheduled re-runs, push updates (SSE) | Not started | ADR; worker tests; reconnect behaviour |

## Gap analysis (code audit, 2026-10-16)

| Area | Today | Missing |
| --- | --- | --- |
| Ingestion | `POST /api/datasets` reads CSV, TSV, XLSX, JSON and JSON Lines (`server/datasets.py`): 4 MB uploaded, 10 MB as CSV, 50,000 rows, 500 columns; stored content-addressed with format and shape; pasted CSV still works | `.xls`, OpenDocument, Parquet, connectors; choosing a sheet in the interface; deleting a dataset |
| Several datasets | Storage keeps many; one `dataset_id` per run | Multi-dataset runs, joins |
| Dynamic inputs | A saved column mapping (`server/mapping.py`, ADR 0025) sets measures, breakdown, date, date order and grain, reading currency and Arabic digits; without one, numeric typing at 50% and 90% parse rates, the measure from the glossary or name hints, and a date column named month, date, period, week or year | Weeks and fiscal years; derived columns; more than one breakdown; decimal commas |
| Prep and cleaning | Trim, drop empty and duplicate rows, null non-numbers; mapped dates become sortable period labels, unmapped periods still sort as strings | Imputation, outlier treatment; cleaned data not downloadable |
| Modelling | Linear trend with backtest, anomalies, contributions and correlations, causal checks, concentration, sensitivity | Classification, multivariate regression, clustering, seasonality |
| Visualisation | Up to four bar or line `ChartSpec`s per run, as hand-written SVG (`RunsView.tsx`): bars from a zero line, a marked forecast boundary, a table of the numbers under each chart. The Overview shows key figures and the latest headlines | Dashboard pages, filters, slicers, drill-down, tooltips |
| Live data | A run advances while the Runs view is open (350 ms ticks) or through `server/worker.py` | Connectors, scheduled refresh, SSE or websockets |

Reusable foundations: the metric glossary (`metrics.json`), custom stages (ADR 0020), agent runtimes and the MCP server (ADR 0021), and durable runs with database leases (ADR 0006).

## Shipped

| Date | What | Evidence |
| --- | --- | --- |
| 2026-10-16 | A2, column mapping: roles per column, suggestions with reasons, every-row validation with an error summary, runs that copy the mapping (ADR 0025) | 769 Python tests with PostgreSQL; 60 frontend unit tests; 69 of 72 end-to-end checks run and pass, 3 skipped by design |
| 2026-10-16 | Agentic OS setup: `AGENTS.md`, `scripts/verify.py` and the `verify` skill; the server compresses and caches the built interface as Vercel does (ADR 0023, amendment) | 719 Python tests with PostgreSQL; 54 frontend unit tests; 63 of 66 end-to-end checks pass, 3 skipped by design; Lighthouse mobile Performance 99, up from 86 to 88, and 100 for the other three |
| 2026-10-16 | A1, the dataset API: CSV, TSV, Excel, JSON and JSON Lines read into one canonical table; stored-dataset picker; uploads in the Datasets view (ADR 0024) | `50babcc`; 699 Python tests with PostgreSQL; 54 frontend unit tests; 63 of 66 end-to-end checks run and pass, 3 skipped by design |
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
- **Data upload limit:** resolved by A1. The capstone file (2.1 MB, 5,000 rows, 60 columns) is within the new limits; it has not been uploaded here, because course files stay out of this environment's repository.
- **Production checks:** auth, the database and the model provider are unverified on Vercel; see `docs/KNOWN_LIMITATIONS.md`.
- **Hooks:** they need `python3`, and they run only after a person trusts the folder in Claude Code.
