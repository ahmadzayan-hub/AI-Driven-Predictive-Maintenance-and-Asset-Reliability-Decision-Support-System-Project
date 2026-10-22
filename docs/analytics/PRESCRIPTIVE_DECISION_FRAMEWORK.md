# Prescriptive decision framework

Date: 22 October 2026 · Status: **Implemented** in slice three of the release
gate (`docs/adr/2026-10-22-release-gate-slice-three.md`), designed against
findings A2, A3 and A13 of the assessment. Section 1 describes the stage as
it was that morning; sections 2 to 4 are now in code (`server/analytics.py`
prescriptive and sensitivity stages, `server/runs.py`), with the departures
noted inline. Section 5 is still a proposal.

## 1. What the prescriptive stage does today

- Ranks options by an assumed uniform improvement (`PLANNING_UPLIFT = 0.10`)
  applied to each option's current total; declares the direction (better
  higher or lower) from the glossary, or ranks by size and says so.
- Includes a hold-course option and prints the assumption beside the
  recommendation. The headline reports the gain as "worth N" (A3).
- The sensitivity stage re-scores at 5%, 10% and 20% with the same uplift
  for every option, so the order cannot change (A2).
- No cost, constraint, probability of success, decision id or approver is
  recorded (A13). The approval gate binds to the report's hash.

The executive brief adds decisions with a proposed owner and gate
(`server/executive_advisory.py`), which is the right shape to build on.

## 2. The decision record (target)

One record per significant recommendation, persisted with the run and bound
to the approval that publishes it.

| Field | Source | Rule |
| --- | --- | --- |
| `decision_id` | run id plus option key | stable across re-reads of the run |
| `issue` | the finding the option answers | cites the finding id |
| `scope` | asset, site or process | from the group the option names; "whole fleet" otherwise |
| `evidence` | calculation ids | every number in the record cites one |
| `risk` | the observed exposure (downtime, cost, overdue) with its population | observed, never a probability unless a model card supports it |
| `alternatives` | every option scored, including hold course | each with its own uplift range and cost |
| `expected_impact` | per option, under the stated uplift range | labelled illustrative until an uplift source is given |
| `cost` | user input or source reference | "not stated" blocks the ranking by value |
| `constraints` | operational, engineering, financial, safety | free text with a named owner |
| `uncertainty` | the flip points: the uplift or cost at which the ranking changes | from the sensitivity stage once it varies per option |
| `recommended_action` | the best-supported alternative | withheld when no direction or no cost is known |
| `approval` | the approver's subject, decision and time | written by the approval gate, never by a stage; the run detail composes it from the approval row |
| `recommendation_basis` | `value`, `size_no_direction` or `size_no_cost` | added in code: says why `recommended_action` is empty when it is |
| `audit` | run id, dataset snapshot hash, analysis version, report hash | from the run |

## 3. Rules

1. The gain is labelled "illustrative at an assumed X% change" in the
   headline and the table until the uplift comes from an input or a cited
   source.
2. Sensitivity varies per-option uplift and cost ranges and reports the flip
   points; "stable" is only stated when no flip point lies inside the ranges.
3. A ranking by value needs a direction and a cost. Without them the stage
   ranks by size and says so, and `recommended_action` is empty. In code the
   recommendation claim and headline still name the best option by size,
   labelled as such; the record is where the distinction is binding.
4. The record is written by the prescriptive and sensitivity stages, checked by
   the validator (every figure cites a calculation), and completed by the
   approval gate. No stage can approve.
5. Nothing is executed. The record is advice for a person with the permission.

## 4. Validation

As implemented: `tests/test_analytics.py::PrescriptiveInputsTestCase` (a
stated uplift flips the order; a stated cost is netted and cited; a dominant
option is stable; the range is an input; inputs are validated in both
languages), `::DecisionRecordTestCase` (every field, every cited figure, the
Arabic section), and `tests/test_runs.py` (the record travels with the run,
the gate completes it, publishing is refused without it). The list below was
the plan.

- Property test: distinct per-option uplifts must be able to flip the order.
- Every report with a recommendation shows "illustrative" beside the gain.
- A publish request is refused without a decision record for each
  recommendation claim.
- The record's figures reconcile with the calculations they cite
  (`scripts/figures_check.py`).

## 5. Optimisation

Mathematical optimisation is not justified by the current data: there is no
cost per option, no capacity constraint and no probability of success in the
datasets the platform has seen. When a customer supplies them, a
constraint-based allocation can be added as an opt-in stage under the stage
contract (ADR 0020), with its own decision record fields.
