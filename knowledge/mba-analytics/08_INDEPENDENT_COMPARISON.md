# Independent Miyaar analysis and team comparison — المقارنة المستقلة

## Purpose and present status

The user wants Miyaar to provide an independent agentic analytics and decision-support path alongside the team's work. Team deliverables are comparison artifacts, not ground truth. Attachment reconciliation and empirical results belong to a separate review. This knowledge task did not recompute its metrics or inspect those attachments; the public collection publishes methodological safeguards, not private analysis results.

The method-selection dialogue, separate model evaluation, staged approvals and verification principles are grounded in [S007](SOURCE_INDEX.md#s007), pp141–148,160–164; [S040](SOURCE_INDEX.md#s040), pp13–19; [S041](SOURCE_INDEX.md#s041), pp7–19; and [S042](SOURCE_INDEX.md#s042), pp3,10–11. The checklist below is our proposed implementation of those principles for the user's comparison.

## Before interpreting team results

- [ ] Receive the other task's verified attachment identities, versions, schema, requirements and access/rights boundaries. Do not assume matching filenames imply matching data.
- [ ] Define the business question, decision owner, observation grain, time horizon, units, relevant population and constraints.
- [ ] Freeze the authorized dataset snapshot and preserve originals. Record all transformations and unresolved data issues.
- [ ] Predefine the independent calculation and method plan. Record baseline methods, validation design, relevant error costs and reasons to reject unsupported methods.
- [ ] Keep the team's claimed outcomes out of method/threshold selection as far as practicable. If they were already seen, disclose that exposure.

## Analytical execution checklist

- [ ] Recompute descriptive metrics from the dataset using deterministic, inspectable calculations; check joins, denominators, missingness and totals.
- [ ] Separate diagnostic associations from causal conclusions. Record alternative explanations and limitations.
- [ ] Apply the [prediction gate](03_METHOD_SELECTION.md#proposed-prediction-gate): confirmed label lineage, usable predictors, credible split, baseline and evaluation.
- [ ] Apply [leakage controls](04_VALIDATION_UNCERTAINTY.md#proposed-leakage-controls--تسرب-البيانات); investigate precomputed risk/priority/probability columns.
- [ ] Pursue prescriptions only with explicit actions, objective, constraints and evidence. Verify feasibility and sensitivity; label provisional rules honestly.
- [ ] Preserve failed checks, rejected models and negative findings. Do not hide them to make the independent route appear successful.
- [ ] Record which calculations actually ran. Record LLM reasoning separately if it is authorized and actually executed; do not substitute narrative for computation.
- [ ] Complete a separately evidenced review of material claims. If no independent reviewer ran, state that plainly.

## Comparison and discrepancy handling

Freeze the independent findings before comparison. Reconcile definitions, input versions, filters, rounding and reporting periods first. Then compare methods, validation, uncertainty, recommendations and presentation. Equality alone does not prove correctness; disagreement alone does not prove either side is wrong.

| Discrepancy record field | Meaning |
|---|---|
| ID and claim | Stable reference to the disputed metric or interpretation |
| Team artifact locator | File/version, page/slide/chart/table and stated value or claim |
| Miyaar evidence locator | Input hash, calculation/result ID, method and observed value |
| Common scope | Population, grain, period, units, filters and denominator |
| Difference | Numeric delta where meaningful, or a precise conceptual difference |
| Possible cause | Definition, data version, aggregation, method, rounding, leakage or unsupported inference |
| Review | Recalculation performed, evidence examined and unresolved alternatives |
| Resolution | Corrected, definition difference accepted, or unresolved; owner and rationale |

Do not choose the team's number as the expected answer. Do not tune a model or suppress a valid discrepancy to match the report, Power BI or presentation. A material unresolved difference remains visible to the human decision owner.

## Final acceptance and required versus optional outputs

- [ ] Every material claim maps to a calculation, source citation, explicit assumption or labelled reasoning step.
- [ ] Observed facts, predictions, scenarios and proposed actions are visually and verbally distinct.
- [ ] The required report (PDF), presentation (PPTX) and dashboard (PBIX), plus any optional motion-video script, share the same approved claim registry and snapshot.
- [ ] Actual deterministic execution, actual LLM runs, independent review and human approval are separately documented.
- [ ] Rights/privacy review covers outputs, screenshots, tooltips, notes and narration; no public publication or external model transfer is presumed.
- [ ] Human approval identifies the exact final artifact hashes, accepted limitations and unresolved discrepancies.

## Proposed claim registry template

```text
claim_id:
claim_text:
claim_type: observed | calculated | predictive | scenario | proposed_action
input_snapshot_hashes:
source_or_calculation_locator:
population_grain_period_units:
method_and_parameters:
validation_and_baseline:
assumptions_and_uncertainty:
actual_execution_record:
llm_reasoning_record_if_authorized:
independent_review_record:
team_comparison_and_discrepancy_ids:
human_approval_record:
output_artifact_hashes:
```

This is a proposed evidence schema, not an assertion that the canonical repository already implements every field. See [integration notes](README.md#retrieval-and-execution-boundary) for the conventions actually inspected.

## Review-informed comparison safeguards

A separate empirical review supplied during curation motivates the following checks. They are proposed general safeguards, not calculations performed by this knowledge task, and no private records or project result tables are reproduced here.

- Distinguish lower observation density from an incomplete calendar period; inspect distinct periods before calling a year partial.
- Compare a same-record classifier with both a simple baseline and any existing priority score. Improvement over the simple baseline alone does not establish incremental discrimination.
- Do not relabel same-record high-loss classification as future asset-failure prediction.
- Confirm that an asset identifier represents a consistent entity across time and class before treating records as a longitudinal panel.
- Report scenario savings as conditional estimates, never achieved savings without outcome evidence.
- Keep required PBIX/PPTX/PDF delivery separate from an optional motion video. Record the requirements source and its review status.
