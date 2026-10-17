# Interface validation record

Date: 2026-10-17. This record distinguishes source review, executable checks and design previews.

## Local evidence

- The pure Python analytics, assistant, utilities and documentation subset passed. Full API tests stalled inside FastAPI TestClient's AnyIO portal in this execution environment; the two stalled test processes were stopped. No full local-suite pass is claimed.
- Dependency-free snapshot, event, custom-stage and calculation-table checks passed when executed directly with Node. The frontend package cache is incomplete; npm cannot reach its configured proxy under the current command sandbox, so TypeScript, Vitest, build and browser verification are pending GitHub Actions.
- The first deterministic review scorecard was 40%: brain and dependency-free checks passed; the three package-dependent gates did not run successfully. This is not a product-quality score. No gate was accepted on the user's behalf.
- Two independent read-only source reviews found skip-link/hash routing, exact-report availability, Arabic comprehensive calculation headers, dialog overflow, draft recovery, hidden install-event capture and chunk-retry issues. Fixes and regression checks were added. Runtime results are recorded below only after CI produces them.
- Editable Figma screens were rendered and visually inspected. These are design previews; they do not prove browser behavior, WCAG conformance, native installation or user task timing.

## Required CI evidence

The existing CI workflow runs Python with PostgreSQL, frontend unit tests, typecheck/build, Playwright and automated accessibility checks. This change also adds brain/snapshot contracts, the existing interface-budget function, and an `agentic-ui-evidence` artifact containing the production bundle, real browser screenshots and any test traces.

CI commit, workflow URL, measured sizes and final results: pending the branch update and completed workflow. Do not copy historical README counts into this section as current evidence.

## Acceptance targets

| Target | Evidence required | Current status |
| --- | --- | --- |
| Manager identifies main finding and next action within ten seconds | Timed representative-manager usability task | Not observed; finding and decision are explicit in the design and implementation |
| Evidence reached within two interactions | Browser journey from finding card to evidence | Regression added; execution pending |
| Keyboard-only approval | Browser focus/Enter and dialog navigation | Regression added; execution pending |
| Interrupted draft recovered | Navigate, reload and failed-send recovery | Component/browser regressions added; execution pending |
| Arabic phone journey | Real Arabic report at 390 px; 320 px overflow check and axe | Regression added; execution pending |
| Both themes, larger text, landscape and reduced motion | Browser/device review | Reduced-motion existing suite retained; additional manual/device review remains open |
| Windows, Android and iOS installation | Actual platform installation and launcher test | Not observed; browser-guided PWA support only |
| Bundle and Web Vitals | Production sizes; Lighthouse or real-user performance | CI bundle measurement pending; no LCP/CLS/INP result claimed |

Open items remain unaccepted until evidence or an explicit named-owner decision resolves them.
