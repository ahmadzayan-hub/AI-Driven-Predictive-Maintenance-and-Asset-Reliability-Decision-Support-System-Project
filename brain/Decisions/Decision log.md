---
type: decision
aliases: [ADR index, Architecture decisions]
tags: [decisions]
status: active
updated: 2026-10-28
review_every_days: 30
sources: [docs/adr]
---

# Decision log

- `2026-10-26-local-resource-lifecycle`: explicitly release Motion SQLite connections; retain only required OS bootstrap values in isolated test processes.

- `2026-10-26-approved-palette-and-source-workspace`: approved navy/blue/cyan
  palette, shared page hierarchy and responsive source cards; exact allowances
  remain visible without oversized KPI tiles. Runtime and image-sharing gates
  remain separate from synthetic layout tests.

- `2026-10-24-reviewed-mba-reference-collection`: reviewed original reference summaries use existing [[Knowledge retrieval]], retain partial coverage and model-context exclusion, and link the [[MBA analytics reference]].

Every architecture decision record in `docs/adr/`, one line each. A record states what was true and what was decided on its date. It is never edited to fit later facts; a superseded record points forward instead. A new behaviour change gets a new record, as [[Soul]] requires.

| ADR | Decision | Shapes |
| --- | --- | --- |
| 0001 | SQLite locally, PostgreSQL hosted, for run-engine persistence | [[Agentic OS]] |
| 0002 | [[Managed identity]], roles and [[Tenant isolation|tenant isolation]] | [[Agentic OS]] |
| 0003 | Sign-in flow and request rate limiting | [[Agentic OS]] |
| 0004 | Content-addressed dataset storage and upload | [[Analytics OS roadmap]] |
| 0005 | Backups, restore drills, measured RPO and RTO | [[Agentic OS]] |
| 0006 | Durable execution with database leases, not a workflow engine | [[Governed pipeline]] |
| 0007 | The four business-analytics types as governed agents | [[Governed pipeline]] |
| 0008 | Per-tenant quotas and usage, without inventing costs | [[Agentic OS]] |
| 0009 | Hermes and the size of the specialist roster | [[Hermes orchestrator]] |
| 0010 | Experiment and causal inference as a governed stage | [[Governed pipeline]] |
| 0011 | A metric glossary that can be wrong out loud | [[Weighted KPIs]] |
| 0012 | Failure injection, and what it found | [[Agentic OS]] |
| 0013 | Supply chain: pinned actions and a bill of materials | [[Agentic OS]] |
| 0014 | Memory belongs to an owner | [[Agentic OS]] |
| 0015 | Erasing one owner, and saying what survived | [[Agentic OS]] |
| 0016 | A range that survives being looked at (always-valid ranges) | [[Governed pipeline]] |
| 0017 | Choosing the narrator, and saying who chose it | [[Model gateway]] |
| 0018 | The interface in the reader's language | [[Identity]] |
| 0019 | A conversational agent that understands and acts | [[Model gateway]] |
| 0020 | Custom agents as plugins | [[Custom stages]] |
| 0021 | Agent frameworks: measured, adapted, not adopted | [[Agent runtimes and MCP]] |
| 0022 | Reports in the reader's language | [[Identity]] |
| 0023 | The analytics workspace interface | [[Design system]] |
| 0024 | The dataset API: several formats, one canonical table | [[Analytics OS roadmap]] |
| 0025 | Column mapping: the owner says what each column is | [[Column mapping]] |
| 0026 | Uneven periods are read per record | [[Weighted KPIs]] |
| 0027 | Agents are measured: confusion matrices, recall floors, blind holdouts, seeded reviewer memos | [[Agent evaluation]] |

