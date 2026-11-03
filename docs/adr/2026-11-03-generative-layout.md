# Generative layout: a plan per dataset, validated and grounded (slice 1: server)

Date: 2026-11-03 · Status: Accepted for slice 1. The owner set the controlling
requirement on 2 November 2026: an LLM-designed, data-specific interface, not a
fixed dashboard with numbers substituted.

## Context

Miyaar's sources differ: maintenance records, contracts, budgets, mixed files.
The owner asked that each authorised dataset get the interface that suits it,
designed by a language model from the data's profile and the user's objective.
Brand, navigation, permissions and accessibility stay fixed. Every number must
come from a computed result, and no model output may run as code.

## Decision

1. **A declarative plan, version 1** (`server/layout_plan.py`).
   - A plan holds an objective and 1 to 10 sections.
   - Each section has a unique id, a registered component, an English and
     Arabic title and purpose, a span of 1 to 3, allowed interactions, and a
     binding.
   - Components: `kpi`, `trend`, `ranking`, `comparison`, `distribution`,
     `table` and `gap`.
   - A binding is a query of the existing query engine (`server/query.py`:
     named aggregates, filters, at most two groupings), or a column list for
     `table`. There are no expressions, URLs, scripts or remote components.
2. **Profiling, with no values sent.** The planner sees field names, types,
   roles, fill counts and distinct counts only. It never sees row values,
   category labels or ranges. The fingerprint hashes the schema, so a refresh
   of the same schema keeps it.
3. **Capability assessment.** These analyses are supported or refused with a
   reason:
   - `descriptive`
   - `trend`: needs a recognised date column;
   - `ranking`: needs a text column with 2 to 50 groups and a measure;
   - `distribution`
   - `forecast`: always refused by the planner. It needs a validated model
     result, so no curve is ever drawn from nothing;
   - `predictive_risk`: needs the risk-ranking stage to have succeeded;
   - `prescriptive`: needs the scenario stage to have succeeded.

   An unavailable analysis that matters appears as a `gap` section with its
   reason, never as an invented figure.
4. **Validation rejects the whole plan.** It rejects:
   - unknown keys, components or properties;
   - a wrong version or duplicate ids;
   - missing Arabic text;
   - links, markup or templates in text;
   - a component whose capability is unavailable;
   - a trend not grouped by the date column.

   It then **grounds** every binding by running it through `query.aggregate`
   or `query.records` against the real table. A binding that does not
   execute, such as an invented field, rejects the plan with the query's own
   reason. A partly valid plan is never rendered.
5. **Planners.**
   - The configured model is asked through the existing `ModelGateway.ask_json`
     only when the caller allows it and the run's privacy checks
     (`run_blocks_model`) allow it.
   - Otherwise, or when the model's plan fails validation, a deterministic
     **rule planner** derives a plan from the same profile.
   - The response says which planner was used (`source`: `model` or `rules`)
     and why.
6. **API.** `POST /api/runs/{id}/layout` with `{objective, use_model}` takes
   the read permission and has the same ownership and 404 rules as the
   table's query endpoints. It returns `plan`, `source`, `notes`, `problems`,
   `capabilities` and `fingerprint`.

## What this slice does not do yet

- **Interface:** the renderer and its cross-filtering, Jarvis scope,
  pinning, undo and restore of earlier views.
- **Persistence:** versioning plans in the store, which needs a schema
  migration.
- **No real model run:** no end-to-end run with a real provider has happened.
  No model is configured in this environment, so every plan produced here
  came from the rule planner. The model path is tested only with recorded
  fake answers, and is not claimed as working against a provider.

## Verification

`tests/test_layout_plan.py`, 11 tests, all on synthetic data:

- Four schemas (maintenance, contracts, budget, and an unseen training
  schema) produce four different grounded layouts. Trends appear only where
  there is a date, and every plan names the missing forecast as a gap.
- Eleven hostile or invented plans are rejected whole: an unknown component,
  an invented field, a link, markup, a template, an extra key, a duplicate id,
  a trend on text, a gap for an available capability, missing Arabic, and an
  unknown aggregate. A wrong version and an extra top-level key are also
  rejected.
