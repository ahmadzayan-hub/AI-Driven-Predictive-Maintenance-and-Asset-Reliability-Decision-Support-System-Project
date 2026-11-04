## 5. Verified calculations and interpretation
<!-- kb: domain=analytics.9226.kpi; synthetic=true; evidence=CALCULATED; limits=synthetic_educational_data|not_validated_prediction|not_operational_rmd -->


### 5.1 Calculation scope

These are deterministic calculations over **all 5,000 synthetic records**, with no class/date filter. They include dates through December 2026. They are suitable as source-version reconciliation targets, not as live RTA KPIs or validated physical-portfolio performance.

The values below were recalculated from SRC-28 on 5 November 2026. CALC-01 identifies this audit. All monetary units are **USD**, not AED.

### 5.2 Additive controls

| Measure | Recalculated total |
| --- | ---: |
| Operating hours | 2,380,296.3696 |
| Planned operating hours | 2,998,339.9037 |
| Downtime hours | 91,073.6880 |
| Failure count | 7,597 |
| Preventive work orders | 31,560 |
| Corrective work orders | 10,428 |
| Total preventive + corrective work orders | 41,988 |
| Completed work orders | 36,048 |
| Overdue work orders | 5,940 |
| First-time fixes | 7,984 |
| Repeat repairs | 2,444 |
| Maintenance cost, USD | 50,430,446.2805 |
| Spare-parts cost, USD | 26,888,677.3741 |
| Labour cost, USD | 14,354,056.4155 |
| Generated production/service loss, USD | 228,881,052.0055 |
| Synthetic safety incident count | 3 |
| Synthetic stockout count | 84 |

Use cost components as decompositions only after confirming the accounting definition. Avoid double counting them on top of Maintenance_Cost_USD.

### 5.3 Aggregate KPI catalogue

Let Σ denote the sum over the selected valid records. Every numerator and denominator must use the same authorised scope and filters.

| KPI | Formula for this educational source | Result |
| --- | --- | ---: |
| Availability | 100 × (1 − Σ downtime / Σ planned hours) | 96.9625% |
| Utilisation | 100 × Σ operating hours / Σ planned hours | 79.3871% |
| Pooled operating hours per failure | Σ operating hours / Σ failures | 313.3206 h |
| Downtime per failure, MTTR proxy | Σ downtime / Σ failures | 11.9881 h |
| Overdue work-order share | 100 × Σ overdue / Σ(preventive + corrective) | 14.1469% |
| Preventive work-order share | 100 × Σ preventive / Σ(preventive + corrective) | 75.1643% |
| First-time-fix rate | 100 × Σ first-time fixes / Σ corrective | 76.5631% |
| Repeat-repair rate | 100 × Σ repeat repairs / Σ corrective | 23.4369% |
| Service target met rate | 100 × count(actual ≤ target) / count(eligible observations) | 46.1200% |
| Loss-to-maintenance ratio | Σ generated loss / Σ maintenance cost | 4.5385 |
| Loss per downtime hour | Σ generated loss / Σ downtime | USD 2,513.1414/h |
| Maintenance cost per operating hour | Σ maintenance cost / Σ operating hours | USD 21.1866/h |
| Generated loss per record | Σ generated loss / record count | USD 45,776.2104 |

The normal rounded presentation is 97.0%, 79.4%, 313.3 h, 12.0 h, 14.1%, 75.2%, 76.6%, 23.4%, 46.1%, 4.54, USD 2,513/h, USD 21.19/h and USD 45,776/record.

Pooled operating-hours-per-failure is the project's MTBF convention. Its interpretation as a true reliability estimator requires valid exposure windows and failure definitions. The 12.0-hour value should retain the **MTTR proxy** qualification because the source's repair-time field is inconsistent with downtime.

### 5.4 Reconcile earlier publication/workbook figures

