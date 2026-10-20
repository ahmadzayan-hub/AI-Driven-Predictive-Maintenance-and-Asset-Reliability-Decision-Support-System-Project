# Project assessment and corrective work

Reviewed: 2026-10-20. Baseline: `cf45f14fee7d6d045190d01a54eccae8f4f82078`,
on `main`. Scope: the public software repository, synthetic local execution,
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

The dated decisions in `docs/adr/2026-10-20-*.md` explain behavior and tradeoffs.
Current executed commands, counts, skips and budgets are kept in
[README testing](../../README.md#testing), the canonical verification record.
Reproduction scripts, before/after observations, complete local logs and the
dependency inventory are retained outside the public repository.

Complete Linux CI passed on integrated source `390f4c6`, including both browser
suites. The full Windows frontend run remains resource-sensitive even with
one worker; its failed attempts are retained, and no complete Windows UI
validation is claimed. This does not replace real-device and assisted-use
acceptance.

## Coverage and remaining limits

| Area | Evidence and judgment |
| --- | --- |
| Product and usability | The end-to-end workflow is implemented. Automated desktop/mobile and EN/AR checks cover key journeys; observed manager tasks, real device installation and assistive-technology acceptance remain necessary. |
| Architecture and persistence | Modular stages and two storage adapters support testing and recovery. Atomic stages improve correctness but hold transactions while work executes; SQLite serializes writers. Measure contention and service capacity before expanding use. |
| Data quality and analytics | Mapping, reconciliation, joins, denominator handling and model-input timing are testable. Source semantics, observation grain, stable asset identifiers and operational thresholds still require a domain owner. |
| AI and evaluation | Synthetic evaluations meet configured floors. They are limited by their labels and development history; intent holdout macro recall is 72%, and the existing adversarial causal-wording probe reports 6% recall. Heuristic screening is not exhaustive anonymization or causal validation. |
| Security and privacy | Confirmed tenancy and detected-PII paths were repaired. This is a source-level review with regression tests, not a penetration-test certificate. Historical public exposure remains an owner decision below. |
| Operations and recovery | Local crash/recovery, worker and database checks provide execution evidence. Actual hosted identity, durable storage, scheduled refresh, direct egress, provider access, backup restoration and alert ownership require deployment-specific acceptance. |
| Dependencies and supply chain | Current dependency audits and the SBOM/license gate are recorded with verification. Versions, advisories and license obligations must be maintained continuously; a passing audit is a point-in-time result. |
| Maintainability | Small modules, dated ADRs and extensive tests help review. Keep one canonical verification record, synchronize product docs with shipped behavior, and avoid using self-written evaluation cases as independent acceptance. |
| Commercial readiness | Organizational tenancy, service ownership, support, pricing and billing acceptance are product decisions. The current owner-scoped implementation should not be described as validated organization administration. |

## Release gates that code alone cannot close

1. **Contain historical public private/course material — repository owner.**
   Metadata reinspection confirms protected paths on five historical branch
   tips. No protected contents were downloaded. Removing current files would
   leave historical copies. Recommended immediate containment is to make the
   repository private while retaining team access, then agree a reviewed
   remediation with affected owners and GitHub. This requires an owner decision:
   AGENTS.md prohibits branch deletion and history rewriting. No acceptance or
   destructive remediation is implied by this review.
2. **Validate the hosted release — service owner.** Run managed-auth isolation,
   worker/refresh, database restart and restore, error/alert, and sanitized
   provider checks against an explicitly approved deployment of the corrected
   commit. Record actual URLs, commit identity and outcomes without credentials.
   Hosting metadata currently identifies an older Git production commit
   (`42e53d00`); the fixes in this review are not proven deployed.
3. **Accept the maintenance decision — maintenance/domain owner.** Supply an
   approved input-timing and KPI register, an independently chosen historical
   holdout or prospective pilot, false-positive/false-negative consequences,
   and a manager acceptance task. Report calibration, cohort exclusions,
   uncertainty and operational value before enabling consequential use.

No gate is accepted on somebody else's behalf. Prioritize these gates before
adding more agents, forecasts, dashboard screens or commercial claims.
