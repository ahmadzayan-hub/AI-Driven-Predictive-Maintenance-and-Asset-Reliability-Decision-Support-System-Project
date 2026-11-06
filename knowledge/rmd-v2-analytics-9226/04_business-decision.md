## 3. Business decision and Team 3 project
<!-- kb: domain=analytics.9226.decision; limits=academic_case|not_rmd_operational_rule -->


### 3.1 Primary decision

**Which assets or maintenance interventions should receive priority next month, within the available budget, technician capacity, access windows and spare parts?** [USER-REQ; HIST-01]

The project sequence is:

**Business challenge → measurable business problem → decision → analytical questions → data → analysis → insight → action → KPI and benefit.**

The broad challenge is maintaining reliability and service while resources are limited. A measurable problem must identify a specific gap, baseline, target, period and scope. The original synthetic dataset demonstrates analysis; it does not establish that RMD currently has a particular performance gap.

### 3.2 Decision brief

| Field | Definition for this project |
| --- | --- |
| Decision owner | Accountable maintenance/asset planning owner; named operational authority to be confirmed |
| Planning horizon | Next month, explicitly dated for each run |
| Unit of action | An identifiable intervention on a valid asset, not a generic CSV row |
| Candidate choices | Monitor, inspect, preventive work, corrective work, spares action, overhaul or renewal, as authorised |
| Constraints | Budget, crew skills/hours, access/possession windows, parts, dependencies and mandatory tasks |
| Benefits | Lower expected disruption, better resource allocation, fewer repeat repairs and improved service |
| Required evidence | Stable asset identity, event timing, condition history, work-order state, consequence and intervention feasibility |
| Primary output | Ranked and justified work package with constraints, confidence/limits, owners and review decision |
| Approval | Human engineering and planning authority reviews operational recommendations |
| Current limitation | Original synthetic data lack trustworthy asset histories and action-specific constraints |

### 3.3 Proposed primary KPI set

Choose three to five primary KPIs during scope approval. A practical initial set is availability, downtime/failure burden, overdue work-order rate, maintenance cost and target-met rate. Reliability and repair measures can sit in the detail view. Targets remain unset until a valid baseline and approved target authority exist.

A KPI catalogue must record business meaning, numerator, denominator, scope, period, exclusions, aggregation, unit, source, target authority and action owner. Do not assign red/amber/green bands from convenience.

### 3.4 Team contribution map

| Member | Contribution described in the project sources |
| --- | --- |
| Ahmed Rashed | Fleet maintenance, downtime, work orders and technician capacity |
| Ahmed Zaian | Railway asset criticality, reliability, obsolescence and lifecycle cost |
| Khaled Amer | Risk scoring, probability modelling and financial risk |
| Malak Philippe | IT work management, resource allocation and project delivery |
| Ali Elraey | Biomedical maintenance, MTBF/MTTR and procurement |

These are source-described contributions, not a verified completion record or an appointment to an RTA role. [SRC-26 p.22; SRC-27 team profile]

### 3.5 Project outputs described by the sources

The publication proposes five dashboard themes: fleet health; reliability and failure; work-order performance; maintenance cost and production/service loss; predictive risk and intervention. It also proposes classification, regression, clustering, forecasting, anomaly detection and maintenance recommendations. These are analytical directions, not proof that all models have been implemented and validated. [SRC-27 §§9-12]

The assessed storyline should connect the business situation, data and method to findings, recommendation, resource implications, value, limitations and next steps. The student's defence must explain the data and calculations, not just operate the interface. [SRC-17 pp.7-18]