| Source presentation | What it actually calculates or counts | Correct handling |
| --- | --- | --- |
| Availability 96.8% | Mean Availability_Pct = 96.779802% | Label mean record availability, or use the 96.9625% ratio-of-totals measure |
| Mean MTBF 342.5 h | Mean of source MTBF_Hours = 342.54109624 | Distinct from pooled 313.3206 h |
| Mean MTTR 11.7 h | Mean MTTR_Hours = 11.7087411 | Distinct from downtime-per-failure proxy of 11.9881 h |
| Backlog 14.2% | Mean WO_Backlog_Rate = 14.178472% | Distinct from aggregate overdue share 14.1469% |
| SLA compliance 75.8% | Mean capped ratio score = 75.782986% | Label score. Actual target-met rate is 46.12%, 2,306/5,000 |
| High-Risk Assets 289 | 289 records with Risk_Category = High | Label high-risk records; they involve 143 nominal IDs, which still lack stable asset identity |
| Overdue Work Orders 3,950 | 3,950 observations with any overdue orders | Actual total overdue-order count is 5,940 |
| Preventive work 75.2% | Ratio of count totals | Matches 75.1643%; mean row ratio is 76.793598% |
| First-time fix 76.6% | Ratio of total first-time fixes to total corrective orders | Matches 76.5631%; mean stored row rate is only 64.716888% because of weighting and zero-case conventions |

Different aggregations are not automatically errors. Ambiguous labels that hide those differences are the problem.

### 5.5 Sanity checks

- Completed + overdue = preventive + corrective for every source row.
- First-time fixes + repeat repairs = corrective orders for every source row.
- Zero-failure rows and zero-corrective rows both number 985.
- Source “No Failure” agrees with zero failure count.
- Source Quarter agrees with the parsed Record_Date.
- Operating_Hours does not exceed Planned_Operating_Hours on its own.
- In 93 rows, operating hours plus downtime exceed planned hours. If all three describe the same non-overlapping time window, those records conflict. The source does not establish an alternative convention, so preserve the issue for resolution.
- For the 4,015 positive-failure records, downtime differs from failure count multiplied by stored MTTR. The largest absolute difference is 15.2714 hours. Do not silently overwrite one measure with the other.

### 5.6 Reproducible audit example

The following example expects the original CSV in the current working directory. It is a verification recipe for the source version, not an application backend implementation.

~~~python
from pathlib import Path
import hashlib
import pandas as pd

source = Path("Group_9226_Team_3_Enterprise_Dataset.csv")
expected_sha = "1eb08b41a755edf4890f4fc2b4f2e10faf39f1f437be5d488b485fc55c6d21bf"
assert hashlib.sha256(source.read_bytes()).hexdigest() == expected_sha

df = pd.read_csv(source, encoding="utf-8-sig")
df["Record_Date"] = pd.to_datetime(df["Record_Date"], errors="raise")
assert df.shape == (5000, 60)
assert df["Record_ID"].is_unique
assert df.isna().sum().sum() == 0

total_wo = df["Preventive_WO_Count"].sum() + df["Corrective_WO_Count"].sum()
availability = 1 - df["Downtime_Hours"].sum() / df["Planned_Operating_Hours"].sum()
overdue_share = df["Overdue_WO_Count"].sum() / total_wo
target_met_rate = (df["SLA_Actual_Hours"] <= df["SLA_Target_Hours"]).mean()

assert abs(availability - 0.9696252956885864) < 1e-10
assert abs(overdue_share - 0.1414689911403258) < 1e-10
assert abs(target_met_rate - 0.4612) < 1e-10
assert df.duplicated(["Asset_ID", "Record_Date"]).sum() == 4820

identity_changes = df.groupby("Asset_ID")["Asset_Class"].nunique().gt(1)
assert identity_changes.sum() == 180
print("Source reconciliation complete; asset identity still needs repair.")
~~~

For production calculations, validate zero/missing denominators explicitly and return an unavailable result with its reason. A zero result must mean a measured zero, not a hidden error.