| 0028 | Views load on demand, idle prefetch and measured first-load budget | [[Design system]] |
| 0029 | Governed run workspace, exact-artifact review and hash navigation | [[Design system]] |
| 0030 | Several datasets per run: declared joins and a merge stage | [[Analytics OS roadmap]] |
| 0031 | The cleaned table: download, fields, totals and records | [[Analytics OS roadmap]] |
| 0032 | Dashboard pages with filters in the address and drill-down | [[Design system]] |
| 0033 | Modelling stages as plugins, each against its baseline | [[Custom stages]] |
| 0034 | [[Live data]]: connectors, scheduled refreshes, pushed updates | [[Analytics OS roadmap]] |
| 0035 | A view's strings ship with the view | [[Design system]] |
| 0036 | Maintenance SaaS product identity over the existing Agentic OS engine | [[Identity]], [[Agentic OS]] |
| 0037 | Isolated bilingual maintenance design preview with fictional fixtures | [[Design system]], [[Agentic OS]] |
| 0038 | Explicit dataset intake, workbook sheet selection and governed upload-to-dashboard flow | [[Column mapping]], [[Governed pipeline]] |
| 0039 | Structural detectors run as a governed stage, so a finding travels as evidence | [[Custom stages]], [[Governed pipeline]] |
| 0040 | Maintenance risk models: inputs curated by timing, an informative baseline, a verdict needing two tests | [[Custom stages]], [[Governed pipeline]] |
| 0041 | The shipped configuration registers every stage, and a derived label's threshold is set on the training rows alone | [[Custom stages]], [[Governed pipeline]] |
| 0042 | An unmeasured cell is not a zero: a per-KPI missing-value policy with disclosed counts | [[Weighted KPIs]], [[Governed pipeline]] |
| 0043 | The repository takes the product's name; historical links stay where the work happened | [[Agentic OS]] |
| 0044 | The vault path comes from the environment | [[Governed pipeline]] |
| 0045 | Railway Asset Manager decision-screening contract | [[Custom stages]], [[Governed pipeline]] |
| 0046 | Opt-in maintenance decision profile | [[Custom stages]], [[Governed pipeline]] |
| 0047 | Reconciling the two histories in one repository | [[Agentic OS]] |
| 0048 | Distinctive brand integration with explicit agent-evidence gates | [[Design system]], [[House style]], [[Agent evaluation]] |
| 0049 | The KPI register reaches a run | [[Weighted KPIs]], [[Governed pipeline]] |
| 0050 | Bounded voice companion rather than cloning JARVIS | [[Agent runtimes and MCP]] |
| 0051 | The executive view reads measurements, not fixtures | [[Weighted KPIs]], [[Design system]] |
| 0052 | Bounded serverless event streams | [[Governed pipeline]] |
| 0053 | Dedicated Supabase data plane and managed Auth bootstrap (renumbered from a duplicate 0046) | [[Agentic OS]] |
| 0054 | Miyaar bilingual workspace redesign and honest browser voice states | [[Agentic OS]], [[Design system]] |
| 0055 | Opt-in local instruction model, bounded Whisper transport and reproducible runtime setup | [[Agentic OS]], [[Model gateway]] |