- A recorded valid model plan is used and labelled with its provider, and
  the payload sent carries no category values.
- A recorded invalid plan is never rendered, and the rule planner is used.
- Prompt-injection text in a field name changes no binding.
- With no model, no permission, or a provider failure, the response says so.
- An empty table gives only a gap section.

`tests/test_query.py` adds two checks:

- an API test on a real run;
- the endpoint is added to the tenancy tests: another owner gets a 404, and
  a viewer and an admin can read.

## Slice 2: the interface (2026-11-03)

The owner asked for linked filters, Jarvis scoped to the selection, pinning
and restoring earlier layouts.

1. **A dashboard page, "Designed for this data"** (`DesignedPage`,
   lazy-loaded).
   - It renders a server-validated plan using registered components only:
     KPI value, trend line, ranked bars, distribution bars, records table, and
     "Not available yet" with the reason in the reader's language.
   - The layout comes first. The Jarvis console follows it on this page.
2. **Linked filters.**
   - Every section's query adds the dashboard's shared filters to its own
     binding.
   - A pick on a ranking or trend updates the dashboard state, the same URL
     state the other pages use, so every section and the coverage line change
     together. A distribution is not pickable.
3. **Jarvis scope.** Jarvis is bound to the same filter list
   (`DashboardJarvis filters`). A pick therefore changes its scope, and the
   existing scope rule asks the reader to refresh the binding instead of
   answering about the old scope.
4. **Versions and pins** (`layoutHistory.ts`, browser storage per run).
   - Up to five versions are kept for one schema fingerprint.
   - A refresh shows the stored layout and does not design again.
   - "Redesign" adds a version, and pinned sections carry over first.
   - "Earlier layouts" restores any kept version.
   - A schema change starts afresh and drops pins.
   - A late answer from an earlier request or another run is discarded.
   - A failed design keeps the last valid layout and says so.
5. **Bilingual server text.** Capability reasons and planner notes are now
   `{en, ar}`. The result names the `provider` when a model designed the
   plan.

**Limitations:** versions live in this browser only, until a stored history
has its schema migration. A layout designed by a real model has still not
been observed.

**Budget:** measured after the build, against the slice-1 head.

| | Slice 1 | Slice 2 | Change |
| --- | --- | --- | --- |
| Script total | 272,570 B | 275,715 B | +3,145 B |
| Style total | 36,875 B | 37,371 B | +496 B |

First load is unchanged, because the page is a lazy chunk. The owner approved
raising the limits to 276 KB and 37.5 KB ("Ok go", 3 November 2026).

**Verification:**

- `DesignedPage.test.tsx`, 5 tests:
  - history: five versions, pins carried within a schema and dropped on a
    new one;
  - a design happens once, and a refresh keeps it;
  - shared filters reach every section's query, and a pick narrows the
    state;
  - pin, redesign and restore;
  - a failure keeps the last layout, and a late answer for another run is
    dropped.
- Screenshots of the page were taken on the synthetic maintenance run in
  English and Arabic, using the Jarvis demo server.

## Slice 3: one complete decision path (2026-11-03)

The owner asked for one finished path before the look spreads to the rest of
the platform: upload, a generated page, a question to Jarvis, and a decision
backed by evidence. The page answers the manager's three questions first.

1. **The structure follows the data** (`domain(prof)`, inferred from field
   names only, and named in the result as `domain`).
   - Maintenance: priorities on downtime, failures or cost; risk and
     prescriptive gaps named.
   - Costs: actual, budget and their ratio, priorities, a variance comparison.
   - Contracts: count and value, priorities by count; no distribution and no
     failure model forced on them.
   - Anything else: totals and priorities on the lead measure.
2. **A brief first** (`brief`, no binding). Three cards from the run's
   executive answer under the current filters: what is happening, what is
   expected (the validated risk result, or the plain reason none exists), and
   what to decide. The decision is marked "Proposed, awaiting your review",
   shows its evidence on demand and opens the run's human approval.
