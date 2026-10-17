# Project progress

Last updated: 2026-10-17, session `7ba0117d` (A3 and A4). The session-end skill keeps this file current; the SessionStart hook reads the *Now* section into every new session.

**Vision.** Agentic OS becomes an analytics OS. It digests several datasets with dynamic inputs, then carries them through preparation, cleaning and modelling to a multi-page interactive dashboard with live data, with insights and key findings that are always traceable to a calculation. The reasoning behind it is in `brain/Projects/Analytics OS roadmap.md`.

## Now

- **Capstone, due 22 Oct (upload 21 Oct):**
    - Release candidates built on 16 Oct and sent to the user: `Group_9226_Team_3_Report.pdf` (24 A4 pages) and `Group_9226_Team_3_Presentation.pptx` (15 slides with notes), with the Power BI kit, a submission checklist and the build scripts. Report, deck and the kit's 30 expected values reconcile.
    - **Reviewed on 16 Oct by the review loop** (`docs/AGENT_TEAM.md` §5). The gates went 50.0% → 56.2% → 62.5% → 62.5%: all ten the session could act on pass, and six are the team's.
        - The rebuilt PDF is tagged and has bookmarks.
        - The deck's slides have titles and readable alt text.
        - The clip's stockout scene now states an association, not a cause.
        - `Team3_Review_Round1_Corrections.md` went to the user. It holds the verified corrections to two headline claims (row-average gaps, stockouts), with owners and replacement wording.
    - Still open, for the team:
        - build the `.pbix` in Power BI Desktop from the kit;
        - apply the memo's corrections in the shared report and deck;
        - the highlighted team items (registration numbers, screenshots, notebook names, the instructor email);
        - owners rerunning their own figures;
        - rehearsals on 20, 23 and 24 Oct.
    - The drafts are private documents shared with the team.
- **Operating system for this repository: done 2026-10-16.** CLAUDE.md, `AGENTS.md` for other coding agents, Memory.md, this board, session-logs.md, the second brain in `brain/`, session hooks and skills in `.claude/`, and `scripts/verify.py` with its `verify` skill. The SessionStart hook fired live in this session, at its start and after each compaction.
- **Interface, phases 0 and 1: done 2026-10-16** (`dea3b38`, ADR 0023, plan in `docs/UI_PLAN.md`). Design system v2 generated with the vendored ui-ux-pro-max skill, bundled Fira fonts, chart fixes, and the Overview and Datasets views.
- **A1, the dataset API: done 2026-10-16** (ADR 0024). `POST /api/datasets` reads CSV, TSV, Excel, JSON and JSON Lines into one canonical table with the standard library. Uploads go up to 4 MB, the platform's limit, and 10 MB as CSV. The Runs view has a stored-dataset picker, and the Datasets view adds files.
- **A2, column mapping: done 2026-10-16** (ADR 0025). The owner gives each column a role (measure, dimension, date, ignore), chooses the measure, breakdown, date order and grain, and saves it with the dataset after every-row validation. Runs copy the mapping; unmapped data runs as before. The Datasets view has a *Columns* panel with preview, suggestions and an error summary.
- **Agent team: done 2026-10-16** (`docs/AGENT_TEAM.md`).
    - **Reviewers:** five read-only reviewer subagents on Haiku or Sonnet by job, run by the `review-loop` skill with `scripts/review_gate.py` and `scripts/figures_check.py`.
    - **Makers:** `dashboard-analyst`, with the `dashboards` skill: `scripts/analyse.py`, then a Claude Dashboard or an offline page.
    - **Local models:** `scripts/consult.py` for free local second opinions, untested live here.
    - **ADR 0026:** uneven periods are read per record.
- **Agents are measured: done 2026-10-17** (ADR 0027).
    - **Suites and floors:** every classifying agent has a labelled synthetic suite with a confusion matrix, precision and recall (`scripts/evaluate_agents.py`, `evals/`). Floors are enforced by `tests/test_evals.py`.
    - **Blind holdout recall, before → now:** intent 65% → 80%, jargon 40% → 83%, causal wording 67% (new and the weakest), privacy 83% → 100%, router 75% → 90%, raw-data guard 50% → 100%.
    - **Round 5, on a fresh blind set (v4), before → after:** intent 68% → 72%, jargon 83% → 92%, causal wording 69% → 69%. The rules plateau near 70% on unseen sentences for intent and causal wording.
    - **Reviewer benchmark:** three seeded memos in `evals/reviewers/`, scored by `scripts/score_review.py`. The Tier 0 figures checker went from 0% to 75% on the blind memo. The LLM reviewers were already near their ceiling, so the prompt changes are not proven on held-out memos.
    - **Assistant:** forget by description, with confirmation.
