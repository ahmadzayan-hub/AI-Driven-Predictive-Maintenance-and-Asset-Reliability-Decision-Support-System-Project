# Project assessment and corrective work

Reviewed: 2026-10-20. Baseline: `cf45f14fee7d6d045190d01a54eccae8f4f82078`,
on `main`. Scope: the then-public software repository, synthetic local execution,
SQLite and an isolated PostgreSQL service, CI evidence, and read-only hosting
metadata. Private course datasets and submission files were not retrieved.

## Assessment

The project has a substantial working foundation for governed analytics:
structured ingestion, explicit mappings, controlled KPI definitions, traceable
calculations, human approval, bilingual dashboards, and persistent state.
The maintenance model contract is stronger than a generic classifier because
it records input timing, compares chronological holdouts with simple baselines,
and can report unsupported or weak results.

The appropriate next milestone is a controlled pilot after the release gates
below. The repository does not establish commercially ready SaaS operation,
prospective failure prediction, optimal maintenance scheduling, or realized
savings. Passing software tests cannot establish those outcomes.

## Confirmed defects corrected

| Priority | Reproduced problem | Correction and regression evidence |
| --- | --- | --- |
| High | Another tenant could enumerate and read published vault notes even though the originating run was inaccessible. | Both reads join notes to run ownership; tests cover viewers, auditors, admins and no filesystem fallback. `tests/test_published_note_access.py`. |
| High | A synthetic email used as a group label reached the narrator despite the privacy stage detecting it. | Detected main/joined PII and exact outgoing text keep narration, assistant context and runtime/tool replies on the deterministic path. Private report history remains protected after switching runs. `tests/test_model_privacy_boundary.py`. |
| High | Concurrent dataset/run requests could exceed quotas; interrupted creation left partial task plans. | Owner-scoped transactions cover admission, deduplication, run and task creation. Both adapters exercise independent competing connections and injected failure. `tests/test_atomic_admission.py`. |
| High | Concurrent advancement could mistake a live task for an orphan and execute it twice. | Run-scoped transactions serialize advance, approval, pause and cancel; reconnect cannot replay a statement inside a lost transaction. `tests/test_atomic_admission.py`, `tests/test_recovery.py`. |
| High | Missing model inputs changed the evaluated population while the baseline retained excluded records, fabricating improvement. | Model and baselines use the same eligible training and held-out cohorts; both classes must remain measurable; category levels come from training data. `tests/test_maintenance_targets.py`. |
| High | A model clearing a relative baseline margin but still too close to chance recommended intervention. | Reports require the actual useful verdict; weak-model claims and recommendations retain the limitation. `tests/test_maintenance_targets.py`. |
| Medium | Scheduled workers did not honor the API's configured resource limits or environment-selected configuration. | Worker startup loads the same configuration, vault path, gateway environment and quota policy. `tests/test_worker_limits.py`. |
| Medium | Allowed cross-origin managed-auth requests failed preflight. | Explicitly allow the Bearer Authorization header. `tests/test_published_note_access.py`. |
| Medium | Rounded intermediate totals caused false reconciliation failures for many fractional groups; Arabic model claims omitted a required figure. | Keep internal aggregate precision and round at presentation; preserve EN/AR figure parity for useful and weak models. `tests/test_analytics.py`, `tests/test_maintenance_targets.py`. |
| Medium | Asset evidence stopped after eight recent runs; KPI state could belong to the previous run or language. | Search the complete returned list in bounded batches, disclose the API's existing 50-run cap, and bind KPI state to run and language. `frontend/src/features/assets/AssetIntelligenceView.test.tsx`. |
| Medium | Truncated dashboard series looked complete; some Arabic stage/state labels and KPI formula text were misleading. | Bilingual truncation notices, translated states/titles, and correct numerator/denominator wording. Dashboard and intake regression tests. |
| Medium | Expired credentials left JSON and download flows in a stale session. | A shared unauthorized event clears the current credential, while delayed refusals for an older token cannot log out a newly authenticated user. API and store tests. |
| Medium | Missing API dependencies silently skipped large parts of local validation; the full command omitted two CI checks. | Dependency preflight now gates Python execution; native contracts and the Miyaar browser suite are included. `tests/test_verify.py`. |
| Medium | Git synchronization to `main` could implicitly trigger production despite the repository's approval requirement. | Vercel Git deployment is disabled for `main`; CI continues and release requires a separately approved deployment. `tests/test_release_policy.py`. |
| High | Presentation roles removed valid maintenance predictors, while chart date grain changed the evaluation split. | Contract types and retained source dates now govern domain evaluation; explicit ignores and privacy exclusions remain effective through joins. Synthetic full model-card comparisons cover mapping and date grain. `tests/test_maintenance_mapping.py`. |
| Medium | Automatic breakdown selection chose unique record identifiers and produced a recommendation about individual row IDs. | Conservative grouping chooses repeated categories, excludes identifier/date/detected-personal fields, and preserves explicit mappings. Ungrouped experiment planning carries its own assumption. `tests/test_analytics.py`. |
| Medium | A single-dataset `breakdown` request was accepted and silently ignored. | Return localized validation before writes or quota consumption; callers use the saved mapping. Joined overrides retain their existing contract. `tests/test_breakdown_contract.py`. |
| Medium | Application responses and the hosted static shell lacked a browser Content Security Policy. | Scoped policies allow required resources and the fixed prepaint hash, deny arbitrary inline scripts, preserve export policy, and cover Vercel's bare `/api` shell fallback. `tests/test_content_policy.py`, `frontend/e2e/csp.spec.ts`. |
| Medium | Dependency floors let the same commit install different Python versions. | Hash-checked, cross-platform transitive lock preserves reviewed versions; isolated audit tooling does not change the tested environment. Fresh installation, dependency consistency, audit and SBOM checks cover it. |

