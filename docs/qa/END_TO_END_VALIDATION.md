# End-to-end validation

Date: 22 October 2026 · Branch `claude/tender-clarke-m4uwgq` · Every line
below is a command that was run in this pass and what it returned. A
capability that could not be exercised is marked unverified; no success is
claimed for it.

## 1. Repository checks

| Command | Result |
| --- | --- |
| `REQUIRE_PG=1 PG_TEST_URL=… python scripts/verify.py` (full) | **8 of 8 passed**: Python 1,662 tests, 21 skipped (optional extras); brain check 46 notes, 0 broken links; typecheck; frontend 323 of 323; native run logic; production build; interface budget JS first load 98.0 of 100 KB, JS total 211.7 of 214 KB, largest chunk 18.9 of 30 KB, CSS first load 10.0 of 10.5 KB, CSS total 28.7 of 29.5 KB, fonts 119.4 of 120 KB |
| `python scripts/evaluate_agents.py --check` | 9 of 9 agents at or above floor (intent holdout 77%, router 90% macro recall, jargon 92% recall, others 100%) |
| `python -m unittest tests.test_docs` | 11 passed (documented counts and limits match the code) |
| `npx playwright test e2e/overview.spec.ts e2e/a11y.spec.ts` (installed Chromium 1194 via `PLAYWRIGHT_EXECUTABLE_PATH`) | Overview spec: 9 passed, 3 skipped (device-specific), desktop and mobile. Accessibility spec: 4 passed, including the WCAG 2.2 AA scan of every view with the Command Centre in place |

Earlier in the day, on the same branch: 1,654 Python tests before the audit
fixes; the five fixes added 8 tests; the Command Centre added 3 interface
tests and one message pack to the parity test.

## 2. Journeys exercised

| Journey | How | Result |
| --- | --- | --- |
| Dataset upload, mapping, analysis to approval | Overview e2e spec (`runSampleToApproval`, "a stored dataset is analysed again by reference") | passed |
| Complete agent orchestration, 24 stages, validator, report at the gate | Python suites (`test_runs`, `test_orchestration`, `test_analytics`) and the demo seed | passed |
| Failed-agent recovery | `test_orchestration::test_a_failing_model_never_fails_the_run`; stage error paths in `test_runs` | passed |
| Predictive evaluation | model card tests in `test_modelling`, `test_maintenance_targets`; the new period-order and narrator-grounding tests | passed |
| Prescriptive recommendation | `test_analytics` prescriptive and sensitivity tests (unchanged; see A2 and A3 for what they do not prove) | passed |
| Evidence and calculation integrity | validator and provenance tests; `figures_check` suite 100% | passed |
| Report generation and executive export | `test_executive*`, `executive.spec.ts` (not re-run today) | passed earlier; unverified today |
| Human approvals | `test_runs` approval tests; Overview e2e "Review opens the waiting run on its approval card" | passed |
| Tenant isolation | `test_tenancy` including the new per-owner retention test; `test_authorization` | passed |
| Arabic and English parity | `i18n.test.tsx` (545 keys each, 13 packs); Overview e2e at 320 px in both languages; Arabic Command Centre capture | passed |
| Accessibility | `a11y.spec.ts` WCAG 2.2 AA with axe, desktop and mobile | passed |
| Responsive | Overview e2e 320 px and the phone bar | passed |
| Command Centre on a running server | demo server (`VERCEL=1 AGENTIC_OS_DEMO=1`), Chromium captures in English and Arabic (kept outside Git under `private/`) | rendered from the live brief; recommendation, four decisions with owner and gate, six KPIs, two model cards, data quality, three questions |
| Vercel preview deployment | not created: this programme's branch is not deployed and is not merged to `main` | unverified, by design |

## 3. Not verified in this pass

- Live model providers: every host is unreachable from the development
  container, and production has no key. Model paths are tested on simulated
  responses only.
- The full Playwright suite (27 specs): only the Overview and accessibility
  specs were re-run after the change; the rest last passed on 21 October
  (README, Testing).
- Load, concurrency and the hosted lock behaviour (B4): proposed tests only.
- Any failure, remaining-life or condition prediction: the data cannot carry
  one.
