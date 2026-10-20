# Rounding is not a reconciliation failure

- Status: accepted
- Date: 2026-10-20
- Changes the validator's `group_totals_reconcile` check in
  `server/analytics.py`. No other stage changes.

## Problem

The capstone dataset was put through the governed pipeline here for the first
time: 5,000 rows, 60 columns, the `maintenance` profile, no column mapping. The
run advanced through all 23 stages and was then **rejected**, with the reporter
and the publish stage skipped. One check had failed:

```
FAIL group_totals_reconcile :: Σ(groups)=40,161.05 vs total=40,161.27
```

The arithmetic was correct. The preparer rounds each group total to two decimals
for display and rounds the overall total once, so with an unmapped breakdown on
`Record_ID` — 5,000 groups of one row each — the rounded group totals fell
0.22 short of the total. The check compared those two rounded figures against a
flat `< 0.01`, so it was certain to fail on any breakdown with more than a
handful of groups. A difference of 5.5 parts per million rejected a whole
analysis, which is the opposite of what the check is for: it exists to catch a
total that the parts cannot reach, and instead it caught two-decimal display
rounding.

Worth naming plainly: no test caught this because no test ran a breakdown with
more than a few groups, and the defect is invisible on the tidy fixtures the
suite uses.

## Decision

A parallel session reached the same defect from its own review and removed the
cause at its source in commit `1dd73ae`: the preparer no longer rounds a group
total or the overall total at all, summing each with `math.fsum` and leaving
rounding to whatever formats a figure for a reader. That is the better half of
the fix and it is theirs; evidence should carry the precision of its source.
The reproduction above is from before that commit.

This record keeps the other half, which that change does not provide: the
validator recomputes the group totals from the rows instead of adding up the
preparer's own figures, and then checks three things:

- its unrounded sum reaches the total, within `0.01`;
- every published group figure is within half a cent of its recomputation;
- the set of groups is the same on both sides.

Recomputation is what an independent check should have been doing anyway. The
stage's docstring already says "independent deterministic verification"; adding
up numbers the preparer published and comparing them with another number the
preparer published was not that.

**Rejected: widening the tolerance with the group count.** The first fix made
the allowance `0.01 + 0.005 × groups`, which is the correct bound for per-group
rounding and was measured passing. At 5,000 groups it allows ±25.01, so a
genuine mis-sum of 25 units in a total of 40,161 would have passed as rounding.
A check that grows slack with the size of the data is a check that stops
working exactly where the data gets interesting, so it was replaced rather than
shipped. With the rounding gone from the preparer, the tolerances here stay
fixed: a cent on the sum, half a cent on any one group.

## What this is worth, measured

`tests/test_analytics.py` gains a `GroupReconciliationTestCase` of four tests,
and every one was watched failing before the code that makes it pass:

- 300 groups reconcile, and the test states the arithmetic both ways: the
  published figures reach the total to six places, while rounding each of them
  first falls 0.60 short — which is what the rejected runs were rejected for.
  Against the original flat cent this test errored rather than failed, because
  the run was rejected and the validator's output was never recorded in the run
  context;
- a total 50.00 away from the rows is still rejected;
- a total **0.50** away from the rows is still rejected — this is the test the
  rejected widened tolerance failed, and the reason it was rejected;
- moving one unit from one group to another, which leaves the sum intact, is
  caught by the per-group comparison.

Measured on this workspace after the change and after merging the parallel
session's work, in the project venv: `tests.test_analytics` **78 tests**,
`tests.test_metrics` 32, `tests.test_stages`, `tests.test_maintenance` and
`tests.test_docs` alongside them for **183 together**, and `tests.test_joins`
46 with 10 skipped for want of PostgreSQL — all passing. The full suite result for this session is recorded in
[README testing](../../README.md#testing).

Re-run live against the same 5,000-row dataset through the API, the run that
was rejected now reaches `awaiting_approval` with 41 claims, and the check
reads:

```
RECONCILE: True | Σ(groups)=40,161.27 vs total=40,161.27; recomputed 5000
group total(s), largest difference from the published figure 0.0000
```

## Consequences

- A high-cardinality breakdown no longer fails validation for rounding, so the
  unmapped first run of a wide table reaches a human instead of a rejection.
  Commit `1dd73ae` is what makes that true; this record makes the check
  independent as well as correct.
- The check is now stricter than it was, not looser: it compares unrounded sums
  at one cent and each published group figure at half a cent, and it notices a
  group that the rows do not support even when the total still adds up.
- The validator now walks the rows once more per run. At the 50,000-row dataset
  limit that is one pass over one column, which is small beside the stages that
  precede it, and it was not measured separately.
- Rejecting a run remains the right behaviour when the parts genuinely do not
  reach the total. Nothing here makes the validator lenient; it makes it
  independent.
- `Record_ID` being chosen as the breakdown at all is a separate defect, in the
  preparer's fallback detection, and is not addressed here.