3. **Three priorities** (`priorities`, limit 3). Selecting one sets the shared
   filter; the list keeps all three choices visible and marks the chosen one.
   A focus panel shows what drives it (`drivers`, another text column) and the
   records behind it. A column with one value per record is never used as a
   group or a driver.
4. **Jarvis tied to the selection.** On maintenance data the focus panel
   offers two questions; a click fills the Jarvis question and binds it to the
   same filters. Other domains say that Jarvis answers maintenance questions
   only, instead of offering a question it cannot answer.

**Verification:**

- `tests/test_layout_plan.py`, 13 tests: each kind gets its own structure,
  a brief takes no binding, drivers must be real, and no record number is a
  group or driver.
- `DesignedPage.test.tsx`, 8 tests: the brief with evidence and decision,
  priority to focus to Jarvis prompt, and the note for contracts.
- `e2e-jarvis/designed-path.spec.ts`, English and Arabic, on a 24-row
  synthetic file: upload, run, generated page, three priorities, Pumps
  selected, drivers by Asset_ID, records, Jarvis answers 2,460 for 6 of 24
  records (checked by hand: 400 + 404 + 408 + 412 + 416 + 420), evidence
  opened, and the run's approval reached.

**Budget:** measured after the build, against slice 2.

| | Slice 2 | Slice 3 | Change |
| --- | --- | --- | --- |
| Script total | 275,715 B | 277,554 B | +1,839 B |
| Style total | 37,371 B | 38,019 B | +648 B |

First load is unchanged (96.1 of 100 KB script, 10.4 of 10.5 KB style), because
the page is a lazy chunk. The owner approved raising the limits to 278 KB and
38.1 KB ("Approve", 3 November 2026).

**Limitations:** the domain is inferred from field names, so a file with
unhelpful names gets the general structure. Jarvis's calculated questions
cover maintenance only. A real model has still not designed a page here.

## Slice 4: three kinds of records through the same page (2026-11-03)

The owner asked for three different datasets to be tested. Slice 3 proved the
path on maintenance records; this slice runs contracts and budget files through
the real server and page, and fixes what the screenshots showed.

1. **Contracts read by obligation.** The priority list groups by the status
   column first (status, milestone, stage, type) and weighs each group by the
   contract value, so a tie of counts never decides the order. The drivers
   column prefers the party (vendor, supplier, contractor). When a date column
   is recognised, the trend is titled "value due by date".
2. **Name matching follows priority.** `_find` now takes the earliest matching
   word, not the earliest column, so "status" wins over "milestone" whatever
   the column order.
3. **A date is never a driver.** The rule planner leaves date columns out of
   groups and drivers, and validation rejects a model plan that names a date
   column as drivers.
4. **A priority list keeps its own choices.** Its query ignores the filter on
   its own column, so the other two choices stay visible after a selection.
5. **Readable figures.** A ratio KPI shows as a percentage (103.5%), and a
   KPI title does not repeat a column already named "Actual" or "Budget".

**Considered and reverted:** recognising any column whose name ends in "date"
(such as `Due_Date`) as the run's time axis. It changed how the maintenance
models read `Failure_Date` and broke six governed-run tests, so the pipeline's
date detection is unchanged. A contract file's due date shows as a trend only
when it is mapped or named as the pipeline expects ("Date", "Month" and the
like).

**Verification:**

- `tests/test_layout_plan.py`, 15 tests. New: a date is never a driver, a
  dated contracts table gets "value due by date", and contracts priorities are
  by status, weighted by value, with drivers by milestone.
- `DesignedPage.test.tsx`, 9 tests. New: a ratio reads 103.5%, and the priority
  query leaves out its own column's filter.
- `e2e-jarvis/designed-kinds.spec.ts`, contracts and budget files in English
  and Arabic. Each opens with the brief, has its own structure (contracts: no
  distribution; budget: no failure model), shows three priorities (Overdue for
  contracts, IT for the budget), and opens a focus panel with records and the
  note that Jarvis covers maintenance only. The Jarvis suite has 16 of 16
  passing.

**Budget:** 277,617 of 278,000 bytes of script and 38,019 of 38,100 of style.
No raise.
