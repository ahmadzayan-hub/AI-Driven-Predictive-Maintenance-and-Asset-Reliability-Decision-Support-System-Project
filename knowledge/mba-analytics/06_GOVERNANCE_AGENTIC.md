# Agentic analytics, responsibility and evidence — حوكمة التحليل والوكلاء

## Source-backed workflow

The recent lecture sequence uses a working distinction between a single reactive agent action and an agentic workflow with several steps and checkpoints. It presents four stages: cleaning, model/technique planning, scope selection and building the deliverable. Treat this as the course's teaching model rather than a universal definition of agency. [S040](SOURCE_INDEX.md#s040), pp7,22; [S041](SOURCE_INDEX.md#s041), pp3–4.

| Course stage | Evidence the lecture requests | Locator |
|---|---|---|
| Clean | Identify issues, propose changes, record before/after and challenge a correction | S041 pp7–9 |
| Model | Establish grain, measures and dimensions; propose a few decision-relevant techniques | S041 pp10–12 |
| Scope | Define audience, a small KPI set, refresh need and a concrete decision | S041 pp13–15 |
| Build and verify | Produce and inspect the output; test behavior and freshness against source changes | S041 pp16–19 |

The governance lecture identifies hallucinated relationships, wrong aggregation, private data sent to APIs, drift and missing audit trails as risks. It calls for owners, human checks, prompt/model/timestamp logging and verification of numerical work. [S042](SOURCE_INDEX.md#s042), pp3,6,10–11. These requirements support traceable reasoning, not a claim that a named role has executed.

## Proposed separation of responsibilities

| Layer | Responsibility | Evidence required before claiming it happened |
|---|---|---|
| Deterministic calculations | Parse data, apply approved transformations, calculate metrics and evaluation results | Code/version, input hashes, parameters, logs and output hashes |
| LLM reasoning, if separately authorized | Form questions, explain verified results, propose hypotheses and draft narrative | Actual run/provider/model identity, authorized data scope, prompt/output records and citations |
| Independent review | Recompute material claims, challenge assumptions and inspect discrepancies | Separate reviewer identity or process, checks performed, findings and resolution status |
| Human approval | Accept definitions, risks, decisions and any publication | Identified approver, exact artifact/version/hash and scope of approval |

This table is proposed operating guidance. A Markdown role, task label, generated “review passed” sentence or orchestration diagram is not evidence of runtime execution. Self-checks by the same author should be labelled self-checks, not independent review.

## Observed execution in this knowledge task

- Deterministic local work ran: recursive metadata inventory, SHA-256 hashing, installed Poppler extraction, standard-library XML/CSV parsing, aggregate profiles, two source-example arithmetic checks and original-integrity verification.
- An AI assistant authored the summaries and inspected selected passages and images.
- No Miyaar project analysis pipeline, project model training, external model-provider API, locally loaded model, independent reviewer run or human approval was claimed or performed here.
- No source script was executed and no original source, database or production system was changed during curation. Repository integration of these summaries is a separate, tested code/documentation change.

## Proposed approval gates

Use checkpoints for material changes to meaning: accepting the data dictionary and cleaning rules, accepting the method/evaluation plan, accepting the decision scope, and approving the exact final outputs. Record which choices are routine implementation and which require the decision owner's judgment. Existing user authorization still governs the work; this reference must not invent new operational permission.

Private data stays within the authorized boundary. Publication of these reviewed original summaries does not authorize forwarding user data to external model providers or publishing underlying records. The package's `model_context_allowed` field is false. A later integration must preserve that restriction rather than silently relax access controls.

## BACC and organizational ownership

The older and newer BACC lectures treat governance, staffing, workflows, skills, adoption and business alignment as part of analytics capability. They are organizational responsibilities that cannot be satisfied by creating software role files alone. [S016](SOURCE_INDEX.md#s016), pp4–13; [S038](SOURCE_INDEX.md#s038), pp18–32. Their unsourced impact figures are not evidence of Miyaar performance.