| 0056 | Causal-claim lint covers Arabic as well as English | [[Governed pipeline]] |
| 0057 | Local Markdown knowledge collections with heading citations | [[Agent runtimes and MCP]] |
| 0058 | Scoped executive evidence agent, bilingual dashboards and capability-aware Claude skills | [[Agentic OS]], [[Design system]], [[Weighted KPIs]] |
| 0059 | Business HTML and Word exports, native Print / Save as PDF and exact evidence revisions | [[Agentic OS]], [[Design system]], [[Weighted KPIs]] |
| 0060 | Reporting-standards wording lint distinguishes supported statements from unsupported claims | [[Governed pipeline]] |
| 2026-10-20-a-clips-number-must-be-in-its-source | A clip's figure is read against the file its source names, not merely required to cite one | [[Agent team]], [[Governed pipeline]] |
| 2026-10-20-decision-records-are-dated-not-numbered | The sequential counter is closed at 0060; a new record is named for the day it was decided | [[Session lifecycle]] |
| 2026-10-20-semantic-performance-colors | Explicit performance colors and sourced per-analysis display targets with neutral unknowns | [[Agentic OS]], [[Design system]], [[Weighted KPIs]] |
| 2026-10-20-observed-agent-collaboration | Observed workflow handoffs, stage inspection and independent visual pause with restrained [[Accessible motion|accessible motion]] | [[Agentic OS]], [[Design system]], [[Hermes orchestrator]] |
| 2026-10-20-agent-measurement-loop | Agents are measured on a schedule in a bounded loop that hands over to a person; holdout text never leaves the evaluation | [[Agent evaluation]], [[Agent runtimes and MCP]] |
| 2026-10-20-labelled-cases-from-real-use | **Accepted:** new labelled cases come from independent blind synthetic sets now; per-item consented contribution stays closed until a measured mismatch and a pilot customer's written agreement; blind_v6 then blind_v7: causal wording recall 28% to 60% after the fix, intent gain within noise | [[Agent evaluation]], [[Tenant isolation]], [[Model privacy]] |
| 2026-10-21-run-request-timeout | Run transport waits through bounded narration and serialized controls without replaying failed POSTs | [[Model gateway]], [[Governed pipeline]] |
| 2026-10-21-register-availability-and-pooled-reliability-measures | Register availability is uptime on planned time (96.96%), utilisation is its own measure, MTBF pooled with censoring, MTTR, overdue rate and SLA attainment added | [[Weighted KPIs]], [[Team 3 maintenance dataset]] |
| 2026-10-21-durable-worker-and-source-credentials | Persisted background run progress and owner/host-scoped operator credential aliases | [[Maintenance pilot]], [[Live data]] |
| 2026-10-21-maintenance-operations | Organization membership, evidence-linked drafts, independent repair authorization and completion audit | [[Maintenance pilot]], [[Tenant isolation]] |
| 2026-10-21-prospective-maintenance-validation | Immutable prospective protocols and bounded read-only MaintainX integration | [[Maintenance pilot]], [[Agent evaluation]] |
| 2026-10-21-operations-workspace | Lazy bilingual operations and validation workflows with actual API state | [[Maintenance pilot]], [[Design system]] |
| 2026-10-21-course-artifacts-untracked | Preserve local confidential artifacts while removing them from future source trees; history remains contained | [[Soul]], [[Team 3 Capstone]] |
| 2026-10-21-browser-journey-isolation | Exact browser-owned fixtures and scoped budgets preserve full sequential accessibility and approval checks | [[Design system]], [[Agentic OS]] |
| 2026-10-21-performance-status-presentation | Shared bilingual status badges and a five-state legend; counts without targets remain neutral | [[Design system]], [[Weighted KPIs]] |
| 2026-10-21-reviewer-maintenance-method-check | The analytics reviewer checks maintenance and reliability method (check 7, `domain_method`); the figures checker reads percentage points | [[Agent evaluation]], [[Agent team]] |
| 2026-10-21-kpi-register-aligned-with-power-bi | MTTR, first-time fix and repeat repair follow the team's Power BI Method page (definition 2); four report measures added, 18 in all; a KPI number never breaks across lines | [[Weighted KPIs]], [[Team 3 maintenance dataset]] |
| 2026-10-21-view-only-demo-mode | A no-sign-in demo is one read-only principal on generated data, refused next to a real provider; server half only, not to be switched on yet | [[Tenant isolation]], [[Managed identity]] |

| 2026-10-21-executive-analytics-advisory | Decision-led bilingual maintenance briefs, five-domain exposure, explicit source roles and instructor escalation without master-data mutation | [[Business report exports]], [[Evidence and claims]] |

