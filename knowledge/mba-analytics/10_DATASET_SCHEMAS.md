# Course dataset schema cards — مخططات البيانات

Schema-level references only. No records, personal values, ranges, distributions or project-result tables are published. All six schemas need a confirmed dictionary, observation grain, units and source/generation history before analysis. They are not substitutes for the independently reconciled project inputs.

## S076 — Sales

Source: [S076](SOURCE_INDEX.md#s076). Schema has 11 columns. The examples below are header-level observations, not validated semantic definitions.

| Header example | Observed representation | Unit evidence |
|---|---|---|
| SalesID | numeric-parseable | Unknown; confirm in data dictionary |
| Date | ISO date | Unknown; confirm in data dictionary |
| Region | string/date-or-category | Unknown; confirm in data dictionary |
| ProductCategory | string/date-or-category | Unknown; confirm in data dictionary |
| Quantity | numeric-parseable | Unknown; confirm in data dictionary |
| UnitPrice | numeric-parseable | Unknown; confirm in data dictionary |
| TotalSales | numeric-parseable | Unknown; confirm in data dictionary |

Intended use: descriptive schema/quality exploration first. Numerical IDs are identifiers, missing-like tokens may be valid categories, and unspecified units remain unknown. Personal or demographic fields require review even when not listed here. Existing scores, probabilities, targets and recommended actions need lineage and leakage checks before predictive use. No automatic training is implied.

## S078 — Telecom and digital transformation

Source: [S078](SOURCE_INDEX.md#s078). Schema has 59 columns. The examples below are header-level observations, not validated semantic definitions.

| Header example | Observed representation | Unit evidence |
|---|---|---|
| Record_ID | string/date-or-category | Unknown; confirm in data dictionary |
| Observation_Date | ISO date | Unknown; confirm in data dictionary |
| Region | string/date-or-category | Unknown; confirm in data dictionary |
| Country_Zone | string/date-or-category | Unknown; confirm in data dictionary |
| Monthly_Revenue_USD | numeric-parseable | USD (header) |
| Monthly_Cost_USD | numeric-parseable | USD (header) |
| Profit_Contribution_USD | numeric-parseable | USD (header) |
| Network_Downtime_Hours | numeric-parseable | hours (header) |
| Customer_Satisfaction_Score | numeric-parseable | Unknown; confirm in data dictionary |
| Net_Promoter_Score | numeric-parseable | Unknown; confirm in data dictionary |
| Compliance_Audit_Score | numeric-parseable | Unknown; confirm in data dictionary |
| Digital_Maturity_Score | numeric-parseable | Unknown; confirm in data dictionary |

Intended use: descriptive schema/quality exploration first. Numerical IDs are identifiers, missing-like tokens may be valid categories, and unspecified units remain unknown. Personal or demographic fields require review even when not listed here. Existing scores, probabilities, targets and recommended actions need lineage and leakage checks before predictive use. No automatic training is implied.

## S079 — Project/contractor portfolio

Source: [S079](SOURCE_INDEX.md#s079). Schema has 60 columns. The examples below are header-level observations, not validated semantic definitions.

| Header example | Observed representation | Unit evidence |
|---|---|---|
| Project_ID | string/date-or-category | Unknown; confirm in data dictionary |
| Portfolio_Category | string/date-or-category | Unknown; confirm in data dictionary |
| Project_Type | string/date-or-category | Unknown; confirm in data dictionary |
| Project_Phase | string/date-or-category | Unknown; confirm in data dictionary |
| Planned_Duration_Days | numeric-parseable | days (header) |
| Actual_Duration_Days | numeric-parseable | days (header) |
| Schedule_Delay_Days | numeric-parseable | days (header) |
| Completion_Percentage | numeric-parseable | percent (header; scale still needs confirmation) |
| Risk_Category | string/date-or-category | Unknown; confirm in data dictionary |
| Vendor_Performance_Score | numeric-parseable | Unknown; confirm in data dictionary |
| Contractor_Performance_Score | numeric-parseable | Unknown; confirm in data dictionary |
| Active_Risk_Count | numeric-parseable | Unknown; confirm in data dictionary |

Intended use: descriptive schema/quality exploration first. Numerical IDs are identifiers, missing-like tokens may be valid categories, and unspecified units remain unknown. Personal or demographic fields require review even when not listed here. Existing scores, probabilities, targets and recommended actions need lineage and leakage checks before predictive use. No automatic training is implied.

## S080 — Governance and risk

Source: [S080](SOURCE_INDEX.md#s080). Schema has 60 columns. The examples below are header-level observations, not validated semantic definitions.

| Header example | Observed representation | Unit evidence |
|---|---|---|
| Record_ID | string/date-or-category | Unknown; confirm in data dictionary |
| Assessment_Date | ISO date | Unknown; confirm in data dictionary |
| Fiscal_Year | numeric-parseable | Unknown; confirm in data dictionary |
| Fiscal_Quarter | string/date-or-category | Unknown; confirm in data dictionary |
| Policy_Review_Age_Days | numeric-parseable | days (header) |
| Corrective_Action_Days_Open | numeric-parseable | days (header) |
| Financial_Exposure_USD | numeric-parseable | USD (header) |
| Operational_Downtime_Hours | numeric-parseable | hours (header) |
| Risk_Category | string/date-or-category | Unknown; confirm in data dictionary |
| Risk_Source | string/date-or-category | Unknown; confirm in data dictionary |
| Risk_Event_Type | string/date-or-category | Unknown; confirm in data dictionary |
| Risk_Status | string/date-or-category | Unknown; confirm in data dictionary |

Intended use: descriptive schema/quality exploration first. Numerical IDs are identifiers, missing-like tokens may be valid categories, and unspecified units remain unknown. Personal or demographic fields require review even when not listed here. Existing scores, probabilities, targets and recommended actions need lineage and leakage checks before predictive use. No automatic training is implied.

## S081 — Infrastructure and security

Source: [S081](SOURCE_INDEX.md#s081). Schema has 64 columns. The examples below are header-level observations, not validated semantic definitions.

| Header example | Observed representation | Unit evidence |
|---|---|---|
| Asset_ID | string/date-or-category | Unknown; confirm in data dictionary |
| Observation_Date | ISO date | Unknown; confirm in data dictionary |
| Asset_Type | string/date-or-category | Unknown; confirm in data dictionary |
| Asset_Category | string/date-or-category | Unknown; confirm in data dictionary |
| Capacity_Utilization_Percent | numeric-parseable | percent (header; scale still needs confirmation) |
| CPU_Utilization_Percent | numeric-parseable | percent (header; scale still needs confirmation) |
| Memory_Utilization_Percent | numeric-parseable | percent (header; scale still needs confirmation) |
| Storage_Utilization_Percent | numeric-parseable | percent (header; scale still needs confirmation) |
| Asset_Risk_Score | numeric-parseable | Unknown; confirm in data dictionary |
| Predictive_Failure_Probability | numeric-parseable | Unknown; confirm in data dictionary |
| Business_Impact_Score | numeric-parseable | Unknown; confirm in data dictionary |
| Compliance_Risk_Index | numeric-parseable | Unknown; confirm in data dictionary |

Intended use: descriptive schema/quality exploration first. Numerical IDs are identifiers, missing-like tokens may be valid categories, and unspecified units remain unknown. Personal or demographic fields require review even when not listed here. Existing scores, probabilities, targets and recommended actions need lineage and leakage checks before predictive use. No automatic training is implied.

## S082 — Industrial operations and ERP

Source: [S082](SOURCE_INDEX.md#s082). Schema has 60 columns. The examples below are header-level observations, not validated semantic definitions.

| Header example | Observed representation | Unit evidence |
|---|---|---|
| Record_ID | string/date-or-category | Unknown; confirm in data dictionary |
| Transaction_Date | ISO date | Unknown; confirm in data dictionary |
| Plant | string/date-or-category | Unknown; confirm in data dictionary |
| Production_Line | string/date-or-category | Unknown; confirm in data dictionary |
| Downtime_Hours | numeric-parseable | hours (header) |
| Available_Production_Hours | numeric-parseable | hours (header) |
| Cycle_Time_Minutes | numeric-parseable | minutes (header) |
| Production_Cost_USD | numeric-parseable | USD (header) |
| Supplier_Performance_Score | numeric-parseable | Unknown; confirm in data dictionary |
| Stockout_Risk_Index | numeric-parseable | Unknown; confirm in data dictionary |
| Supplier_Risk_Index | numeric-parseable | Unknown; confirm in data dictionary |
| Operational_Risk_Score | numeric-parseable | Unknown; confirm in data dictionary |

Intended use: descriptive schema/quality exploration first. Numerical IDs are identifiers, missing-like tokens may be valid categories, and unspecified units remain unknown. Personal or demographic fields require review even when not listed here. Existing scores, probabilities, targets and recommended actions need lineage and leakage checks before predictive use. No automatic training is implied.
