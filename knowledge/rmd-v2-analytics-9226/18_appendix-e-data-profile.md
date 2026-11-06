## Appendix E. Reproducible original-data profile
<!-- kb: domain=analytics.9226.dataset; synthetic=true; evidence=CALCULATED; limits=synthetic_educational_data|not_validated_prediction|not_operational_rmd -->


This profile describes all 5,000 original synthetic observations. It does not repair physical-asset identity or establish actual railway performance. Source: SRC-28 and CALC-01.

### E.1 Coverage

| Year | Records | Share of all records |
| --- | ---: | ---: |
| 2024 | 2,004 | 40.08% |
| 2025 | 2,000 | 40.00% |
| 2026 | 996 | 19.92% |

There are 166 records dated after the handover date of 5 November 2026. The full source is an educational 2024-2026 scenario. Unequal yearly record counts prevent interpretation of unnormalised totals as a performance trend.

| Asset class | Industry | Records |
| --- | --- | ---: |
| Biomedical Equipment | Healthcare | 1,022 |
| Heavy Equipment | Mining | 1,034 |
| Industrial Pump | Oil & Gas | 1,017 |
| Power System | Infrastructure | 958 |
| Railway Signalling | Railway | 969 |

### E.2 All 42 numeric fields

Means and sample standard deviations below describe source rows. They are not interchangeable with the ratio-of-totals KPI definitions in section 5. Fraction-valued percentage fields retain their stored 0-1 scale.

| Field | Mean | Sample SD | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Asset_Age_Years | 8.032253 | 3.285609 | 0.2000 | 19.7984 |
| Operating_Hours | 476.059274 | 125.737609 | 215.9033 | 831.5301 |
| Planned_Operating_Hours | 599.667981 | 145.649086 | 350.0699 | 849.9586 |
| Downtime_Hours | 18.214738 | 15.361949 | 0.0000 | 113.9806 |
| Failure_Count | 1.519400 | 1.090441 | 0.0000 | 6.0000 |
| Preventive_WO_Count | 6.312000 | 2.006255 | 3.0000 | 12.0000 |
| Corrective_WO_Count | 2.085600 | 1.606857 | 0.0000 | 9.0000 |
| Completed_WO_Count | 7.209600 | 2.363807 | 2.0000 | 17.0000 |
| Overdue_WO_Count | 1.188000 | 0.849000 | 0.0000 | 4.0000 |
| MTBF_Hours | 342.541096 | 168.477297 | 53.4034 | 826.5668 |
| MTTR_Hours | 11.708741 | 3.750977 | 1.0000 | 26.1980 |
| Maintenance_Cost_USD | 10,086.089256 | 5,826.751364 | 1,011.0741 | 43,903.2085 |
| Spare_Parts_Cost_USD | 5,377.735475 | 4,978.970193 | 200.0000 | 31,424.6417 |
| Labor_Cost_USD | 2,870.811283 | 1,569.673772 | 293.1851 | 12,414.1490 |
| Energy_Consumption_kWh | 51,089.559604 | 24,729.009938 | 9,028.0837 | 140,095.5933 |
| Temperature_C | 52.500611 | 19.066651 | 2.4981 | 95.7816 |
| Vibration_mm_s | 3.684412 | 0.832030 | 0.6799 | 7.1192 |
| Pressure_Bar | 62.269953 | 69.232629 | 0.2000 | 201.1071 |
| Condition_Score | 76.744478 | 9.576508 | 44.5060 | 100.0000 |
| Availability_Pct | 0.967798 | 0.029189 | 0.7551 | 1.0000 |
| Utilization_Pct | 0.793954 | 0.079569 | 0.5307 | 0.9800 |
| Technician_Hours | 54.486534 | 23.886005 | 9.1153 | 155.3596 |
| First_Time_Fix_Count | 1.596800 | 1.211826 | 0.0000 | 7.0000 |
| Repeat_Repair_Count | 0.488800 | 0.581328 | 0.0000 | 3.0000 |
| Safety_Incident_Count | 0.000600 | 0.024490 | 0.0000 | 1.0000 |
| SLA_Target_Hours | 12.153600 | 7.615196 | 4.0000 | 24.0000 |
| SLA_Actual_Hours | 11.682592 | 4.794498 | 1.0000 | 27.9369 |
| Spare_Parts_Lead_Days | 16.336081 | 5.093960 | 1.0000 | 33.8238 |
| Inventory_Stockout_Count | 0.016800 | 0.128534 | 0.0000 | 1.0000 |
| Production_Loss_USD | 45,776.210401 | 48,024.607624 | 0.0000 | 394,436.1278 |
| Reliability_Index | 76.930179 | 13.863052 | 43.2388 | 99.1520 |
| WO_Backlog_Rate | 0.141785 | 0.093125 | 0.0000 | 0.3333 |
| Preventive_Maintenance_Ratio | 0.767936 | 0.159841 | 0.3077 | 1.0000 |
| First_Time_Fix_Rate | 0.647169 | 0.362611 | 0.0000 | 1.0000 |
| Repeat_Repair_Rate | 0.155831 | 0.186209 | 0.0000 | 0.6667 |
| SLA_Compliance_Score | 0.757830 | 0.279944 | 0.1472 | 1.0000 |
| Cost_per_Operating_Hour | 22.272977 | 14.155361 | 2.4971 | 113.7592 |
| Downtime_Cost_Rate | 2,007.957276 | 1,445.521532 | 0.0000 | 4,499.3384 |
| Condition_Risk_Score | 22.022289 | 6.244257 | 1.8970 | 43.3259 |
| Failure_Probability | 0.295072 | 0.098218 | 0.0424 | 0.6546 |
| Maintenance_Priority_Score | 18.789654 | 6.612869 | 0.8537 | 42.8533 |
| Asset_Health_Index | 78.542326 | 7.201359 | 50.2156 | 97.8445 |

