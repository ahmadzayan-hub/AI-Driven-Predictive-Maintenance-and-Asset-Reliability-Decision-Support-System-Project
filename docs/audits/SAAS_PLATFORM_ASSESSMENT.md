# SaaS platform assessment

Date: 22 October 2026 · Scope: the repository at `main` `1d2d008` and the
production deployment of that commit · Method: four read-only code reviews
(backend and security, analytics and model validation, interface and
bilingual UX, agent layer and quality gates), each finding checked against the
file and line it cites; the two most serious defects reproduced by running the
code; the real validation commands run and their counts recorded.

Nothing in this document is inferred from product descriptions. Where a
reviewer could not run something, the finding says so.

## 1. Executive summary

The platform is further along than a typical capstone build and more honest
than most analytics products: every figure in a report cites a calculation, a
validator rejects claims without evidence, the KPI register is a ratio of sums
over a named population, models are shown against a baseline and called weak
when they do not beat it, and publishing waits for a person. English and
Arabic parity holds by construction (545 keys each). All nine measured agents
meet their recall floors today.

Five defects were serious enough to fix in this pass rather than list:

1. **Wrong trend direction in unmapped runs.** Periods were ordered as text, so
   a series rising ten a month from January to August reported "down 4%".
   Reproduced, fixed, tested.
2. **Model summaries were never grounded.** A model could add a figure to the
   executive summary. Fixed: such a summary is set aside and the report says so.
3. **Model roles skipped the personal-data boundary.** Fixed: every role passes
   the same check as the narrator; a run with personal data gets built-in notes.
4. **A hosted deployment with a shared database and no sign-in ran everyone as
   the owner.** Reproduced, fixed: it refuses to start.
5. **Session trimming crossed tenants.** Reproduced, fixed: per owner.

What remains is a prioritised backlog (section 5). The most important open
items are: the sensitivity stage cannot change a ranking by construction; the
prescriptive "expected gain" is an assumed 10% with no cost; rate columns can be
summed in the default pipeline; forecasts have no naive baseline; the approval
inbox is capped at the 50 newest runs; money carries no currency; one
process-wide lock serialises model calls; there is no request logging; and the
executive experience is spread over four screens with no single command centre.

## 2. Verified facts

| Claim in the brief | Verified | Evidence |
| --- | --- | --- |
| React, TypeScript, Vite frontend | Yes | `frontend/package.json`; `frontend/src/app/App.tsx` |
| Python FastAPI backend | Yes | `server/app.py:363` `create_app`; `api/index.py` for Vercel |
| Hermes orchestration | Yes, as code, not a model | `server/runs.py` run engine; `server/orchestration.py` model roles over it |
| Deterministic agents and configurable stages | Yes | `server/analytics.py` `PIPELINE`; `server/stages.py` (ADR 0020) |
| Governed reports and human approval | Yes | validator `server/analytics.py:3499`; approval gate `server/runs.py:717-782` |
| Upload and analysis pipelines | Yes | `POST /api/datasets`, `POST /api/runs` |
| SQLite and PostgreSQL | Yes | `server/storage.py` |
| English and Arabic | Yes, 545 keys each | `frontend/src/i18n/en.ts`, `ar.ts`; `tests/i18n.test.tsx` |
| Vercel deployment | Yes, production live | `asset-reliability-team3-saas.vercel.app`, commit `1d2d008`, demo mode |
| PR #6 status | Merged 18 October | brand mark, Overview evidence status, agent evaluation CI step |

Not production-ready despite being documented: the agent and MCP optional
runtimes (their tests skip in CI); the live model path (no key in production;
tested on simulated responses only); the pilot CMMS connection (no customer
account); any failure or remaining-life prediction (the course dataset cannot
carry one, `session-logs.md:928`).

## 3. Checks run on 22 October

