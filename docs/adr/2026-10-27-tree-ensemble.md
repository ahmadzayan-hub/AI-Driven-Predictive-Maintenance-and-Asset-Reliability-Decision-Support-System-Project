# A tree ensemble: threshold rules, scored against the average and the line

Date: 2026-10-27 · Status: Accepted (the "trees and ensembles" item of the
modelling row in the 16 October code audit, `project-progress.md`; the
slice after `2026-10-27-fiscal-year.md`). Amends ADR 0033, whose "not
done" list named it.

## Context

The regression of ADR 0033 fits a straight line. Maintenance data is full
of thresholds: a failure rate that jumps past an age, a cost that steps
with a site. A line averages such steps away and reports a weak model
where a rule would have found a strong one. Trees find thresholds, and
ADR 0033 left them out only because they needed care to do in the
standard library within a run's time.

## Decision

1. **A fifth model plugin, `TreeModel` (`tree_model`)**, on the `models`
   profile after the sensitivity stage like the others, written to the
   ADR 0020 contract in `server/modelling.py`. It is a bagged ensemble of
   regression trees: 16 trees, depth at most 4, leaves of at least 5
   records, each split chosen by variance reduction over about the square
   root of the inputs and at most 8 candidate thresholds per input, each
   tree on a bootstrap sample of at most 1,500 evenly spaced training
   records. The settings are fixed and stated; nothing is tuned on the
   held-out data.
2. **The same inputs, split and baseline as the regression**: the other
   measures and up to three text columns as indicators, the screen for
   leaked inputs, the chronological or every-fifth split, the average error
   on held-out records against always guessing the training average, and
   the 5% rule to beat it.
3. **And the straight line as a second comparison.** The least-squares
   model of ADR 0033 is fitted on the same training records and scored on
   the same held-out ones; the card and a fact claim say whether the rules
   beat it (so the relationship has thresholds a line misses) or not (so
   the line describes it as well and is easier to read). This is the
   question a reader has: not "are trees good" but "do they add anything".
4. **What the trees lean on** is reported as each input's share of the
   explained variance across all splits, the top five, and the strongest
   is named as an association, never a cause.
5. **The card** has kind `trees` and carries the tree count, depth, leaf
   count, the straight line's error and the improvement over it. The Runs
   view renders it with the existing card, verdict first; no new strings.

## Consequences

- `tests/test_modelling.py`: `TreeTests` (a threshold relationship beats
  the average and the line with the right input first; a straight
  relationship beats the average but says the line is as good; noise is
  weak; too few records is a limitation; the arithmetic of one tree and a
  small forest) and the governed models run now lists the `trees` card and
  still passes validation in both languages.
- A `models` run takes about a tenth of a second longer on 400 records.
- Not done: classification trees, gradient boosting, choosing inputs by
  when they were recorded, and any tuning beyond the fixed settings.
