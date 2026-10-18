# UI and agent improvement plan

Date: 2026-10-18. Scope: advice for the maintenance SaaS application and the Claude Code team that develops it. This is an implementation backlog, not a record of completed features.

## Recommendation

Complete one trustworthy journey: **upload -> suitability assessment -> governed analysis -> real executive overview -> evidence -> human approval**. Preserve React/FastAPI, the shared design tokens, bilingual components, durable run engine and deterministic calculations. Expand autonomy where evaluation demonstrates a benefit.

## What was inspected

- The [maintenance specification](../docs/design/MAINTENANCE_UI_SPEC.md), its saved English desktop screenshot, the design-system master and current source. The screenshot is an earlier synthetic preview capture; no live browser journey was rerun today.
- [MaintenancePreview.tsx](../frontend/src/features/maintenance/MaintenancePreview.tsx) still reads fictional fixtures. Real upload and general run dashboards are separate experiences.
- [config.json](../config.json) registers general models; it does not register maintenance governance/risk stages or configure an agent runtime. Environment overrides were not checked, so this does not establish deployment configuration.
- [ADR 0040](../docs/adr/0040-validated-maintenance-risk-models.md) and [targets.py](../server/maintenance/targets.py) add maintenance targets, timing-filtered inputs and baseline comparisons. Both current targets concern the same maintenance record; this is not evidence of future asset remaining life. Their reported scores were not independently reproduced in this advisory pass.
- [auth.py](../server/auth.py) now excludes user metadata from role selection and supports server assignments. This is a change since the prior assessment, not a newly verified closure of its authorization finding.
- [governance.py](../server/maintenance/governance.py) still declares `can_fail_run=False` while its fatal option can return a failed stage. Recheck full-engine behavior before closing the earlier finding.
- [AGENT_TEAM.md](../docs/AGENT_TEAM.md), runtime/tool interfaces and evaluation records already provide specialist roles, bounded execution and review/evaluation machinery. Improve these foundations rather than duplicating them.

## Product interface

Use the executive overview as the maintenance workspace landing page once it is connected to real runs. Preserve useful deep links and place the assistant beside the work as contextual help. Record the entry-point change in a new ADR because the existing normal app opens on chat.

Suggested navigation: **Overview / Data & analyses / Reliability / Reviews & reports**. Keep model evidence inside each analysis, with detailed agent activity available on demand. Preserve the existing accessible routes and labels where compatibility requires them.

| ID | Priority | Improvement and user benefit | Starting locations | Acceptance check |
| --- | --- | --- | --- | --- |
| UI-01 | First | Connect a real run to the maintenance overview so an upload leads directly to useful findings | `frontend/src/features/maintenance/`, `frontend/src/features/dashboard/`, `server/maintenance/`, `server/app.py` | Two synthetic datasets produce their own reconciled values; no sample fixture can appear in a real run |
| UI-02 | First | Turn intake into Upload -> Map -> Check -> Analyse, retaining valid choices after a recoverable error | `frontend/src/features/datasets/`, `frontend/src/features/runs/RunsView.tsx` | Supported formats work in both languages; worksheet discovery handles a cover sheet before parsing; failed imports cannot start a sample run |
| UI-03 | First | Show a suitability card naming available analyses and missing prerequisites | Mapping, domain contract and run creation | Missing planned hours withholds availability and explains why; absent timestamps/labels withhold unsupported predictions while allowing supported descriptive analysis |
| UI-04 | First | Make every headline KPI open an evidence panel: formula, source snapshot, period, unit, population, exclusions and quality flags | `EvidencePanel.tsx`, dashboard and maintenance KPI API | Display and export reconcile under identical filters; missing values never become measured zeros |
| UI-05 | Next | Show a compact activity timeline with preparation, analysis, checking and review groups | `RunTimeline.tsx`, `runEvents.ts`, run engine events | Refresh/reconnect preserves actual stage status; a failed mandatory stage cannot look complete; safe retry does not duplicate work |
| UI-06 | Next | Make the review queue actionable with evidence, recorded reviewer and persisted decision status | Maintenance reviews and approvals views | Review survives reload, is permission checked and remains distinct from report publication or work-order dispatch |
| UI-07 | Next | Add a contextual assistant scoped to the selected run and filters | Chat, dashboard state, `server/tools.py`, runtime adapter | A question about a filtered chart cites the matching calculation and snapshot; changing context does not reuse another user's results |
| UI-08 | Throughout | Improve English/Arabic keyboard, touch and failure recovery paths | Shared controls, lazy message packs and tokens | RTL identifiers remain legible; focus returns correctly; status changes are announced; phone layouts and text enlargement preserve actions |

