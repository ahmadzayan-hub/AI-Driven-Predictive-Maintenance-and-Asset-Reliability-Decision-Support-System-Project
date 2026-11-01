# Stage reports leave out headings with nothing under them

Date: 2026-10-28 · Status: Accepted (the "stage reports still print every
section" item of the interactive dashboard decision,
`docs/adr/2026-10-27-interactive-dashboard.md`; the executive brief already
did this, `2026-10-27-interactive-dashboard.md` decision 3).

## Context

The comprehensive analysis report assembles the four type reports and a set
of fixed sections: key metrics, every claim with its evidence, charts,
validation, and assumptions. A run that drew no charts printed a `## Charts`
heading over nothing; a run whose stages produced no calculation or claim
printed an empty key-metrics or claims table. The reader saw the same
heading as a substantive section and had to read on to learn there was
nothing under it. The executive brief had already stopped doing this.

## Decision

1. **Three optional sections are printed only when they have content.**
   Key metrics needs at least one calculation row; every claim needs at
   least one claim row; charts needs at least one chart. Each is built by a
   helper (`_metric_lines`, `_claim_lines`, `_chart_lines` in
   `server/analytics.py`) that returns no lines when there is nothing to
   print, so the headings and their separator rules go with them.
2. **The omission is named once.** The assumptions and limitations section
   gains one line naming the sections left out, in the reader's language
   (`left_out` and `separator` in the report text, English and Arabic).
   Absence stays explicit without a heading each.
3. **Validation, the four questions, the measures section, data quality,
   and the per-type sections are unchanged.** They are always produced by the
   stages, and removing them would remove what a reviewer checks.
4. **Approval binds to the stored report, so existing runs are unaffected.**
   A run's report is hashed when it is produced; changing the text changes
   the hash only for runs produced after this change.

## Consequences

- A thin run reads shorter, and its limitations say what it lacks.
- The report text changes for new runs. Anyone comparing a new report with an
  old one will see the three headings disappear where they were empty.

## Tests

- `tests/test_stage_report_sections.py`: empty runs produce no metric, claim
  or chart lines in either language; populated runs keep their headings and
  rows; the omission line names every section in both languages; the headings
  are the titles the report has always used.
- The existing run, analytics, report-contract and report-language suites pass
  unchanged (207 tests, 20 skipped for the optional runtimes).
