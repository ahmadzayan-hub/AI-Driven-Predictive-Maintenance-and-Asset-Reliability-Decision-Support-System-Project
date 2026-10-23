# Delivery roadmap

Date: 22 October 2026 · Source: `docs/audits/SAAS_PLATFORM_ASSESSMENT.md`
(finding ids below refer to it) · Owner decisions are marked.

Status words: **Implemented** (in code, with tests), **Tested** (verified by
the recorded command), **Partially implemented**, **Blocked** (needs something
outside this repository), **Proposed** (designed, not built).

## 1. Delivered in this pass (branch `claude/tender-clarke-m4uwgq`)

| Item | Status | Evidence |
| --- | --- | --- |
| Period order in unmapped runs (A1) | Implemented, Tested | `tests/test_analytics.py::UnmappedPeriodOrderTestCase` |
| Narrator grounding (A15, G2) | Implemented, Tested | `tests/test_analytics.py::NarratorGroundingTestCase` |
| Model roles behind the privacy boundary (B2, G3) | Implemented, Tested | `tests/test_orchestration.py::PrivacyBoundaryForRolesTestCase` |
| Fail-closed hosted identity (B1) | Implemented, Tested | `tests/test_demo.py` |
| Per-owner session retention (B3) | Implemented, Tested | `tests/test_tenancy.py::SessionRetentionPerOwnerTestCase` |
| Executive Command Centre (U5), counts as counts (U7), list link (U6), demo write gaps (U2) | Implemented, Tested | `frontend/src/tests/views.test.tsx` (Command Centre); `frontend/e2e/overview.spec.ts` |
| Built-in Hermes, agents and consultants; a model per role; free open-model providers | Implemented, Tested (earlier today) | ADRs dated 2026-10-22 |
| Slice one of the release gate: illustrative gain label (A3), no GPT-to-Groq substitution (G7), uncapped approval queue (U1), announced loading states (U9), read-only CI token (B15) | Implemented, Tested | `docs/adr/2026-10-22-release-gate-slice-one.md` |
| Slice two of the release gate: rates never summed, trended or ranked (A4), a naive baseline and weak rule for every forecast (A5), figures checked against cited evidence (A6), approve only after reading (U3), JWT audience and issuer required (B7) | Implemented, Tested | `docs/adr/2026-10-22-release-gate-slice-two.md`; `tests/test_analytics.py::RatesAreNeverSummedTestCase`, `::ForecastBaselineTestCase`, `::ClaimFiguresMatchEvidenceTestCase`; `frontend/src/tests/approval-card.test.tsx` |
| Slice three of the release gate: decision inputs and record (A2, A13), signalling escalation (A8), currency (U4), landing and phone bar (U12), per-session locking, transactional restore and request logging (B4, B5, B10), blind-set floors (G1), model call ledger (G4), browser coverage of demo, Assets and Approvals (U13) | Implemented, Tested | `docs/adr/2026-10-22-release-gate-slice-three.md` |
| P2 slice one: verdict bound (A9), declared splits (A10), incomplete periods (A12), loopback by default (B8), idempotent run creation (B14, in part), wall-clock limits on custom stages and agent runtimes (G10) | Implemented, Tested | `docs/adr/2026-10-23-p2-slice-one.md`; `tests/test_p2_slice_one.py` |

## 2. Next release gate (P1)

Closed on 22 October. The three slices and their records are in section 1;
the open P2 and P3 items are in section 3. Two owner decisions taken under
the 22 October instruction can be reversed knowingly: the currency field in
the mapping with "currency not stated" as the default (U4), and landing on
the Command Centre with Approvals in the phone bar (U12). The signalling
rule (A8) escalates every recorded failure on a safety-function asset class
and names its condition threshold as a convention, not a standard.