| Check | Result |
| --- | --- |
| `python -m unittest discover tests` (PostgreSQL up) | 1,654 passed, 21 skipped, before this pass; see `docs/qa/END_TO_END_VALIDATION.md` for the after figure |
| `python scripts/evaluate_agents.py --check` | 9 of 9 at or above floor. Weakest: intent holdout 77% (floor 76), router 83% accuracy / 90% macro recall (floor 90) |
| `npm --prefix frontend run typecheck`, `test` | pass; 319 tests |
| Interface budget (`scripts/verify.py`) | JS total 208.4 of 210 KB, first load 97.9 of 100, CSS total 28.2 of 29, fonts 119.4 of 120: almost no headroom |
| Production `/api/health` | demo mode; every model task `built-in`; no problems |
| Production `/api/runs/5fe5d44a8391/executive` | 240 records, 14 measures, 4 decisions with owner and gate, 2 model cards (both `not_supported`), 12 findings |

## 4. Findings

Severity: **Blocker** (wrong answers, data exposure, or loss), **Major**
(wrong impression, governance gap, or availability), **Minor**. Status:
**Fixed** in this pass with a test, or **Open** with a priority (P1 next
release, P2 following, P3 backlog).

### 4.1 Analytics, predictive and prescriptive

| # | Sev | Current behaviour | Expected | Evidence | Impact | Correction | Validation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Blocker | Unmapped runs sorted period labels as text | Chronological order, or no trend | `server/analytics.py` preparer `sorted(trend.items())`; reproduced: rising Jan..Aug reported "down 4%" | Every trend, forecast, anomaly and driver reading wrong on month-named or day-first data | Cleaner labels periods with the mapping parser; unreadable labels keep recorded order and say so | `tests/test_analytics.py::UnmappedPeriodOrderTestCase` | Fixed |
| A2 | Blocker | Sensitivity stage cannot change the ranking: every option's gain is `base × 10%`, so 5, 10 and 20% give the same order; "stable" is true by construction | Vary what can flip a ranking: per-option effect, cost, probability | `analytics.py:3172`, `2722-2738`; `tests/test_analytics.py:612-620` asserts `stable` | Approvers read "holds across every assumption" as evidence | Say the ranking is scale-invariant; vary per-option uplift or cost ranges; report flip points | Property test: distinct uplifts must be able to flip | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| A3 | Blocker | Prescriptive "expected gain" is an assumed 10% of a group total with no cost; the headline says "worth N" | Headline labels the figure illustrative; options carry cost and constraints; uplift from input or source | `analytics.py:3149`, `3172`, `3475-3481`; `PLANNING_UPLIFT = 0.10` unsourced | Leaders quote an assumption as a saving | Label "illustrative at an assumed 10%"; take uplift and cost as inputs; hold the recommendation without a direction | Every recommendation shows "illustrative" beside the gain | Fixed 22 Oct, slice one (`docs/adr/2026-10-22-release-gate-slice-one.md`) |
| A4 | Major | The default pipeline sums the chosen measure by group and period with no check of its kind; a rate or MTBF column becomes "total availability" | Rates go through the KPI register (ratio of sums) or are refused for trend and top-share | `analytics.py:1126-1143`, `metrics.py:299-303`; register used only by `app.py:1211`, `executive.py:83` | Average-of-rates defect in the main report path | Look up the measure's scale; route rates to `kpis.compute`; refuse otherwise | Test with a FRACTION column | Fixed 22 Oct, slice two (`docs/adr/2026-10-22-release-gate-slice-two.md`) |
| A5 | Major | Forecast has no baseline; accuracy is MAPE on 1 to 3 held-out points; ± band on period 1 only | Naive and seasonal-naive baseline on rolling folds; residual intervals; "weak" rule | `analytics.py:3011-3043` | A trend a naive guess would match is presented as a forecast | Add baselines and 3+ folds; reuse the 5% weak rule from `modelling.py` | Random-walk series must read weak | Fixed 22 Oct, slice two (`docs/adr/2026-10-22-release-gate-slice-two.md`) |
| A6 | Major | Validator checks that evidence ids exist, not that a claim's numbers match the calculation it cites | Figure match from claim text to cited values | `analytics.py:3566-3577`, `3602-3608` | A claim can cite a calculation and state a different number | Add a figure-match check using `figures()` | Seed a mismatching claim; validator must fail | Fixed 22 Oct, slice two (`docs/adr/2026-10-22-release-gate-slice-two.md`) |
| A7 | Major | `availability_inherent` and `mttr` include planned downtime | Corrective downtime only, or relabel | `server/maintenance/kpis.py:441-476` | Understates availability against OEM targets | Add a corrective-downtime basis or rename | Hand recompute on a planned-only record | Open P2 |
| A8 | Major | Rail screening routes a failure on a Low-criticality signalling asset to routine review; thresholds unsourced | A failure on a safety function always escalates | `rail_asset_decisions.py:60-61`; contract timings `contract.py:111`, `145` | Route-to-failure logic on a safety-critical class | Escalate any signalling failure; source the 60 threshold | Low-criticality signalling row with a failure must flag | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| A9 | Major | "Useful" maintenance-risk verdict on 50 held-out records with no interval; noise simulation called "useful" 7% of the time | Lower confidence bound above chance, or permutation test | `maintenance/targets.py:40-45`, `394-402` | About 1 in 14 noise targets yields an intervention recommendation | Report n, interval and positives; require the bound | Simulation in the suite, fail above 1% | Open P2 |
| A10 | Major | Split falls back silently from chronological to every-fifth record under 5 periods | Declare the split on the verdict; require time or asset grouping | `modelling.py:122-137`, `408`, `548`; `targets.py:325` | Optimistic scores on asset data with drift | Downgrade to weak or not evaluated unless chronological or grouped | 3-period dataset yields `not_supported` | Open P2 |
| A11 | Major | Generic regression and classification take every numeric column; leakage only disclosed | Timing-screened inputs | `modelling.py:88-101`, `176-183` vs `targets.py:101-109` | An outcome column can predict the target | Pass governance exclusions and detector findings into these stages | Seed a target-derived column; expect exclusion | Open P2 |
| A12 | Major | Forecast and anomaly ignore `trend_counts`; a partial period reads as a drop | Normalise or declare uneven periods | `analytics.py:1281` vs `2971`, `2622` | False drop on a partial month | Add the limitation claim and drop an incomplete last period | Halve the last period; expect a limitation | Open P2 |
| A13 | Major | No structured decision record (id, alternatives, cost, confidence, approver) | A decision object persisted with the run | grep: no `decision_id`, `alternatives`, `approved_by` in `server/` | No audit trail from advice to action | Add `decision` to the run engine; link evidence ids and approver | Schema test; publish refused without a record | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| A14 | Major | Model cards carry no version, snapshot hash, training window or drift check; no probabilities or calibration in the pipeline | Versioned cards; probabilities with Brier against baseline | `modelling.py:212-218`; `reliability_validation.py:59-135` is separate | Scores cannot be reproduced or retired | Add version and snapshot; feed outputs into the registered-window protocol | Same snapshot gives identical cards | Open P2 |
| A15 | Major | A model summary could add a figure | Set aside and explained | `analytics.py` prescriptive narration | Invented figures in the executive summary | `orchestration.grounded()` on the narration | `NarratorGroundingTestCase` | Fixed |
| A16 | Minor | Driver share printed as `abs(share)`; associations on the first 4 numeric columns with no n | Signed shares; n stated | `analytics.py:1394-1461` | "Accounts for 158%" reads oddly (seen in the live demo brief) | Signed shares; name gross movers | Test +100 and -80 groups | Open P3 |
| A17 | Minor | Anomaly rule cannot fire below 6 periods (max residual z 1.67 at n=4) | A rule that can fire, or a stated minimum | `analytics.py:2624-2651` | "Nothing stands out" where nothing could | Minimum 8 periods or robust rule | Obvious outlier at n=4 | Open P3 |
| A18 | Minor | Exact duplicate rows dropped; coercion failures not a calculation; dropped indices not kept | Every transformation recorded and reversible | `analytics.py:496-561` | A repeated identical job disappears | Keep `dropped_indices`; add `c_coercion` | Unparseable numerics appear as a claim | Open P2 |
| A19 | Minor | Clustering "improvement over baseline" cannot fail; seasonal model judged on one season | Stability check; two holdout seasons | `modelling.py:677-769`, `798-851` | Weak evidence read as a found structure | Bootstrap stability; two seasons | Uniform noise fails | Open P3 |