All seven [[Analytics OS roadmap]] milestones have their records.
| 2026-10-21-connected-agent-workspace | Responsive connected workflow, bounded zoom and recorded asset inspection; lazy-view allocation | [[Agent collaboration]], [[Design system]] |
| 2026-10-22-worker-model-role-parity | Background execution honors model roles, concise local briefs and the shared privacy boundary; owner-selected one-model CPU profile | [[Model gateway]], [[Hermes orchestrator]], [[Model privacy]] |
| 2026-10-22-a-model-per-role | A model per role, written as provider and model | [[Model gateway]], [[Hermes orchestrator]] |
| 2026-10-22-built-in-roles | Built-in Hermes, agents and consultants play any role no model is configured for | [[Hermes orchestrator]], [[Model gateway]] |
| 2026-10-22-free-open-models-and-task-map | Free open-source model providers and a task-to-model map | [[Model gateway]] |
| 2026-10-22-hosted-open-source-models | Hosted open-source models for the hosted site | [[Model gateway]], [[Agentic OS]] |
| 2026-10-22-generated-ids-never-look-personal | Generated ids never look like a person's number | [[Model privacy]], [[Tenant isolation]] |
| 2026-10-22-arabic-rendered-analysis-reports | Arabic analysis content and rendered house-style reports; a report-language choice per run | [[Identity]], [[House style]], [[Governed pipeline]] |
| 2026-10-22-android-app-first-release | The Android app's first release, authored with a tested core; compiles once an SDK is reachable | [[Agentic OS]] |
| 2026-10-22-audit-fixes-period-order-grounding-privacy-identity | Audit fixes: period order, narrator grounding, role privacy, hosted identity, session retention | [[Governed pipeline]], [[Model privacy]], [[Managed identity]] |
| 2026-10-22-executive-command-centre | The Overview is the Executive Command Centre: a decision brief from real run figures | [[Design system]], [[Weighted KPIs]] |
| 2026-10-22-release-gate-slice-one | Release gate, slice one: illustrative gain label, no substituted models, uncapped approval queue, announced loading, read-only CI token | [[Release acceptance]], [[Governed pipeline]] |
| 2026-10-22-release-gate-slice-two | Release gate, slice two: rates never summed, a naive baseline and weak rule for every forecast, figures checked against cited evidence, approve after reading, JWT audience and issuer | [[Release acceptance]], [[Governed pipeline]], [[Approval gate]] |
| 2026-10-22-release-gate-slice-three | Release gate, slice three: decision inputs and record, signalling escalation, currency, landing on the Command Centre, hosted robustness, blind floors, model ledger, browser coverage; the P1 list closed | [[Release acceptance]], [[Governed pipeline]], [[Approval gate]] |
| 2026-10-22-decision-inputs-interface | The Analytics form collects an improvement and a cost per group; the run view shows the decision record | [[Governed pipeline]], [[Approval gate]], [[Design system]] |
| 2026-10-23-p2-slice-one | P2 slice one: a Wilson lower bound on the maintenance-risk verdict, declared splits, incomplete periods left out, loopback by default, idempotent run creation, wall-clock limits on custom stages and agent runtimes | [[Model validation]], [[Run lifecycle]], [[Custom stages]], [[Release acceptance]] |
| 2026-10-23-blind-v7-into-dev-causal-and-intent-fix | blind_v7 moves into dev; causal and intent rules fixed as linguistic families; no blind floor for those two until blind_v8; one contested "accounts for" case set aside | [[Agent evaluation]] |

| 2026-10-23-fail-closed-write-limiter | Fail-closed shared write limits; model transaction-boundary repair remains separate | [[Model gateway]], [[Tenant isolation]] |

| 2026-10-23-bounded-model-admission | Bounded admission before run transactions; tenant propagation and conservative settlement | [[Model gateway]], [[Tenant isolation]] |

- `2026-10-23-explicit-local-owner-workspace`: reuse local identity and SQLite only behind an opt-in loopback/browser boundary; never create shared passwords or weaken managed identity.


- `2026-10-24-kpi-review-context`: disclose missing metadata, preserve evidence navigation, and avoid invented ownership or numeric values. Local candidate; integration and rendered acceptance pending.
- `2026-10-24-column-grant-preflight`: SELECT-only PUBLIC and effective client column ACL checks; reviewed catch-up SQL unchanged. See [[Tenant isolation]].
- `2026-10-24-hermes-desktop-portable-package`: proposed portable Hermes package with a help-only preview and explicit local data/tool scope; preserves the web app and [[Agent runtimes and MCP]]. Activation remains separate.


- `2026-10-25-navigable-business-reports`: shared HTML navigation, bounded executive summaries and Word page fields; browser and Office verification kept distinct.

- `2026-10-25-explicit-chat-availability`: truthful model-readiness and bounded failure replies.
- `2026-10-25-selected-data-chat`: owned report context and bounded deterministic calculations.
- `2026-10-25-value-led-workflow`: task-stage navigation with preserved routes and human review.
- `2026-10-25-reference-workspace-layout`: shared reference-led shell and contextual source panel.

### 2026-10-25 — Dataset workspace composition

Use navigation-aligned shared panels and a responsive source/context split.
Validate the Datasets route itself, not only Assistant or Overview fixtures.
See the composition decision in docs/adr/2026-10-25-dataset-workspace-composition.md.

### 2026-10-25 - Shared visual identity and phone reflow

Separate navigation from evidence with semantic navy/blue/cyan tokens; retain dark mode and accessibility. Contain the phone shell without suppressing content scrolling. Full filenames remain available through bidirectional text and accessible actions. See docs/adr/2026-10-25-shared-visual-identity-and-mobile-reflow.md.

## Records added on the 27 October catch-up

One line per record, read from its title and decision; the record itself is the source (`docs/adr`).

