# Project assessment — 17 October 2026

**Assessment:** a working governed analytics prototype with a substantial reusable
engine. The maintenance product needs integration and evaluated prediction
evidence. Hosted customer use should wait for the authorization and execution
policy defects below to be fixed and verified. The capstone package also has
unfinished acceptance items.

This is a review of the local workspace. It is not a production penetration
test, a certification, a verification of the remote GitHub head, or an audit of
every line. No product code, deployment, source dataset or teammate deliverable
was changed. Reproductions used isolated temporary databases, synthetic records
and ephemeral test signing keys; no live provider credentials were used.

## Readiness by outcome

| Outcome | Assessment | Basis |
| --- | --- | --- |
| General upload → analysis → report/dashboard | Working prototype | Existing parsers, mappings, joins, governed stages, query endpoints and real API browser evidence |
| Maintenance contract and KPIs | Implemented helpers; integration incomplete | `server/maintenance/contract.py` and `kpis.py` exist; production callers of the KPI register were not found |
| Structural maintenance diagnostics | Stage implemented; opt-in and policy defect found | ADR 0039 and stage tests; not registered in the checked `config.json`; fatal-policy reproduction below |
| Executive maintenance interface | Demonstrable design preview | `MaintenancePreview.tsx` imports fictional `SAMPLE_ASSETS`; actual runs open a separate computed dashboard |
| Predictive maintenance | Research/prototype stage | Generic models and baseline cards exist; domain timing exclusions are not enforced by those models |
| Capstone submission | Release candidates with incomplete evidence | Report/deck files exist; no PBIX or notebook found in the inspected delivery folders; report source has unresolved markers |
| Hosted SaaS pilot | Blocked pending remediation and operational checks | Reproduced role-trust defect; organization boundaries, deployment worker/recovery and current PostgreSQL validation remain open |

These are qualitative judgments, not a measured completion percentage. There is
no accepted denominator that would justify saying the product is “90% finished.”

## Findings, in priority order

### R1 — Critical before hosted use: user metadata can grant platform privileges

**Code:** [server/auth.py](../../server/auth.py), lines 135–145; permission table
near line 25; [server/app.py](../../server/app.py), ownership check near line 481.