### 4.2 Backend, security and operations

| # | Sev | Current behaviour | Expected | Evidence | Impact | Correction | Validation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Blocker | Vercel with `DATABASE_URL` and no provider ran as `local-owner` with approve rights for every visitor | Fail closed | `server/auth.py` `build_identity`; reproduced | Any visitor reads and approves every tenant's data | Refuse to start; `AGENTIC_OS_DEMO=1` is the explicit opt-in | `tests/test_demo.py` | Fixed |
| B2 | Blocker | Model roles sent claim texts to providers with no personal-data check | Same boundary as the narrator | `server/runs.py:621-650`; `orchestration.py` | Named people in group labels leave for a third-party model | `model_privacy.blocks_model` on every role; built-in writer when blocked | `PrivacyBoundaryForRolesTestCase` | Fixed |
| B3 | Blocker | `trim_sessions` kept the 32 newest across all owners | Per owner | `server/storage.py:596-600`; reproduced | One tenant deletes another's conversations | Per-owner retention | `SessionRetentionPerOwnerTestCase` | Fixed |
| B4 | Major | One process-wide lock wraps model calls and pipeline stages | Lock in-memory state only; per-session and per-run locks | `server/app.py:376`, `731-746`, `1075-1076`; `storage.py:170-177` | One slow model call stalls every tenant for up to 24 s under a 30 s limit | Move `assistant.handle` and `engine.advance` outside the global lock | Stub model sleeping 5 s with concurrent GETs | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| B5 | Major | Restore deletes every table then inserts, with no transaction | One transaction; validate before any delete | `storage.py:692-708`; `backup.py:50-68` | Recovery can leave the database empty | Wrap in `atomic()`; validate first | Monkeypatch insert to raise; counts unchanged | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| B6 | Major | Rate limit is per instance; chat has no model-call quota; buckets never evicted | Store-backed limiter; per-tenant model budget | `rate_limit.py:19-44`; `quota.py:103` | A leaked token spends hosted model budget | Store-backed bucket; daily model-call quota | 700 POSTs across two instances | Open P2 |
| B7 | Major | `aud` and `iss` verified only when configured | Required with a provider | `auth.py:159-166`, `298` | Tokens minted for another app in the same Supabase project are accepted | Require both; fail closed | Foreign-aud token rejected | Fixed 22 Oct, slice two (`docs/adr/2026-10-22-release-gate-slice-two.md`) |
| B8 | Major | `scripts/serve.py` binds `0.0.0.0` by default in unauthenticated local mode | Loopback by default | `server/serve.py:90` | Local data open to the LAN | Default loopback; explicit `--lan` | Connect from another host: refused | Open P2 |
| B9 | Major | Memory backend returns `{}` on any exception; migrations wrapped in bare `except`; 500 handler does not log | Narrow excepts; log with request id; 503 on database failure | `storage.py:729-740`, `273-311`; `app.py:553-559` | Silent memory loss; no triage | Narrow and log | Fault injection on `memory_save` | Open P2 |
| B10 | Major | No logging and no request id in the API | JSON request logging with hashed subject | `server/app.py` (no logger) | Incident triage by timestamp alone | Middleware | Echo `X-Request-ID` | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| B11 | Major | One PostgreSQL connection per process; one RLock per statement; transactions hold it | Small pool; per-statement locking | `storage.py:158-177`, `777-792` | One statement at a time per instance | Pool and per-statement lock | 20 concurrent GETs with a 2 s transaction | Open P2 |
| B12 | Major | All DDL runs on every cold start; no schema version | Versioned migrations recorded in a table | `storage.py:261-312` | Concurrent cold starts race on DDL | `schema_migrations` table | Two processes on an empty database | Open P2 |
| B13 | Major | Publishing writes vault files before the state change; model timeout can exceed the function limit | Database as publish target on hosted runtimes; clamp timeouts | `runs.py:750-782`; `model_gateway.py:141-144`; `vercel.json:14` | 500 after partial writes on Vercel | Database target; clamp when `VERCEL=1` | Approve with a read-only vault | Open P2 |
| B14 | Major | OpenAPI disabled; two error envelopes; no idempotency on `POST /api/runs` | One contract, one envelope, idempotency keys | `app.py:368-374`, `911-923`; `operations_api.py:132` | A retry creates a second run | Enable OpenAPI behind auth; idempotency key | Post the same run twice; one run | Open P2 |
| B15 | Major | Workflows declare no `permissions` block | `contents: read` at workflow level | `.github/workflows/ci.yml:16`; `ui-budget-fast.yml:8` | Default token scope in CI | Add the block | grep matches | Fixed 22 Oct, slice one (`docs/adr/2026-10-22-release-gate-slice-one.md`) |
| B16 | Minor | Connector host allowlist only when set | Default-deny in production | `connectors.py:114-118` | Scheduled fetcher for arbitrary public hosts | Require the allowlist in production | Create a source with it unset | Open P2 |
| B17 | Minor | CORS lacks PATCH; two CSP sources | One source of truth | `app.py:461`; `operations_api.py:174`; `vercel.json` | Cross-origin work-order updates fail | Add PATCH; generate CSP once | Preflight PATCH | Open P3 |
| B18 | Minor | `/api/health` is public and returns model names, map and exception text | Liveness public; detail authenticated | `app.py:626-642`; `routing.py:219-221` | Fingerprinting | Split the endpoint | Unauthenticated GET | Open P3 |
| B19 | Minor | Absolute server paths in responses; dataset name unescaped in YAML frontmatter | Relative paths; escaped values | `runs.py:702`, `762`; `app.py:997` | Forged note metadata | Relative paths; `json.dumps` | Name with a quote and newline | Open P2 |
| B20 | Minor | `uvicorn[standard]` extras unused at runtime; `httpx` comment wrong; error mapping copied three times | Runtime deps match imports; one handler | `requirements.in:11-14`; `operations_api.py:127-132` | Larger bundle; drift | Trim extras; one exception handler | Import-graph check | Open P3 |

