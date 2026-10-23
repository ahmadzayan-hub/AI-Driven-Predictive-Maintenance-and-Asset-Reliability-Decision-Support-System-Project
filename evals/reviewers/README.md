# Reviewer benchmark

Synthetic memos with planted defects, for measuring the review loop's reviewers (ADR 0027). Nothing here is real data.

| Memo | Subject | Paragraphs | Defects | Role |
| --- | --- | --- | --- | --- |
| `A/` | A retail chain's year | 16 | 10 | Dev: its misses chose the fixes |
| `B/` | A light-rail fleet's year | 14 | 9 | Held out. The same author wrote A and B |
| `C/` | An outpatient department's year | 15 | 9 | Blind: an independent agent wrote it from the category definitions only |
| `D/` | A metro line's signalling and telecom maintenance | 30 | 14 | Blind and harder: subtler defects (soft causal verbs, a percentage-point slip, a wrong base) and 10 correct decoy paragraphs; `labels.json` also lists the decoys and why each defect is wrong |
| `E/` | A light-rail fleet's rolling stock and depot equipment | 26 | 12 | Blind, maintenance judgement: 9 `domain_method` defects where every figure is sourced and every sum holds, 3 ordinary controls, 11 decoys. Dev for the reviewer's check 7 since it was written from E's misses |
| `F/` | A metro's station and line-side assets | 27 | 12 | Blind, held out for check 7: written by an independent agent that saw neither the reviewer's instructions nor memo E; 9 `domain_method` defects, at least 4 of kinds E does not have (series reliability averaged, hidden failure without a failure-finding task, common-cause in a standby pair, survey interval longer than the P-F interval, Weibull shape misread, criticality by cost, MTBF read as life, safety defects deferred to meet a backlog target), 3 controls, 11 decoys |

Each folder holds the memo (`memo.md`, paragraphs `[P01]`…), the register a figure must come from (`register.csv`, columns `Check` and `Expected`), and the labels (`labels.json`). The labels give one category per defective paragraph:

- `unsourced_figure`
- `arithmetic`
- `causal_claim`
- `denominator`
- `overclaim`
- `domain_method` (memo E on): a reliability or maintenance method misapplied, such as the wrong availability basis, an MTBF that leaves out surviving units, early failures read as wear-out, or run-to-failure on a safety item. It is in the analytics reviewer's lane.

## Runs

A run is a reviewer's reply, saved as `runs/<reviewer>-<memo>-<tag>.txt`. The reviewer is `figures-auditor`, `analytics-expert-reviewer` or `figures-tool` (the Tier 0 checker). Tags:

- `named-v1`, `named-repeat`, `named-newtool`, `named-v3`: the project subagent as the session loaded it, in its first run, a repeat run, a run after the checker changed, and a run with its v3 instructions loaded.
- `ctl-v1`, `ctl-v2`, `ctl-v3`: a general-purpose agent on the reviewer's model, given the v1, v2 or v3 instructions, with everything else the same. This is the controlled comparison, because a subagent's edited instructions only load in a new session.
- `v1` to `v6`: the checker after each round of fixes (v5 reads percentage points; v6 ignores clock times and longer numbers in coverage).

Each run is told to put the paragraph id on the FINDING line and add a `Category:` line, and to open only the memo and its register.

```bash
python scripts/score_review.py --summary [--json evals/reviewers/summary.json]
python scripts/score_review.py --bench evals/reviewers/C --findings reply.txt --categories causal_claim,denominator,overclaim
python scripts/score_review.py --bench evals/reviewers/C --figures-tool --categories unsourced_figure,arithmetic
```

To add a memo, have an agent that has not seen these write it from the category definitions, then recompute its register and labels before use. Never change a label after seeing a reviewer's results.
