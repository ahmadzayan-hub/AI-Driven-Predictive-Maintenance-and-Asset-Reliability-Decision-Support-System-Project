# Interface validation record

Date: 2026-10-17. This record distinguishes source review, executable checks and design previews.

## Local evidence

- The pure Python analytics, assistant, utilities and documentation subset passed. Full API tests stalled inside FastAPI TestClient's AnyIO portal in this execution environment; the two stalled test processes were stopped. No full local-suite pass is claimed.
- Dependency-free snapshot, event, custom-stage and calculation-table checks passed when executed directly with Node. The frontend package cache is incomplete; npm cannot reach its configured proxy under the current command sandbox, so TypeScript, Vitest, build and browser verification are pending GitHub Actions.
- The first deterministic review scorecard was 40%: brain and dependency-free checks passed; the three package-dependent gates did not run successfully. This is not a product-quality score. No gate was accepted on the user's behalf.
- Two independent read-only source reviews found skip-link/hash routing, exact-report availability, Arabic comprehensive calculation headers, dialog overflow, draft recovery, hidden install-event capture and chunk-retry issues. Fixes and regression checks were added. Runtime results are recorded below only after CI produces them.
- Editable Figma screens were rendered and visually inspected. These are design previews; they do not prove browser behavior, WCAG conformance, native installation or user task timing.

## Local evidence, Claude Code session, against `d53397d`

`python scripts/verify.py --e2e` with PostgreSQL, on 2026-10-17. This environment has npm, PostgreSQL 16 and a pre-installed Chromium, so the package-dependent gates ran here.

- **First run of `8a72368`:**
    - The type check failed with 19 errors: six new strings sat in the plural dictionaries. Fixed in `5738d39`.
    - Nine browser checks then failed. One was an app bug: a saved goal draft hid the dataset the reader had just chosen, now scoped per dataset in `ecf0d78`. The rest were tests that predate the kept-alive views and grouped bands.
- **Result on `d53397d`, all seven steps passed:**
    - 865 Python tests, 16 skipped for optional libraries;
    - brain check clean;
    - type check;
    - 84 frontend unit tests;
    - production build;
    - interface budget;
    - 80 browser checks: 76 passed, 4 skipped by design because each covers one viewport.
- **Budget, gzipped:**
    - first-load JavaScript 91.9 of 100 KB;
    - all JavaScript 117.2 of 160 KB;
    - largest on-demand chunk 7.3 of 30 KB;
    - CSS 9.2 of 10 KB;
    - fonts 119.4 of 120 KB.
    - Before ADR 0029, first load was 85.7 KB and CSS 7.7 KB. CSS has 0.8 KB left.
- **Lighthouse 13.4.1, mobile, three runs on the same build (median):**
    - Performance 99, Accessibility 100;
    - first and largest contentful paint 1.55 s;
    - total blocking time 38 ms;
    - layout shift 0.000;
    - 25.2 KB of JavaScript unused at load.
    - These are lab figures from a local server, not real-user Web Vitals; INP needs real use.
- `15d8a41` came after this run and is left to CI.

## Required CI evidence

The existing CI workflow runs Python with PostgreSQL, frontend unit tests, typecheck/build, Playwright and automated accessibility checks. This change also adds brain/snapshot contracts, the existing interface-budget function, and an `agentic-ui-evidence` artifact containing the production bundle, real browser screenshots and any test traces.

CI commit, workflow URL, measured sizes and final results: pending the branch update and completed workflow. Do not copy historical README counts into this section as current evidence.

## Acceptance targets

| Target | Evidence required | Current status |
| --- | --- | --- |
| Manager identifies main finding and next action within ten seconds | Timed representative-manager usability task | Not observed; finding and decision are explicit in the design and implementation |
| Evidence reached within two interactions | Browser journey from finding card to evidence | Passes locally on desktop and phone (`d53397d`) |
| Keyboard-only approval | Browser focus/Enter and dialog navigation | Passes locally on desktop and phone (`d53397d`) |
| Interrupted draft recovered | Navigate, reload and failed-send recovery | Unit and browser checks pass locally (`d53397d`) |
| Arabic phone journey | Real Arabic report at 390 px; 320 px overflow check and axe | Passes locally at 390 and 320 px, with axe (`d53397d`) |
| Both themes, larger text, landscape and reduced motion | Browser/device review | Reduced-motion existing suite retained; additional manual/device review remains open |
| Windows, Android and iOS installation | Actual platform installation and launcher test | Not observed; browser-guided PWA support only |
| Bundle and Web Vitals | Production sizes; Lighthouse or real-user performance | Bundle within budget; Lighthouse lab LCP 1.55 s, CLS 0.000, TBT 38 ms (local). No real-user INP |

Open items remain unaccepted until evidence or an explicit named-owner decision resolves them.