### 4.3 Interface, journeys and bilingual UX

| # | Sev | Current behaviour | Expected | Evidence | Impact | Correction | Validation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U1 | Major | Approval inbox and Overview waiting list use the 50 newest runs only; the oldest waiting request falls off silently | Every awaiting run listed, or a cap warning | `server/storage.py:385`; `ApprovalsView.tsx:28,37` | A publish request can wait unseen | `GET /api/runs?state=awaiting_approval` with pagination; cap warning | 60 awaiting runs; the oldest returned | Fixed 22 Oct, slice one (`docs/adr/2026-10-22-release-gate-slice-one.md`) |
| U2 | Major | Demo shows connector refresh, pause, save, delete and the KPI-policy button, which the server refuses | Hidden in demo | `DatasetsView.tsx:313`; `ConnectorsPanel.tsx:188-323`; `ExecutiveOverview.tsx:261` | Visitors see controls that 403 | `useReadOnly()` on both | Demo render has no Save, Refresh or Policy | Fixed in this pass (Command Centre commit) |
| U3 | Major | Approve publishes in one click with the report collapsed | Report opened or a confirmation naming the artifact | `ApprovalCard.tsx:24-63` | Accidental publish | Open the preview by default or confirm | Approve disabled until opened | Fixed 22 Oct, slice two (`docs/adr/2026-10-22-release-gate-slice-two.md`) |
| U4 | Major | Money KPIs say "source currency"; no currency anywhere | Currency from the dataset, formatted | `executiveMessages.ts:31,115`; `server/metrics.py` | Financial exposure unreadable | Currency in the mapping (ADR); flag "currency not stated" until then | `formatMoney` test | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| U5 | Major | No command centre: the executive brief is reachable only through Dashboard, then a run, then a section; Overview shows counts | One executive home over the latest run with evidence links | `DecisionActions.tsx:23-62`; `OverviewView.tsx:178-219`; `DashboardView.tsx:274-278` | Executives must know which of four screens holds a figure | Build the Command Centre on the Overview from `/api/runs`, `/api/runs/{id}/executive` and approvals | One screen shows decision, priorities, KPIs, models, evidence, approvals, freshness | Fixed in this pass (see section 6) |
| U6 | Major | "See all analyses" opens the new-analysis form | Opens the list | `OverviewView.tsx:367-368` | Mislabelled control | Navigate to the list | Click lands on the list | Fixed in this pass |
| U7 | Major | Plain counts show "Not assessed" | Status only when a target exists | `OverviewView.tsx:231`; `PerformanceValue.tsx:23-38` | The approval queue reads as a review verdict | Render counts as numbers | Count tiles have no status text | Fixed in this pass |
| U8 | Major | Asset view copy is railway-specific outside a railway profile | Domain-neutral wording | `features/assets/messages.ts:6-8`, `:39-41` | Another industry on a decision screen | Generic copy; railway behind a profile key | Grep test | Open P2 (owner decision) |
| U9 | Major | 12 loading placeholders are `role="status"` with no text, so screen readers say nothing | Visually hidden text inside the status | `App.tsx:325`; `OverviewView.tsx:125`; others | Silent loads for screen-reader users | One shared `Loading` component | `getByRole('status')` has text | Fixed 22 Oct, slice one (`docs/adr/2026-10-22-release-gate-slice-one.md`) |
| U10 | Major | Asset KPI fetch failure is swallowed; evidence assembled from up to 50 run payloads | Error with retry; one summary endpoint | `AssetIntelligenceView.tsx:36-60` | Figures vanish silently; page slows with history | Error state; server endpoint | Abort `/kpis`; expect alert | Open P2 |
| U11 | Major | Relationship chart plots 500 points; its table shows 100 with no note | Match or say "showing 100 of 500" | `DashboardView.tsx:41`, `:656` | Numeric alternative does not match the chart | Truncation note or pagination | 300 points gives the note | Open P2 |
| U12 | Major | Landing is the assistant; Approvals is two taps away on a phone | Land on the decision view; Approvals in the phone bar | `App.tsx:91`, `:101-105`; `routing.ts:19` | Executives open to a chat box | Land on the Command Centre; Approvals in the bar | Returning user lands on the decision view | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| U13 | Major | No e2e for demo mode; Assets and Approvals never axe-scanned or checked at 320 px | Every nav view scanned; a demo journey | `frontend/e2e/a11y.spec.ts:32-61` | Regressions invisible to CI | Add the views to the loops; add a demo journey | New specs pass | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| U14 | Minor | Nav naming conflicts (Analytics is the run list; Operations is administration) | One noun per destination | `App.tsx:58`, `:85`; `en.ts:193-194` | Users misfile tasks | Rename; group administration | Label assertion | Open P2 |
| U15 | Minor | Four upload entry points, two implementations | One flow in Datasets | `RunsView.tsx:286`; `DatasetsView.tsx:75` | Mapping and preview exist on one path only | Route every CTA to Datasets | Each entry reaches the same preview | Open P2 |
| U16 | Minor | No as-of time on Overview tiles or asset figures; empty dashboard picker has no action | Source time on every figure; a button | `AssetIntelligenceView.tsx:94`; `DashboardView.tsx:91-92` | Stale numbers not visibly stale | `updated_at` near tiles | Time element present | Fixed on the Command Centre; Open P3 elsewhere |
| U17 | Minor | Voice toggles change name and `aria-pressed`; "Ctrl K" on macOS; faint field focus halo | Fixed label; platform-aware; 2 px outline | `VoiceDictation.tsx:187`; `App.tsx:464`; `app.css:1403` | Minor friction | As expected | Manual check | Open P3 |
| U18 | Minor | Parity test covers 12 of 18 message packs; `ExecutiveOverview.tsx` has 23 lines over 200 characters; KPI verdict logic duplicated | All packs tested; export logic in a hook; one KPI component | `tests/i18n.test.tsx:179-181` | Drift can ship | Add packs; extract | Test count rises | Open P2 |
| U19 | Minor | Budget headroom: JS 1.6 KB, CSS 0.8 KB, fonts 0.6 KB | Headroom for the roadmap | `scripts/verify.py:43-47` | Next feature breaks CI | Subset fonts; split CSS; recorded allocations | Build and `check_budget()` | Allocation recorded for the Command Centre; subsetting Open P2 |
| U20 | Minor | Navy navigation exists only in the design preview; amber used for attention, not only accents; hidden scrollbar on dashboard tabs | Per the brief: navy rail, restrained gold | `tokens.css:16-21`; `app.css:132-141`; `dashboard.css:191` | Brand reads inconsistently | Owner decision on the rail; reserve amber | Visual review | Open P2 (owner decision) |

