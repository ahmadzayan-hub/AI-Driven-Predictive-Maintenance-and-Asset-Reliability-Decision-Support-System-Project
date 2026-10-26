# Planning probability and forecast-state wording

Date: 2026-10-24. Status: Proposed for review; not activated locally.

## Context

Source inspection confirmed two contradictions in generated report prose.
The observational planning paragraph described effects below the computed
80%-power threshold as invisible. That threshold describes a probability
under the planning assumptions, not an absolute limit on detection.
The combined report also always described a forecast extending the historical
pattern, including when the predictive stage refused to produce a forecast.

An earlier counter-direction example did not reproduce in the current saved
result: the cited group change and overall change had opposite signs. The
existing sign predicate and contribution evidence remain unchanged.

## Decision

- Explain the existing planning threshold as detecting a true effect of that
  size about four times in five under the stated assumptions. Smaller effects
  may still be detected, with lower probability. This clarifies the absolute
  wording in ADR 0010; it does not change power arithmetic or planning inputs.
- Select the combined report's forecast limitation from the actual forecast
  result. A nonempty forecast retains its historical-pattern assumptions.
  An empty forecast states that no forecast was produced and directs readers
  to the predictive limitation. Insufficient history and unequal coverage
  remain distinct reasons in that section.
- Apply both changes in English and Arabic. Preserve calculations, evidence
  identifiers, validators, uncertainty, approval and publication gates.
- Existing stored reports remain immutable. These changes affect newly
  generated reports only after a reviewed source update; they do not silently
  rewrite a previous draft or approved output.

## Verification and limits

Synthetic regressions independently recompute the existing planning threshold,
check probabilistic wording in both languages, and cover insufficient history,
unequal coverage and a forecast that is actually produced. Existing experiment,
period-coverage and report-language tests are also exercised. The session log
records the commands; private runtime evidence remains outside the repository.

Full hosted verification and independent review are still required. No live
source replacement, report approval, model invocation, dependency change or
production deployment is part of this correction.
