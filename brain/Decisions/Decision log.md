---
type: decision
aliases: [ADR index, Architecture decisions]
tags: [decisions]
status: active
updated: 2026-10-23
review_every_days: 30
sources: [docs/adr]
---

# Decision log

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

