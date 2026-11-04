# Faithful figures, full comparisons and a clean report hand-over

Date: 2026-11-04 · Status: Accepted

## Context

The owner asked for four concerns to be checked against the current code: does
Ask Miyaar receive the exact report and filters, do comparisons show every
value, are forecast claims qualified by actual validation, and does spoken
rounding change small or near-100 values. Each was investigated before any change.

| Concern | Finding on `main` at `91499c1` |
| --- | --- |
| Report and filters | Already correct inside the dashboard: its Ask Miyaar panel binds the run and the exact filters (`DashboardJarvis`). The Command Centre link hands over the run only, which matches its unfiltered brief, but an earlier binding of the same run *with* filters was kept, so the chat could answer on a narrower scope than the brief it came from. |
| Comparisons | Defect. A designed comparison ("Actual and budget by Dept") asked for two measures and drew only the first; budget never appeared in its bars or table. |
| Forecast qualification | Partly in place. The Command Centre turns its forecast state valid only for a model that beats its baseline. The slides' forecast page used one generic sentence and showed no model's metric, baseline or held-out size. |
| Rounding | Defect. Ask Miyaar showed and spoke two decimals, so 99.996 read as 100 and 0.004 as 0. The slides printed percentages to one decimal (99.96 as 100.0%). |

## Decision

1. **One rounding rule, `faithfulOptions` (interface) and `faithful` (server).** Two
   decimals, unless that rounding would land a value on a whole number or zero it is
   not on; then up to six decimals, and three significant digits for anything
   smaller. A whole value stays whole. Ask Miyaar's displayed and spoken figures use
   it, so they always agree; the slides use the server copy. The report document
   already keeps twelve significant digits and is unchanged.
2. **Every measure of a comparison is drawn and tabled.** When a section names more
   than one measure, each group shows one bar per measure on a shared scale, each
   named, and the table has one column per measure. Such a section offers bars and
   table only; a line of two different measures is not drawn. Picking a group still
   filters the dashboard.
3. **The forecast slide states each model's own validation:** metric against its
   baseline on the held-out records, then the same verdict the interface gives
   (`modelTone`): beats its baseline on past records only, does not beat it, or not
   assessed. With no model it says no forecast is claimed.
4. **A report handed to Ask Miyaar is re-bound to its whole scope** when the chat held
   that run with filters; an already whole binding is left alone.

## Consequences

Figures can carry more decimals than before where it matters, which is the point.
The chart change adds a short series label; no new dependency. Tests:
`faithfulNumber.test.ts`, a near-100 speech test, a comparison test in
`DesignedPage.test.tsx`, a hand-over test in `chat-availability.test.tsx`, and two
slide tests in `tests/test_executive_exports.py`.
