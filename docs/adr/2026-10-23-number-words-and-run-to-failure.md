# The checker reads counts in words; run-to-failure is judged on both sides

- Status: accepted
- Date: 2026-10-23
- Extends ADR 0027 (agents are measured) and
  `2026-10-21-reviewer-maintenance-method-check.md` (check 7).
- Closes progress board Next item 4, parts "number words in the checker's
  coverage" and "the auditor's false alarm on correct run-to-failure". The
  second held-out maintenance memo stays open.

## Problem

1. **Number words.** `scripts/figures_check.py` read digits only. On memo F
   its coverage pass reported three register values as missing although the
   memo carries them in words: "five interchange stations", "the five months
   since renewal" and "two rectifiers" (Interchange stations 5, Months since
   renewal 5, Rectifiers per substation 2).
2. **Run-to-failure false alarm.** In both saved runs on memo F
   (`runs/figures-auditor-F-named-v1.txt` F09 and `-named-repeat.txt` F16),
   the figures-auditor filed P15 as an `overclaim`, quoting "'No safety or
   operational consequence' unsupported". P15 is a labelled decoy: decorative
   concourse light fittings move to replacement on failure; they have no
   safety function, a failure is visible on the daily walk-round, and
   emergency lighting is a separate, tested system. The finding contains no
   figure. The auditor's step 6 invites a separate `overclaim` finding, and
   nothing in its instructions says that a stated consequence of failure is a
   maintenance-method question. The analytics reviewer did not raise it in any
   run, but its check 7 stated only the defect side ("run-to-failure on a
   safety item is a defect"), and did not name hidden failures at all.

## Decision

1. **The checker reads counts written in words**, in English (zero to
   ninety-nine, hyphenated or spaced compounds, "hundred", "a thousand",
   "and" inside a number, "million" and "billion" as scales) and Arabic
   (masculine and feminine units, 11 to 19, the tens in both cases, the two
   spellings of a hundred, joined hundreds such as ثلاثمئة, the duals, ألف and
   آلاف, and a leading و). A word figure is a token like a digit one: in
   coverage it must equal the register value exactly ("five" is never a
   rounded 4.9) and is reported "(in words)"; in sourcing, a count up to 31
   or a year is a label, as in digits, and a larger figure must be sourced.
   Left out on purpose: ordinals (they rank, and "second" is a unit of time),
   fractions ("two-thirds", "خمس السكان" before a definite noun), vague plurals
   ("hundreds of"), ratios ("one in five"), and "one" as a pronoun or idiom
   ("one of the", "a one-off", "no one", "the new one is", "كل واحد").
2. **Check 7 names both sides of a run-to-failure decision.** A hidden
   failure (one that shows only on demand) needs a failure-finding task, like
   a safety item. Run-to-failure on an item with no safety function whose
   failure is evident in normal duties, with any nearby safety function
   carried by a separate tested system, is correct, and so is the memo's
   statement of that consequence.
3. **The figures-auditor leaves maintenance method to check 7.** A statement
   with no figure in it about an asset's design or the consequence of its
   failure is not an `overclaim` for the auditor to file. One bullet added to
   step 6; its lane and its other steps are unchanged.

## Evidence

Figures tool, `python scripts/score_review.py --bench evals/reviewers/<X>
--figures-tool`, in its lane (`unsourced_figure`, `arithmetic`), before (v6)
and after (v7); the runs are saved as `runs/figures-tool-<X>-v7.txt` and are
identical to v6 on every memo. Coverage is the plain checker run on the memo
and its register.

| Memo | Lane recall v6 → v7 | Detection precision | False alarms | Coverage v6 → v7 |
| --- | --- | --- | --- | --- |
| A | 100% → 100% | 100% → 100% | 0 → 0 | 10/10 → 10/10 |
| B | 100% → 100% | 100% → 100% | 0 → 0 | 9/9 → 9/9 |
| C | 75% → 75% | 100% → 100% | 0 → 0 | 10/11 → 10/11 |
| D | 100% → 100% | 100% → 100% | 0 → 0 | 73/90 → 73/90 |
| E | no lane defects | – | 0 → 0 | 122/129 → 122/129 |
| F | no lane defects | – | 0 → 0 | 158/168 → 161/168 |

On F the three counts in words are now found; the seven values still missing
are the "correct method" figures the memo is meant to lack and the "01:00 to
05:00" window. No label was changed.

The instruction change is **not measured**. Edited subagent instructions load
only in a new session, so the auditor's P15 false alarm and check 7's
behaviour on the decoys need a controlled (`ctl`) run of each instruction
text on memos E and F, and a run of the subagents as loaded in the next
session, before anything is claimed.

## Limits

- Memo F is now dev data for the auditor's run-to-failure bullet, and the
  checker's number words were chosen after seeing F's coverage. The unit
  tests use fresh sentences.
- Arabic is read without diacritics; a number written with harakat is split
  into pieces and not read. Spelled-out decimals ("four point nine") and
  "dozen" are not read.
- A number word in a label ("three-phase") is read as a count, as "3-phase"
  would be.

## Verification

`tests/test_evals.py`: three new tests (English counts, words that are not
counts, Arabic counts) were watched failing on the previous checker.
`tests/test_agent_team.py`: one test that check 7 names hidden and evident
failure and that the auditor leaves method to it, watched failing on the
previous instructions.