### 4.4 Agents, evaluations and CI

| # | Sev | Current behaviour | Expected | Evidence | Impact | Correction | Validation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | Major | CI floors judge `holdout`, which was tuned to for causal (ADR 0056) and is "not blind" for standards; the untouched blind sets (blind_v7: causal 60%, intent 61%) have no floor; the script's docstring says holdout was never used to choose fixes | Floor the latest untouched blind set; relabel tuned holdouts as dev | `tests/test_evals.py:67-73`; `evaluate_agents.py:13-14`, `251`; `evals/standards.json` | A 100% holdout is quoted where the blind score is 60% | Floor blind_v7 and blind_v6; new blind set for standards; fix the docstring | `evaluate_agents.py --check` | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| G2 | Major | Narrator output unchecked for figures and jargon | Grounded and linted | `analytics.py:3439-3441` | Invented figure in the summary | Grounding applied (A15); jargon lint still open | Test present for grounding | Partly fixed |
| G3 | Major | Role calls bypassed the privacy boundary | Same guard as the narrator | `runs.py:621-650` | Personal data to a provider | Fixed (B2) | Test present | Fixed |
| G4 | Major | No cost, token or latency record for any model call | Per-call ledger with per-tenant budgets | `model_gateway.py:398-413`; `quota.py:103` | Spend and slowness invisible | Record provider, model, latency, tokens, failover | Health or ledger shows counts | Fixed 22 Oct, slice three (`docs/adr/2026-10-22-release-gate-slice-three.md`) |
| G5 | Major | Structured output enforced on Ollama only; greedy regex parse; consultants free text | Native JSON mode per provider; schema validated server-side; structured consultant risks | `model_gateway.py:391-396`; `server/assistant.py:300` | Fragile parsing | Validate `INTENT_SCHEMA`; structured risks | Schema test | Open P2 |
| G6 | Major | Agreement between consultants delegated to an LLM; built-in brief tells the reader to compare | Deterministic comparison by finding reference | `orchestration.py:52-59`, `105-107` | Claimed contradiction detection without code | Compare structured risks (after G5) | Conflict test | Open P2 |
| G7 | Major | Router aliases `gpt`, `gpt-4o` to Groq's `gpt-oss`; the eval labels this correct | Refuse rather than substitute | `routing.py:63-65`; `evals/router.json:17,38` | A named model is silently swapped | Drop the aliases except `gpt-oss`; relabel | Router eval | Fixed 22 Oct, slice one (`docs/adr/2026-10-22-release-gate-slice-one.md`) |
| G8 | Major | `search_knowledge` and `agent_scorecard` have no eval cases; `intent_model` unmeasured | Cases and a scheduled floor | `assistant.py:40-41`; `evals/intent.json` | Two actions unmeasured | Add cases; schedule the model eval | Eval counts | Open P2 |
| G9 | Major | Three reviewer subagents have no benchmark; no reviewer floor | Seeded memos and floors | `evals/floors.json`; `evals/reviewers/runs` | Reviewer quality unmeasured | Seed memos for the three | Floors recorded | Open P2 |
| G10 | Major | No timeout on agent runtimes or custom stages; stages run in-process without a sandbox | Wall-clock limit; timeout as stage failure | `server/assistant.py:358`; `stages.py:36-38` | A hung stage hangs a run | Deadline wrapper | Timeout test | Open P2 |
| G11 | Major | MCP, LangGraph, Pydantic AI and LLMRouter tests skip in CI | A job that installs `requirements-agents.txt` and fails on skips | `ci.yml:47`; `test_mcp.py:217` | Optional runtimes untested | Second CI job | Skips become failures | Open P2 |
| G12 | Minor | Orchestration failures are silent (`except: pass`) | Reason recorded and shown in health | `runs.py:636-637`, `649-650` | Operators cannot see why a note is missing | Record `orchestration_problem` | Test | Open P3 |
| G13 | Minor | Grounding is lexical: "doubled", "one in five" pass; notes added after the validator | Quantity words in `grounded()`; lint notes | `orchestration.py:43`, `208-221` | Spelled-out figures slip through | Word list; run lint on notes | Test | Open P3 |
| G14 | Minor | Review acceptance `by` is any non-empty string | Signed or committed acceptance checked against known reviewers | `review_gate.py:108-113` | An agent can fill in a person's name | Verify against git author | Test | Open P3 |
| G15 | Minor | Tool schemas and the executor disagree on `run_id` and `remember.category` | Validate arguments against `inputSchema` | `tools.py:72-105`; `assistant.py:646-673` | Drift | Validate in `ToolBox._call` | Test | Open P3 |

