## 4. Original dataset and complete schema
<!-- kb: domain=analytics.9226.dataset; synthetic=true; limits=synthetic_educational_data|not_validated_prediction|not_operational_rmd -->


### 4.1 Dataset identity

| Attribute | Verified value |
| --- | --- |
| Source | Group_9226_Team_3_Enterprise_Dataset.csv |
| Source ID | SRC-28 |
| Records | 5,000 |
| Fields | 60 |
| Published field grouping | 18 qualitative, 30 quantitative, 12 derived executive |
| Unique Record_ID values | 5,000 |
| Nominal Asset_ID values | 180; not validated physical assets |
| Asset classes | Heavy Equipment, Biomedical Equipment, Industrial Pump, Railway Signalling, Power System |
| Industry contexts | Mining, Healthcare, Oil & Gas, Railway, Infrastructure |
| Sites | 25 |
| Date range | 5 January 2024 to 25 December 2026 |
| Distinct calendar months | 36 |
| Distinct dates | 60 |
| Missing cells | 0 under the CSV parser used |
| Exact duplicate rows | 0 |
| Duplicate Record_ID values | 0 |
| Synthetic data seed | 922603, as stated in publication/workbook; not independently regenerated |
| Source SHA-256 | 1eb08b41a755edf4890f4fc2b4f2e10faf39f1f437be5d488b485fc55c6d21bf |

Evidence: SRC-27 §§3-5; SRC-28; SRC-29; CALC-01.

The source describes the grain as an asset observation with maintenance context. A row aggregates counts and hours; it is not a single failure event or a single work order. Observation start/end timestamps and non-overlap rules are absent.

### 4.2 Context and identity fields: 18

| Field | Import type | Meaning and handling |
| --- | --- | --- |
| Record_ID | String, unique key | Stable source-row identifier, T3-00001 through T3-05000. Use for lineage. |
| Record_Date | Date | Observation label, not a verified event start or prediction timestamp. |
| Quarter | Category | Q1-Q4; consistent with parsed dates in this source. Add year for time grouping. |
| Asset_ID | String | Nominal source identifier; fails physical-asset identity consistency. |
| Asset_Class | Category | Five synthetic asset classes. |
| Industry_Context | Category | Five industries; do not inherit the publication's four-industry count. |
| Site | Category | Synthetic Site-01 through Site-25. |
| Region | Category | Central, North, South, Remote. |
| Criticality | Ordered category | Low, Medium, High, Critical. Any numeric encoding is an explicit modelling choice. |
| Manufacturer | Category | OEM Alpha, Beta, Gamma, Delta; synthetic labels. |
| Maintenance_Strategy | Category | Reactive, Preventive, Condition Based, Predictive. Observational label; no causal effectiveness proof. |
| Work_Order_Type | Category | Corrective or Preventive; row still contains aggregate WO counts. |
| Failure_Mode | Category | Mechanical Wear, Software/Control, Hydraulic Leak, No Failure, Electrical Fault, Sensor Failure. Current-outcome leakage risk. |
| Condition_Status | Category | Normal, Watch, Alert. Definition/derivation needs confirmation. |
| Technician_Team | Category | Team A-D; no individual employee data. |
| Shift | Category | Day or Night. |
| Risk_Category | Category | Low, Medium, High. Source-generated category; not an approved RTA risk grade. |
| Work_Order_Status | Category | Closed or Overdue. In this file, Overdue aligns with positive Overdue_WO_Count. |

### 4.3 Quantitative fields: 30

