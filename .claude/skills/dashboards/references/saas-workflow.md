# Executive dashboard implementation workflow

Use this reference when changing Asset Reliability's application. The
endpoint map below is code-grounded as of 19 October 2026; read the current
client and server definitions before relying on a payload or adding one.

## Read the implementation first

- `frontend/src/shared/api.ts` and `types.ts`: authenticated requests and DTOs.
- `server/app.py`: route authorization, run ownership and readiness checks.
- `server/maintenance/kpis.py`: controlled measure definitions.
- `server/executive.py`: the deterministic filtered executive briefing.
- `frontend/src/features/`: current run/dashboard views and query controls.
- `frontend/src/app/lazyViews.tsx` and `frontend/src/i18n/pack.ts`: lazy loading.
- `design-system/agentic-os/MASTER.md`, its `pages/dashboard.md` and
  `frontend/src/shared/styles/tokens.css`: current product styling.
- Relevant ADRs, `docs/UI_PLAN.md` and `scripts/verify.py`: behavior and gates.

Use `rg --files` to resolve a moved path. Keep existing app contracts and
house-style tokens; old generated palette examples are not new CSS tokens.

## Existing run APIs

| Evidence or interaction | Existing contract | Display obligation |
| --- | --- | --- |
| Available analyses | `api.listRuns()` → `GET /api/runs` | Select an authorized run explicitly; do not silently mix runs. |
| Run state, reports and evidence | `api.getRun(id)` → `GET /api/runs/{id}` | Keep queued/running/failed/approval states visible. |
| Filtered executive briefing | `api.runExecutive(id, language, filters, signal)` → `GET /api/runs/{id}/executive` | Preserve the selected filter scope and separate filtered measures from whole-run findings/model evaluations. |
| Executive business report | `api.downloadExecutive(id, language, filters, updatedAt, snapshotId, format, signal)` → `GET /api/runs/{id}/executive/export` | Default HTML or genuine DOCX; require both prepared timestamp and content revision. On 409, refresh and reprepare. Native Print / Save as PDF opens the browser dialog. |
| Whole-run maintenance KPI register | `api.runKpis(id, language)` → `GET /api/runs/{id}/kpis` | Preserve formula, population, unit, numerator, denominator and coverage. |
| Available fields | `api.tableFields(id, language)` → `GET /api/runs/{id}/fields` | Offer only fields supported by that cleaned table. |
| Filtered chart aggregates | `api.queryTable(id, spec, language)` → `POST /api/runs/{id}/query` | Use the typed query DSL, not SQL or browser-side copies of raw data. |
| Authorized detail rows | `api.tableRecords(id, spec, language)` → `POST /api/runs/{id}/records` | Paginate in the app; never put rows into an LLM prompt. |
| Cleaned-table export | `api.downloadTable(id, language)` → `GET /api/runs/{id}/data.csv` | Keep the authenticated client and server-derived filename. |
| Approval decision | `api.decideApproval(...)` → the existing approval route | Preserve human review and deterministic audit records. |

Prefer the executive contract for the filtered executive page. Its
priorities/questions are deterministic decision support, not an autonomous
work-order executor. Filtering does not rerun model training or revalidate
whole-run findings; retain the server's scope labels and limitations.
Business reports carry these boundaries, calculation references and missingness
into English/Arabic files. Keep JSON as internal API transport, not the default
executive handoff. Print only after the actual report document and fonts load;
an initial blank popup's load listener may be lost during Blob navigation.

The older KPI endpoint computes the whole run and accepts a language,
not dashboard filters. Label those cards as run-wide when charts are
filtered. A filter affecting a KPI must use implemented server semantics
with population/coverage evidence; changing its caption is not enough.

`KpiMeasure.value === null` has an explicit `undefined_reason`. Keep
`records_excluded`, `records_unmeasured`, `missing_policy` and `unavailable`
visible where relevant. Preserve `QueryAnswer.matched_records`, `records`
and `truncated`; a limited category result is not the whole population.
Show localized empty, unavailable, unauthorized, not-ready and retry states.
The existing cleaned-table routes return 409 until cleaning is complete.

## Executive information hierarchy

Start with a short decision statement and scope: selected run, period,
population, source freshness and approval state. Choose a small set of
relevant measures, then show the comparison or driver breakdown that
explains them. Put the next supported action beside its reason; let a
reader open the source calculation and an accessible table.

For maintenance, useful questions include downtime concentration, recurring
failure categories, cost exposure and data-quality exclusions. Use only
measures actually supported by the input and KPI register. Asset-level
history, remaining useful life, failure probabilities and savings require
their own stable identity, timing, model evaluation and definitions.
Do not manufacture them from a work-order count or a decorative health dial.

Model evidence needs the target, prediction-time inputs, holdout method,
sample sizes, metric, baseline and known limitations. A weak model remains
labelled weak. General Miyaar guidance is distinct from a measured finding.

## English, Arabic and visual behavior

- Ship every UI string in English and Arabic; view-specific strings stay
  in lazy translation packs. Use the same information and interactions.
- Use logical spacing/alignment and `dir="rtl"` in Arabic. Keep IDs,
  Western-digit values and mixed-direction units readable with appropriate
  isolation. Do not mirror a chronological axis without clear labels.
- Show units, denominator/population and meaningful precision beside values.
  Follow existing number formatting; never change source values to fit a card.
- Use deployed navy/cyan semantic tokens, restrained surfaces and a clear
  hierarchy. Static cards do not lift or imply clickability. A selected
  state, warning or forecast always has text in addition to color.
- Keep SVG charts with descriptive titles and the same numbers as tables.
  Bars start at zero, negative values use the correct side, and forecasts
  have a labelled boundary and a distinct line style.
- Wrap filters, allow keyboard operation, preserve focus after updates,
  respect reduced motion and both themes, and avoid page-level overflow
  at phone, tablet and desktop sizes.

## Verification matrix

| Change | Meaningful check |
| --- | --- |
| KPI/query contract | Synthetic fixture with independently calculated expected values; changed filters/cohorts, missing readings and zero denominators; ownership and not-ready behavior. |
| Dashboard view/state | Run switching, stale response cancellation, empty/unavailable/error/retry states, evidence navigation and real action routing. |
| Localization/accessibility | English LTR and Arabic RTL, keyboard/focus, chart tables, light/dark, reduced motion, axe and narrow-screen screenshots. |
| Packaging | Typecheck, affected unit/browser checks, production build and the existing verifier's bundle gates. |
| End-to-end claim | Real API-backed intake → mapped run → dashboard → evidence → approval, with synthetic data and actual recorded outcomes. |

Use the project environment. Typical frontend checks are `npm --prefix
frontend run typecheck`, `npm --prefix frontend test`, and `npm --prefix
frontend run build`; the final combined gate is `python scripts/verify.py
--e2e` when the task warrants the complete workflow. Choose affected tests
while iterating. Restore unrelated generated screenshots after verification.
Keep test counts in README; hand over actual commands and remaining limits.
