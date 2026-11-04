## 6. Data-quality findings and a defensible repair strategy
<!-- kb: domain=analytics.9226.quality; synthetic=true; limits=synthetic_educational_data|not_validated_prediction|not_operational_rmd -->


### 6.1 Findings that block specific analytical claims

| Finding | Evidence | What it prevents |
| --- | --- | --- |
| All 180 IDs change class/industry/site/manufacturer | Grouped distinct-value checks | Reliable physical-asset history, asset-level remaining-life claims |
| Every ID has only one distinct date | Grouped date check | Within-asset forecasting or meaningful lagged histories |
| 4,820 excess asset/date repetitions | Duplicate-key check | Treating one row as one unique asset-period |
| No observation start/end windows | Schema inspection | Confirming non-overlapping exposure and work-order totals |
| 166 records fall after 5 November 2026 | Date comparison | Presenting the complete file as historical observations available as of handover |
| Five industries, source narrative says four | Distinct values vs publication §1 | Blind adoption of publication metadata |
| All workbook dataset cells stored as text | Workbook cell inspection | Reliable numeric analysis without explicit conversion |
| No generating script or exact composite formulas | Source review | Exact regeneration or validation of synthetic score derivation |
| No future-failure event label or horizon | Schema review | Claiming a validated next-month failure prediction |
| Three rare synthetic safety incidents | Count inspection | Credible safety-event modelling or operational safety conclusions |
| Different sensors across mixed asset classes | Schema and class context | Universal pressure/temperature/vibration thresholds |
| Source verification checks are narrow/static | SRC-29 Verification sheet | Treating the approval banner as comprehensive data readiness |

### 6.2 A concrete identity example

| Record_ID | Record_Date | Asset_ID | Asset_Class | Industry_Context | Site |
| --- | --- | --- | --- | --- | --- |
| T3-00001 | 2024-01-05 | AST-001 | Industrial Pump | Oil & Gas | Site-25 |
| T3-00181 | 2024-01-05 | AST-001 | Power System | Infrastructure | Site-08 |
| T3-00361 | 2024-01-05 | AST-001 | Railway Signalling | Railway | Site-17 |

These are distinct synthetic observations sharing the same nominal asset and date. Changing the name of the key does not supply a real longitudinal history. [SRC-28, identified Record_ID values]

### 6.3 Preserve the original and choose an explicit route

**Route A: cross-sectional educational analysis.** Keep each Record_ID as a distinct synthetic observation. Statistical independence is not established by unique record IDs; assess dependence and generator structure before inferential analysis or model validation. Use descriptive comparisons, transparent score explanations and carefully scoped modelling exercises. Label the data as observation-level scenarios. Do not claim that an asset deteriorates over successive dates.

**Route B: a new longitudinal synthetic version.** Define a stable asset registry, one asset class/manufacturer per asset, explicitly model permitted attribute changes, generate an asset-period panel with unique keys and consistent observation windows, and then generate future outcome labels. Version and document the generator, assumptions, seed and validation. This is new synthetic data, not a correction that can recover unknown real histories.

**Route C: approved operational data.** Import an authorised asset register and event/work-order history, confirm identifiers and timestamps with the owner, reconcile grain and join cardinality, and validate the decision model with actual operational users.

The choice depends on the project objective. No route has been executed by preparing this Markdown.

### 6.4 Transformation log

Every change should record source hash, affected record/field, old value, new value, reason, rule version and reviewer where required. Preserve raw, cleaned and calculated layers. Do not write over the original source to make a test pass.
