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
| `H/` | A depot reliability review against a written brief (`brief.md`) | 20 | 8 | Blind, for the brief-compliance reviewer (assessment G9): a false word count, a scope paragraph without its period and count, an average of rates, a risk without likelihood or impact, a recommendation without an objective, one without owner or date, a cost total without its treatment, no uncertainty statement; 7 decoys. No register: the lane is requirement compliance |
| `I/` | A change packet for a public repository | 18 | 8 | Blind, for the security-privacy reviewer (G9): a committed demo credential, course registration numbers, dataset rows in a model prompt, shell injection, path traversal, a force-push, HTML injection, routine deploys without permission; 10 decoys that do the same things correctly. No register |
| `J/` | An interface change packet | 16 | 8 | Blind, for the accessibility and parity reviewer (G9): an image without alt text, an English-only string with its parity test skipped, a keyboard trap, 18 px targets, a percent sign on the wrong side in Arabic, a 400 px drawer at 320 px, an untranslated control, 2.7:1 text contrast; 8 decoys. No register |
| `G/` | A tramway's infrastructure assets | 28 | 12 | Blind, second held out for check 7: written by an independent agent with no access to the repository, the reviewer's instructions or any earlier memo; 9 `domain_method` defects (MTBF ignoring units that did not fail, early failures read as wear-out, replacing a constant-hazard part, calendar-hour availability, an inspection interval longer than the P-F interval, a common-cause pair treated as independent, active repair used as downtime, series reliability averaged, run-to-failure on a hidden-failure safety item), 3 controls, 11 decoys including a correct run-to-failure |

Each folder holds the memo (`memo.md`, paragraphs `[P01]`…), the register a figure must come from (`register.csv`, columns `Check` and `Expected`), and the labels (`labels.json`). The labels give one category per defective paragraph:

- `unsourced_figure`
- `arithmetic`
- `causal_claim`
- `denominator`
- `overclaim`
- `domain_method` (memo E on): a reliability or maintenance method misapplied, such as the wrong availability basis, an MTBF that leaves out surviving units, early failures read as wear-out, or run-to-failure on a safety item. It is in the analytics reviewer's lane.

Memos H, I and J carry their own categories, one lane each, named in `scripts/score_review.py` (`LANES`): the brief reviewer's `missing_evidence`, `length_or_order`, `missing_element`, `standards_gap` and `method`; the security reviewer's `secret`, `personal_data`, `raw_data_to_model`, `unsafe_input` and `soul_rule`; the accessibility reviewer's `alt_text`, `translation_parity`, `keyboard`, `target_size`, `rtl_order`, `overflow` and `contrast`. Their `labels.json` also records why each planted hunk is wrong and which paragraphs are decoys.

## Runs

A run is a reviewer's reply, saved as `runs/<reviewer>-<memo>-<tag>.txt`. The reviewer is `figures-auditor`, `analytics-expert-reviewer`, `figures-tool` (the Tier 0 checker), or, from 23 October, `brief-compliance-reviewer`, `security-privacy-reviewer` or `accessibility-i18n-reviewer`. Tags:

- `named-v1`, `named-repeat`, `named-newtool`, `named-v3`: the project subagent as the session loaded it, in its first run, a repeat run, a run after the checker changed, and a run with its v3 instructions loaded.
- `ctl-v1`, `ctl-v2`, `ctl-v3`: a general-purpose agent on the reviewer's model, given the v1, v2 or v3 instructions, with everything else the same. This is the controlled comparison, because a subagent's edited instructions only load in a new session.
- `v1` to `v7`: the checker after each round of fixes (v5 reads percentage points; v6 ignores clock times and longer numbers in coverage; v7 reads counts written in English and Arabic words).

- `ctl-v4`, `ctl-v4-repeat` (figures-auditor, memo F, 2026-10-23): a general-purpose agent given the auditor instructions with the step-6 bullet that leaves a stated failure consequence to check 7. The saved file keeps each FINDING and Category line; the reasoning lines are shortened. Memo F is dev data for that bullet, since its false alarm chose the fix.
- `named-v3-r1` to `named-v3-r3` (analytics reviewer, memo G): three runs of the subagent as this session loaded it, on the second held-out memo.

Each run is told to put the paragraph id on the FINDING line and add a `Category:` line, and to open only the memo and its register.

```bash
python scripts/score_review.py --summary [--json evals/reviewers/summary.json]
python scripts/score_review.py --bench evals/reviewers/C --findings reply.txt --categories causal_claim,denominator,overclaim
python scripts/score_review.py --bench evals/reviewers/C --figures-tool --categories unsourced_figure,arithmetic
```

To add a memo, have an agent that has not seen these write it from the category definitions, then recompute its register and labels before use. Never change a label after seeing a reviewer's results.

## First runs of the three lane reviewers (23 October 2026, assessment G9)

Each reviewer ran once as the loaded subagent on its own blind memo, told to open only the memo (and the brief for H), and its reply was saved verbatim before scoring. Floors in `evals/floors.json` are these scores, rounded down.

| Reviewer | Memo | Lane recall | Detection recall / precision | False alarms | Notes |
| --- | --- | --- | --- | --- | --- |
| `brief-compliance-reviewer` | H | 75% (6 of 8) | 75% / 75% | 2 | Missed the false word count in the summary (P02) and placed the missing uncertainty statement on the appendix body (P20) where the label has the appendix heading (P19), which counts as a miss and a false alarm. Its other false alarm was the title line, which carries the benchmark tag "(synthetic benchmark H)" the brief's requirement 11 forbids: a fair reading of the memo as written, kept as recorded. Two secondary findings (uncited figures on defective paragraphs) were right. |
| `security-privacy-reviewer` | I | 100% (8 of 8) | 100% / 89% | 1 | Every planted hunk found in category, with rotation named for the committed credential. The one false alarm is a block it wrote on the correct `private/` hunk while saying no finding was needed; the scorer counts a FINDING block as a finding. |
| `accessibility-i18n-reviewer` | J | 100% (8 of 8) | 100% / 100% | 0 | Every planted hunk found in category with no false alarm, citing the WCAG criteria. |

Each memo was written once, labelled before the run, and is now dev data for its reviewer: a change to a reviewer's instructions needs a fresh blind memo to be measured on.

