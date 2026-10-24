# Method selection — اختيار طريقة التحليل

## Source-backed selection dialogue

Laursen and Thorlund organize method choice around three questions: is the request reporting or analytical interpretation; is the analysis hypothesis driven or data driven; and does it predict a target or explore structure? They also consider available competencies, tools, cost and whether the task will recur. [S007](SOURCE_INDEX.md#s007), pp141–148. The practical AI lecture similarly chooses forecasting methods by stability, horizon and available drivers. [S040](SOURCE_INDEX.md#s040), pp13–14.

## Method map with proposed acceptance checks

The first three columns summarize the sources. The final column is proposed Miyaar validation guidance, not a claim that these checks have run.

| Question / data need | Candidate method in sources | Source | Proposed acceptance check |
|---|---|---|---|
| Summarize recorded performance | Reports, descriptive statistics, visual analysis | S007 pp149–155; S039 pp4,10–15 | Reconcile counts, scopes, units and aggregations |
| Examine a specified association | Correlation or regression | S003 pp29–32,45–47 | Inspect plots, outliers, variable meaning and appropriate assumptions; do not infer causation |
| Estimate a numeric target | Regression; predictive models | S007 pp157–160; S040 p13 | Compare with a simple baseline on suitable held-out observations; inspect errors and stability |
| Predict a labelled category | Classification | S040 pp13,19 | Verify label timing/meaning; evaluate false positives and false negatives at the intended threshold |
| Forecast a time-indexed measure | Time-series methods, exponential smoothing, ARIMA, regression with drivers | S003 pp38–40; S040 pp14,17 | Verify temporal coverage and horizon; compare chronological forecasts with a baseline |
| Discover groups without a target | Clustering / exploratory analysis | S007 pp147–148; S040 p18 | Check feature scale, stability and usefulness; avoid treating clusters as proven natural classes |
| Compare plausible futures | Scenario analysis | S003 pp33–37 | State assumptions, identify what changes across scenarios and test the decision's sensitivity |
| Propagate uncertain inputs | Monte Carlo simulation | S003 pp66–69 | Justify input distributions and dependence; check simulation stability and report conditional results |
| Allocate limited resources under a linear formulation | Linear programming | S003 pp70–74 | Verify units, objective, constraints, bounds and feasibility; do not reuse the book's faulty example result |
| Assess an intervention | Business experiments / A/B testing | S003 pp20–24 | Establish a credible comparison, allocation and outcome measurement before a causal claim |

Full citations resolve through [SOURCE_INDEX.md](SOURCE_INDEX.md). The table names methods present in the sources; it does not supply missing statistical derivations or establish that any method suits Team 3.

## Proposed prediction gate

Predictive work proceeds only if all of these can be answered with evidence:

- What exactly is predicted, for which entity, as of which time, and over what horizon?
- Is the label observed independently, or calculated from the proposed predictors? Is an existing “probability” merely a supplied score?
- Would every predictor be available at prediction time? Are post-event measures, recommendations or outcomes accidentally included?
- Are there enough relevant outcomes and observations to support a credible evaluation? Use evidence, not a universal row-count shortcut.
- What split respects time, repeated assets or other dependence? What simple baseline must the method improve upon?
- Which error metric and operational error costs matter, and who accepts the threshold?

The sources support separate model building and evaluation, but do not give a full temporal/group leakage protocol. The detailed questions above are proposed controls. See [validation](04_VALIDATION_UNCERTAINTY.md).

## Proposed prescriptive gate

A recommendation is prescriptive only to the extent that actions, objectives, constraints and tradeoffs are specified. Require allowed actions, resource limits, safety conditions, costs and time horizon. Check a proposed solution against every constraint. If these inputs are absent, provide transparent scenarios or a provisional priority rule and label it accordingly; do not claim an optimal policy.

For the independent comparison, record rejected methods and the reason for rejection. A documented “prediction unsupported by these data” is a valid analytical finding. Do not tune a method merely to reproduce the team's report.