These acceptance checks are **NOT TESTED for the proposed changes**. Existing components already implement portions of this behavior; reuse and extend them.

### Refine the existing visual design

- Keep the navy navigation, restrained blue actions, flat cards and semantic status colors. The saved preview already has a coherent visual hierarchy.
- Reduce the tall introductory heading area in the operational view. Give the current scope, source freshness and primary next action that space.
- Keep a small set of useful KPIs. Show comparison deltas only when periods and populations are comparable; provide the comparison basis in evidence.
- Place the most important exceptions and next review actions higher on the page. A ranked bar chart may communicate condition counts more precisely than a donut when comparing categories is the task; choose with a short user task test.
- Separate observed condition, rule-based priority and evaluated model prediction in labels. Each needs its own evidence; do not carry fictional condition scores into uploaded data.
- Keep charts and their accessible numeric tables together. Keep site/period/filter scope consistent across cards, charts, assistant answers and exports.
- Give each failure a useful recovery action: choose another sheet, correct mapping, change scope, reconnect or retry. Distinguish no records, insufficient evidence, stale results and a failed request.
- Preserve the existing bundle budgets and reduced-motion behavior. Measure before adding heavier charting, animation or agent-graph libraries.

For asynchronous updates, W3C guidance supports programmatic status announcements without forcing focus to move: [WCAG status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html). Automated accessibility checks should be supplemented with keyboard and assistive-technology observation.

## Application agents

The pipeline specialists and Claude Code's development reviewers serve different purposes. Most existing analytics stages are deterministic computations. The optional language-model runtime can plan tool use; it should operate within the existing engine's permissions and gates.

Group existing responsibilities in the UI rather than adding another agent for every screen:

| Responsibility | Output the user can inspect | Execution approach |
| --- | --- | --- |
| Understand the task | Goal, chosen profile, target, horizon, scope and unresolved ambiguity | Rules for clear requests; optional bounded planner for multi-step requests |
| Prepare and validate | Schema mapping, units, joins, quality findings and suitability | Server-side deterministic tools |
| Calculate reliability | Defined KPIs, concentrations, comparisons and exceptions | Deterministic calculations with provenance |
| Evaluate prediction | Actual features, timing exclusions, temporal split, baseline, class-specific errors and limitations | Evaluated model stage, only when prerequisites hold |
| Explain results | A concise decision brief and report draft citing calculation IDs | Templates or a narrator receiving approved aggregate evidence only |
| Verify and review | Evidence checks, unresolved findings and exact artifact awaiting approval | Independent validation; a person authorizes publication |

Hermes remains the durable orchestrator. A planner proposes a structured plan using approved tools; the server validates and executes it. Dataset contents are untrusted data and cannot select tools or change permissions.

### Strengthen the contracts and runtime

1. Extend the existing stage result contract with versioned evidence references, prerequisites and explicit non-applicability reasons where needed. Keep `status`, `claims`, `calculations` and `quality_checks` as the foundation.
2. Persist the selected maintenance profile, column mapping, prediction timing contract and dataset snapshot with the run. The same contract must govern calculation, model selection, display and export.
3. Give tools narrow schemas, server-side authorization and predictable error responses. Reuse the existing toolbox instead of adding unrestricted Python, shell or SQL execution to the copilot.
4. Keep raw rows inside server computation. A language model receives only permitted aggregate results, verified claims and minimal schema metadata. Scrub schema labels and small-group outputs where necessary; aggregation alone is not a privacy guarantee.
5. Extend existing call limits and leases with measured token/cost/time budgets where applicable, safe cancellation, bounded retries and idempotent actions. Test restart and timeout recovery.
6. Make the activity panel show concise decisions, tool actions, artifact links, warnings and timestamps. Display measured durations/costs only when recorded. Do not generate an arbitrary agent-confidence percentage.
7. Retain useful approved workspace settings such as mappings, units and KPI definitions with ownership and versions. Treat prior narrative conclusions as claims needing fresh evidence when a dataset changes.
8. Provide a deterministic fallback when the optional model provider is unavailable, clearly labelled. Do not prevent supported calculations merely because narration cannot run.

