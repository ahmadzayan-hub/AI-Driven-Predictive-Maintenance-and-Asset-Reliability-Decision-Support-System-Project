# Miyaar executive workspace: Power BI reference and visual directions

Date: 2026-10-25. Scope: review branch from `main` merge SHA `a647e74ea8a7e8c5035160993acbafebc3860d35`. No production deployment, model provider, schema or hosting change.

## Inspected evidence, not inferred from file names

- The supplied `Group_9226_Team_3_Dashboard_v1.3.0.0(1).pbix` was opened as a Power BI package archive. SHA-256: `e12c9fb13314fc56171ebf7d372ceeb6e38a7876489e5b121329ffdde54785f6`. It has eight report definitions: **Summary, Scorecard, Reliability, Work Orders, Cost & Loss, Risk, Method, Detail**. Source `DataModel` is binary. Package inspection does **not** constitute rendering in Power BI Desktop, execution of measures, or reconciliation of the source dataset.
- The supplied October 2026 Team 3 analytical PDF, Section 7 (pp. 14–16), depicts the Summary, Reliability and Risk report pages. Figure 7.1 (p. 15) includes KPI measures, quarter trend, class-loss comparison, a criticality-by-strategy matrix and decision requests. Figure 7.2 (p. 16) shows detailed reliability and risk analysis.
- The PDF's Appendix B (p. 29) distinguishes calculated MTBF 313.3 h and MTTR 12.0 h, maintenance cost USD 50,430,446, production loss USD 228,881,052, loss/spend ratio 4.54 and service target met 46.1%. Section 5 (pp. 8–9) explains why a stored MTTR and the 75.8% SLA score cannot substitute for the defined KPIs.
- The PDF states the 5,000-record enterprise dataset is **synthetic and educational**. A projected USD 6.56M annual net benefit is a simulation, not realized savings. Do not automatically treat those MBA reference figures as values belonging to other Miyaar uploads.
- No separate light SaaS, finance or agentic design image attachment could be verified in this repository review. The provided Power BI/report pages are the visual references inspected. Original PBIX and PDF are not copied into this branch.

## Baseline on the currently merged source

PR #59 and PR #60 are merged; a visual redesign must **not** replace the completed four featured, source-backed KPIs; primary data comparison; decision queue; contextual evidence; preserved deep links; or existing three navigation areas. Source locations:

- `frontend/src/app/App.tsx`: Decision, Data & Analysis, Reports & Outputs plus secondary tools.
- `frontend/src/features/dashboard/ExecutiveOverview.tsx`: filtered KPI cards, source disclosures, decisions, model readiness and human approval.
- `frontend/src/features/dashboard/charts.tsx`: source-backed native charts and accessible full-value tables.
- `frontend/src/features/dashboard/dashboard.css`: chart and responsive styling, including this branch's focused narrow-phone fix.
- `frontend/e2e/executive.spec.ts`: actual FastAPI fixture, 1280×720 desktop and 320px phone, exported screenshot and independent clipping/RTL checks.

These are verified **source facts**. An independent before/after visual capture of a locally running application was not possible in this inspection environment. The historical PR statements about passing CI and actual screenshots are not new test results.

## Two lightweight design directions

| Consideration | A. Dense analysis desk | B. Decision-first evidence canvas |
| --- | --- | --- |
| Opening | Power BI-like chart mosaic, many small KPI tiles | Four governed KPIs, a primary measured chart and a concise review queue |
| Strength | Fast parallel metric scanning for analysts | Clear first decision and drill-down for managers |
| Weakness | Tiny legends, competing emphasis and phone overflow risk | More steps to access some second-order analyses |
| Evidence | Full metric matrix, slicers and filter state on the surface | KPI details, verified method and full tables behind contextual disclosures |
| Mobile | Requires stacked reorganisation and long scrolling | Compact KPI row then primary chart; secondary views reachable |
| Decision | Study only | **Retain and refine the existing merged direction** |

Design decision: **B**. Preserve the working four-KPI executive hierarchy delivered in PRs #59/#60, with white/off-white surfaces, navy text, restrained teal/blue accents, meaningful status colours, and authentic chart values. The existing tokens and bundled font govern the result. This iteration corrects a specific remaining failure: narrow-screen category labels were cut to an ellipsis while horizontal bars and full numeric values competed for one row. The phone layout now gives the full label and number one row, and the full-width bar the next. Desktop layout and data processing remain unchanged.

## Traceability and acceptance

1. Compare Summary → decision opening, Scorecard → KPI evidence disclosures, Reliability/Work Orders/Cost & Loss → Data & Analysis, Risk → explainable ranked findings, Method → definitions, Detail → drill-down.
2. Validate the same Miyaar run, filters and declared currency across both languages at 320px, 390px, tablet, 1280×720 and desktop. Compare *actual app* screenshots from both revisions, not a PDF screenshot against a new app.
3. Long category labels must be fully readable on phones, their bar widths visible, and the document must not develop horizontal overflow. Keep chart numerical-table disclosures keyboard operable. The grouped chart must continue deriving its data from the API.
4. Run `python scripts/verify.py --quick`, then `python scripts/verify.py --e2e` on the final SHA in a provisioned checkout. Check first-load and total JS/CSS budgets **without increasing the ceilings**.
5. Separately verify import → mapping → analysis → dashboard/evidence → review → report persistence/reload → export in English and Arabic with real API responses.
6. Record source SHA, exact test outputs, skipped checks and before/after screenshots. Do not claim production, comparative Power BI superiority or WCAG certification on source inspection alone.

## Boundaries

No PBIX execution, desktop app operation, fresh live-application screenshot, model retest or real-user comprehension test is claimed in this source-only review. No database, credentials, Supabase, model providers, backend calculation, deployment, production status or separate Hermes Desktop integration is changed. Presentation and video remain Phase 2.
