---
type: project
aliases: [Agentic OS project]
tags: [project]
status: active
updated: 2026-10-31
review_every_days: 14
sources: [docs/implementation/PLATFORM_RELEASE.md, README.md, docs/ROADMAP.md, docs/VERCEL_DEPLOYMENT.md, project-progress.md, docs/RMD_EVIDENCE.md, docs/assessments/2026-10-20-project-review.md, docs/assessments/2026-10-21-saas-competitive-benchmark.md, docs/adr/0023-the-analytics-workspace-interface.md, docs/adr/0024-the-dataset-api.md, docs/adr/0028-views-load-on-demand.md, scripts/verify.py, docs/adr/0058-executive-dashboard-agent-and-scoped-evidence.md, docs/adr/2026-10-31-reliability-model.md, docs/adr/2026-10-31-risk-ranking.md, docs/adr/2026-10-31-what-if-scenarios.md, docs/adr/2026-10-31-data-health.md, docs/adr/2026-10-31-snapshot-drift.md]
---

# Agentic OS

The engine in this repository, described in [[Identity]]: a governed business-analytics assistant with a web workspace and a command-line interface. It powers **AI-Driven Predictive Maintenance and Asset Reliability Decision-Support System SaaS Project** (ADR 0036). The public product scope is in `docs/PROJECT_CHARTER.md`; the engine name and technical identifiers remain stable.

## Where it lives

- **Repository:** `ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project`, named by [[Decision log]] 0043 and made temporarily private with owner approval on 20 October to contain historical exposure. All collaborator permissions and branch tips were preserved; anonymous repository and API access returned 404. The earlier names `ahmadzayan-hub/agentic-os-final-project` and `ahmadzayan-hub/11` redirect, but repository and CI evidence now require authorized access.
- **Default and integration branch:** `main`, verified on 20 October. The owner authorized merging all completed work; PR #15 brought the Miyaar workspace and local AI profile into it with both parents preserved. Executive business exports and performance colors are integrated; the latter merged at `98f33c4`, preserving incoming main through `6c5170c` and both parents. The Desktop and active Miyaar checkouts select `main`; the owned local runtime was rebuilt and restarted with its existing database. Older feature refs are retained snapshots of work already landed.
- **Production:** read-only metadata on 20 October identifies the older `42e53d00` Vercel deployment behind Vercel Authentication. Current application identity, durable storage and the corrected source still require hosted acceptance; earlier owner-access observations are historical.

## What it does today

- The platform shares an authenticated API schema and readable error contract,
  retains exact-request retry identity across a web reload and queries owned
  asset evidence across stored history. Missing KPI cards have a retry action;
  chart tables retain all plotted sample values. The [[Approval gate]] supports
  transaction-only SQL publication and a fresh review for a changed destination.
  The Kotlin/Compose Android app has a built, signature-verified debug APK;
  Windows Edge and macOS WebKit actual-API journeys are tested. Windows/iOS use
  the PWA. Device, secure credential storage, store and production acceptance
  remain distinct. The application handoff and README hold the observed scope.

- RMD Evidence connects private document/workbook ingestion, confirmed mappings,
  immutable record-grain calculations, investigation review, bilingual views,
  authorized [[Knowledge retrieval]] and a real report [[Approval gate]].
  The reuse map and acceptance boundaries are in docs/RMD_EVIDENCE.md.
  The owner omitted unavailable source files from this delivery; synthetic
  verification does not imply those sources were studied.
  Real API-backed desktop and phone journeys pass in English and Arabic through
  evidence review and keyboard approval to confirmed publication; manual
  comprehension and production performance remain separate acceptance work.
  Integration retains main's run safeguards and chart scales. The requester
  remains scoped across deadline workers; [[Knowledge retrieval]] describes
  that authorization boundary and its regression evidence.

- Workspace conversation has an explicit hosted [[Model gateway]] option and
  structured [[Agent runtimes and MCP|LangGraph decisions]]. Model failure is
  disclosed without a second slow request; exact help/status shortcuts answer
  directly. Local and hosted activation are separate. The hosted synthetic
  acceptance probe is blocked by the team's payment-card requirement; this
  activation did not release hosted model support. README holds actual tests
  and latency limits.

- A restrained collaboration view in Runs connects the [[Hermes orchestrator]] to observed workflow groups, stage results, current evidence and recent activity. The [[User]] chose brief handoffs and expandable details. Pause live view holds only the panel; the [[Approval gate]] remains separate. English/Arabic and reduced motion follow the [[Design system]]. The dated collaboration decision and `docs/design/AGENT_COLLABORATION_MOTION.md` explain why this is not a message transcript; README records actual verification.

- The 20 October review repaired published-note tenancy, detected-personal-data model handoffs, worker resource policy, atomic quota/run operations, maintenance cohort comparisons and bilingual evidence presentation (`1dd73ae`). The [[Approval gate]] remains human-controlled. Git synchronization to `main` cannot automatically publish production; the privacy, hosted-operation and domain acceptance gates remain explicit in the assessment. [[Session lifecycle]] verification records are kept in README.
- Follow-up `ede59b1` separates domain-model types and source chronology from chart mappings, keeps automatic groupings conservative, refuses unsupported single-dataset overrides, enforces browser resource policies and locks server dependencies. The [[Governed pipeline]] retains explicit mapping authority and privacy exclusions; independent [[Agent evaluation]] and domain acceptance are still required.
- Final combined-source Linux CI passed at `fadc18d`, including both browser suites after their mappings were made explicit. README is the verification record. The [[Approval gate]] still applies to production release and independent domain acceptance. Immediate historical privacy containment is verified; remediation before any public release remains owner work.