This selective approach follows Anthropic's recommendation to increase agent complexity only when it improves outcomes: [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).

### Measure whether the agents improved

Extend `evals/`, `scripts/evaluate_agents.py` and `scripts/score_review.py` before replacing them. Add end-to-end tasks as well as individual classifier checks. Keep development cases separate from unseen evaluation cases; repeated tuning on a holdout makes it a development set.

Measure task completion, calculation agreement, unsupported-claim rate, issue precision/recall, authorization failures, recovery success, elapsed time and actual provider cost. For predictive tasks, also report the held-out population, class-specific errors, a meaningful baseline and uncertainty. Set acceptance criteria before evaluating; an improvement in a single score does not establish operational usefulness.

Include synthetic cases for missing units, missing dates, no stable asset ID, duplicate join keys, invalid numbers, empty filters, class imbalance, label leakage, instructions embedded in data, Arabic requests, provider outage, interrupted workers and cross-user access. Run stochastic evaluations repeatedly when judging prompt changes.

Anthropic's evaluation guidance emphasizes inspecting both task outcomes and execution traces with multiple evaluation methods: [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

## Claude Code development agents

Use the existing roster. Give each implementation task a bounded objective, allowed files, dependencies, acceptance criteria and a required evidence artifact. Keep reviewers read-only and independent of the implementer.

Start with deterministic checks, then send the resulting scorecard and relevant changes to the appropriate analytics, security/privacy or accessibility reviewer. Recompute challenged figures with code. Bound the review loop and record unresolved findings rather than weakening gates. Add harder unseen reviewer cases so prompt improvements can be measured.

Keep `Memory.md`, `project-progress.md` and the session log aligned with observed results. New code, enabled configuration, passing local tests and verified production behavior are separate states. Do not duplicate a feature because an older assessment predates its implementation.

## Delivery order

| Increment | Deliverable | Exit evidence |
| --- | --- | --- |
| 1. Establish trust | Recheck the assessment against today's code; close authorization, fatal-policy, KPI and model-contract findings | Negative authorization tests; full-engine stop/continue tests; KPI missing-value tests; leakage tests; reproducible verification baseline |
| 2. Complete the main journey | Guided intake and a real maintenance executive overview | A supported upload yields matching server, screen and export values with evidence and honest unavailable states in both languages |
| 3. Make assistance useful | Contextual copilot, compact activity view and review persistence | Correct scoped tool selection, cited answers, bounded execution, permission enforcement and recovery under failure |
| 4. Improve with evidence | Broader evaluation, usability observation and operational rehearsal | Comparable evaluation results and measured task usability; worker restart, tenant isolation and restore evidence before a hosted pilot |

**First implementation task after the release blockers:** connect one uploaded dataset to real downtime and cost metrics, a ranked contribution view and a source/evidence drawer. Add availability only when planned-hour inputs satisfy its definition. Add asset histories only when stable identity is established. Add predictions only when timing and evaluation support the stated decision.

Have a maintenance manager try to identify the largest recorded downtime contributor, inspect its basis and prepare a review decision. Observe completion, navigation errors and whether they understand limitations. Set a usability target before the trial; no measured target or result is claimed here.

## Validation scope of this plan

Source/document inspection, one saved synthetic desktop screenshot and primary-source guidance informed this plan. No product code, prompt configuration, data, deployment or live model was changed. No new backend, browser, model-quality or accessibility result is asserted. Implementation acceptance remains to be executed and recorded.