`JwtIdentity._principal_from` searches top-level claims, `app_metadata`, then
`user_metadata` for recognized roles. If a trusted role has not already been
found, user metadata can supply `owner` or `admin`. Both carry the cross-owner
`admin` permission. A signed JWT authenticates the token; it does not make every
metadata field administrator-controlled. Supabase explicitly identifies user
metadata as user-editable and unsuitable for authorization.
[Supabase user documentation](https://supabase.com/docs/guides/auth/users).

**Observed reproduction:** in an isolated API, a normal second user received
`viewer` and HTTP 404 for the first user's synthetic run. With the same subject
and `user_metadata.agentic_os_role = owner`, the application assigned `owner`
and returned HTTP 200 for that run. The test issuer was simulated with an
ephemeral key; no hosted service was accessed.

**Required change:** remove user-editable metadata from authorization decisions.
Use an explicit trusted claim or server-managed membership/role lookup, validate
the intended issuer/audience, and distinguish workspace ownership from platform
administration. Preserve least-privilege fallback.

**Acceptance:** a valid user token with any role-like value in user metadata must
never gain write, approval or cross-owner access. Test every protected resource
with two users and a separately authorized platform administrator. Test unknown
roles and trusted/untrusted claim precedence.

### R2 — High: the configured fatal governance policy does not stop the run

**Code:** [server/maintenance/governance.py](../../server/maintenance/governance.py),
lines 93–96 and 123; [server/runs.py](../../server/runs.py), lines 533–537;
[tests/test_maintenance_governance.py](../../tests/test_maintenance_governance.py),
the `test_fail_on_high_stops_the_run_instead` test.

`fail_on_high=True` changes the returned stage status to `failed`, but the
descriptor still has `can_fail_run=False`. The engine correctly follows that
descriptor and continues. The existing test checks the stage's returned status,
not the run's terminal behavior.

**Observed reproduction:** a synthetic dataset with structural findings produced
`task_state=failed`, `run_state=awaiting_approval`, and a report despite the fatal
option. Nothing was published. This contradicts the option's documented promise
to stop processing.

**Required change:** make the effective engine failure policy match the option;
add a full-engine regression test. Preserve the deliberate nonfatal behavior
when `fail_on_high=False`.

**Acceptance:** the fatal case ends in `failed`, does not execute downstream
analysis/report generation and cannot request publishing approval.

### R3 — High: model exclusion claims are not enforced by the models

**Code:** [server/maintenance/governance.py](../../server/maintenance/governance.py),
lines 115 and 134–135; [server/modelling.py](../../server/modelling.py),
`_inputs` near line 88 and regression/classification input selection near lines
397 and 538; [config.json](../../config.json).

The domain contract distinguishes information available before the decision
from outcomes, derived fields and unknown timing. The governance stage reports
excluded inputs, but generic model selection does not consume that list. It
excludes its target/date and selects other numeric and low-cardinality fields.
The checked configuration registers the generic models, not the maintenance
governance stage.

**Observed reproduction:** the selector admitted fields including
`Failure_Count`, `Operating_Hours` and `Maintenance_Cost_USD` which the maintenance
contract excluded when predicting downtime. This probe tested selection; it
does not claim a measured effect on a private model's accuracy.

**Required change:** add an explicit maintenance analysis profile with a persisted
feature-timing contract, target, prediction horizon and enforced input allowlist.
Reconcile the inputs named in governance claims with the model card's actual
inputs. Keep general-purpose exploratory models clearly labeled as such.

Also review the classifier's default target: its upper-quartile threshold is
computed from all outcomes before splitting (around lines 525–537). For a
prospective evaluation, fix a domain threshold or learn it on training data
only. Split by time when testing future maintenance decisions; group by entity
only after entity identity has been established. Chronological splitting already
exists in the generic implementation when suitable periods are available, but
can fall back to every-fifth-row evaluation when the split is too small.
These distinctions matter because unavailable future information can inflate
evaluation scores. [Scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage),
[time-series evaluation guidance](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-of-time-series-data).

**Acceptance:** tests prove that outcome/unknown-timing inputs cannot enter a
maintenance model; changing held-out outcomes cannot change training labels or
preprocessing. Produce a reproducible baseline comparison and an honest verdict
even if the model is weak. A classifier score is not evidence of a useful
remaining-useful-life or asset-failure predictor.

### R4 — High before domain dashboard binding: missing KPI inputs become zero

**Code:** [server/maintenance/kpis.py](../../server/maintenance/kpis.py),
`_num`, `_total`, `compute` and `computable` near lines 31, 99, 117 and 238.

The register correctly uses ratios of sums and named populations, but `_total`
turns an unparseable/missing measurement into zero. `computable` checks formula
columns without checking columns required by population predicates.

**Observed reproductions:** downtime values `[10, missing]` produced 5 hours per
record with no undefined reason or invalid-record count. First-time fix was
reported computable when its numerator/denominator existed but
`Work_Order_Type`, needed for its corrective-only population, was absent.

**Required change:** define missing/invalid/zero policies per KPI, require
population columns, reject nonfinite numbers, and return eligible/valid/excluded
counts. Use complete numerator/denominator pairs or withhold a result according
to an explicit policy. Do not silently treat an unknown value as a measured zero.

This is a helper-level finding. The generic dashboard was not shown to use this
register; remedy it before connecting the domain KPI endpoints/UI.

### R5 — Product integration gap: the maintenance experience is still split

**Code:** [MaintenancePreview.tsx](../../frontend/src/features/maintenance/MaintenancePreview.tsx),
sample import near line 9; [maintenance UI specification](../../docs/design/MAINTENANCE_UI_SPEC.md);
[ADR 0039](../../docs/adr/0039-governed-diagnostics.md).

The preview is honestly labeled synthetic, and the upload link reaches real
analysis. However, the executive equipment/condition views are not populated by
the uploaded run. The KPI register has no identified runtime consumers outside
its package. Governance registration is intentionally opt-in, so its existence
does not mean ordinary uploads receive those diagnostics.

**Next integration:** one maintenance profile → validated domain contract →
server-computed KPIs and model cards → the executive view. Every value should
carry a run ID, source snapshot, units, period, population and calculation
reference. Show unavailable evidence as unavailable. Until stable asset identity
exists, use observation-level views rather than invented asset histories.

### R6 — Delivery gap: finish the required artifacts and evidence

Inspected `private/capstone/` contains report/presentation candidates and a Power
BI build kit. No `.pbix`, `.ipynb` or `.ows` was found in that inspected tree or
the project-study folder. Files may exist elsewhere; this is not a claim about
every machine or shared drive.

The report source still requests the model notebook name, source transformations,
PBIX reconciliation/opening evidence and AI-validation details. The private
study records that the supplied official schedule was “to be announced”; the
team's planned dates need confirmation against the authoritative course page.

**Advice:** use the existing kit to complete the required PBIX, run the actual
model notebook, replace evidence placeholders, reconcile final figures across
all three deliverables, and open them in their intended applications. The web
application remains supporting evidence; it does not replace the required PBIX.
This review did not re-render or certify the binary PDF/PPTX candidates.

### R7 — Verification and documentation need a single current baseline

The Desktop working copy has no `.git`, so this review cannot identify a checked
commit or prove equivalence to a successful CI run. Python requirements use
minimum versions without a production lock/constraints file. Current CI has a
PostgreSQL service and useful test/audit steps, but this review did not inspect a
remote CI result.

Several records drift from current code. For example, the threat model opens by
saying there is no authentication layer and later documents JWT authentication;
the charter still describes contract/stage work as absent although opt-in code
now exists. Historical ADRs should remain historical; current status documents
should distinguish implementation, enabled configuration and verified behavior.

**Advice:** establish a reproducible source snapshot and tested dependency set,
then fix resource cleanup/fixture portability and run the complete native/CI
checks including PostgreSQL. Add the adversarial integration cases above;
passing unit tests alone did not catch the fatal-policy mismatch.

## What to keep

- The existing Python/FastAPI/React architecture and standard-library analysis
  core. This review found no reason to restart with another framework.
- Server-side parsing, explicit mapping and joins, stored run state, provenance,
  and exact-report human approval.
- Bilingual UI, accessible tables alongside charts, lazy-loaded views and measured
  bundle budgets.
- The distinction between verified computations and optional narrative wording.
- Synthetic test fixtures and private storage for course/customer material.

These are useful implemented controls. Their presence does not cancel the
specific defects above.

## Recommended sequence and gates

| Order | Work | Evidence to move on |
| --- | --- | --- |
| 1 | Repair role trust and fatal governance policy | Negative authorization tests; full-engine fatal/nonfatal tests; no cross-owner exposure or unintended continuation |
| 2 | Establish a passing reproducible baseline | Current source snapshot; full checks with PostgreSQL; full browser journey; failure categories resolved or explicitly bounded |
| 3 | Close capstone evidence gaps alongside software stabilization | Working PBIX; rerunnable model analysis; reconciled PDF/PPTX; no unresolved placeholders; confirmed official dates |
| 4 | Deliver one maintenance workflow end to end | Contract and units → enforced features → approved KPI definitions → real executive dashboard → reviewed report |
| 5 | Run a controlled SaaS pilot | Managed sign-in tested live; agreed organization/platform roles; durable worker deployment; isolation, restore and failure-recovery evidence |
| Later | Expand formats, scale and commercial functions | Customer need, measured bottlenecks, storage design and explicit scope for billing/organization administration |

Keep the upload promise precise: supported tabular formats within documented
limits, with a suitability assessment. “Any dataset” should never imply that an
arbitrary upload supports every KPI or prediction. Add workbook sheet discovery
before parsing if cover sheets are a common customer input.

For the first pilot, choose a single reviewable decision such as identifying the
largest recorded downtime/cost concentrations. Add forecasting only when its
inputs and out-of-time evaluation support it. Defer new agent frameworks,
additional cosmetic screens and paid-service features until that workflow is
reliable.

## Evidence files

### Checks executed for this review

The existing verifier, run through `verify_with_logs.py` solely to retain full
step output, printed **1 of 6 steps failed: Python tests**.

| Check | Actual result |
| --- | --- |
| Python suite | 1,090 tests; 2 failures, 259 errors, 140 skipped |
| Error classification | All 259 reported ERROR blocks end in `PermissionError [WinError 32]` during cleanup; both assertion failures compare CRLF fixture bytes with LF expectations |
| Maintenance, detectors and governance modules | 68 tests, OK |
| Frontend unit suite | 120 passed |
| Type check and production build | Passed |
| Brain check | Passed; no broken links or stale notes |
| Interface budgets | Passed; first-load JS 93.5/100 KB, total JS 149.9/160 KB, largest chunk 13.1/30 KB; CSS 9.4/10 KB initially and 14.5/16 KB total; fonts 119.4/120 KB |

The error classification explains the reported failures; it does not establish
that every product behavior is correct. In particular, the separate synthetic
probes reproduced defects despite the passing focused domain tests. The full
error log and [category summary](python-error-summary.json) are retained.

PostgreSQL was not configured. Browser suites were not rerun for this read-only
code assessment; the immediately preceding intake session recorded passing
focused real-API and isolated preview checks. Current production sign-in, remote
CI, live external sources and the final binary deliverables were not validated.

- [Local reproduction script](probes.py): temporary synthetic API/run tests and
  direct model/KPI checks. It prints no token, key or dataset rows.
- [Reproduction output](probes.json): observed results in machine-readable form.
- [Verifier summary](verification.txt) and per-step logs in this directory:
  the existing `scripts.verify` functions run unchanged through a logging wrapper.
- [Reviewed source fingerprints](reviewed-source-sha256.json): hashes of the
  inspected core files, so later fixes can be distinguished from this snapshot.
- [Existing upload guide](../../docs/DATASET_ANALYTICS.md) and
  [private delivery plan](../project-study-2026-10-17/DELIVERY_PLAN.md).

Only repository/documentation review, local synthetic reproductions and the
checks recorded with this assessment are claimed. No live model call, production
authentication test, paid-customer pilot, real-device accessibility study or
complete capstone submission was performed.
