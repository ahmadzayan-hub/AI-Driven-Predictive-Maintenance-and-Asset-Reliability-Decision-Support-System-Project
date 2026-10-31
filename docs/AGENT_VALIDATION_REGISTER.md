# Agent and Output Validation Register

Updated 18 October 2026 | Status: development assessment, not an operational certificate

## What has been reviewed

The repository's `server/analytics.py` declares 21 core stages from planner to reporter. `server/runs.py` supplies **Hermes**, the stateful orchestrator, and a separate approval-gated publish step. The joined-dataset `merge` stage is conditional. `config.json` also registers optional model and maintenance specialists, including `rail_asset_manager`, `reliability_model` and `risk_ranking`; not every stage runs on every profile.

### Validation matrix

| Group | Source code / existing checks | Coverage verdict |
| --- | --- | --- |
| Planner, source, contract, profiling, quality, privacy and cleaning | `server/analytics.py`; `tests/test_analytics.py`, `test_runs.py`, `test_datasets.py`, `test_evals.py` | Structural and synthetic behavior covered; not production data certified |
| Metric governance, preparation, segmentation and descriptive analytics | `server/analytics.py`, `server/metrics.py`, `tests/test_metrics.py`, `tests/test_analytics.py` | Arithmetic contracts covered; customer metrics require owner-approved definitions |
| Diagnostic, causal inference, forecast, anomaly, prescriptive and sensitivity | `server/analytics.py`, `tests/test_analytics.py`, `tests/test_evals.py` | Synthetic code checks exist; causal and prediction generalization **not** demonstrated by these tests |
| Visualization, lineage, independent validator and reporting | `server/analytics.py`, `tests/test_runs.py`, `tests/test_report_language.py` | Calculations/citations/approval workflow tested; editable executive DOCX/PPTX output needs separate validation |
| Model stages: regression, classification, clustering, seasonal forecast | `server/modelling.py`, `tests/test_modelling.py` | Baseline tests exist; individual prediction target and chronology remain decision-specific |
| Maintenance Governance, Risk and Railway Asset Manager | `server/maintenance/`, `server/rail_asset_decisions.py`, `tests/test_maintenance_governance.py`, `tests/test_maintenance_targets.py`, `tests/test_rail_asset_stage.py` | Synthetic stage contracts and refusals covered; no authority for live railway decisions |
| Reliability model (R1) | `server/maintenance/reliability.py`, `tests/test_reliability_model.py` | Synthetic fleets with known shapes recovered within 10%; governed run passes the validator in English and Arabic; class pattern only, no single-asset remaining life, human review before any interval change |
| Risk ranking (R2) | `server/maintenance/risk_ranking.py`, `tests/test_risk_ranking.py` | Chance checked against the survival ratio by hand; ranking, cost fallback and extrapolation flag tested; governed run passes in English and Arabic; criticality not weighted; no work order issued |
| Conversation intent, column roles, privacy, raw-data guard, model router, jargon, causal wording and figure checks | `scripts/evaluate_agents.py --check`, `evals/`, `tests/test_evals.py` | Labelled dev and holdout classification performance with floors; not a universal agent accuracy measure |
| Hosted identities, tenant access and background work | `server/auth.py`, `server/storage.py`, `server/worker.py`, `tests/test_tenancy.py`, `tests/test_auth.py` | Automated tests present; live provider login, recovery, storage and isolation still need deployed pilot evidence |
| Live third-party language models | `server/model_gateway.py`, `tests/test_model_gateway.py` | Stubbed/provider-wire testing; no verified live-provider quality, toxicity or hallucination score |

## Meaning of a passed gate

