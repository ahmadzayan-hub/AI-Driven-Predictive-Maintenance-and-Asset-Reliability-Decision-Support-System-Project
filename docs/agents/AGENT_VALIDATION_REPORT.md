# Agent validation report

Date: 22 October 2026 · Companion to `docs/AGENT_VALIDATION_REGISTER.md`
(the per-output register) and `docs/AGENT_TEAM.md` (tiers and the review
loop). Scores below are from `python scripts/evaluate_agents.py --check` run
today; everything else is from the code it cites.

## 1. Scores today

| Suite | What it measures | Dev (floor) | Holdout (floor) | Blind (floor, since 22 October) |
| --- | --- | --- | --- | --- |
| intent | rules intent classifier, 10 labels | 331 cases, 100% (1.0; includes blind_v7 since 23 October) | 60 cases, 83% macro recall (0.76) | none since 23 October: blind_v7 (61% before the fix) moved into dev, blind_v8 pending |
| column_roles | column mapping suggestions | 64, 100% (1.0) | 33, 100% (1.0) | no blind set |
| personal_data | privacy agent | 64, 100% (1.0) | 33, 100% (1.0) | no blind set |
| router | provider from a model name | 23, 100% (1.0) | 12, 83% accuracy, 89% macro recall (0.88, after the GPT cases were relabelled OpenAI) | no blind set |
| raw_guard | rows that must not reach a model | 13, 100% (1.0) | 7, 100% (1.0) | no blind set |
| jargon | validator's jargon check | 68, 100% (1.0) | 24, 96% accuracy, 92% recall (0.91) | blind_v6, 40 cases, 85% recall, 100% precision (0.85) |
| causal | causal wording lint | 155, 100% (1.0; includes blind_v7 since 23 October, one contested case set aside) | 32, 100% (0.68; read while the fixes were chosen, ADR 0056) | none since 23 October: blind_v7 (60% recall, 88% precision before the fix) moved into dev, blind_v8 pending; probe_v5 32 cases, 56% recall, adversarial and unfloored |
| figures | figures checker | 19, 100% (1.0) | 11, 100% (1.0) | no blind set |
| standards | standards lint | 112, 100% (1.0; blind_v1 and blind_v2 moved in on 23 October) | 24, 100% recall (0.9; written by the session that wrote the patterns, not blind) | blind_v3, 40 cases, 14% recall on the 22 refused sentences, every compliant sentence left alone (0.13); blind_v1 had scored 0% and blind_v2 32% before each moved into dev and scored 100% |

All nine suites pass their floors, now on every split they have. Since
22 October each text classifier declares its blind split in
`scripts/evaluate_agents.py` (`SUITES[...]["blind"]`), the script scores it
on every run and `--check` and `tests/test_evals.py` hold it to a floor set
from the score measured that day, rounded down (G1 closed, 22 October).
Nothing was tuned: the blind scores before and after the change are the
same numbers (causal 60%, intent 61%, jargon 85%).

The honest reading. The causal and intent holdouts were read while fixes
were chosen (ADR 0056) and are a second dev score; the number to quote is
the blind one, 60% and 61%. The new standards blind set is the finding of
the day: `evals/standards.json` `blind_v1` holds 36 sentences an executive
report might contain, 18 English and 18 Arabic, written from the five
refusal categories in the suite's `about` text without opening the lint.
The lint caught none of the 19 refused sentences (an ideal allocation,
a programme that paid for itself, overall upkeep spending, 412 assets in
the critical band, a team that should bring an inspection forward, and
their Arabic counterparts) while correctly passing all 17 compliant ones.
Its 100% on dev and holdout measures the keyword list against sentences
written to match it; its blind recall is 0%, so its floor is 0.0 and will
only mean something once the lint is rewritten against a model or a
broader rule set and a fresh blind set is written to judge that work.
Nothing in the lint was changed in response, by design: a fix chosen on
`blind_v1` would move the set into dev and call for `blind_v2`.

## 2. Contracts, as implemented

