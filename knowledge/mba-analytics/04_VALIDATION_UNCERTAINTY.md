# Validation, assumptions and uncertainty — التحقق وعدم اليقين

## What the sources establish

The managerial text separates building candidate models, evaluating them with data set aside for that purpose, and scoring actual data with the selected model. Its three-stage diagram was visually checked against the extraction. [S007](SOURCE_INDEX.md#s007), pp144,160–164; diagram p161, printed p135.

The lectures name MAE, RMSE and MAPE for forecast comparison, and confusion matrices, ROC, precision and recall for classification. They do not provide a complete metric implementation or acceptance threshold in the reviewed slides. [S040](SOURCE_INDEX.md#s040), pp17,19. They warn about overfitting, model drift, incorrect aggregation and hallucinated connections, and call for human review and checking the mathematics. [S042](SOURCE_INDEX.md#s042), pp3,8,11.

The books warn about poor data, overly complex models, spurious associations and treating correlation as causation. Sampling and the business question matter; outliers require investigation. [S003](SOURCE_INDEX.md#s003), pp29–32,38–40,45–47; [S005](SOURCE_INDEX.md#s005), pp137,157–158,162; [S006](SOURCE_INDEX.md#s006), pp14–15.

## Assumptions: source scope and proposed checks

| Method | Source-supported limitation | Proposed check before Miyaar use |
|---|---|---|
| Correlation | Association is not causation; zero correlation does not prove independence | Inspect relationship shape, paired observations, outliers and sampling. Do not infer significance from magnitude alone |
| Regression | Relationships and model quality depend on data and assumptions | Establish target type, functional form, residual behavior, dependence and the intended inferential versus predictive use |
| Forecasting | Future behavior need not repeat historical patterns | Confirm time order, frequency, missing periods, seasonality and horizon; evaluate on later periods |
| Clustering | Groups are discovered from available features | Review scaling and distance choices, stability and practical interpretation |
| Simulation | Output depends on assumed uncertain inputs | Document distributions, dependence and sensitivity; distinguish simulated scenarios from observed frequencies |
| Linear programming | The model assumes a linear formulation and constraints | Test feasibility and whether integer, nonlinear or safety requirements are being omitted |

Sources: [S003](SOURCE_INDEX.md#s003), pp29–40,45–47,66–74; [S007](SOURCE_INDEX.md#s007), pp147–148; [S040](SOURCE_INDEX.md#s040), pp14,18. Detailed formal assumption tests are not exhaustively taught in the inspected material. Obtain an appropriate methodological specification before using inferential p-values or intervals as project evidence.

## Correlation worked-example check

The Pearson example in [S003](SOURCE_INDEX.md#s003), PDF pp30–32 (printed pp13–15), was checked against the displayed formula and paired values. Recalculation gives approximately **−0.987135**, while the book prints **−0.389**. The table's total-row placement is also inconsistent. This is an arithmetic correction, not a hypothesis test. Full source transcription and the local calculation record are deliberately excluded from this public collection.

Do not carry the book's magnitude-only significance shortcut into Miyaar. Record the actual inferential method, sample size and assumptions instead. See [source issues](09_SOURCE_ISSUES.md).

## Proposed leakage controls — تسرب البيانات

A search of the extracted PDFs found no explicit `leakage`, `cross-validation` or `train-test` text matches. This is a text-search observation, not proof that every equivalent idea is absent. Held-out evaluation is present in S007. The following finer controls are proposed application guidance:

1. Define the prediction cutoff before choosing features. Exclude information created after the outcome or decision.
2. Investigate supplied targets, probabilities, risk scores and recommendations. A target computed from the inputs may demonstrate recovery of a rule rather than prediction of an independent event.
3. Split by time or entity when the use case requires it. Prevent the same asset or near-duplicate observation from creating misleadingly easy evaluation across partitions.
4. Fit imputation, encoding, scaling and feature selection using the training portion only, then apply the learned transformation to evaluation data.
5. Use validation data for model choices; retain a final untouched evaluation where feasible. Record every adjustment made after seeing results.
6. Do not choose features, thresholds or explanations to match the team's deliverables. Compare only after the independent method and results have been recorded.

## Proposed uncertainty report

Separate data-quality uncertainty, sampling uncertainty, model error, changing conditions and uncertain business assumptions. State which can be quantified and which cannot. Present the evaluation population, time span, error metric, baseline and failure modes with every predictive claim. For simulation or scenario outputs, state the assumptions beside the result. An LLM's confident wording is not a statistical confidence interval.

Record missing evidence explicitly. Do not manufacture confidence intervals, causal certainty, accuracy percentages or expected savings when the required calculation and assumptions are unavailable.
