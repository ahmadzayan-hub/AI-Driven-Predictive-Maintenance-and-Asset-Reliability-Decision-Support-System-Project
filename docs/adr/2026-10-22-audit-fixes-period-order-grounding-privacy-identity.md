# Audit fixes: period order, narrator grounding, role privacy, hosted identity, session retention

Date: 2026-10-22 · Status: Accepted (platform assessment, 22 October;
`docs/audits/SAAS_PLATFORM_ASSESSMENT.md`)

## Context

A code-grounded assessment of the platform reproduced five defects. Each is
small, in code the pipeline or the API already owns, and fixed here rather than
left on a backlog.

1. **Periods sorted as text in unmapped runs.** Without a saved column mapping,
   the preparer ordered the trend with `sorted()` on raw labels. A series rising
   ten a month from January to August came out as "down 4% on the latest period,
   off by about 11% when tested". Every trend, forecast, anomaly, change and
   driver reading inherited the wrong order.
2. **The model's executive summary was never grounded.** Orchestrator notes drop
   a sentence that adds a figure; the narrator's summary did not.
3. **Model roles skipped the personal-data boundary.** Hermes, agent and
   consultant calls sent verified sentences to providers without the
   `model_privacy` check the narrator and the assistant apply.
4. **A hosted deployment with a shared database and no sign-in ran as the local
   owner.** On Vercel with `DATABASE_URL` set and no provider, every visitor was
   `local-owner` with approve rights over every tenant's data.
5. **Session trimming crossed tenants.** Keeping the 32 newest sessions across all
   owners let one tenant's activity delete another's conversations.

## Decision

1. The cleaner labels the period column for unmapped runs with the mapping
   parser already used for mapped ones (`server/mapping.period_labels`), so dates
   in any readable form order by calendar. Bare month names order by calendar
   under a numbered label (`01 Jan`). A column that does not read as periods keeps
   the order recorded in the data, never alphabetical, and the cleaner says so in
   a limitation claim.
2. A model summary that states a figure not in the verified facts is set aside;
   the facts become the summary, and the report says why, in the run's language.
3. Every model role passes `model_privacy.blocks_model` on the run's privacy
   decision and the exact outgoing text. A run that carries personal data has
   every role played by the built-in writer (`ModelRoles.restricted()`). Hermes'
   plan, written before the privacy stage, sends only the goal and stage titles,
   which are scanned like any other text.
4. `build_identity` refuses to start on Vercel with `DATABASE_URL` and no
   provider. `AGENTIC_OS_DEMO=1` is the explicit opt-in for a view-only showcase
   on a shared database.
5. `trim_sessions` is per owner. Creating a session trims that owner only.

## Consequences

- Unmapped runs on month-named or day-first data now give the right trend; runs
  on ISO dates are unchanged. A dataset whose period labels are not dates reads
  as recorded, which is what a reader can check.
- A hosted deployment that was relying on the silent local fallback will fail
  to start until a provider or the demo flag is set. That is the point.
- Model roles on a run with personal data produce built-in notes, labelled.

## Verification

`tests/test_analytics.py` (`UnmappedPeriodOrderTestCase`, `NarratorGroundingTestCase`),
`tests/test_orchestration.py` (`PrivacyBoundaryForRolesTestCase`),
`tests/test_demo.py` (`test_vercel_with_a_shared_database_needs_sign_in_or_an_explicit_demo`),
`tests/test_tenancy.py` (`SessionRetentionPerOwnerTestCase`). The first defect was
reproduced before the fix with an eight-month rising series and a `Month` column
of month names.
