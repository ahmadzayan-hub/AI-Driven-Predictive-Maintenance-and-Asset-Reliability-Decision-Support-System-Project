# Bounded, durable evidence-specialist loops

Status: opt-in code candidate. No production activation or live-model acceptance.

## Purpose and scope

The existing deterministic analytics pipeline remains the default. Its stages
are tools, not independent reasoning agents. A new `specialist_evidence` profile
is available only when an operator explicitly injects a decision driver into
`RunEngine`. No environment setting enables it, no scripted driver ships in
runtime code, and missing configuration never invents a model decision.

Four separate role/task identities execute decision → granted tool → observation
loops: evidence steward, analysis investigator, report drafter and independent
evidence verifier. The coordinator alone controls handoffs. Each checkpoint binds
run, owner, task, role/version, model, source/content/analysis version, goal,
mapping, glossary, remaining limits, pending operation and artifact references.
Same-model use does not collapse their separate state or tool grants.

The first slice accepts one authorized dataset. It is not yet an RMD evidence-pack
agent, post-report chat, voice assistant, motion renderer or arbitrary agent
factory. Existing deterministic analysis functions provide actual measurements;
raw rows never enter the decision context. A model may select approved analyses,
request input, stop, or propose a draft. It cannot publish, approve, delete,
assign access, execute shell commands, contact external tools or spawn agents.

## Validation and budgets

Strict schemas reject unknown tool arguments. Limits are at most six decisions
per role for the entire run, forty tools per run, two repair cycles, twelve
handoffs and a five-minute default deadline (operator maximum thirty minutes).
A lower remaining role budget can stop repairs before the repair ceiling. A
repeated tool/argument signature with no progress terminates the role. Decisions
are limited to 24 KB, tool results to 32 KiB, model context to 64 KiB and each
checkpoint to 192 KiB. These are ceilings, not promises to consume the allowance.
Limits cannot expand during restart; the saved contract must still match.

The explicit gateway adapter requires an already configured model, the same
engine gateway, durable admission and a single recipient. No cross-provider edge
is accepted for this slice. Existing owner/day credits reserve before a call.
No paid provider or live catalog call is part of these tests. The scripted driver
exists only in tests and is identified as such in its trace.

Source text is evidence, never a grant. The established personal-data guard checks
both source privacy and exact outgoing content. Server-generated SHA-256 metadata
uses lossless a–p hex encoding in model messages so a digit-heavy hash is not
mistaken for a phone number; source text and claim values are never exempted.
Original hashes remain in durable checkpoints and human review.

## Persistence and interruption

No table or migration is added. Existing task result JSON and run-row transaction
locks persist each intent before dispatch and each result/handoff after dispatch.
Operation tokens plus checkpoint revisions fence duplicate/stale completions;
worker leases, cancellation, pause, deadline and source versions are rechecked.
The next process resumes committed tool observations rather than rerunning them.
A pending pure tool can retry after an expired interrupted operation; report
artifact insertion occurs only in the fenced commit transaction, not the handler.

Preparation runs under the same bounded operation timeout and checks cancellation
before provider dispatch. A known preparation timeout makes no provider attempt.

A timed-out or expired in-flight model operation is explicitly uncertain and
stops. It is not retried and may already have consumed admission/paid usage.
Cancellation cannot revoke a provider request already dispatched; its late result
is discarded. Python deadlines abandon a thread, not sandbox or kill it. There
are no external write tools here; exactly-once external effects would require a
separately reviewed idempotency/outbox contract.

## Evidence review and publication

The verifier independently recomputes deterministic claims and their calculation
references, checks the exact draft hash and rejects unsupported text/numbers.
This first draft format composes canonical verified claim text, not unconstrained
prose or a new numerical authority. Repair returns fixed evidence issues to the
drafter and invalidates the previous verification hash. Calculations retain their
original methods and evidence IDs; missing metric meaning, target, period or
responsible person is not inferred. Contextual user clarification is a separate
versioned contract, not an implicit assignment or threshold approval.

Only a verified exact draft reaches the existing human publication gate. Source,
analysis configuration, report content and destination checks remain effective at
approval time. A verifier cannot approve publication. A new application without
the specialist verifier refuses to publish specialist reports. Existing owner
and dataset checks remain in force; no global memory store is used.

## Acceptance status

Offline tests prove the wiring: distinct loops/handoffs, evidence replay, forged
claim and tool rejection, bounds, tenant separation, real store transactions,
fresh-process restart, stale worker rejection and cancelled late-result discard.
The suite runs against SQLite and the existing explicitly disposable PostgreSQL
CI database; unavailable local PostgreSQL cases are skipped visibly, never called
passed. Complete regression and hosted CI results must be reviewed separately.

Not proven: real-model decision quality/latency, production checkpoint durability,
provider cost, a production account session, API/worker opt-in integration, or
container activation. The current daemon remains non-activating and does not
inject this profile. Subsequent integration must include the conversational
ToolBox dependencies in its reviewed runtime image and run hosted acceptance.

## Next integration gate

A separate integration change must select a configured driver consistently in the
API and worker, reject absent/ambiguous model selections and preserve default-off
behavior. Its tests must prove authenticated profile creation, worker restart and
human review with injected transport. Real-model acceptance then requires the
named account/model, explicit no-spend eligibility or approved usage cap, secure
credential configuration if needed, and an actual measured session. Neither this
constructor seam nor an offline fixture is a user-accessible live Agentic OS.
