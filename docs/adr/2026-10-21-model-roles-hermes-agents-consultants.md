# Model roles: Hermes on a language model, agents on Ollama, Claude and OpenAI as consultants

Date: 2026-10-21 · Status: Accepted (owner request, 21 October: "use Hermes
a language model as orchestrator and Ollama LLM for agents and Claude and
OpenAI LLM as consultation models"). Amends [ADR 0009](0009-hermes-and-the-specialist-roster.md).

## Context

Hermes was the run engine only: fixed code that sequences the stages,
enforces the state machine and holds the approval gate. Every agent was
code, and one model call phrased the executive summary. The owner asked for
Hermes to run on a language model, the agents on Ollama, and Claude and
OpenAI as consultants.

What must not change is the product's claim: every figure traces to a
calculation, raw data never reaches a model, and a human approves
publication. A model that could reorder stages, skip the validator or
approve its own report would break all three.

## Decision

Three model roles, each named by provider and each optional
(`server/orchestration.py`):

| Role | Variable | What the model does | What stays in code |
| --- | --- | --- | --- |
| Hermes | `AGENTIC_OS_HERMES_MODEL` | Plans the run from the goal and the roster (stored on the planner task); before the report, reads the verified findings and the consultants' notes and writes the approver's brief: what to check first, where the consultants agree or disagree | Stage order, the state machine, retries, the approval gate |
| Agents | `AGENTIC_OS_AGENT_MODEL` (normally `ollama`) | After a stage succeeds, phrases that stage's own verified findings as the agent's note (stored on the task) | Every calculation, check and claim |
| Consultants | `AGENTIC_OS_CONSULTANTS` (e.g. `anthropic,openai`) | Before the report, each independently names up to three risks or questions for the approver; asked in parallel | Nothing they write changes a figure or a decision |

Rules every role obeys:

1. A model sees verified sentences (stage claims) and the goal, never a
   dataset row.
2. A model writes words only. A note containing any number absent from its
   facts is dropped (`grounded`), so a report figure cannot come from a model.
3. The report gains one labelled section, "Orchestrator and consultant
   notes", stating that the notes add judgement, not figures. It is part of
   the artifact the approver sees and approves.
4. A provider that is not configured is reported in `/api/health`
   (`model_roles.problems`) and skipped. A model failure never fails a run.
5. Nothing configured, the default and every test, leaves runs exactly as
   before.

Hermes therefore runs on a language model for judgement and stays code for
control. ADR 0009's separation holds: Hermes still analyses nothing, and no
stage approves its own work.

## Consequences

- With Ollama, Claude and OpenAI configured, a run makes one model call per
  stage with findings (agents), one plan call, two consultant calls in
  parallel and one brief call. Locally that adds seconds per stage.
- Ollama must run on a server the deployment can reach. A model on a laptop
  is unreachable from Vercel's serverless functions, so the agent role does
  not work on the hosted site until Ollama is hosted somewhere reachable.
- Claude and OpenAI are metered by their providers.
- Agent notes are stored on each task and returned by the run API; the
  interface does not display them yet. Hermes' brief and the consultants'
  notes appear in the report itself.

## Verification

`tests/test_orchestration.py`, with a stand-in model, no network:
- no configuration means no role;
- each role takes a reachable provider, and an unreachable one is reported;
- a note may repeat a figure but never add one;
- an invented figure drops only that consultant's note;
- the report section labels every author in English and Arabic;
- a full pipeline run with all three roles gets a Hermes plan, Ollama agent
  notes, both consultants and Hermes' brief in the report, and no dataset
  row reaches any model;
- a failing model never fails the run;
- without roles the report is unchanged.

No live model call was made: no model or key is available in the
development container.
