# Analytics reviewer checks maintenance method; checker reads percentage points

Date: 2026-10-21 · Status: Accepted (owner request, 21 October)

## Context

Memo E plants nine maintenance-method errors where every figure is sourced
and every sum holds. The analytics reviewer, on its v2 instructions, scored
83% and then 92% lane recall in two runs as the session loaded it. In one of
those runs it marked a safety-critical track-brake contactor moved to
run-to-failure as correct. Its instructions had no check for maintenance
method and no `domain_method` category.

Separately, the figures checker read "fell from 40.9% to 37.5%, a decline of
8.3 percentage points" (memo D) as an unsourced 8.3. The 8.3 is the relative
change (3.4 / 40.9) written as points; the gap is 3.4 points.

## Decision

1. **Reviewer check 7, maintenance and reliability method,** with a
   `domain_method` category. It covers availability basis, MTBF over the
   whole exposure, failure pattern deciding policy, measures judged on their
   own definition, spares and backlog, and one rule stated outright:
   strategy follows the consequence of failure, not the price of the part,
   so a run-to-failure decision on a braking, signalling, fire, door or
   other safety item is a defect however cheap the part.
2. **Percentage points in the checker.** A figure followed by "percentage
   points", "points", "pp" or the Arabic نقطة مئوية, in a sentence with two
   or more sourced percentages, is checked against the gap between them. If
   it matches the gap it is derived. If it matches their relative change
   instead it is an arithmetic slip, reported with the gap as the computed
   value. Otherwise it is left to the sourcing check.

## Evidence

Controlled runs: a general-purpose agent on the reviewer's model, given the
v2 or v3 instructions and nothing else different, one run each.

| Memo | v2 | v3 |
| --- | --- | --- |
| E: planted paragraphs found | 10 of 12 (missed P09 PM compliance, P18 safety contactor) | 12 of 12 |
| E: `domain_method` in the right category | 0 of 9 (no such category in v2) | 8 of 9 |
| E: false alarms on 11 decoys | 0 | 0 |
| A, B, C, D: lane recall | 100%, 80%, 100%, not run | 100%, 80%, 100%, 100% |

v3 flagged the contactor as a blocker. The one miss in category is the
alarm-count paragraph (P16), which every run on every version has called an
overclaim; the label is not changed. B's 80% is the same on every run and
version.

Checker v5 against v4: memo D lane recall 83% → 100%; A, B, C and E
unchanged, no new false alarm. The unit test uses fresh sentences, so D
stays a held-out test of the checker.

## Limits

- One controlled run per version, so the E figures are not a stable estimate.
- **Memo E is now dev data for the reviewer:** check 7 was written after
  seeing E's misses, so E no longer measures it independently. A new blind
  maintenance memo is needed for that.
- The edited subagent loads from the next session; the runs above used the
  instructions text, not the loaded subagent.
- The points rule only fires when the sentence holds both percentages.

## Verification

`tests/test_evals.py`: the points test (a correct gain in points, a correct
small rise, and a relative fall written as points) was watched failing
before the change. Scores: `python scripts/score_review.py --summary`.
