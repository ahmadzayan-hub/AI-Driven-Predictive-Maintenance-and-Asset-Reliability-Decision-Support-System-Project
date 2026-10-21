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

## Held-out result, memo F (21 October)

Memo F was written afterwards by an independent agent that saw neither
these instructions nor memo E: a metro's station and line-side assets, 9
`domain_method` defects (series reliability averaged, repair time used as
restoration time, a hidden failure losing its failure-finding task,
common cause in a standby pair, a survey interval longer than the P-F
interval, a Weibull shape misread, safety defects deferred to meet a
backlog target, condition monitoring ranked by cost, MTBF read as life),
3 controls and 11 decoys. Committed before any review.

| Run | Planted paragraphs found | `domain_method` in category | False alarms |
| --- | --- | --- | --- |
| v2, controlled | 11 of 12 (missed P16, monitoring ranked by cost) | 0 of 9 (no such category) | 0 |
| v3, controlled | 12 of 12 | 9 of 9 | 0 |
| v3, the subagent as loaded (confirmed by its list of checks) | 12 of 12 | 9 of 9 | 0 |

Repeat runs, same day: two more of the loaded subagent, one more controlled
run of each version.

| Version | Runs | Planted paragraphs found, each run | `domain_method` in category | False alarms |
| --- | --- | --- | --- | --- |
| v3 (3 loaded, 2 controlled) | 5 | 12 of 12 in all 5 | 9 of 9 in all 5 | 0 in all 5 |
| v2 (controlled) | 2 | 11 of 12 in both; P16 missed both times | 0 of 9 (no such category) | 0 |

The result is stable across runs on F: v3 never missed a planted paragraph
or raised a false alarm, and v2 missed the same paragraph twice. The figures
auditor's repeat raised the same single false alarm (P15, the correct
run-to-failure decision); with the analytics reviewer, the team scored 100%
recall and 92% precision. Five runs on one memo is still one memo.

The honest reading: on F, v2 already saw 8 of the 9 method errors and
filed them under other labels; v3 adds the category and caught one more.
Most of the lane-recall gap (25% against 100%) is the label, not the
judgement. The figures auditor raised one false alarm, on the correct
run-to-failure decoy (P15).

## Addendum: clock times and longer numbers in the checker

The auditor's run on F showed the checker's coverage pass reporting figures
as present when they were not: "05:00" was read as a rounded 4.9, and a
count of 5 was found inside "5.2". A time of day is now not a figure, and a
register value is not matched inside a longer number. Benchmark scores do
not change (they use the sourcing and arithmetic passes); on F, coverage now
correctly reports 4.9 as missing, and three counts the memo writes in words
("five", "two") as missing too, since the checker does not read number words.

## Verification

`tests/test_evals.py`: the points test (a correct gain in points, a correct
small rise, and a relative fall written as points) was watched failing
before the change. Scores: `python scripts/score_review.py --summary`.
