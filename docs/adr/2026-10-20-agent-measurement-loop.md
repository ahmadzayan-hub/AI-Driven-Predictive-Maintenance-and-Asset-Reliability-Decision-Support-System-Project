# Agents are measured on a schedule, in a bounded loop that hands over to a person

Date: 2026-10-20 · Status: Accepted

## Problem

The owner asked that the agents stay active until their tasks are done, and
that they be connected to tools for continuous updates that improve their
knowledge and their confusion matrices.

Two halves of that already existed. The worker keeps stepping runs until a
human gate, survives a failing run and reclaims a crashed task (ADR 0006).
`scripts/evaluate_agents.py` computes every classifying agent's confusion
matrix and recall (ADR 0027). What was missing: the measurement was a
photograph. Nothing recorded it over time, nothing compared it with the
previous one, nothing ran it unattended, and no tool let an agent or an MCP
client read it.

Three things are tempting and wrong:

1. **Let the agents tune themselves against the evaluation.** The holdout is
   the only number that says how a rule behaves on sentences it was not
   fitted to. `docs/KNOWN_LIMITATIONS.md` item 6 already records what happens
   when it is fitted to: causal wording went from 69% to 100% and stopped
   being independent evidence. A loop that optimises the holdout produces
   rising numbers and no information.
2. **Let an agent add cases to the suites.** A case written by the thing under
   test, or accepted without a person, makes the suite agree with the agent.
3. **Loop without a bound.** `docs/KNOWN_LIMITATIONS.md` item 5: runs are
   bounded, and permanent accuracy cannot honestly be promised.

## Decision

`server/agent_learning.py`, `scripts/agent_loop.py`, one new read-only tool.

- **Ledger.** Every measurement is one line in `data/eval-ledger.jsonl`
  (git-ignored, bounded to 2,000 lines, a damaged line skipped on read). A
  line holds each suite's dev and holdout recall, accuracy, confusion matrix
  and the revision. Dev misses are kept by text. Holdout misses are kept as
  counts and label pairs only: no held-out sentence is ever written to the
  ledger, the work order or the scorecard.
- **Comparison.** `below_floor` (the contract in `evals/floors.json`),
  `regression` (a headline fell by more than half a point since the previous
  line), `dev_miss` (a dev case is wrong). The gap between dev and holdout
  recall is reported as information for whoever writes fresh cases and never
  fails anything.
- **Loop.** Measure, compare, and, only when improvers are registered, let
  them act on the work order and measure again. Stops at `done` (nothing
  left), `needs_person`, `stalled` (two rounds without dev gain) or `budget`
  (five rounds, or a time budget). These are the review loop's bounds. With
  no improver registered, which is the default, it measures once and hands
  over, because nothing here edits a rule. An improver may be a script, a
  person or a model-backed agent runtime; it sees dev text and holdout counts.
- **Proposals.** Fresh labelled cases go through a queue. Only one-sentence
  suites take them (intent, jargon, causal; `standards.json` is hand-formatted and would be rewritten whole, so it waits until normalised); a proposal names its
  source; accepting or rejecting names the person. Acceptance writes to the
  **dev** split only, never the holdout, and a sentence already in any split
  is refused. Nothing accepts a case by itself.
- **Worker.** `AGENTIC_OS_EVAL_INTERVAL_SECONDS` (off by default, one minute
  at least) makes the worker measure inside its existing loop, record the
  line and log a regression or a floor breach on stderr. It changes nothing.
  A failing measurement is logged and the worker carries on, as it does for a
  failing run or source.
- **Tool.** `agent_scorecard` (optional `suite`) is an assistant action, so
  agent runtimes (ADR 0021) and MCP clients get it through the same `ToolBox`.
  It reads the ledger; with none it measures without recording, so a chat
  question never writes to a hosted deployment's disk. Not destructive.
  English and Arabic replies.

## What it measured while being built

The tool's first reply was withheld from the model by the project's own
privacy guard: a sixteen-digit recall such as 0.7166666666666667, and an ISO
timestamp, both read as phone numbers. Recall is now rounded to four
decimals and the date is written with the month spelled out. The regression
test uses real recall values and was watched failing first.

Measured at the start of this change: every dev suite 100%; holdout intent
72%, router 90%, jargon 92%, the rest 100%. The causal floor (68%) is far
below its current holdout (100%) because that holdout was fitted to; the
floor is stale and was not raised, because raising a floor is a person's
decision.

## Consequences and limits

- "Done" means no floor is broken, nothing regressed and nothing is waiting
  for a person. It does not mean the agents are accurate: intent is at 72%
  on its holdout and the loop reports `done`.
- Continuous improvement still needs a source of genuinely new labelled
  cases. This change gives them a safe path in (the queue) but does not
  create them. Not done, on purpose: harvesting live chat sentences or users'
  column-mapping corrections as labels. Both are real signal, and both carry
  tenant data and possibly personal data into a shared file. That needs its
  own decision on consent, tenancy and redaction.
- The reviewer subagents (`evals/reviewers`) are not part of the ledger: their
  scores come from model runs saved by hand.
- The ledger is one file on one machine. Several worker instances each keep
  their own. A hosted deployment without a writable disk uses the tool's
  measure-without-recording path.
- The label-pair confusions shown for the holdout are aggregates of labels,
  not sentences. They are a weaker leak than the sentences, not none: an
  improver that reads them and tunes toward them is fitting to the holdout.
  The rule is stated in every work order; the code cannot enforce it on a
  free-text improver.

## Validation

`tests/test_agent_learning.py`: the ledger, the absence of held-out text from
every record, each finding kind, each loop state and the improver's failure,
the proposal rules (dev only, named person, no repeats, bounded queue), the
steward's schedule, the worker surviving a failing measurement, and the tool
in both languages passing the privacy guard.