Carried forward from slice three: the standards lint scored 0% on its first blind
set and waits for the rewrite planned for the causal lint; per-tenant model
budgets remain open (the ledger is per process). The interface inputs for uplift and cost, and
the decision record card on the run, were delivered the same day
([decision](../adr/2026-10-22-decision-inputs-interface.md)).

## 3. Following release (P2) and backlog (P3)

As marked in the assessment: KPI bases (A7), input screening in generic
models (A11), model versioning and calibration (A14), transformation
reversibility (A18); rate limiting and model quota (B6), narrow excepts (B9),
connection pool (B11), versioned migrations (B12), hosted publish target
(B13), the rest of the API contract (one error envelope and OpenAPI behind
auth, B14), connector allowlist (B16); railway wording behind a profile (U8, owner decision), asset KPI errors
and endpoint (U10), chart table note (U11), naming (U14), one upload flow (U15),
as-of stamps (U16), pack parity and executive hook (U18), font subsetting
(U19), navy rail (U20, owner decision); structured consultant output and
deterministic agreement (G5, G6), eval cases for the two unmeasured actions
(G8), reviewer benchmarks (G9), optional runtime CI job (G11); and the P3 items.
The first P2 slice (A9, A10, A12, B8, the idempotency half of B14, G10) was
delivered on 23 October ([decision](../adr/2026-10-23-p2-slice-one.md)).

## 4. The brief's deliverables and their status

| Deliverable | Status | Where |
| --- | --- | --- |
| `docs/audits/SAAS_PLATFORM_ASSESSMENT.md` | Implemented | this pass |
| `docs/architecture/TARGET_SAAS_ARCHITECTURE.md` | Implemented (incremental target, no rebuild) | this pass |
| `docs/design/PRODUCT_UX_REDESIGN.md` | Implemented (journey around the five questions; which screens to keep, merge, add) | this pass |
| `docs/design/DESIGN_SYSTEM.md` | Partially implemented: points at the brand system and tokens that exist, lists the brief's deviations for owner decision | this pass; `docs/design/ASSET_RELIABILITY_BRAND_SYSTEM.md` |
| `docs/agents/AGENT_VALIDATION_REPORT.md` | Implemented (contracts, suites, today's scores, gaps) | this pass; `docs/AGENT_VALIDATION_REGISTER.md` |
| `docs/analytics/PREDICTIVE_MODEL_VALIDATION.md` | Implemented (every model as built: target, validation, baseline, metrics, gaps) | this pass |
| `docs/analytics/PRESCRIPTIVE_DECISION_FRAMEWORK.md` | Proposed (decision record schema and rules, not yet in code) | this pass |
| `docs/voice/VOICE_ASSISTANT_FEASIBILITY.md` | Partially implemented: what exists (dictation, server transcription, playback) and the adoption rules; no external repository reviewed in this pass | this pass |
| `docs/qa/END_TO_END_VALIDATION.md` | Tested (real commands and counts) | this pass |
| `docs/implementation/DELIVERY_ROADMAP.md` | Implemented | this file |

## 5. What is not in scope of this pass, and why

- **Navigation redesign to the brief's six groups.** The audit found no value in
  reproducing it screen for screen: most groups would be empty or duplicate
  existing views. The Command Centre, the executive overview, Assets,
  Approvals, Datasets and Analyses cover the five questions today. Renames are
  P2 (U14).
- **Product rename to "Asset Reliability AI".** The brand mark already reads
  "Asset Reliability"; the full product title in `CLAUDE.md` and the capstone
  documents is the long form. Owner decision; a rename touches the README,
  manifest, charter and the capstone appendix.
- **Multi-agent architecture changes.** Not justified: the assessment found the
  deterministic stages reliable and the model roles already optional and
  grounded. The one place a model is used where code is better (consultant
  agreement) is a P2 fix.
- **A voice JARVIS integration.** Not without the licence, dependency and
  security review the brief itself requires (`docs/voice/VOICE_ASSISTANT_FEASIBILITY.md`).