- Chat in English or Arabic that maps a sentence to a typed action, in the Miyaar workspace (ADR 0054).
- An opt-in local instruction model and authenticated Whisper voice input with editable drafts (ADR 0055). Setup and bounded actual acceptance are recorded in `docs/LOCAL_AI_SETUP.md` and `README.md`; device checks and production acceptance remain separate.
- Analyses through the [[Governed pipeline]], sequenced by the [[Hermes orchestrator]], of a dataset in CSV, TSV, Excel, JSON or JSON Lines (ADR 0024), joined with up to four others on declared keys (ADR 0030).
- A six-page dashboard per analysis over its cleaned table (ADRs 0031, 0032), optional models each tested against a baseline (ADR 0033), and live sources that refresh on a schedule and push changes to open pages (ADR 0034).
- A scoped executive overview and read-only evidence agent (ADRs 0058–0059): controlled KPIs, populations, review priorities and calculation references in English and Arabic RTL. Business exports use standalone HTML or genuine Word DOCX, with native Print / Save as PDF. Timestamp plus content revision binds each file to its prepared evidence. Models remain run-wide; briefs do not approve reports. Claude development instructions are integrated; hosted Artifact availability is separate.
- Performance colors with configured per-analysis targets (the 20 October performance-color decision): red bad, blue okay and green good, with status words in both languages and business exports. Directions, inclusive boundaries, controlled units and sources persist in separate audited history. Unknown/missing values stay neutral; target edits change the display policy rather than approvals or the measured figures. The [[Decision log]] links the decision; the [[Design system]] defines the shared interface vocabulary.
- Reports with claims linked to calculations, published through the [[Approval gate]].
- On the maintenance profile since 31 October 2026: a failure pattern per asset class (Weibull, running assets censored), assets ranked by the chance of failing within 90 days times recorded cost per failure, and planned-replacement intervals compared with run to failure. Each is advisory and stays behind the [[Approval gate]]. Every run also states its data health (measure values usable as recorded, each loss named), and each live-source snapshot is compared with the previous one, with a note when it moved materially.
- Optional narration through the [[Model gateway]]; extension through [[Custom stages]] and [[Agent runtimes and MCP]].
- The bundled [[Sample sales data]] works without an upload.
- An Overview of key figures, the latest findings and the approval queue, and a Datasets view that analyses a stored dataset again by reference. Both follow the [[Design system]].

## Verified state on 2026-10-17

- After views began loading on demand (ADR 0028): `python scripts/verify.py --e2e` with PostgreSQL passed 863 Python tests (16 skipped), the brain check, the type check, 66 frontend unit tests, the build and the budget. First-load JavaScript was 85.7 of 100 KB. End-to-end: 69 passed and 3 skipped by design; the 2 new checks passed after a fix to the test. Lighthouse mobile scored 98, against 99 before.
- `python scripts/verify.py` with PostgreSQL passed all six steps. That run had 851 Python tests; the suite has since grown to 856, all passing with PostgreSQL and the same 16 optional-library skips. It also passed the brain check, the type check, 60 frontend unit tests, the build, and the interface budget (JavaScript 96.7 of 100 KB). The end-to-end suite was not run on this date.
- Every classifying agent is measured ([[Agent evaluation]]).

## Verified state on 2026-10-16

- `python scripts/verify.py --e2e`, with PostgreSQL, passed all seven steps: 719 Python tests with 16 optional-library skips, the brain check, the type check, 54 frontend unit tests, the build, the interface budget (JavaScript 92.9 of 100 KB gzipped, fonts 119.4 of 120 KB), and 63 of 66 end-to-end checks, with 3 skipped by design.
- Lighthouse on the self-hosted server: Performance 99 on mobile in each of three runs and 100 on desktop, with Accessibility, Best Practices and SEO at 100. Before the server compressed and cached the build, mobile Performance was 86 to 88 (ADR 0023, amendment).

These counts go stale fast; `README.md` is the one place where they are maintained.

## Direction

The 21 October commercial comparison, `docs/assessments/2026-10-21-saas-competitive-benchmark.md`, recommends validating a bilingual reliability decision-support layer connected to an existing maintenance system. Official product and named customer evidence from MaintainX, Fiix, Augury and IBM Maximo shows the importance of maintenance-action closure, operational integration and domain validation. This is a recommendation for [[User]], not an approved business strategy. The [[Analytics OS roadmap]] and [[Agent evaluation]] should retain the distinction between implemented controls, software tests and measured customer outcomes; the [[Approval gate]] remains human-controlled.

The [[Analytics OS roadmap]]'s seven milestones were built by 17 October 2026: several datasets, dynamic inputs, a dashboard, models and [[Live data|live data]]. Decisions are in the [[Decision log]].

## Related

- [[User]], who owns it.
- [[Agent team]], the subagents and review loop that check this project's work and deliverables.
- [[Team collaboration]], for how teammates contribute.
- [[Session lifecycle]], for how work on it is run.

## Maintenance pilot

[[Maintenance pilot]] connects reviewed evidence to explicitly authorized work and recorded outcomes. Prospective protocols and baseline probabilities precede outcome adjudication; hosted and customer acceptance remain separate.