| Field | Import type/unit | Meaning and key limitation |
| --- | --- | --- |
| Asset_Age_Years | Decimal years | Source observation age; longitudinal interpretation fails with current identity. |
| Operating_Hours | Decimal hours | Operating exposure within an unspecified observation window. |
| Planned_Operating_Hours | Decimal hours | Planned exposure; denominator of source availability/utilisation. |
| Downtime_Hours | Decimal hours | Aggregate downtime; not consistently Failure_Count × stored MTTR_Hours. |
| Failure_Count | Non-negative integer | 0-6 per record; count in the current observation, not a future label. |
| Preventive_WO_Count | Non-negative integer | Preventive work-order count. |
| Corrective_WO_Count | Non-negative integer | Corrective work-order count. |
| Completed_WO_Count | Non-negative integer | Completed orders; completed plus overdue equals preventive plus corrective in this file. |
| Overdue_WO_Count | Non-negative integer | Count of overdue orders, distinct from count of rows with any overdue order. |
| MTBF_Hours | Decimal hours | Matches Operating_Hours / max(Failure_Count,1) after rounding; finite no-failure values are a generator convention. |
| MTTR_Hours | Decimal hours | Stored synthetic repair measure; denominator/event meaning not established. |
| Maintenance_Cost_USD | Decimal USD | Total synthetic maintenance cost. |
| Spare_Parts_Cost_USD | Decimal USD | Cost component; do not add it to total maintenance cost without establishing accounting boundaries. |
| Labor_Cost_USD | Decimal USD | Cost component; preserve exact field spelling. |
| Energy_Consumption_kWh | Decimal kWh | Observation energy use. |
| Temperature_C | Decimal degrees Celsius | Synthetic condition reading; thresholds must be asset-specific. |
| Vibration_mm_s | Decimal mm/s | Synthetic vibration reading; no sensor calibration/range authority supplied. |
| Pressure_Bar | Decimal bar | Synthetic pressure reading; semantic relevance varies by asset class. |
| Condition_Score | Decimal, nominal 0-100 | Higher values represent better condition in the project narrative; weighting/source generation not supplied. |
| Availability_Pct | Decimal fraction 0-1 | Source row availability. Format as percent; never multiply twice. |
| Utilization_Pct | Decimal fraction 0-1 | Source row utilisation. |
| Technician_Hours | Decimal hours | Aggregate work effort. Not an action-specific duration estimate. |
| First_Time_Fix_Count | Non-negative integer | Count used with corrective work-order denominator. |
| Repeat_Repair_Count | Non-negative integer | Together with first-time fix, equals corrective count in this source. |
| Safety_Incident_Count | Non-negative integer | Three synthetic incidents across the file; no link to real RTA safety events. |
| SLA_Target_Hours | Decimal hours | Synthetic per-record target of 4, 8, 12 or 24 hours. Not an approved contractual SLA. |
| SLA_Actual_Hours | Decimal hours | Observation service-duration measure. Meaning must be matched to the target before operational use. |
| Spare_Parts_Lead_Days | Decimal days | Synthetic lead time; not an inventory stock position. |
| Inventory_Stockout_Count | Non-negative integer | 0 or 1 per source row, total 84. |
| Production_Loss_USD | Decimal USD | Generated economic consequence. No independently measured realised business loss. |

### 4.4 Derived executive fields: 12

| Field | Scale/unit | Evidence and handling |
| --- | --- | --- |
| Reliability_Index | Score | Composite derivation unavailable. Retain as supplied with that limitation. |
| WO_Backlog_Rate | Fraction 0-1 | Matches overdue / (preventive + corrective) after rounding. Label it as overdue share for precise reporting. |
| Preventive_Maintenance_Ratio | Fraction 0-1 | Matches preventive / (preventive + corrective). |
| First_Time_Fix_Rate | Fraction 0-1 | Matches first-time fix / max(corrective,1); the zero-denominator convention is not suitable for all reporting. |
| Repeat_Repair_Rate | Fraction 0-1 | Matches repeat repairs / max(corrective,1). |
| SLA_Compliance_Score | Fraction 0-1 | Matches min(1, target hours / actual hours) within source rounding. It is a score, not a binary compliance result. |
| Cost_per_Operating_Hour | USD/hour | Maintenance cost divided by operating hours, within rounding. |
| Downtime_Cost_Rate | USD/hour | Closely follows loss divided by downtime for positive downtime. Recompute from saved values; small residuals remain. |
| Condition_Risk_Score | Score | Exact generating formula and approved thresholds unavailable. |
| Failure_Probability | Fraction 0-1 | Synthetic generated score, observed range 0.0424-0.6546. No validated horizon or calibration evidence. |
| Maintenance_Priority_Score | Score | Exact weights and generating formula unavailable. Ranking this column is not a newly trained model. |
| Asset_Health_Index | Nominal 0-100 score | Composite source score; underlying weighting and validation evidence unavailable. |

No composite formula should be reverse-engineered and presented as the official source definition. If a new formula is needed, define it as a new version with explicit weights, assumptions and validation.

### 4.5 Import and workbook rules

The CSV is the simplest canonical input for calculations. Normalise encoding with UTF-8 BOM handling. Strip an initial BOM from field names, parse Record_Date as a date, cast the nine count fields to integers and cast the remaining numeric fields to decimals. Preserve source values before cleaning.

The original workbook has these sheets:

| Sheet | Observed extent | Role |
| --- | --- | --- |
| Dataset | 5,001 rows × 60 columns, including header | Text-valued copy of all source records |
| Project Overview | 20 rows, maximum 6 columns | Project metadata and team context |
| Data Dictionary | 61 rows × 5 columns | Field labels and broad categories; composite formulas are not supplied |
| Verification | 15 rows, maximum 4 columns | Static source checks |
| Executive KPIs | 18 rows, maximum 3 columns | Static KPI snapshot with some imprecise labels |
| Statistical Summary | 43 rows × 5 columns | Summary of 42 numeric fields |

The workbook contains **zero formulas**. After BOM normalisation and explicit numeric conversion, its Dataset values matched the CSV on all 60 columns. A PASS cell or a source approval banner is stored text, not a new validation run. [SRC-29; CALC-01]

Before joining or forecasting, resolve the asset-key defects. Do not deduplicate the 4,820 repeated asset/date keys by dropping rows, because the rows have distinct Record_ID values and different contents.
