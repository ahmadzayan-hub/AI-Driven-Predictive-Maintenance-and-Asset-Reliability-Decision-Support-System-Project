# ADR 0038 — Uploaded datasets through the governed analysis workflow

**Status:** Accepted
**Date:** 2026-10-17

## Context

The owner wants to upload their datasets and have the application's agents
analyze them. The maintenance preview uses fictional fixtures; the existing
dataset API, column mapping, pipeline and computed dashboards already handle
real tabular data. An empty upload selection could previously start a sample
run, and the interface did not expose the API's named-workbook-sheet option.

## Decision

- Link the maintenance preview's primary upload action to
  `#/runs?source=upload` in the normal application. Overview's New analysis
  action also opens upload mode. The normal app retains authentication and
  owner-scoped dataset/run APIs; the preview remains fictional.
- Require a successful upload, nonempty pasted CSV or a selected stored
  dataset in those source modes. Check readiness at submission as well as in
  the button state. Only explicitly selecting the sample uses sample data.
  Clear the previous upload and pasted CSV before a replacement, including
  failed or oversized replacements. Disable source changes while uploading.
- Reuse column-role review before starting an uploaded or stored dataset.
  Preserve saved mapping validation and explicit joins. Analysis remains a
  deliberate Start run action, followed by automatic governed stages.
- Return the actual `selected_sheet` alongside workbook sheet names. After a
  successful workbook upload, allow another sheet to be submitted from the
  same File object. File bytes are parsed on the server, never by a model.
  Sheet selection is explicit; it never silently combines unrelated tables.
- Explain supported tabular formats and the existing upload/row/column/CSV
  bounds in English and Arabic. Keep limits unchanged. Predictions require
  suitable data; the optional `models` profile retains baseline evaluation.
- Reuse the existing execution mechanism: an open Runs view advances the run;
  the separately started worker advances runs without a browser. Both stop
  before publishing until the owner approves the exact report.
- For browser verification, resolve Python from `PYTHON_EXECUTABLE`, the
  project virtual environment, or the existing `python3` fallback. Close
  SQLite connections before temporary-directory cleanup in dataset tests so
  Windows can remove those disposable databases.

## Boundaries and alternatives

No dependency, parser format, quota or tenant boundary changes. No raw dataset
is given to a language model. The maintenance design is not automatically
populated with invented asset scores for arbitrary input: computed results
open in the run's existing dashboard. Failure prediction and maintenance KPIs
still depend on the domain contract and evaluated models.

The workbook picker is available after the first visible sheet parses. A
workbook with a non-tabular cover must have its data sheet moved first or be
exported as CSV; the API can also select a sheet explicitly. Previously stored
datasets remain available if an attempted sheet switch fails.

A new autonomous agent framework or frontend spreadsheet parser would duplicate
existing behavior and weaken the provenance boundary. Increasing file limits
would require storage and hosting changes beyond this intake improvement.

## Verification and reconsideration

Unit checks cover source readiness, failed replacements, sheet selection,
route restoration and locale parity. Parser/API checks verify the chosen
worksheet's columns and rows enter its run. Real browser checks upload CSV,
Excel and JSON, verify report/dashboard aggregates, and confirm the approval
gate in English and Arabic on desktop and phone.

Revisit intake discovery when workbooks with cover sheets, additional formats
or larger datasets are prioritized. Revisit execution hosting before promising
unattended runs in a deployment that has no worker.
