# An interactive dashboard: cross-filter by clicking, a saved view per dataset, and no empty sections

Date: 2026-10-27 · Status: Accepted (the "saved layouts; cross-filtering by
clicking a chart" cell of the visualisation row in the 16 October code
audit, `project-progress.md`, and the owner's 27 October request that the
platform choose its pages, charts, models and deliverable content from the
data, with every figure traceable and the reader able to interact with the
charts and keep what they prefer; the slice after
`2026-10-27-tree-ensemble.md`). Amends ADR 0032 and ADR 0058.

## Context

The dashboard of ADR 0032 already chooses its pages from the table's
fields, keeps every choice in the address and answers every figure from
the run's cleaned table through the query endpoint of ADR 0031. Three
things a reader expects of an interactive dashboard were missing. A bar
or a point could be read and drilled into from its numbers table, but not
clicked to narrow every other figure to that group. The address survived
a reload but nothing survived the next run over the same dataset: a reader
who always wants the breakdown by site, per record, started again each
time. And the executive documents of ADR 0058 printed a heading and a
"nothing available" sentence for every section that had nothing to
report, so a thin run read as a long document of absences.

## Decision

1. **Cross-filter by clicking.** Every bar of the overview's comparison
   and of the breakdown page, and every point of the overview's and the
   trend page's lines, is a button. Clicking one keeps that group alone:
   the breakdown value becomes the column's only filter, or the period
   becomes a range of one period, and every figure on every page follows,
   because the filter lives in the address like every other (`pick` and
   `isPicked` in `state.ts`). The kept mark is pressed and highlighted;
   clicking it again releases the group. A chart with clickable marks is
   a group of buttons rather than an image, so assistive technology reads
   the marks as controls, each named *Keep only X* or *Show every group
   again (X)*; its numbers table and drill-down are unchanged. The
   histogram and the scatter plot are not clickable: a bin is already a
   range filter from its table, and a point is one record.
2. **A saved view per owner and dataset, on the server.** `dashboard_views`
   holds one row per owner and dataset key, where the key is the stored
   dataset's id or, for a run without one, its dataset name. It stores the
   page and the address query. `GET`, `PUT` and `DELETE
   /api/runs/{run_id}/view` read, replace and forget the view of the run's
   dataset; the address is validated against the dashboard's own keys
   (`f.<column>`, `from`, `to`, `lo`, `hi`, `hiop`, `by`, `per`, `vs`,
   `sort`, `desc`, `o`), bounded to 2,000 characters, 60 settings and
   200 characters a value, and refused in the reader's language otherwise.
   Another owner's run is a 404; a viewer cannot save. The dashboard
   applies the view once when it opens from a bare address (no page and no
   query), says so, and offers *Save this view* and *Forget the saved view*
   in the filter bar; the demo's read-only identity sees neither. The table
   is backend-only like the others: in `TABLES`, `RESTORE_ORDER`, the hosted
   schema contract and `database/migrations/20261027_dashboard_views.sql`
   with row level security on and direct-client grants revoked.
3. **No empty sections in the executive documents.** A section of the
   HTML and DOCX brief whose only content would be its "nothing to report"
   statement (findings, model evaluations, review priorities, decision
   questions, controlled KPIs) is left out, and the decision context names
   every such section once with its statement, so absence stays explicit
   without a heading each. A section with real content beside a missing
   part keeps the statement in place, as before. The dashboard's pages were
   already chosen from the fields (ADR 0032) and are unchanged.
4. **The budget.** The dashboard chunk grows by the click handlers, the
   saved-view hook and eight strings in each language, all in the lazy
   pack. After folding the per-page click props into one helper and the
   save and forget handlers into one, the total script came to 256.6 KB
   against a 256 KB ceiling; the ceiling moves to 257 KB. First load is
   unchanged at 99.7 of 100 KB script and 10.5 KB style.

## Consequences

- A reader narrows every figure with one click and widens it with the
  next, and the address still says exactly what is shown, so a filtered
  page is still shareable and still traceable to its query.
- A saved view follows the dataset, not the run: the next analysis of the
  same export opens on the reader's page with their filters. It is one
  view per dataset, not a library of layouts, and it keeps choices, not
  charts: the pages and their figures are still chosen from the fields.
- A thin run's brief is shorter and says in one sentence what it lacks.
  Readers of earlier briefs will miss the per-section placeholders; the
  decision context carries the same words.
- Not done: cross-filtering from the histogram or the scatter plot,
  several named views per dataset, a choice of chart per page, and the
  stage reports' fixed sections (`report_markdown`), which still print
  every section. `docs/KNOWN_LIMITATIONS.md` item 27 says so.

## Tests

- `tests/test_dashboard_views.py`: the dataset key, the canonical address,
  six bilingual refusals, the table in the backup order; and on SQLite and
  PostgreSQL, a view that follows the stored dataset across runs, is
  invisible to another owner, cannot be saved by a viewer, is replaced
  rather than duplicated, is forgotten, and is shared by sample runs by
  name.
- `tests/test_report_navigation.py`: absent sections carry no heading and
  are named once in the decision context, in English and Arabic; a section
  with content beside a missing part keeps its statement.
- `frontend/src/features/dashboard/state.test.ts`: keep, release, replace
  a wider selection, and a period as a range of one.
- `frontend/src/features/dashboard/DashboardView.test.tsx`: a click on a
  bar writes the filter to the address and a second click clears it, in
  both languages; a saved view is applied once from a bare address; saving
  and forgetting go to the server and are confirmed.
- `frontend/e2e/dashboard.spec.ts`: keep a group by clicking, the coverage
  and the address follow, axe passes with the pressed mark, save the view,
  reopen from a bare address, forget it, release the group.
