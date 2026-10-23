# Chart axes state their scale, and zero is drawn at zero

- Status: accepted
- Date: 2026-10-23
- Extends ADR 0032 (dashboard pages) and the run report charts of ADR 0029.
- Closes the "axis integrity" item of the dashboard conformance work on the
  progress board.

## Problem

The board listed four conformance items for the charts: axis integrity, a
single axis, entity-stable colour and a table per chart. A code audit of every
chart (`frontend/src/features/dashboard/charts.tsx`, the run report charts in
`RunsView.tsx` and the maintenance preview) found three of the four already
met. Every dashboard `Figure` requires a `table`, and the run report and
maintenance charts carry their own numbers tables. No chart has a second value
axis. Colour is the single accent, or fixed per condition in the maintenance
donut, so no colour depends on the order data arrives in.

Axis integrity was not met, in two ways:

1. **The run report line chart drew its baseline at a fixed position, not at
   zero.** The scale ran from `min(values, 0)` and the axis line sat at the
   bottom of the band. With a negative value in the series, the line a reader
   takes for zero was at the minimum, and nothing said so. The chart also had
   no value labels at all, so its height meant nothing without opening the
   table.
2. **The dashboard charts labelled only one end of their scale.** The line
   chart showed its maximum, the scatter plot its maximum, and the histogram no
   count at all. A reader could not tell whether the scale started at zero, or
   where.

## Decision

- `valueScale(values, top, bottom)` in `frontend/src/shared/charts.ts` is the
  one place a vertical scale is computed. It always contains zero, and returns
  where zero falls, so the zero line is drawn where zero is.
- Every line, histogram and scatter labels both ends of its value scale. The
  run report line chart draws its zero line at zero and labels its minimum and
  maximum. A flat series gets one label, not two on top of each other.
- Bars keep measuring from a zero line (`barGeometry`), which already met the
  rule; their numbers stay in the table beside them.

## Consequences

- Nine new tests guard it, four on the scale and five on rendering (`frontend/src/features/dashboard/charts.test.tsx`
  and `frontend/src/tests/charts.test.ts`). Four of the five render tests were
  run against the previous chart code and failed, so they test the change and
  not the harness. The run report chart is covered through the shared scale,
  not by its own render test, because it is internal to `RunsView.tsx`.
- The run report line chart's plot area moves 6 units in from the start edge to
  make room for its labels. Axes still read left to right in both languages.
- Out of scope and still open on the board: message-first analytical captions,
  and independent domain and manager acceptance of the dashboard.
