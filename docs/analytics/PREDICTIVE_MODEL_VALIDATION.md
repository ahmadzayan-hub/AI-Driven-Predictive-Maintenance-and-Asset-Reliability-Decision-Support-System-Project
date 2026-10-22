# Predictive model validation

Date: 22 October 2026 · What each model in the code does, how it is
validated, against which baseline, with which metric, and what is missing
against the brief's mandatory list. No performance figure is quoted here:
performance belongs to a run's model cards, never to a document.

## 1. Models as implemented

| Model | Target | Inputs | Split | Baseline | Metrics | Where |
| --- | --- | --- | --- | --- | --- | --- |
| Linear trend forecast (default pipeline) | next 3 period totals of the chosen measure | the period series | refit on all but the last 1 to 3 periods; needs 6 | none | MAPE on the held-out points (zero actuals skipped); R² on the fit; shown as a band on period 1 only | `server/analytics.py::predictive` |
| Regression (least squares, ridge 0.001; opt-in) | the measure per record | every other numeric column, up to 3 text columns | latest 20% of periods; every-fifth record under 5 periods; training capped at 5,000 | training mean | MAE, improvement over baseline (weak under 5%), held-out R² | `server/modelling.py` |
| Classification (Gaussian naive Bayes; opt-in) | a category, or top quarter of the measure (threshold from training rows only) | as above | as above | most common class | balanced accuracy, accuracy, per-class hit rates, confusion; no precision, recall or calibration | `server/modelling.py` |
| Clustering (k-means, 2 to 5; opt-in) | none | numeric columns including the measure | none; silhouette on a 400-row sample | one group | silhouette (needs 0.25), spread explained | `server/modelling.py` |
| Seasonal forecast (trend plus season; opt-in) | next full season | the period series | last season held out; needs 3 seasons | best of last value, last season, trend | MAE, improvement (weak under 5%) | `server/modelling.py` |
| Maintenance risk: repeat_failure, sla_breach (naive Bayes; opt-in) | corrective job has more than one failure; job misses SLA | known-before columns only (timing-screened) | chronological with 5+ periods, else every fifth; at least 50 held out | stronger of majority class and best known-before grouping rule | balanced accuracy; "useful" needs +5% over baseline and 55% | `server/maintenance/targets.py` |
| Rail asset screening | none (rules) | criticality, failures, condition | none | none | counts only; says "no model, no prediction" | `server/rail_asset_decisions.py` |
| Reliability validation (external predictions) | failure in a registered window | predictions registered in advance | prospective, adjudicated | a baseline probability per prediction | confusion, Wilson intervals, Brier against baseline, calibration bins, lead time, false alerts per asset-month | `server/reliability_validation.py` |

## 2. Against the brief's mandatory validation

| Requirement | Status | Notes |
| --- | --- | --- |
| Prediction target identified | Met | every card names it; unsupported targets say why |
| Input features identified | Met for maintenance risk; partly for generic models | generic stages take every numeric column (A11) |
| Temporal and target leakage prevented | Met for maintenance risk (contract timing, leakage detector); not for generic models (A11) | |
| Data sufficiency validated | Met | minimum periods, minimum held-out records; "not supported" otherwise |
| Chronological validation for time series | Partly | silent fallback to every-fifth under 5 periods (A10) |
| Comparison against a meaningful baseline | Met for models; **not for the default forecast** (A5) | |
| Suitable metrics | Partly | MAE, balanced accuracy present; no precision, recall, PR-AUC or calibration in the pipeline (A14); MAPE on 1 to 3 points (A5) |
| Uncertainty and limitations reported | Partly | limitation claims; no intervals on verdicts (A9); forecast band on period 1 only |
| Model and dataset versions tracked | Not met | no version, snapshot hash or training window on cards (A14); the run has a dataset snapshot hash |
| Drift and degradation identified | Not met | only the separate prospective protocol |
| Unsupported predictions rejected | Met | `not_supported` with a reason; no score reported |
| No artificial confidence | Met | no confidence number is produced anywhere |

## 3. What the data allows

The course dataset records each asset once, with pre-computed failure
probability and health index columns (`session-logs.md:928`). It cannot
carry a failure, remaining-life or condition forecast, and the maintenance
risk targets are cross-sectional job screens. The platform says so in its
reports; this document repeats it so that nobody reads "predictive
maintenance" as asset failure prediction on that data.

## 4. Next steps, in order

1. Naive and seasonal-naive baselines with rolling folds for the default
   forecast; the 5% weak rule (A5).
2. Declare the split on the verdict; require chronological or asset-grouped
   splits on asset data (A10).
3. Timing-screened inputs for the generic stages (A11).
4. Card version, snapshot hash and training window; probabilities with Brier
   against the baseline; calibration bins (A14).
5. Confidence bounds or a permutation test on the "useful" verdict (A9).
6. Feed pipeline model outputs into the registered-window protocol, which is
   the right design and already exists.
