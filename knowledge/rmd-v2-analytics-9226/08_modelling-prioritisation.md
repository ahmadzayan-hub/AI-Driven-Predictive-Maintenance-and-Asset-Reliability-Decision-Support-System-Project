## 7. Modelling and maintenance prioritisation
<!-- kb: domain=analytics.9226.model; synthetic=true; limits=synthetic_educational_data|not_validated_prediction|not_operational_rmd -->


### 7.1 Match the technique to the question

| Question | Suitable starting method | Required evidence |
| --- | --- | --- |
| Where are downtime and cost concentrated? | Aggregation, Pareto and stratified comparisons | Defined grain, exposure, periods and reconciled totals |
| What factors accompany poor performance? | Diagnostic comparisons and regression where appropriate | Confounding analysis; no unsupported causal claim |
| Will a defined failure occur next month? | Simple classifier baseline, then a suitable alternative | Stable identities, dated features, future labels and usable warning horizon |
| What workload is expected? | Last-value, seasonal or mean baseline before more complex forecasting | Consistent time series, sufficient history and rolling evaluation |
| Which asset profiles differ? | Clustering with suitable scaling/mixed-data handling | Interpretable groups and stability checks |
| Which actions fit the monthly resources? | Transparent rule baseline or constrained optimisation | Action-level costs, duration, skills, access, parts and mandatory obligations |

A fitted model must be compared with the simplest useful baseline. Retain a baseline when a complex model does not improve the relevant outcome.

### 7.2 Leakage and target design

For future failure prediction, define a prediction time t, a horizon H, a failure definition and a label observed after t. A feature is eligible only if its value was available at t. Apply the same rule to derived features and historical aggregations.

Current-period Failure_Count, Failure_Mode, Downtime_Hours, work-order outcomes, repair duration and post-event cost may reveal the event being predicted. Source-generated Risk_Category, Failure_Probability and composite health/priority scores may encode the target-generating mechanism. Do not include them automatically.

A random row split can mix information about the same physical entity or period. A chronological split can also be misleading if the data do not represent valid longitudinal histories. Use an appropriate time/asset grouping design for the intended deployment population, and keep preprocessing fitted on training data only.

If a teaching exercise defines the target as Failure_Count > 0 in the same record, 4,015/5,000 records are positive. An always-positive classifier would therefore have 80.3% accuracy. This is a useful baseline illustration, not a next-month prediction task. Failure_Mode would directly expose this current-record target and must not be presented as an early-warning feature. [SRC-28; CALC-01]

### 7.3 Historical split and model results

The original dates support a numerical split of **3,340 records before September 2025** and **1,660 from September 2025 onward**. This matches the split reported in earlier MIYAAR context. It does not validate the feature set, labels, model, original asset identities or test results. [SRC-28; CALC-01; HIST-02]

Earlier project context reported approximately 0.73 AUC for a recommended classification approach, a small regression improvement, descriptive clustering and a simple-average forecasting baseline that performed best. No corresponding model weights, full evaluation outputs, exact code revision or held-out predictions were inspected here. These remain historical claims. [HIST-02]

### 7.4 Evaluation that serves maintenance decisions

For classification, report the positive class, counts, precision/recall, PR-AUC where imbalance makes it useful, ROC-AUC, calibration, confusion matrix at the selected threshold and uncertainty. Add warning lead time, false alerts per asset-period, missed consequential events, review workload and intervention feasibility.

For regression/forecasting, report MAE and RMSE in operational units, compare against the same baseline and horizon, show errors by class/site/criticality, and check interval coverage if intervals are provided. MAPE needs explicit handling of zero or near-zero actual values.

For clustering, describe the groups and their stability; a cluster is not an approved risk class. For causal claims about maintenance strategies, comparisons require a defensible study design and control for confounding. Synthetic strategy-health relationships cannot prove real maintenance effectiveness.

### 7.5 Proposed prioritisation contract

A monthly candidate action record should include:

- Valid asset and action identifiers.
- Evidence available at the decision date.
- Mandatory status and approved criticality/consequence.
- Estimated risk reduction with its evidence or scenario assumption.
- Cost, technician hours/skills, access window, parts and dependencies.
- Recommended action, justification, alternatives and uncertainty.
- Named decision owner, approval state and outcome tracking.

Define mutually exclusive alternatives for each asset and planning period. Select at most one alternative, unless a combined intervention is explicitly modelled as a separate feasible package. Sum expected benefits only when they do not double count the same avoided failure or loss.

An illustrative optimisation chooses action variables x_i to maximise total expected avoidable consequence less intervention cost, subject to budget, capacity, access, parts, action-exclusivity and mandatory-task constraints. For example:

~~~text
maximise  sum_i x_i * (expected_avoidable_loss_i - intervention_cost_i)
subject to:
  sum_i x_i * intervention_cost_i <= approved_budget
  sum_i x_i * technician_hours_i <= available_qualified_hours
  access, parts, dependencies and mandatory-task rules
  for each asset-period alternative group g: sum_i_in_g x_i <= 1
  x_i in {0, 1}
~~~

This formulation is a proposed design, not a validated solution. Do not use the source's Failure_Probability as a calibrated probability without evidence. Where benefit evidence is insufficient, provide a transparent scenario comparison and identify the missing inputs.

### 7.6 What the current data can support

The original data support educational calculation, schema validation, dashboard prototypes, demonstration of aggregation choices, and cautious exploration of synthetic relationships. They do not establish field-ready failure prediction, remaining useful life, verified savings, approved maintenance thresholds or an executable monthly plan.
