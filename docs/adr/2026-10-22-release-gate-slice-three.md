# Release gate, slice three: decision inputs and record, signalling escalation, currency, landing, hosted robustness, blind floors, model ledger, browser coverage

Date: 2026-10-22 · Status: Accepted (assessment findings A2, A13, A8, U4,
U12, B4, B5, B10, G1, G4, U13 in `docs/audits/SAAS_PLATFORM_ASSESSMENT.md`;
the P1 list in `docs/implementation/DELIVERY_ROADMAP.md`; slices one and
two are the records of the same date). The three owner decisions (A8, U4,
U12) were taken by the owner on 22 October with the instruction to deliver
all remaining P1 items; the choices made under that instruction are stated
below so they can be reversed knowingly.

## Decisions

1. **Uplift and cost are inputs; the sensitivity stage varies them per
   option (A2).** A run may carry `assumptions`: an uplift per target, a
   cost per target, and the uplift range the sensitivity stage explores
   (default 5% to 20%). Every option records its uplift and whether it was
   stated or assumed, its cost when stated, and its net gain; each figure is
   a calculation the claims cite. The ranking is called stable only when the
   winner at the low end of the range (or at its stated uplift) still beats
   every other option at the high end; otherwise the flip point is reported,
   in both languages. The three uniform scenarios are kept and labelled for
   what they are: with one uplift for everyone the order is scale-invariant.
   A property test shows a stated uplift and a stated cost each flip the
   ranking. Nothing in the interface collects the inputs yet; the API does.
2. **One decision record per recommendation (A13).** The prescriptive stage
   writes it (id, issue, scope, evidence, observed risk, every alternative
   with its uplift, cost and gain, expected impact across the range, which
   costs are not stated, constraints, the basis of the ranking), the
   sensitivity stage completes its uncertainty (flip points, range,
   break-even), and the approval gate completes its approval (state, time,
   approver) from the approval row. `recommended_action` is filled only when
   the measure's direction is declared and every cost is stated; otherwise
   the record says the ranking is by size and why. The run detail carries
   the record and the prescriptive report prints it. Publishing a run that
   recommends an action without a record is refused.
3. **A failure on a safety function always escalates (A8).** In the rail
   screening, any observation on a signalling, interlocking, train control,
   train protection or level crossing asset class with a recorded failure
   goes to engineering review whatever its criticality label. The condition
   threshold of 60 is a named screening convention set by the owner today,
   not a figure from a standard, and every screening states the threshold
   and the reason it applied.
4. **Currency is in the mapping or stated as not stated (U4).** A column
   mapping may state the currency of its money columns as an ISO 4217 code
   (three letters); the server validates it with the rest of the mapping and
   refuses anything else by field, in both languages. The executive brief
   carries the code as `currency` (null when the run has no mapping or the
   mapping states none), so the Command Centre, the executive overview and
   the KPI policy editor format money by code ("AED 1,250,000.00"), never by
   a symbol two currencies share. When no currency is stated, money figures
   are labelled "currency not stated" ("العملة غير محددة"); the former
   "source currency" label is retired because it implied a unit the data
   had not declared. Nothing assumes a default currency. The mapping panel
   has the optional field; exports still say "monetary units" (P2).
5. **Returning users land on the Command Centre; Approvals is in the phone
   bar (U12).** An address that names no view, or an unknown one, opens the
   Command Centre; every explicit address, `#/assistant` included, still
   opens what it names, and the first-visit onboarding dialog precedes the
   same landing. The phone bottom bar holds Command Centre, Assets,
   Approvals and Workspace (the demo shows Analyses in place of Workspace);
   Dashboards moves to the drawer under More, because publishing waits on a
   person and approvals must be one tap away. The browser specs that opened
   on the assistant now navigate to it first.
