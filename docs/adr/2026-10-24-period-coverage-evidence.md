# Period coverage evidence and bounded scenario claims

Date: 2026-10-24. Status: Accepted for review; not deployed.

## Context

A real-file acceptance run on the 24 October main baseline stopped at the
validation gate. Forecast and anomaly limitations compared a lower final
period count with a larger earlier-period count, but cited only the final
count. The larger value appeared in a calculation's method text, not its
value. The validator correctly rejected both claims. No private rows are
included in this change; regressions use fabricated counts.

A second issue was methodological: comparing the final count against the
maximum over all historical periods labels a sustained lower-density regime
as an incomplete final month. Record counts alone do not establish calendar
completeness or a business performance change.

## Decision

- Preserve the figure validator. Store and cite both comparison counts as
  separate calculations. Existing claim IDs remain compatible with stored
  evidence; their wording describes lower coverage, not proven incompleteness.
- Keep the existing UNEVEN_PERIODS threshold. Exclude an isolated low-count
  tail only when it falls below that threshold relative to the minimum of
  the preceding three available periods. This remains a coverage precaution,
  not a universal missing-period detector. With absent counts, preserve the
  existing behavior rather than invent coverage evidence.
- If retained periods still have materially unequal record coverage, do not
  forecast raw totals. Request a comparable exposure or explicitly defined
  per-record target. This supersedes ADR 0026's decision to keep the forecast
  unchanged and the historical-maximum tail heuristic in
  `2026-10-23-p2-slice-one.md`. No automatic rate transformation is introduced.
- Default improvement assumptions are scenario screening, not validated
  savings or an approved intervention. Preserve numeric options and approval
  gates, but label the default claim as an assumption and use corresponding
  English/Arabic headline, narration and section wording. Explicitly supplied or mixed
  inputs are also conditional scenarios, not evidence of intervention efficacy.
  Sensitivity describes robustness of the scenario ranking, not an approved action.

## Boundaries

This does not prove future-horizon failure prediction, identify a calendar
period's completeness, estimate a causal treatment effect, execute an
optimization or approve any action. Operational deployment still needs a
prediction timing/exposure contract and validated intervention assumptions.
No provider, dependency, authentication or publication policy is changed.

## Verification

Focused tests cover cited three-digit comparison counts with tamper rejection,
a sustained lower-density year, isolated low coverage wording, bilingual
forecast refusal, continued report generation and scenario-only headings.
Existing constant-coverage and genuine sharp-tail regression behavior remains
covered. Full suite and actual application acceptance outcomes are recorded
in the session evidence; no hosted runtime or Power BI verification is claimed.

Retaining a period can change which anomaly has the largest gap. Its finding
now cites that specific gap calculation rather than the first chronological
anomaly. If outside the bounded displayed subset, the cited gap is retained
as evidence. The figure validator and privacy/model-grounding guards remain
unchanged; a longer scenario claim was shortened to keep existing built-in
notes inside their unchanged bound. Legacy Arabic evidence labels remain
supported when old calculations are re-rendered.

## Counter-direction evidence follow-up

The named counter-direction contribution may fall outside the top-five display subset. Retain its calculation and cite it alongside the total instead of citing only the total. English/Arabic regressions cover both outside and inside the subset, unique evidence IDs and rejection of tampered values. Numerical validation and approval gates remain unchanged. Independent focused tests and the reported mapping passed; combined-head hosted CI remains required.
