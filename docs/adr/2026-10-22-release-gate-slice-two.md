# Release gate, slice two: rates never summed, a baseline for every forecast, figures checked against evidence, approve after reading, audience and issuer required

Date: 2026-10-22 · Status: Accepted (assessment findings A4, A5, A6, U3, B7
in `docs/audits/SAAS_PLATFORM_ASSESSMENT.md`; the P1 list in
`docs/implementation/DELIVERY_ROADMAP.md`; slice one is
`2026-10-22-release-gate-slice-one.md`)

## Decisions

1. **A rate is never summed, trended or ranked (A4).** The governance stage
   records `measure_is_rate` for the chosen measure: true when the
   maintenance contract scales the column as a fraction or a percentage,
   when the glossary gives it the unit `%`, or when its name says so
   (`pct`, `percent`, `%`, `rate`, `ratio`, `share`, `availability`,
   `utilisation`). The preparer carries the flag. For such a measure the
   predictive stage produces no forecast and says why ("a sum of rates is
   not a rate", in English and Arabic), and the prescriptive stage builds
   no option on group totals or group changes; it still offers nothing
   rather than something wrong. The ratio-of-sums figure for a rate is the
   KPI register's, as before. Ordinary measures are unchanged.
2. **Every forecast is backtested against repeating the last period (A5).**
   With six or more periods, the last one to three periods are each
   predicted from the periods before them, by the fitted trend and by the
   naive baseline, and both errors are recorded (`c_backtest`, `c_naive`).
   A trend that does not beat the baseline by the 5% margin the
   maintenance models already use is reported as weak: the baseline claim
   becomes a limitation and the headline ends "no better than repeating
   the last period" (Arabic: "وليست أفضل من تكرار الفترة الأخيرة"). The
   forecast is still shown, with its band, so the reader sees what the
   trend would say and why not to lean on it. Seasonal-naive baselines and
   residual intervals remain open (`docs/analytics/PREDICTIVE_MODEL_VALIDATION.md`).
3. **The validator reads the figures in every claim (A6).** A new check,
   `claim_figures_match_evidence`, parses each claim's text for figures of
   three or more significant digits and finds each one among the values of
   the calculations the claim cites, allowing rounding to any number of
   places, a percent or per-thousand scaling, and figures inside a text
   value such as a range. Dates, hashes, counts under 100 and the scale
   constants 100 and 1,000 are not figures. The check runs before the
   evidence-exists check, and a failure stops the run at
   `partially_completed` like any other validator failure.
   Making the pipeline pass its own check surfaced nine claims that
   stated a number no calculation carried (the driver's share of change,
   the segment count, the prescriptive margin, the held-out record count
   of each maintenance target, the anomaly stage's record count, the
   privacy warning's row counts, each governance finding's figures, the
   forecast band, and the example stage's target); each now cites a
   calculation of its own. That is the finding's point: the check caught
   real gaps on the first run.
4. **Approve needs the exact report opened and confirmed read (U3).** The
   approval card's Approve button is disabled until the "Review the exact
   report" panel has been opened and the reader has ticked "I have read
   this exact report"; Reject never needs either. The hash binding and the
   server-side gate are unchanged. The phone app already worked this way
   (`2026-10-22-android-app-first-release.md`).
5. **A sign-in provider requires an audience and an issuer (B7).** When a
   JWT secret or a JWKS endpoint is configured, the server refuses to start
   unless `AGENTIC_OS_JWT_AUDIENCE` and `AGENTIC_OS_JWT_ISSUER` are set or
   can be derived from `SUPABASE_URL` (`authenticated` and
   `<url>/auth/v1`). A token minted for another application in the same
   project no longer verifies. Local mode, with no provider, is unchanged.
   The test suites set `SUPABASE_URL` and mint tokens through
   `tests/support.py::scoped_token`, which carries both claims.

## Verification

`tests/test_analytics.py::RatesAreNeverSummedTestCase`,
`::ForecastBaselineTestCase`, `::ClaimFiguresMatchEvidenceTestCase`
(including a seeded mismatching claim the validator must reject);
`tests/test_auth.py::test_a_provider_without_audience_and_issuer_fails_closed`;
`frontend/src/tests/approval-card.test.tsx`; the Playwright specs
`runs.spec.ts` and `workspace.spec.ts` (approve through the read gate, by
mouse and by keyboard); the dataset sweep in `tests/test_report_language.py`
in both languages under the new validator check; the full verifier.