## 5. Prioritised backlog

P1 (next release gate): closed on 22 October in three slices: A3, G7, U1,
U9, B15 (slice one); A4, A5, A6, U3, B7 (slice two); A2, A13, A8, U4, U12,
B4, B5, B10, G1, G4, U13 (slice three). Each row above names its record.
P2 and P3 as marked remain open. The delivery order
and the status of each brief deliverable are in
`docs/implementation/DELIVERY_ROADMAP.md`.

## 6. What this pass changed

1. The five blockers above (A1, A15, B1, B2, B3), with tests and a decision
   record (`docs/adr/2026-10-22-audit-fixes-period-order-grounding-privacy-identity.md`).
2. The Executive Command Centre on the Overview, built from the existing
   `/api/runs/{id}/executive` brief, the run detail and the approvals, with the
   demo write-control gaps (U2), the mislabelled button (U6) and the "Not
   assessed" counts (U7) corrected on the way. Its decision record states the
   interface budget allocation.

## 7. Strengths worth protecting

The KPI register (`server/maintenance/kpis.py`): ratios of sums, named
populations, unmeasured records disclosed, undefined rather than zero. Model
discipline: baselines, a 5% weak rule, thresholds from training rows only,
timing-screened inputs for maintenance risk. Causal language: the experiment
stage refuses a cause without an assignment column and prices the experiment.
Prescriptive honesty: a declared direction or a ranking by size that says so,
with a hold-course option. Provenance: every claim carries evidence ids and the
lineage stage checks both directions. Owner scoping on reads and writes, JWT
algorithm pinning, a sound connector egress fence, explicit input bounds,
hash-locked dependencies and SHA-pinned actions in CI. English and Arabic
parity by construction, logical CSS for RTL, chart numeric tables, text-labelled
performance states, reduced motion honoured.
