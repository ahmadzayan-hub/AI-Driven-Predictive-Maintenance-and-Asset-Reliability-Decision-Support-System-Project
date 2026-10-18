# Requirement-to-evidence matrix

**Started:** 18 October 2026. **Baseline:** the Desktop working copy, which has
no `.git` directory — so no commit can be cited for it. The reviewed snapshot is
fingerprinted in [reviewed-source-sha256.json](reviewed-source-sha256.json); the
files changed since are listed per row below. A separate clone at
`%TEMP%/aos/r` tracks `claude/agentic-os-final-project-53j6ql` at `47857ef` and
holds everything pushed up to and including S2. **Nothing from this remediation
has been pushed.**

Status words mean exactly this, and nothing softer:

| Word | Meaning |
| --- | --- |
| **Closed** | Fixed, covered by a test, and the test was shown to fail when the defect is reinstated |
| **Partly closed** | Fixed and tested in part; the remainder is named in the row |
| **Open** | Not started or not yet verified |

A passing test is not evidence on its own. Three times in this work a test
passed while proving nothing — a stage-level assertion that could not see the
engine's behaviour, a skip that read as a pass, and a fixture whose "no signal"
case contained signal. Every **Closed** row below cites a negative control.

## Assessment findings

| ID | Finding | Priority | Status | Evidence |
| --- | --- | --- | --- | --- |
| R1 | User metadata can grant platform privileges | Critical | **Closed** | `server/auth.py`: `user_metadata` removed from role resolution (`TRUSTED_CLAIM_SOURCES`), server-managed `role_assignments` outrank every token claim, `owner` no longer carries `admin`, issuer/audience required when configured. `tests/test_authorization.py`, 28 tests. **Negative control:** reinstating `user_metadata` as trusted and `admin` on `owner` fails 8 tests, including `test_a_self_granted_metadata_role_reaches_nothing` (the assessment's 404→200 reproduction). |
| R2 | Configured fatal governance policy does not stop the run | High | **Closed** | `server/maintenance/governance.py`: `can_fail_run` is set from `fail_on_high` in `__init__`. `tests/test_maintenance_governance.py::FatalPolicyUnderTheEngineTest`, 5 full-engine tests asserting run state `failed`, no downstream task succeeded, no artifact, no publish approval. **Negative control:** restoring `can_fail_run = False` fails 4 of them. |
| R3 | Model exclusion claims are not enforced by the models | High | **Partly closed** | `server/maintenance/targets.py` (ADR 0040) enforces `contract.model_inputs` for the maintenance risk stage: 11 of 60 columns admitted, 49 excluded with reasons; chronological split; informative baseline; absolute chance floor; held-out floor of 50. `tests/test_maintenance_targets.py`, 19 tests. **Not yet done:** the generic ADR 0033 models still select their own inputs, and no maintenance *profile* exists in `config.json`, so an ordinary upload does not get the enforced path. The classifier's upper-quartile threshold is still computed before splitting. |
| R4 | Missing KPI inputs become measured zeros | High | **Open** | Reproduced by the assessment: downtime `[10, missing]` yields 5 h/record with no undefined reason; `computable` ignores columns needed by population predicates. Next in this session. |
| R5 | Maintenance experience is split from real runs | High | **Open** | `MaintenancePreview.tsx` still imports `SAMPLE_ASSETS`. No runtime consumer of the KPI register outside its package. Depends on R4. |
| R6 | Capstone artifacts and evidence incomplete | High | **Open** | No `.pbix`, `.ipynb` or `.ows` found under `private/capstone/`. Report source retains `[Add: …]` markers (8 in `report_draft.md`, 1 in `slides/dashboard.html`, counted by `tools/check_package.py`). |
| R7 | Verification needs one current baseline | Medium | **Partly closed** | `SqlStore.close()` added; `tests/support.py` added; stores closed before temporary-directory cleanup across 18 test files. **Errors 259 → 93**, suite 1,142 tests, 3 failures, 132 skipped. **Not yet done:** ~93 errors remain in `test_assistant` (21), `test_agent_runtime` (19), `test_mapping` (12), `test_erasure` (11), `test_joins` (10) — same Windows file-handle cause, different construction sites. The 3 failures are the CRLF-fixture and subprocess-spawn ones the assessment classified. No dependency lock file yet. PostgreSQL not configured here. |

## Correctness gates, in the order they will be taken

| # | Gate | Depends on | Acceptance |
| --- | --- | --- | --- |
| 1 | R4 — KPI missing/invalid/nonfinite/zero policies | — | Eligible, valid and excluded counts returned; population columns required; an unknown value never becomes a measured zero; unsupported KPIs withheld with a reason |
| 2 | R3 — maintenance profile enforcing the timing contract | R4 | A registered profile persists target, horizon, allowed inputs and exclusions; model cards name the inputs actually used; generic models stay labelled exploratory |
| 3 | R5 — real upload-to-overview journey | R4, R3 | Executive view bound to server-computed results for a real run ID, with source, period, units, population and calculation references; unsupported values shown unavailable |
| 4 | R7 — remaining cleanup, lock file, PostgreSQL | — | Suite runs with errors attributable to named causes only |
| 5 | R6 — capstone artifacts | tools available | Named in the handoff with the exact remaining action where software or human input is missing |

## Boundaries honoured in this work

No deployment, publishing, push, pull request, external message or paid-service
activation. No Git history rewritten. No original private dataset altered. Course
files and personal data stay under `private/`, which `.gitignore` covers.