| Record | Decision | Notes |
| --- | --- | --- |
| 2026-10-23-p2-slice-two | The store as publish target, logged failures and 503 on an outage, one error envelope, a required connector allowlist in production, recorded migrations, the optional-runtime CI job | [[Approval gate]], [[Tenant isolation]], [[Live data]] |
| 2026-10-23-p2-slice-three | A corrective repair time in the register, screened and versioned model cards, reversible cleaning, a store-backed rate limit with a per-owner model budget, one PostgreSQL connection per thread | [[Weighted KPIs]], [[Model validation]], [[Tenant isolation]] |
| 2026-10-23-p2-slice-four | Screened inputs for the generic models, probabilities with a Brier score, a bounded connection pool, structured model answers checked on the server with JSON mode, agreement by finding, eval cases for the knowledge search and the scorecard | [[Model validation]], [[Model gateway]], [[Agent evaluation]] |
| 2026-10-23-p2-slice-five-reviewer-benchmarks | Blind memos H, I and J and first-run floors for the brief-compliance, security-privacy and accessibility-i18n reviewers | [[Agent evaluation]], [[Agent team]] |
| 2026-10-23-p2-slice-six-interface | Committed font subsets pay for one-call asset evidence, the table note, one noun per destination, every upload through Datasets, as-of times, every pack in the parity test | [[Design system]], [[Verification and budgets]] |
| 2026-10-23-p3-slice-seven | The minor findings closed: signed shares, a robust anomaly rule, a noise floor for clustering, health liveness and detail, relative published paths, one connector error handler, orchestration problems recorded, quantity words in grounding, acceptance by a known reviewer, tool arguments held to their schema, one voice toggle name | [[Governed pipeline]], [[Evidence and claims]] |
| 2026-10-23-standards-lint-families-blind-v2 | Standards lint rules as linguistic families; blind_v1 into dev; blind_v2 scored once at 32% and floored | [[Agent evaluation]] |
| 2026-10-23-standards-lint-blind-v3 | blind_v2 into dev, the families widened; blind_v3 scored once at 14% with no false alarms and floored | [[Agent evaluation]] |
| 2026-10-23-database-publication-target | Durable SQL publication without a writable serverless vault; an approval is refused when its reviewed destination changes and a fresh review can be requested | [[Approval gate]] |
| 2026-10-23-platform-contract-and-application-builds | One API error contract behind sign-in, request-bound creation replay, indexed asset evidence, Android debug build with browser-engine journeys | [[Agentic OS]], [[Release acceptance]] |
| 2026-10-23-workbook-sheet-discovery | Workbook sheets listed without parsing; the first that looks like a table is read | [[Column mapping]] |
| 2026-10-23-number-words-and-run-to-failure | The figures checker reads counts in words; run-to-failure is judged on both sides | [[Agent team]], [[Evidence and claims]] |
| 2026-10-23-chart-axes-state-their-scale | Chart axes state their scale and zero is drawn at zero | [[Scoped dashboards]] |
| 2026-10-23-hosted-schema-preflight | Hosted startup validates the reviewed schema and never migrates it | [[Tenant isolation]], [[Backup and restore]] |
| 2026-10-23-managed-auth-onboarding | Managed sign-in with verified PKCE onboarding and passwordless recovery | [[Managed identity]] |
| 2026-10-23-model-failure-boundaries | Explicit model failure categories and recipient-bounded failover | [[Model gateway]], [[Model privacy]] |
| 2026-10-23-daemon-candidate | An opt-in database-backed worker daemon candidate with restart checks | [[Run lifecycle]] |
| 2026-10-23-analysis-workflow-recovery | Analysis lists recover after a failure and human review is explained in the workflow | [[Approval gate]] |
| 2026-10-23-bounded-specialist-loops | Opt-in, bounded and durable evidence-specialist loops | [[Agent collaboration]] |
| 2026-10-23-specialist-runtime-wiring | Default-off evidence-specialist API and worker wiring | [[Agent collaboration]], [[Agent runtimes and MCP]] |
| 2026-10-23-rmd-runtime-context | The requester's context survives runtime deadlines | [[Knowledge retrieval]] |
| 2026-10-23-run-source-handoff | A governed handoff carries an explicit run source reference | [[Run lifecycle]] |
| 2026-10-23-reference-aligned-report-evidence | A bounded, reference-aligned report evidence contract | [[Business report exports]], [[Evidence and claims]] |
| 2026-10-23-compact-executive-export | A compact executive opening with the complete technical evidence behind it | [[Business report exports]] |
| 2026-10-23-report-dubai-typography | Verified Dubai typography in derived executive exports | [[House style]], [[Business report exports]] |
| 2026-10-23-original-dubai-font-and-concise-decisions | The original Dubai font and concise decision presentation | [[House style]] |
| 2026-10-23-miyaar-dubai-executive-direction | Miyaar as asset-maintenance decision support in a Dubai Executive direction | [[Design system]], [[Maintenance decision support]] |
| 2026-10-23-task-first-miyaar-interface | A task-first mobile journey leads the Miyaar interface | [[Design system]] |
| 2026-10-23-report-motion-access | Selected reports and source-bound Motion review | [[Accessible motion]] |
| 2026-10-23-motion-script-gates | Motion drafts gated by script approval with bounded repair | [[Accessible motion]], [[Approval gate]] |
| 2026-10-23-browser-toolchain-audit | The browser toolchain's Zod advisory repaired without weakening the audit | [[Verification and budgets]] |
| 2026-10-24-executive-workspace-hierarchy | Executive workspace hierarchy with progressive disclosure | [[Design system]] |
| 2026-10-24-period-coverage-evidence | Period coverage evidence and bounded scenario claims | [[Evidence and claims]], [[Governed pipeline]] |
| 2026-10-24-undici-development-audit-patch | A compatible undici security floor for the development DOM runtime | [[Verification and budgets]] |
| 2026-10-27-dataset-deletion | A stored dataset can be removed unless an analysis reads it; the analyses are named, runs are never deleted, a live source forgets the snapshot | [[Column mapping]], [[Dataset joins]], [[Tenant isolation]] |
| 2026-10-27-stacked-datasets | A declared join may stack an export with the same columns under the main table, read with the main mapping, repeats dropped and counted, a source column for the breakdown; the script ceiling moves to 254 KB after trimming | [[Dataset joins]], [[Column mapping]] |
| 2026-10-27-week-grain | A week grain labelled by ISO week, chosen by the owner and never by the automatic roll-up; week values read and roll up to the month of their Thursday; forecasts continue weeks, the seasonal model uses 52 | [[Column mapping]] |
| 2026-10-27-miyaar-visual-layer | The Command Centre opens with a brief (greeting, counted sentence, one action, 14-day sparkline); the Miyaar hero carries an AI-core motif with a decorative glow; total ceilings 255 KB script and 35 KB style, first load unchanged | [[Design system]] |
| 2026-10-27-derived-columns | A mapping may declare up to five columns computed from the measures by arithmetic, checked when saved, computed after cleaning, available as the measure and carried through stacks | [[Column mapping]], [[Dataset joins]] |
| 2026-10-27-fiscal-year | A mapping names the month its fiscal year starts in; quarter and year labels read FY2026-Q1 and FY2026 by the end year; forecasts continue the fiscal calendar; day, week and month unchanged | [[Column mapping]] |
| 2026-10-27-tree-ensemble | A fifth model plugin: 16 bagged regression trees in the standard library, scored on held-out records against the training average and the straight line; inputs' shares of explained variance as association | [[Analytics OS roadmap]] |
| 2026-10-27-interactive-dashboard | Cross-filter by clicking a bar or a point, one saved dashboard view per owner and dataset on the server, and executive briefs that leave sections with nothing to report out and name them once; the script ceiling moves to 257 KB after trimming | [[Scoped dashboards]], [[Business report exports]], [[Tenant isolation]] |
| 2026-10-28-stage-report-sections | The comprehensive analysis report prints key metrics, claims and charts only when a stage produced them, and its limitations name the sections left out | [[Scoped dashboards]], [[Business report exports]], [[Approval gate]] |
| 2026-10-28-live-pipeline | The run timeline names the stage running now, marks it as the current step and announces its progress; progress still arrives by the run's poll; agent cards are a later slice | [[Run lifecycle]], [[Agentic OS]] |
| 2026-10-28-agent-cards | Each stage in the run timeline is a card stating its claims and passed checks; the card rules load with the runs view, not on first load; five unused string keys removed to hold the script ceiling | [[Run lifecycle]], [[Agentic OS]] |

- `2026-10-27-assistant-focus-and-context`: isolated candidate; native report disclosure beside composer, scoped session status and stronger first action. Browser acceptance pending.