- **Capstone restyled, 2026-10-17:**
    - The report (23 pages, tagged) and the deck (15 slides) were rebuilt in the house style's blue-led print variant, following the Dubai Design System's principles. The Power BI theme in the kit matches.
    - The capstone gates are unchanged: all ten the session can act on pass, and six remain the team's.
    - The typeface is IBM Plex Sans with IBM Plex Sans Arabic, the user's choice; Dubai can replace it if its files are supplied.
- **House style: done 2026-10-17.** `.claude/skills/rta-style/` (colours, type and layout only, no logo, name or data) themes the offline dashboards, the clips and the evaluation report, checked for AA contrast in light and dark.
- **Views load on demand: done 2026-10-17** (ADR 0028). The chat and the shell ship first; the other views and dialogs are chunks fetched when shown, and prefetched in idle time. First load fell from 96.7 to 85.7 KB gzipped, and Lighthouse's unused script halved, but load speed did not measurably change (mobile 98 against 99, largest paint 2.13 s both). The budget now counts the first load, all scripts and the largest chunk.
- **Governed UI, delivered 2026-10-17 (ADR 0029):** editable Figma light/dark and Arabic phone designs, shared run snapshots, grouped progress, exact-report approvals inbox, evidence dialog, assistant result cards, hash deep links, scoped text drafts, upload previews and PWA installation guidance. Existing on-demand loaders and their idle prefetch are retained. The real publishing journey, recovery, keyboard review, Arabic phone layout and bundle checks pass in [CI 39019826211](https://github.com/ahmadzayan-hub/agentic-os-final-project/actions/runs/39019826211). [Design handoff](docs/design/AGENTIC_UI_SPEC.md), [actual screenshots](docs/screenshots/) and [validation with open observations](docs/design/VALIDATION.md).
- **A3, several datasets per run: done 2026-10-17** (ADR 0030). A run joins up to four stored lookups onto its main dataset on declared keys, right after cleaning. A repeated lookup key is refused, a left join keeps every total, an inner join says what it left out, and every join reports its key coverage; the Validation Expert recounts the rows. The run form has a join builder with a preview.
- **A4, the cleaned table: done 2026-10-17** (ADR 0031). `GET /api/runs/{id}/data.csv` downloads the cleaned, merged table as spreadsheet-safe CSV; `/fields`, `/query` (totals by group under filters, rates as ratios of sums) and `/records` answer questions of it without sending it to the browser. Another owner's run is a 404.
- **Next build: A5, dashboard pages (ADR 0032)**, then A6 models and A7 live data.

## Next

1. Observe the manager's timed review task, real Windows/Android/iOS PWA installation and assistive-technology use; measure fresh Web Vitals. Automated interface checks and bundle budgets pass; see the validation record for the remaining observations. CSS is near its existing limit, so trim before adding styles or record a justified budget change in an ADR.
2. A5 dashboard pages on the A4 query API (ADR 0032), then A6 and A7; workbook sheet selection (phase 2).
3. Harder reviewer memos (subtler defects, longer documents), so prompt changes can be measured. For intent and causal wording, try a model behind the rules once a rotated key or a local model is available; the rules plateau near 70% on blind sets.
4. Invite the team as collaborators and protect the default branch (owner action, on GitHub).

## Analytics OS milestones

Status values: Not started, In progress, Done (date, evidence).

| # | Milestone | Status | Gate to call it done |
| --- | --- | --- | --- |
| A1 | Dataset API: `POST /api/datasets`, CSV, XLSX and JSON parsers, larger limit, picker in the Runs view | Done 2026-10-16: ADR 0024; 53 reader and API tests on SQLite and PostgreSQL; end-to-end upload of CSV, XLSX and JSON | ADR; API and parser tests; e2e upload of each format |
| A2 | Column mapping: choose measures, dimensions and the date column; date parsing; replaces name heuristics | Done 2026-10-16: ADR 0025; 50 mapping tests on SQLite and PostgreSQL; e2e mapping in English and Arabic, desktop and phone | ADR; tests on mapped and unmapped data; Arabic and English UI |
| A3 | Several datasets per run: dataset list, declared join keys, merge stage after cleaning | Done 2026-10-17: ADR 0030; 46 join tests on SQLite and PostgreSQL (row counts, key coverage, repeated keys, numeric and date keys, tenancy); join builder end-to-end in English and Arabic, desktop and phone | ADR; join-correctness tests (row counts, key coverage) |
| A4 | Cleaned-data download and an aggregates query endpoint (filter and group-by) | Done 2026-10-17: ADR 0031; 30 query tests on SQLite and PostgreSQL, tenant isolation on all four endpoints; CSV download end-to-end | Tests; tenant isolation tests on the new endpoints |
| A5 | Dashboard: router, pages, global filters, drill-down, richer chart types | Not started | ADR; axe and e2e on every page; desktop and mobile |
| A6 | Modelling stages: regression, classification, clustering, seasonal forecast, each against a baseline | Not started | ADR 0020 plugins; every model reports its baseline |
| A7 | Live data: connectors that snapshot into datasets, scheduled re-runs, push updates (SSE) | Not started | ADR; worker tests; reconnect behaviour |

## Gap analysis (code audit, 2026-10-16)

| Area | Today | Missing |
| --- | --- | --- |
| Ingestion | `POST /api/datasets` reads CSV, TSV, XLSX, JSON and JSON Lines (`server/datasets.py`): 4 MB uploaded, 10 MB as CSV, 50,000 rows, 500 columns; stored content-addressed with format and shape; pasted CSV still works | `.xls`, OpenDocument, Parquet, connectors; choosing a sheet in the interface; deleting a dataset |
| Several datasets | A run joins up to four stored lookups on declared keys (ADR 0030) | Unions; fuzzy or case-insensitive keys |
| Dynamic inputs | A saved column mapping (`server/mapping.py`, ADR 0025) sets measures, breakdown, date, date order and grain, reading currency and Arabic digits; without one, numeric typing at 50% and 90% parse rates, the measure from the glossary or name hints, and a date column named month, date, period, week or year | Weeks and fiscal years; derived columns; more than one breakdown; decimal commas |
| Prep and cleaning | Trim, drop empty and duplicate rows, null non-numbers; mapped dates become sortable period labels, unmapped periods still sort as strings; the cleaned table downloads and answers queries (ADR 0031) | Imputation, outlier treatment |
| Modelling | Linear trend with backtest, anomalies, contributions and correlations, causal checks, concentration, sensitivity | Classification, multivariate regression, clustering, seasonality |
| Visualisation | Up to four bar or line `ChartSpec`s per run, as hand-written SVG (`RunsView.tsx`): bars from a zero line, a marked forecast boundary, a table of the numbers under each chart. The Overview shows key figures and the latest headlines | Dashboard pages, filters, slicers, drill-down, tooltips |
| Live data | A run advances while the Runs view is open (350 ms ticks) or through `server/worker.py` | Connectors, scheduled refresh, SSE or websockets |

Reusable foundations: the metric glossary (`metrics.json`), custom stages (ADR 0020), agent runtimes and the MCP server (ADR 0021), and durable runs with database leases (ADR 0006).

## Shipped

| Date | What | Evidence |
| --- | --- | --- |
| 2026-10-17 | A3 and A4: several datasets per run with declared joins and a merge preview (ADR 0030); the cleaned table as CSV, fields, totals and records (ADR 0031) | 941 Python tests with PostgreSQL (16 skipped); 87 frontend unit tests; end-to-end 82 of 86 run and pass, 4 skipped by design; budget 93.7 of 100 KB first load, CSS 9.4 of 10 KB |
| 2026-10-17 | Views load on demand: chunks per view and dialog, idle prefetch, a bilingual loading and failure state; the budget counts first load, total and the largest chunk (ADR 0028) | 863 Python tests with PostgreSQL (16 skipped); 66 frontend unit tests; budget 85.7 of 100 KB first load; end-to-end 71 of 74 run and pass, 3 skipped by design; Lighthouse mobile 98 (99 before), largest paint 2.13 s both |
| 2026-10-16 | Agent team: reviewer subagents, the review loop and its gates, the figures checker (glued cells, worked arithmetic), the analysis export and dashboards skill, local-model consultation; ADR 0026, uneven periods read per record; motion transcripts keep sources apart | 818 Python tests with PostgreSQL (16 skipped here); 60 frontend unit tests; build within budget; end-to-end not rerun (no interface change) |
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
