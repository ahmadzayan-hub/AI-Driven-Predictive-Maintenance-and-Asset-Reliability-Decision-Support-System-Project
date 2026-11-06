# Classification trees beside naive Bayes

Date: 2026-11-06 · Status: Accepted · Owner request: "Continue next developments till complete the platform"; the gap analysis listed classification trees

## Context

The classification stage fits naive Bayes, which weighs each input on its own. A class set
by two readings together (an alarm when both are high, or both low) is a threshold rule it
cannot represent.

## Decision

1. The classification stage also fits 16 bagged classification trees (Gini splits, depth
   at most 4, leaves of at least 5 records, about the square root of the inputs tried at
   each split, a fixed seed) on the same training records, at most 1,500 evenly spaced.
2. Both models are scored on the same held-out records with the same balanced accuracy and
   the same baseline (always the most common training class). A cited fact states the
   trees' score and improvement and says both models were set in advance and neither was
   chosen by these scores. The model card keeps naive Bayes as the stage's model and adds
   `details.trees` with `chosen_by_test: false`.
3. Votes that tie are broken by class name, never by chance, so a re-run gives the same
   result.

## Consequences

- Test: on a two-threshold class the trees score above 85% and beat naive Bayes by more than
  20 points; on noise they improve little; the claim and the card say they were not chosen
  by the test.
- Not done: boosting; tuning; a separate model card per model.
- Not adopted: filling gaps along time with estimated values. Filled values would enter
  measured KPIs as if observed; the platform keeps reporting gaps instead (see the data
  health record of 31 October).
