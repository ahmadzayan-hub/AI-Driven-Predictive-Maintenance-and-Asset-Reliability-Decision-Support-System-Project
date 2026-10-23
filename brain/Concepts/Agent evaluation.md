---
type: concept
aliases: [Confusion matrix, Recall floors, Blind holdout, Reviewer benchmark]
tags: [measurement, quality, agents]
status: active
updated: 2026-10-23
review_every_days: 30
sources: [docs/adr/0027-agents-are-measured.md, docs/adr/2026-10-20-agent-measurement-loop.md, docs/adr/2026-10-23-blind-v7-into-dev-causal-and-intent-fix.md, server/agent_learning.py, scripts/agent_loop.py, scripts/evaluate_agents.py, scripts/score_review.py, evals/floors.json, evals/reviewers/README.md, evals/reviewers/summary.json]
---

# Agent evaluation

How [[Agentic OS]] knows how often each of its agents is right: labelled synthetic cases, a confusion matrix per agent, recall floors, and holdouts written blind. It is what turns "the agent works" into a number a reader can check.

## Facts

- **Method (ADR 0027):**
    - Fixes come from dev misses only. Holdouts judge them.
    - For the text classifiers, each holdout is written blind by an independent agent from the label definitions alone, then joins dev after the round.
    - Floors in `evals/floors.json` fail the tests on any regression.
- **Overfitting shows:** chat intent scored 100% on dev and 68% on a blind set. After another round it scored 80% on a new blind set of 60 cases.
- **Blind recall on 2026-10-17 (round 5, blind set v4), before → after:**
    - intent 68% → 72%;
    - jargon 83% → 92%;
    - causal wording 69% → 69% (precision 92%).
    - The rules scored 80% on intent on the previous blind set. One blind set overstates how far hand-written rules generalise.
    - Privacy, the raw-data guard and the figures checker each scored 100% on their holdouts.
- **Reviewer benchmark:** three seeded memos.
    - Dev A; B held out, from the same author; C written blind.
    - The Tier 0 figures checker went from 0% to 75% lane recall on C, with no false alarms.
    - The Haiku figures auditor caught every planted figure defect with either prompt. The Sonnet analytics reviewer went from 83% to 100% on A, and stayed at 80% on B and 100% on C.
    - The memos were nearly too easy for the language models.
- **Two lessons from the checker:**
    - A rule that derives figures must keep to prose. The capstone dashboard's data table broke it.
    - It must count one quantity once, which the figures holdout showed.
- **Measured on a schedule (2026-10-20):** `scripts/agent_loop.py` records every measurement in a ledger, compares it with the floors and the previous line, and stops at `done`, `needs_person`, `stalled` or `budget`. The worker repeats it when `AGENTIC_OS_EVAL_INTERVAL_SECONDS` is set, and the `agent_scorecard` tool lets a runtime or MCP client read it. It never edits a rule or a floor and never shows an improver a held-out sentence. New cases come through a queue that only a named person accepts, into dev only. `done` is not accuracy: intent is 72% on its holdout and still reports `done`.
- **Fresh blind sets (2026-10-20):** independent agents wrote `blind_v6` (intent 48, jargon 40, causal 40). First scores: intent 68.5%, jargon 85%, causal wording 45% recall at 69% precision; the causal holdout's 100% had been fitted to. The intent and causal rules were then fixed against `blind_v6`, which moved into dev. A second set, `blind_v7`, judged the fix without being used for it: causal wording 28% to 60% recall and 70% to 88% precision on the same 50 sentences; intent 32 to 35 of 57 correct, a gain within noise. More patterns will not close the intent gap; a model behind the rules or a far larger set is the next step.
- **blind_v7 into dev (2026-10-23):** both sets moved into dev and the rules were fixed against them as linguistic families (soft causal verbs, tracing, pseudo-clefts, Arabic أفضى and عزا, denials; chat shorthand and Gulf phrasings for intent). On those sentences causal went from 60% to 96% recall and 88% to 100% precision, intent from 61% to 100%; these are dev numbers, not blind. Intent holdout rose 77% to 83%. Causal and intent have no blind floor until `blind_v8` is added.
- **Controlled comparison:** an edited subagent loads only in a new session. So prompt versions are compared by giving a general-purpose agent on the same model each version's instructions, and changing nothing else.

## Related

- [[Home]]
- [[Soul]]: no fabricated numbers, so the honest number is the blind one.
- [[Agent team]]: the reviewers this measures.
- [[Weighted KPIs]]: the denominator category in the reviewer benchmark tests this rule.
- [[Model validation]]: assesses analytical models separately from agent classification.
- [[Verification and budgets]]: records the broader delivery checks.
