# ADR 0051 — The executive view reads measurements

**Status:** Accepted
**Date:** 2026-10-18

## Context

ADR 0049 bound the maintenance KPI register to a run and said plainly what it
had not done: the executive view still read fixtures, and pointing it at the
endpoint was the next change. This is that change.

Where to put it had changed in the meantime. `MaintenancePreview` is a design
preview on `?design=maintenance`, mounted outside the application store and
reading `SAMPLE_ASSETS`. Pull request #9 meanwhile added
`AssetIntelligenceView`: a real routed view that lists runs, finds the ones
whose rail-screening stage succeeded, and shows only stages the server actually
returned. Reviving the fixtures preview would have made a third maintenance
surface. The real one already existed.

## Decision

1. **The KPI register is rendered in `AssetIntelligenceView`**, beneath the
   stage evidence it belongs with, fetched per run through `api.runKpis` in the
   reader's language. `MaintenancePreview` is untouched and stays a labelled
   design preview.

2. **A measure with no evidence prints no number.** `formatValue` returns null
   when `value` is null, and the view writes "Not measured" with the register's
   own reason. ADR 0042's point was that a zero here claims perfection from
   nothing; the rule now lives in a function with a test on it.

3. **A figure computed on part of its population says so, in the card.**
   `needsDisclosure` is true whenever `records_unmeasured` is non-zero, and the
   view appends the excluded count to the line. ADR 0042 ends by warning that a
   card hiding the exclusions re-creates the defect one layer up; that sentence
   is now two assertions in `kpiDisplay.test.ts`.

4. **Every card states what it was computed on.** The population and the record
   count sit beside each value, so dividing the register's numerator by that
   count reproduces the figure by hand. `isAuditable` encodes the property, and
   a test proves a figure rounded past the tolerance is rejected rather than
   waved through.

5. **Measures the dataset cannot support are named**, from the endpoint's
   `unavailable` map, instead of leaving a reader to wonder what is absent.

6. **No new CSS.** The section reuses the view's existing classes. The
   interface budget was already over when this started, and adding styles to a
   failing budget would have hidden one problem inside another.

## Consequences

The product now shows computed maintenance measurements rather than fixtures,
in English and Arabic, with their populations and exclusions attached. What it
does not show is any claim beyond measurement: the scope line under the cards
says these are measurements of recorded data, not a prediction, a cause or a
demonstrated saving.

Seven unit tests cover the display rules. The frontend suite is 142 passing,
typecheck is clean and the production build succeeds.

**The interface budget still fails**, at `css total 16.06 of 16.0 KB`, and that
is not this change: it arrived with pull request #9 and is recorded in that
integration's commit. This change edited no stylesheet and moved CSS by 0.004
KB. JS first load is now 98.6 of 100 KB, which leaves very little room. Trimming
or a justified budget change is a decision the owner still has to make, and the
next addition of either kind forces it.

What remains unbound: these are the register's eight measures over the whole
cleaned table, with no filtering by site, class or period, and no drill-through
from a card to the records behind it. Filters belong with the dashboard pages of
ADR 0032 and should reuse them rather than grow a parallel set here.
