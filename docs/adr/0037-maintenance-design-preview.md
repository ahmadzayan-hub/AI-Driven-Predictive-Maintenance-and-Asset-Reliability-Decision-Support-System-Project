# ADR 0037 — Interactive maintenance design preview

**Status:** Accepted
**Date:** 2026-10-17

## Context

The owner requested the maintenance SaaS interface and chose the executive
maintenance overview as its starting screen. The existing governed analytics
workspace is operational code; the maintenance-domain contract and validated
prediction model are still being developed. A design must not imply that
fictional condition scores are operational measurements or evaluated predictions.

## Decision

- Add an opt-in `?design=maintenance` preview to the existing React application,
  loaded as a separate chunk with its own bilingual message pack and stylesheet.
  Keep the existing authenticated workspace as the normal entry point.
- Render the preview without the application store, API calls, model calls or
  service-worker registration. Only entirely fictional fixtures authored for the
  UI ship with it. No course files, customer data or personal identities are used.
- Provide executive, equipment, review, cost and model-evidence views. Site,
  period and equipment search scope every displayed sample calculation. Condition
  scores are explicitly a fixed snapshot and do not change with reporting period.
- Make sample reviews page-local and reset on reload. They do not create a work
  order, approve a report or dispatch an intervention. Existing data, report
  approval and analysis links leave the preview and use the normal workspace.
- Show formulas, denominators, artificial thresholds and source labels. Download
  only the filtered aggregate summary, marked as a fictional design fixture.
  Leave model performance unavailable until a governed evaluation is connected.
- Reuse design tokens, bundled fonts, language/theme stores, modal focus handling,
  loading and error boundaries. Navigation moves keyboard focus to the page
  heading; a disappearing reviewed row returns dialog focus there too.
- Add a separate browser suite over the static production build. It does not
  require a Python server and does not replace the production/API end-to-end suite.
  No package dependency or interface-budget increase is required.

## Consequences and verification

The owner can review a working bilingual interface before backend integration.
The preview has no persistence, tenancy, authorization decisions or maintenance
scheduling. Those remain governed application responsibilities. Future integration
must use server-side aggregate queries and retain the existing identity and
tenant boundaries (ADRs 0002, 0031 and 0032).

Unit tests check arithmetic, global filter consistency, empty scopes, local
review behavior, focus recovery and Arabic search. The browser suite checks
downloads, keyboard dialogs, reload behavior, no API requests, English/Arabic
layouts, light/dark themes, overflow and axe rules. Results and remaining
limitations are recorded in the session log. Design handoff:
[Maintenance UI specification](../design/MAINTENANCE_UI_SPEC.md).
