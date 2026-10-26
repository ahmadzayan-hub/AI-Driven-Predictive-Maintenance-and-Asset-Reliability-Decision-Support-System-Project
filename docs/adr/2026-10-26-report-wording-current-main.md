# Probability and forecast validity on current main

Date: 2026-10-26. Status: Review candidate, no merge or deployment approved.

## Context

PR #63 was based on an older main. Integrate main `9fa13b4240c64be78669ed09b630ad5929ea26d4`
into its existing review branch, preserving both histories and both session logs.
This extends the 24 October wording decision; it does not change calculations.

## Decision

- Retain the approximate normal planning formula, two-sided five-percent
  significance and eighty-percent power. Describe a probability of detecting
  a true effect under the assumptions, not an absolute detection limit or the
  probability that a particular observed finding is true. Keep the method
  calculation and evidence identifiers stable.
- Distinguish an absent forecast, a produced projection without a usable
  backtest error, and a forecast with a measured error. Zero error is measured,
  not missing. Historical error never guarantees future accuracy.
- Preserve the existing four-period forecast and six-period backtest rules.
  Meeting the first threshold does not establish accuracy. Explain the actual
  reason for unmeasured error: short history or zero actual values throughout
  the selected holdout. Do not label the latter as insufficient history.
- Preserve all numbers, input snapshots, evidence references, validators,
  human approval and storage logic. No migration or rewrite of saved reports.
- Disable automatic Vercel deployment for this exact review branch in
  `vercel.json` before updating it, because the owner's permission excludes
  deployment and the previous branch head had an automatic Vercel status.
  Main's existing disabled setting and every other branch setting remain intact.

## Verification

Synthetic bilingual boundary tests cover the planning-power curve, unsupported
thresholds, short/absent history, unequal coverage, a dropped low-coverage tail,
rates, unmeasured projections, zero holdout values and zero measured error.
Compare every calculation and forecast against the current main on the same
synthetic inputs. Reopen main-generated draft and approved synthetic runs with
the candidate, create new runs, and compare persisted-record and note hashes.
Counts and actual execution limits belong in README's testing section.

## Boundaries and sources

The normal planning approximation is not an exact small-sample t-test guarantee.
Repeated observations of the same asset may violate independence. This change
does not calibrate a live forecasting model, measure causal effects, establish
calendar completeness or certify railway safety. Synthetic storage verification
does not assert access to the owner's live database.

- NIST, [statistical power](https://www.nist.gov/glossary-term/44886).
- NIST, [sample sizes required](https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm):
  normal-quantile planning assumptions and unknown-variance limitations. The
  implementation's two independent equal-size groups give variance `2*s²/n`.
- Vercel, [Git configuration](https://vercel.com/docs/project-configuration/git-configuration):
  exact branch identifiers can disable automatic deployment.

### Subsequent owner authorization

The owner subsequently approved publication and instructed merging all open Miyaar
PRs. The earlier blocked-update record above is historical. The current integration
and exact-head verification gates are recorded in
[the integration decision](2026-10-26-approved-pr-integration.md). Deployment remains excluded.