| Agent or stage | Purpose | Inputs | Outputs | Evidence and validation | Refusal | Tools | Oversight | Tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Rules intent (`assistant.understand`) | one action from the catalogue | the sentence | intent dict, `source: rules` | fixed vocabulary | falls back to chat | executes through the catalogue | destructive actions confirmed | `test_assistant.py` (67), `test_agent.py`, `test_evals.py` |
| Model intent (`server/assistant.py`) | action when rules cannot | memory, preferences, headlines, 6 turns; never rows | intent or 600-char reply | regex JSON, allowlist, `arguments_valid`; schema enforced on Ollama only (G5) | invalid answer to rules; privacy hit to rules | same catalogue | same | `test_assistant.py`, `test_model_privacy_boundary.py` |
| Agent runtime and ToolBox | multi-tool loop | message, 9 tools, context | tool texts, closing line | allowlist, scalar args, privacy guard | 8 steps; no deletions; exception to rules | 9 tools | publishing waits | `test_agent_runtime.py` (29), `test_frameworks.py` (skips in CI) |
| MCP server | ToolBox over JSON-RPC | initialize, tools/list, tools/call | content, isError | JSON-RPC shape | standard errors | same | same | `test_mcp.py` (11; SDK test skips) |
| Narrator (`ModelGateway.narrate`) | two-sentence summary of verified facts | goal and facts | text, source | privacy guard before; grounding after (new today) | deterministic template | none | report hash at the gate | `test_model_gateway.py` (44), `test_analytics.py::NarratorGroundingTestCase` |
| Router | provider per report | prompt | decision with reason | alias match; unknown is None | gateway order | none | none | `test_routing.py` (24) |
| Hermes, agents, consultants (`ModelRoles`) | plan, notes, review, brief | goal plus at most 14 claim texts | markdown section | `grounded()`; privacy boundary (new today); built-in writer when no model | exception swallowed, run continues | none | brief is advisory | `test_orchestration.py` (17) |
| Custom stages (`server/stages.py`) | plugin stages | context copy | status, claims, calcs, checks | field contract, limits, id prefix, placement before the governed tail | contract violation fails the stage | in-process, no sandbox (G10) | operator registers | `test_stages.py` (32) |
| Validator | independent verification | run context | checks | ids exist; totals reconcile; jargon; both languages cite the same figures | rejects the run | none | approval gate | `test_analytics.py`, `test_evals.py` |
| Privacy agent and boundary | keep personal data from models | flags and outgoing text | block or allow | pattern detector | unreadable evidence blocks | none | — | `test_model_privacy_boundary.py`, `test_detectors.py` |
| Column mapping | role per column | columns and values | suggestions | — | — | none | owner saves | `test_mapping.py`, `test_maintenance_mapping.py` |
| Tier-0 scripts (claims, standards, figures, raw guard, review gate) | deterministic lint and gates | documents | findings | measured suites | none | none | acceptance needs `by` and `reason` (G14) | `test_evals.py` (40), `test_agent_team.py`, `test_consult.py` |
| Reviewer subagents | figures, analytics, brief, security, accessibility | files | findings | seeded memos for two of five; no floors (G9) | — | read-only | review loop | `test_agent_team.py` (frontmatter) |

## 3. Gaps, in priority order

Closed 22 October: floors on tuned sets (G1). The blind splits (causal and
intent blind_v7, jargon blind_v6, the new standards blind_v1) now carry
floors, the holdouts are described as what they are, and the script's
docstring says which splits were read while fixing. On 23 October causal and
intent blind_v7 moved into dev to fix the rules against it, so those two
suites have no blind split or blind floor until blind_v8 is added
(`docs/adr/2026-10-23-blind-v7-into-dev-causal-and-intent-fix.md`). The standards lint's 0%
blind recall is the open consequence and sits with item 1 below.

1. The standards lint catches only the phrasings it names: 0% recall on
   blind_v1 (36 cases), 100% on the sets written with the patterns in view.
   Same shape as the causal finding in ADR 0056; the fix is a model behind
   the rules, judged on a fresh blind set, not more keywords.
2. No cost, token or latency record for any model call (G4).
3. Structured output on one provider only; consultants free text (G5);
   agreement between consultants left to a model (G6).
4. Router no longer substitutes Groq for GPT names (G7, fixed 22 October); its two holdout misses are Groq-hosted names with `-instant` and `-it` suffixes, left for a dev-set fix.
5. Two newer actions unmeasured; model intent unmeasured (G8).
6. No timeout on runtimes or custom stages (G10); optional runtimes untested
   in CI (G11).
7. Orchestration failures silent (G12); grounding lexical only (G13).

## 4. Where to use a model, and where not

Use deterministic code for: stage order and the approval gate (already),
consultant agreement (G6), the Hermes plan when no judgement is needed (the
built-in plan exists). Use a model, measured, for: intent on sentences the
rules cannot place (the rules plateau at 61% blind), and the written
judgement in notes and briefs, always grounded.

## 5. Not done in this pass

One new evaluation set was written, the standards blind_v1 (36 cases), and
its 0% is recorded as a baseline, not fixed. No other set was written. The
independent Arabic and railway or maintenance scenario sets the brief asks
for are a P2 item with the two unmeasured actions (G8).
