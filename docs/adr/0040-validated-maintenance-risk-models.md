# ADR 0040 — Validated maintenance risk models

**Status:** Accepted
**Date:** 2026-10-18

## Context

ADR 0033 ships four general model stages and states their own limit plainly:
"A model cannot know which columns were recorded after the outcome, so every model
says so: an input observed after the outcome makes a model look better than it is."

That caveat was the best the engine could do, because nothing in it knew when a
column was recorded. The maintenance contract (ADR 0036's product, milestone S1)
now does: every field carries a timing of `before`, `outcome`, `derived` or
`unknown`, and `contract.model_inputs` returns the usable columns with a reason for
each exclusion. On a 60-column maintenance panel that admits 11 and withholds 49.

A model is also only worth fitting if someone can act on it, and only worth
believing if it beats what a person would do without it.

## Decision

`server/maintenance/targets.py` adds `MaintenanceRisk`, an ADR 0020 stage running
after the Sensitivity Agent alongside the ADR 0033 models.

1. **A target is a decision, not a column.** Each `Target` names the question, the
   population it is answered on, the operational decision it supports and the
   horizon. Two ship: `repeat_failure` on corrective work, and `sla_breach`.

2. **Inputs are curated by timing**, from the contract. The stage reports how many
   columns were withheld and why, as an `assumption` claim.

3. **The baseline is the stronger of** the majority class and the best single
   known-before grouping rule — the obvious thing a person would do with the table
   and no model. A grouping rule needs between 2 and 12 groups, so a date or an
   identifier cannot masquerade as one by memorising the training set.

4. **The verdict needs two tests, not one.** ADR 0033's 5% relative margin is kept
   unchanged. It is paired with an absolute floor, because under balanced accuracy
   a majority-class baseline scores exactly 0.5 *by construction* — one class hits
   1.0 and the other 0.0 — so clearing it by 5% can still be a coin flip. A model
   is `useful` only when it beats the baseline by 5% **and** reaches 0.55 in
   absolute terms. This is a property of the metric, decided before any holdout was
   seen, not a threshold adjusted afterwards.

5. **The held-out floor is 50 records**, not 10. Balanced accuracy on a few dozen
   records swings several points on noise alone: a deliberately signal-free fixture
   scored 0.62 on about 80 held-out rows, and 0.514 against a 0.515 baseline once
   the holdout reached 481. Every claim states the held-out count, because a score
   without the number of records behind it cannot be judged.

6. **A column that defines the label is disclosed when it is also an input.**
   `SLA_Target_Hours` is knowable before the work, so predicting a breach from it
   is legitimate, but the model partly reconstructs the comparison that sets the
   target rather than predicting it from independent evidence. The reader is told.

7. **An unfittable target reports no score at all** — not a zero, not a default. It
   names the reason and the decision it would have supported.

## Consequences

On the Team 3 maintenance panel, with a chronological split at 2026-01-25:
`repeat_failure` reaches 0.572 balanced accuracy against a 0.500 baseline on 792
held-out records, and `sla_breach` 0.834 against 0.520 on 996. Both clear both
tests. The first is weak in absolute terms and its claim says so by carrying the
figure; the verdict machinery does not hide a 57% behind the word "useful".

Points 4 and 5 were both found by running the stage on real data and on an
adversarial fixture rather than only on a happy path, and both would have shipped
a flattering evaluation. They are covered by tests that fail if either is relaxed.

The supplied `Failure_Probability` column is excluded by the contract as derived
from outcomes, so it is not available as a baseline. Comparing against it would be
a separate, legitimate question, and would need its timing established first.