Incoming work from `79501e9`/`2de5d25` is also preserved: explicitly declared
metric direction prevents inverted downtime advice, and independent
per-group recomputation strengthens reconciliation. These complement the
original precision fix. Integration is recorded at `b402def`; the additional
mapping, request, browser-policy and dependency corrections are `ede59b1`.
`fadc18d` aligns privacy and browser fixtures with deliberately saved mappings
while retaining their original privacy, export and KPI assertions.

The dated decisions in `docs/adr/2026-10-20-*.md` explain behavior and tradeoffs.
Current executed commands, counts, skips and budgets are kept in
[README testing](../../README.md#testing), the canonical verification record.
Reproduction scripts, before/after observations, complete local logs and the
dependency inventory are retained outside the repository.

The [final complete Linux CI](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/39446235305)
passed on combined source `fadc18d`, including both browser suites. The earlier
green integration at `390f4c6` is retained as historical evidence. The full
Windows frontend run remains resource-sensitive even with one worker; its
failed attempts and the later browser-server startup failure are retained,
and no complete Windows UI validation is claimed. This does not replace
real-device and assisted-use acceptance.

## Measured review outcome

The nine equally weighted gates measured
**66.7% → 66.7% → 66.7% → 77.8% → 77.8%** across five rounds.
All six automated gates passed: executed full validation,
dependency audits, the dependency-license policy, measured agent floors,
documentation contracts and patch hygiene. The final source check requires
every change after CI-tested `fadc18d` to be documentation or operating guidance; it makes
no exception for later application, configuration or test edits.

The initial loop stopped after two rounds without a score increase, with
three owner gates open. The owner's subsequent approval and verified private
conversion closed immediate privacy containment. Two further measured rounds
confirmed **seven gates passed, no accepted exceptions, two gates open**;
the loop then reached its five-round bound. Hosted-release acceptance belongs
to the service owner and independent maintenance validation to the domain owner.

This is checklist completion, not a product-quality, security or
prediction-accuracy rating. The plan, score history and detailed evidence are
retained outside the repository. The completed containment and its remaining
limits are recorded below.

## Coverage and remaining limits

| Area | Evidence and judgment |
| --- | --- |
| Product and usability | The end-to-end workflow is implemented. Automated desktop/mobile and EN/AR checks cover key journeys; observed manager tasks, real device installation and assistive-technology acceptance remain necessary. |
| Architecture and persistence | Modular stages and two storage adapters support testing and recovery. Atomic stages improve correctness but hold transactions while work executes; SQLite serializes writers. Measure contention and service capacity before expanding use. |
| Data quality and analytics | Mapping, reconciliation, joins, denominator handling and model-input timing are testable. Source semantics, observation grain, stable asset identifiers and operational thresholds still require a domain owner. |
| AI and evaluation | Synthetic evaluations meet configured floors. They are limited by their labels and development history; intent holdout macro recall is 72%, and the existing adversarial causal-wording probe reports 6% recall. Heuristic screening is not exhaustive anonymization or causal validation. |
| Security and privacy | Confirmed tenancy and detected-PII paths were repaired. This is a source-level review with regression tests, not a penetration-test certificate. Owner-approved private visibility now contains repository access; historical remediation before any re-publication remains open. |
| Operations and recovery | Local crash/recovery, worker and database checks provide execution evidence. Actual hosted identity, durable storage, scheduled refresh, direct egress, provider access, backup restoration and alert ownership require deployment-specific acceptance. |
| Dependencies and supply chain | Current dependency audits and the SBOM/license gate are recorded with verification. Versions, advisories and license obligations must be maintained continuously; a passing audit is a point-in-time result. |
| Maintainability | Dated ADRs and regression tests help review, but `server/analytics.py` remains large. Extract stages behind their tested contracts in a separate change. Keep one canonical verification record and avoid treating self-written evaluation cases as independent acceptance. |
| Commercial readiness | Organizational tenancy, service ownership, support, pricing, billing and the project's own license remain owner decisions. The current owner-scoped implementation should not be described as validated organization administration. |

## Release gates that code alone cannot close

1. **Immediate privacy containment — completed with repository-owner approval.**
   The owner approved temporary private visibility on 20 October. Authenticated
   metadata confirms the change; all four access entries and all 17 branch tips
   were preserved, and anonymous web/API requests returned 404. No forks or
   Pages site existed at conversion. Historical private/course material remains
   in Git history, accessible to authorized collaborators; no protected contents
   were downloaded for this action. Existing external copies cannot be recalled
   by visibility changes. Agree historical remediation with affected owners and
   GitHub before any re-publication, which requires explicit owner approval.
   Branch deletion and history rewriting remain prohibited. See the
   [containment decision](../adr/2026-10-20-temporary-private-containment.md).
2. **Validate the hosted release — service owner.** Run managed-auth isolation,
   worker/refresh, database restart and restore, error/alert, and sanitized
   provider checks against an explicitly approved deployment of the corrected
   commit. Record actual URLs, commit identity and outcomes without credentials.
   Hosting metadata currently identifies an older Git production commit
   (`42e53d00`); the fixes in this review are not proven deployed.
   Read-only GitHub metadata also shows `main` unprotected and no active
   rulesets. The GitHub connector lacked administration access; the later
   containment action verified the existing Git account has administrator access.
   Agree and apply branch/release governance compatible with the team's
   standing main-branch workflow; only visibility was changed for containment.
3. **Accept the maintenance decision — maintenance/domain owner.** Supply an
   approved input-timing and KPI register, an independently chosen historical
   holdout or prospective pilot, false-positive/false-negative consequences,
   and a manager acceptance task. Report calibration, cohort exclusions,
   uncertainty and operational value before enabling consequential use.

No remaining gate is accepted on somebody else's behalf. Prioritize these gates before
adding more agents, forecasts, dashboard screens or commercial claims.