- Passing unit tests proves behavior against **those fixtures only**.
- Passing `evaluate_agents.py --check` proves the published synthetic classifier recall floors **for the evaluated suites**; it does **not** measure every analytics specialist or guarantee 100% correct answers.
- Since 22 October 2026 the floors in `evals/floors.json` also cover each text classifier's blind split, the set never looked at while fixing: jargon blind_v6 (0.85) and standards blind_v3 (0.13; blind_v1 scored 0.0 and blind_v2 0.31, each moved into dev on 23 October 2026 when the rules were fixed against it, `docs/adr/2026-10-23-standards-lint-families-blind-v2.md` and `docs/adr/2026-10-23-standards-lint-blind-v3.md`). Causal and intent had blind_v7 floors (0.60 and 0.61) until 23 October 2026, when blind_v7 moved into their dev splits to fix the rules; they have no blind floor until blind_v8 is added (`docs/adr/2026-10-23-blind-v7-into-dev-causal-and-intent-fix.md`). The holdout floors are unchanged, but the causal holdout was read while its fixes were chosen (ADR 0056) and the standards holdout was written by the session that wrote the patterns, so the blind score is the one to quote.
- Generated reports require source version, metric definitions, formula traceability, scope/grain, bilingual parity, model card and human approval.
- Any model without chronological, leakage-controlled evaluation must say **unvalidated**.
- Any obsolescence output lacking independently sourced OEM end-of-support evidence must say **insufficient evidence**.
- The maintenance design preview uses clearly labelled fictional equipment and never constitutes field performance evidence.

## Executable audit gates

```bash
python -m unittest discover tests -v
python scripts/evaluate_agents.py --check
python scripts/verify.py --e2e
```

GitHub CI now runs the deterministic labelled-agent evaluation as a named step in addition to the existing broad test suite. Preserve the command output and GitHub run reference for every release. Do not copy historical test counts into live status cards.

## Measured synthetic holdout snapshot, 18 October 2026

Recorded from GitHub Actions run **39147453294**, Python agent-quality stage.
These values are **not** estimated live customer accuracy:

| Labelled check | Holdout cases | Measured result |
| --- | ---: | ---: |
| Conversation intent routing | 60 | **72%** macro recall |
| Column role selection | 33 | **100%** macro recall |
| Personal-data field detector | 33 | **100%** recall |
| Model provider router | 12 | **89%** macro recall (floor 0.88 since 22 October: two GPT cases relabelled OpenAI, no substitution) |
| Raw-row disclosure guard | 7 | **100%** recall |
| Statistical-jargon detection | 24 | **92%** recall |
| Unsupported causal wording detector | 32 | **69%** recall |
| Unsourced/wrong figure detection | 11 | **100%** recall |

**Risk interpretation:** 69% causal-wording recall and 72% intent macro
recall are inadequate evidence for unattended executive publishing.
Retain independent validation and human approval, expand truly blind
language-domain and Arabic adversarial sets, and compare against
model-based baselines before permitting wider autonomous actions.
The 100% marks come from very small educational test cases and must
not be marketed as 100% reliability.

The informational Python dependency audit also reported
`setuptools 79.0.1` with advisory `PYSEC-2026-3447` and a suggested
fix version 83.0.0. Verify whether it is a build-tool-only exposure or a
shipped runtime dependency, then update or document an explicit risk
decision. Do not silently suppress security findings.

## Remaining release blockers

1. Authenticated multi-tenant penetration and isolation checks against deployed environment.
2. Real dataset import and multi-file lineage with error recovery.
3. Model target, feature availability and asset identity approval by railway engineering domain owner.
4. Bilingual executive PDF/DOCX/PPTX render QA with source-figure reconciliation.
5. Source-backed live dashboard acceptance tests, not visual concept mock-ups.
6. Browser/UI walkthrough and accessibility checks on the Vercel preview.
7. Secure storage, secrets, worker duration, backups and restore drill.
8. Demonstration of human review with immutable evidence and no autonomous railway work-order release.

## Example reviewer sign-off

`Unverified → Synthetic checks passed → Preview smoke-tested → Authenticated pilot validated → Operationally approved`

Do not collapse these into a single "AI ready" badge.