6. **Hosted robustness (B4, B5, B10).** The process-wide lock in
   `server/app.py` now protects only in-memory session state: the
   read-modify-write of a session row and, in local mode, the memory file.
   The assistant's model call runs under a per-session lock and the
   pipeline's advance under the engine's own `store.atomic("run:…")`
   transaction, so one slow model call no longer stalls every tenant; on
   SQLite the store's single connection still serialises reads for a
   stage's duration, and PostgreSQL locks only the run. A restore is all or
   nothing: every row of every table is checked against the live schema
   before any delete, and the deletes and inserts run in one transaction on
   both dialects. Every request carries an id (an incoming `X-Request-ID`
   of up to 64 safe characters, otherwise generated), echoed on every
   response including unexpected errors, and writes one JSON line to the
   `agentic_os.requests` logger with method, path without query string,
   status, duration and a 12-character SHA-256 prefix of the token subject
   or "anonymous"; tokens, bodies, query strings and raw subjects are never
   logged.
7. **Floors on blind sets (G1).** Every text-classifier suite declares one
   blind split, written from the label definitions only and never read
   while a rule is fixed, and the evaluation scores it on every run. The
   floors cover that split from today at the measured score rounded down
   (causal 0.60, intent 0.61, jargon 0.85, standards 0.0); dev and holdout
   floors are kept but no longer quoted as generalisation. The causal
   holdout was read while its fixes were chosen (ADR 0056) and the standards
   holdout was written by the session that wrote the patterns, so for those
   suites holdout is a second dev score, and the script's docstring, the
   floors file and the validation report say so. A blind set used to fix
   rules moves into dev and a new one is written before the fix is scored.
   The standards lint scores 0% on its first blind set (36 cases, 19
   refusable sentences, none caught) against 100% on the sets written with
   its patterns in view. The lint is left unchanged; the result stands as
   the baseline for the rewrite already planned for the causal lint.
8. **A model call ledger (G4).** The model gateway keeps an in-process
   ledger of every provider attempt: provider, model, task, outcome (ok,
   empty, error), latency and the token counts the provider reported, never
   estimated; the last 500 entries and per-provider totals, with the totals
   exposed in `GET /api/health` as `model_calls`. Usage now says model
   tokens are tracked per process, not per tenant; per-tenant model budgets
   remain out of scope.
9. **Browser coverage of the demo, Assets and Approvals (U13).** Every
   navigation view is scanned for WCAG 2.2 AA with axe in the state that
   has the most on screen: Asset Intelligence and the Approval inbox join
   the loop, the inbox with a run waiting and its card open. The required
   breakpoints (320, 768 and 1024 px) are checked on the views that carry
   content, including the inbox with a card. The view-only demo gets its own
   Playwright server (port 8125, `AGENTIC_OS_DEMO=1`, a fresh database each
   start) and its own journey: no sign-in, the seeded fictional analysis on
   the Command Centre, the executive overview, and every write control
   replaced by the demo note rather than left to fail, in English and
   Arabic. Specs land on the Command Centre as a reader does and open the
   assistant by its address when they need the composer. The e2e sign-in
   token now carries the audience and issuer slice two made the server
   require, minted with the server's own helper: the committed auth and CSP
   specs had been failing at the previous head for that reason, which the
   hosted CI could not show because no runner was assigned.

## Verification

`tests/test_analytics.py::PrescriptiveInputsTestCase`,
`::DecisionRecordTestCase`; `tests/test_runs.py` (the record travels with
the run, the gate completes it, bad inputs are refused, publishing is
refused without a record); `tests/test_rail_asset_decisions.py` (a
signalling failure escalates at Low criticality; the threshold is stated);
`tests/test_mapping.py` and `tests/test_executive.py` (currency);
`frontend/src/tests/format.test.ts`, `mapping.test.tsx`, `views.test.tsx`,
`dashboard.test.ts` (money format, mapping field, Command Centre, landing);
`tests/test_app_concurrency.py`, `tests/test_app_request_log.py`,
`tests/test_backup.py`, `tests/test_model_gateway.py::CallLedgerTestCase`;
`tests/test_evals.py` with the blind floors and
`scripts/evaluate_agents.py --check`; the Playwright suite with the demo
server; the full verifier with PostgreSQL. Counts are in `README.md#testing`.
