# Maintenance model comparisons and recommendations preserve their evidence

Date: 2026-10-20
Status: Accepted

## Context

The project assessment reproduced three maintenance evaluation defects with
synthetic inputs. Missing numeric inputs were removed from the model's held-out
cohort but remained in the grouping baseline's cohort. A perfect model was
therefore reported as improving by 100% over a rule that was also perfect on the
records the model scored. A separate fitted model scored 0.5424 against 0.5:
its card correctly said `weak`, but its verified claim still recommended sending
a senior technician because it checked only the relative improvement.

English and Arabic maintenance claims also carried different figures. Arabic
omitted the held-out record count and did not mirror the conditional acceptance
limits, so the independent bilingual validator stopped fitted Arabic runs.

The governed-run probe found a separate numerical conservation problem:
rounding every group's aggregate to two decimals before validation made valid
fractional data fail reconciliation. Diagnostic group changes had the same
premature rounding.

## Decision

- Learn categorical input eligibility and levels from training records only.
  Retain complete-input row, label and vector tuples. Fit and score the model,
  majority baseline and grouping rules on the same retained training and
  held-out cohorts. Disclose omitted counts in the model details and recheck
  that both classes survive on both sides after input exclusions.
- Keep the existing acceptance thresholds: a 5% relative improvement and at
  least 0.55 balanced accuracy. Both must pass before a claim or report supports
  an intervention. A weak model stays reportable as a limitation, and its
  report explicitly supports no decision. The card retains the target's
  intended decision as context.
- Preserve the same held-out count, scores and applicable thresholds in English
  and Arabic claims. Exercise the actual maintenance profile and independent
  validator in both languages, up to the existing human approval gate.
- Keep full floating-point evidence for prepared totals, groups, time series
  and diagnostic changes. Use `math.fsum` for aggregation and reconciliation.
  Format rounded values for readers without rounding the evidence first.
  Keep the existing reconciliation tolerance; inconsistent evidence still fails.

## Verification and limits

Regression fixtures cover mismatched missing-input cohorts, loss of a class
after exclusions, held-out categorical levels, the near-chance relative-margin
case, all bilingual claim branches and complete governed runs in both languages.
A high-cardinality fractional fixture checks totals, group shares and
contributions, plus deliberately corrupted evidence that must still fail.
Actual verification results are recorded in the session log and README.

These are evaluation and reporting corrections. They do not establish
prospective failure prediction, calibration, deployment acceptance, a verified
physical asset identity, or permission to execute maintenance actions.
