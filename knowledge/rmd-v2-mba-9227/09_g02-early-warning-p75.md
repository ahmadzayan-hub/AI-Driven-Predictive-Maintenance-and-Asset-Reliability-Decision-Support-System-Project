## 09. Early-warning rule and P75 reference
<!-- kb: domain=mba.9227.g02.p75; limits=academic_case|not_rmd_operational_rule -->


### 09.1 Canonical rule

The presentation defines risk at carrier handover using information available at that point:

~~~text
late_handover = seller handed the order over after the shipping deadline
short_buffer = calendar days remaining to the promised date < state P75 transit days
at_risk = late_handover OR short_buffer
~~~

This is a semantic restatement of the presentation, not the original executable code. The repository's exact field names, parsing, time-zone handling and validation need inspection before reimplementation. [S05, slides 15, 23, 24]

| Case | Documented expected result |
|---|---|
| RJ, late handover, 14 days remaining, P75 14 | AT_RISK because handover was late |
| RJ, on-time handover, 13 days remaining, P75 14 | AT_RISK because the buffer is short |
| CE, on-time handover, 21 days remaining, P75 21 | NOT_AT_RISK; equality is not a short-buffer breach |
| Missing handover timestamp | INCOMPLETE, human review, no AI step or email |

P75 is a historical transit percentile from carrier handover to customer delivery. It is not a legal promise, contractual SLA, model probability, rail overdue threshold or guarantee of future delivery.

### 09.2 All 27 state benchmarks reported in the deck

Source: S05, slide 29. Population: delivered orders with carrier handover; carrier-to-customer calendar-day duration. Values are historical, in-sample and must be recalibrated before a real operational pilot.

| State | Reported delivered count | Median days | P75 days |
|---|---:|---:|---:|
| AC | 80 | 15.0 | 21.0 |
| AL | 397 | 18.0 | 28.0 |
| AM | 145 | 23.0 | 30.0 |
| AP | 67 | 21.0 | 26.5 |
| BA | 3,256 | 14.0 | 20.0 |
| CE | 1,279 | 15.0 | 21.0 |
| DF | 2,080 | 8.0 | 12.0 |
| ES | 1,995 | 10.0 | 14.0 |
| GO | 1,957 | 11.0 | 15.0 |
| MA | 717 | 16.0 | 21.0 |
| MG | 11,354 | 7.0 | 11.0 |
| MS | 701 | 11.0 | 15.0 |
| MT | 886 | 13.0 | 18.0 |
| PA | 946 | 17.0 | 25.0 |
| PB | 517 | 14.0 | 21.0 |
| PE | 1,593 | 13.0 | 19.0 |
| PI | 476 | 13.5 | 20.0 |
| PR | 4,923 | 7.0 | 11.0 |
| RJ | 12,350 | 8.0 | 14.0 |
| RN | 474 | 13.0 | 19.0 |
| RO | 243 | 15.0 | 20.0 |
| RR | 41 | 23.0 | 27.0 |
| RS | 5,344 | 10.0 | 15.0 |
| SC | 3,546 | 9.0 | 15.0 |
| SE | 335 | 14.0 | 21.0 |
| SP | 40,493 | 4.0 | 7.0 |
| TO | 274 | 13.0 | 17.0 |

The listed state counts sum to **96,469**. This is one below the general lateness denominator of 96,470. The transit table additionally requires carrier handover, so the two populations must not be silently equated. The exact record-level reason for the difference was not verified.

The user identified **Outputs/02/state-p75-transit-days.csv** as the authoritative project CSV. That CSV was not obtained in this task. The values above were directly read from the presentation; do not say that the CSV itself was inspected. [S10; S05]

### 09.3 Superseded values
<!-- kb: status=superseded; evidence=SUPERSEDED -->

| State | Superseded provisional value | Correct recorded value |
|---|---:|---:|
| RJ | 8 days | 14 days |
| BA | 12 days | 20 days |
| CE | 10 days | 21 days |

Source for the correction history: S10. Source for the corrected values: S05, slides 15 and 29.

### 09.4 Prediction and leakage lesson

The rule uses information conceptually available at handover, but its thresholds were estimated and evaluated on the historical sample. Therefore “available at decision time” alone does not establish out-of-sample validity.

A defensible future validation should estimate thresholds on earlier data, freeze them, evaluate on later eligible orders, report both missed delays and alert workload, and compare against a simpler baseline. Record calibration window, evaluation window, missing-data handling, seasonality, subgroup counts and any selection bias. These are proposed validation requirements, not completed tests.
