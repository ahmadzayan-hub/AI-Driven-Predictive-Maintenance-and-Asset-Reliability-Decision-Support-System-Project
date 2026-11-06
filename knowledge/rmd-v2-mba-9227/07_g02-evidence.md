## 07. G02 evidence and data definitions
<!-- kb: domain=mba.9227.g02; limits=academic_case|not_rmd_operational_rule -->


Status: DOCUMENT_REPORTED_RESULT unless expressly marked ARITHMETIC_CHECKED. Source: S05, slides 4 to 15 and 28 to 29.

### 07.1 Dataset and model

| Field | Presentation-reported value or method |
|---|---|
| Historical order window | 4 September 2016 to 17 October 2018 |
| Complete-month trend window | January 2017 to August 2018 |
| Linked source tables | 9 |
| Power BI model | 11 tables, 10 single-direction relationships, 43 DAX measures |
| Dashboard pages | 4 |
| All orders | 99,441 |
| Distinct customers using customer_unique_id | 96,096 |
| Sellers | 3,095 |
| Delivered-status orders | 96,478 |
| Delivered-status orders with actual delivery timestamp | 96,470 |
| Missing delivery timestamps within delivered status | 8 |
| Reviewed delivered-order population | 95,824 |
| Source limitations | No intervention outcome, reliable cost/margin, customer-service ticket or carrier-scan evidence in the analysis |
| Reported independent checks | Python/pandas KPI reproduction, filtered checks and 25 KPI groups |

No raw Olist CSVs, final PBIX, DAX source or verification scripts were rerun in this handover.

### 07.2 Grain and join controls

| Table | Grain | Reported rows | Key control |
|---|---|---:|---|
| Orders | One order | 99,441 | Count outcome rates at order grain |
| Order items | One item line | 112,650 | Sum item/freight at item grain without multiplying payment rows |
| Payments | One payment record | 103,886 | Aggregate at its own grain |
| Reviews | One review record | 99,224 | Select one review per order, latest answered, then review_id tie-break |
| Customers | One customer_id for an order | 99,441 | Use customer_unique_id for people |

The presentation reports that a naive join produces 117,329 rows and drops 775 orders without items. Preserve the lesson: more joined rows do not imply more orders, customers or valid outcomes. [S05, slide 10]

### 07.3 Lateness definition

The selected business rule is:

> A delivered order is late when its actual customer-delivery calendar date is after its estimated-delivery calendar date.

The presentation explains that estimated timestamps are at midnight, so comparing full timestamps mislabels deliveries later on the promised day.

| Calculation | Result | Interpretation |
|---|---:|---|
| Calendar-date late count | 6,534 | Selected definition |
| Calendar-date denominator | 96,470 | Delivered status plus actual timestamp |
| 6,534 / 96,470 × 100 | 6.7731%, shown as 6.8% | Arithmetic checked |
| Full-timestamp late count | 7,826, shown as 8.1% | Rejected definition for this case |
| Cancelled orders with a delivery date | 6 | Excluded by the delivered-status filter |

Do not transfer this denominator or date rule into an RMD KPI without its applicable source definition.

### 07.4 Historical findings

| Finding | Presentation-reported result | Limitation |
|---|---|---|
| Low scores among reviewed late orders | 62.4% scored 1 or 2 stars | Association, not causal effect |
| Low scores among on-time orders | 9.3% | Different population from all placed orders |
| Late orders' contribution to low scores | 32.5% of all 1 or 2-star reviews on delivered orders | Do not confuse share of poor reviews with overall late rate |
| Mean review score | 2.27 late versus 4.29 on time | Other factors may confound the comparison |
| Repeat-customer rate | 2,997 / 96,096, approximately 3.1% | Historical observation window, not a verified churn rate |
| Pilot-state late rate | 2,067 / 16,885, approximately 12.2% | Arithmetic checked: 12.2416% |
| Pilot-state low-review rate among reviewed late orders | 70.2% | Pilot segment baseline, not network baseline |
| March 2018 late rate | Approximately 19.0%, 1,328 / 7,003 | Purchase-month cohort |
| Value of items on late orders | Approximately R$0.99 million | Exposure, not demonstrated loss |
| Mean delay among late orders | 10.6 calendar days | Conditional mean among late orders |
| Severe late orders | 2,862, defined as more than 7 calendar days late | Definition specific to the case |

The presentation also warns of right censoring in recent cohorts and seasonality. A simple before/after comparison would not isolate the pilot's effect. [S05, slides 12, 28]

### 07.5 Warning-rule backtest

| Measure | Network | Pilot states |
|---|---:|---:|
| Shipments flagged | 12.9% | 14.4% |
| Late rate among flagged shipments | 17.7% | 21.6% |
| Late rate among unflagged shipments | 5.1% | 10.7% |
| Late orders detected | 33.8% | 25.4% |

The deck reports 49.9% lateness when both warning flags fire. These are **in-sample historical backtest results**, not a trained and prospectively validated prediction model. [S05, slide 15]

The detection percentage and the late rate among flagged orders answer different questions. Do not label either one generic model accuracy.