### E.3 Useful categorical distributions

| Field | Category | Records |
| --- | --- | ---: |
| Criticality | Critical | 862 |
| Criticality | High | 1,535 |
| Criticality | Low | 765 |
| Criticality | Medium | 1,838 |
| Maintenance_Strategy | Condition Based | 1,345 |
| Maintenance_Strategy | Predictive | 1,103 |
| Maintenance_Strategy | Preventive | 1,754 |
| Maintenance_Strategy | Reactive | 798 |
| Work_Order_Type | Corrective | 4,015 |
| Work_Order_Type | Preventive | 985 |
| Failure_Mode | Electrical Fault | 780 |
| Failure_Mode | Hydraulic Leak | 832 |
| Failure_Mode | Mechanical Wear | 795 |
| Failure_Mode | No Failure | 985 |
| Failure_Mode | Sensor Failure | 814 |
| Failure_Mode | Software/Control | 794 |
| Condition_Status | Alert | 263 |
| Condition_Status | Normal | 3,320 |
| Condition_Status | Watch | 1,417 |
| Risk_Category | High | 289 |
| Risk_Category | Low | 1,334 |
| Risk_Category | Medium | 3,377 |
| Work_Order_Status | Closed | 1,050 |
| Work_Order_Status | Overdue | 3,950 |
| Region | Central | 1,306 |
| Region | North | 1,233 |
| Region | Remote | 1,252 |
| Region | South | 1,209 |
| Shift | Day | 2,555 |
| Shift | Night | 2,445 |

### E.4 Bilingual terminology

These Arabic labels support consistent explanations. Use the approved RMD product vocabulary when it differs.

| English | Arabic | Clarification |
| --- | --- | --- |
| Business challenge | تحدي الأعمال | Broad obstacle |
| Business problem | مشكلة الأعمال | Measurable performance gap |
| Decision support | دعم القرار | Evidence supporting an accountable choice |
| Descriptive analytics | التحليلات الوصفية | What happened |
| Diagnostic analytics | التحليلات التشخيصية | Investigating why it happened |
| Predictive analytics | التحليلات التنبؤية | Estimating a defined future outcome |
| Prescriptive analytics | التحليلات التوجيهية | Selecting feasible actions against objectives and constraints |
| Availability | الإتاحية | Must use the agreed service/time definition |
| Reliability | الاعتمادية | Must state failure and exposure definitions |
| Maintainability | قابلية الصيانة | Ability to restore under defined conditions |
| Mean time between failures | متوسط الزمن بين الأعطال | MTBF; clarify pooling and exposure |
| Mean time to repair | متوسط زمن الإصلاح | MTTR; distinguish actual repair time from a downtime proxy |
| Work-order backlog | الأعمال المتراكمة | Define whether overdue, open or both |
| First-time fix | الإصلاح من المرة الأولى | State corrective-work denominator |
| Data leakage | تسرب معلومات إلى النموذج | Information unavailable at prediction time enters training/evaluation |
| Model drift | انجراف النموذج | Describe the actual change and monitored measure |
| Synthetic data | بيانات اصطناعية | Generated for education or testing |
| Source evidence | الأدلة المصدرية | Identifiable supporting records or documents |
| Human approval | الاعتماد البشري | Approval by the authorised role |
