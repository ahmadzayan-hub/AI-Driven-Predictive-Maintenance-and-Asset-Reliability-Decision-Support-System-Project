# Agent validation report

Date: 22 October 2026 · Companion to `docs/AGENT_VALIDATION_REGISTER.md`
(the per-output register) and `docs/AGENT_TEAM.md` (tiers and the review
loop). Scores below are from `python scripts/evaluate_agents.py --check` run
today; everything else is from the code it cites.

## 1. Scores today

| Suite | What it measures | Dev | Holdout (floor) | Blind, unfloored |
| --- | --- | --- | --- | --- |
| intent | rules intent classifier, 10 labels | 274 cases, 100% | 60 cases, 77% macro recall (0.76) | blind_v7 57 cases, 61% |
| column_roles | column mapping suggestions | 64, 100% | 33, 100% (1.0) | — |
| personal_data | privacy agent | 64, 100% | 33, 100% (1.0) | — |
| router | provider from a model name | 23, 100% | 12, 83% accuracy, 89% macro recall (0.88, after the GPT cases were relabelled OpenAI) | — |
| raw_guard | rows that must not reach a model | 13, 100% | 7, 100% (1.0) | — |
| jargon | validator's jargon check | 68, 100% | 24, 96% accuracy, 92% recall (0.91) | blind_v6 40, 85% |
| causal | causal wording lint | 106, 100% | 32, 100% (0.68) | blind_v7 50, 60%; probe_v5 32, 44% |
| figures | figures checker | 19, 100% | 11, 100% (1.0) | — |
| standards | standards lint | 36, 100% | 24, 100% (0.9), not blind | — |

All nine pass their floors. The honest reading: the causal and intent
holdouts were tuned to (ADR 0056) and are no longer independent; the blind
sets show 60% and 61%. The brief's statement that causal identification is
weak is right for the blind set and out of date for the holdout. Floors
should move to the blind sets (assessment G1).

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
| Tier-0 scripts (claims, standards, figures, raw guard, review gate) | deterministic lint and gates | documents | findings | measured suites | — | none | acceptance needs `by` and `reason` (G14) | `test_evals.py` (39), `test_agent_team.py`, `test_consult.py` |
| Reviewer subagents | figures, analytics, brief, security, accessibility | files | findings | seeded memos for two of five; no floors (G9) | — | read-only | review loop | `test_agent_team.py` (frontmatter) |

## 3. Gaps, in priority order

1. Floors on tuned sets (G1). Move to blind_v7 and blind_v6; write a blind set
   for standards; correct the script's docstring.
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

No new evaluation set was written, so no new baseline is claimed. The
independent Arabic and railway or maintenance scenario sets the brief asks
for are a P2 item with the two unmeasured actions (G8).
