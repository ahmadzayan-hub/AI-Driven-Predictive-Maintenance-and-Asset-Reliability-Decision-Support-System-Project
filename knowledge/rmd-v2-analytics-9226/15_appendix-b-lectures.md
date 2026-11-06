## Appendix B. Practical lectures, assessment evidence and Team 3 context
<!-- kb: domain=analytics.9226.course; limits=academic_case|not_rmd_operational_rule -->


All page references use physical PDF pagination. Interpret source content and supplementary RMD recommendations according to the evidence rules in section 1.

### 1. Evidence register and course-identity limitation

| Source ID | Source | Pages | What it establishes |
| --- | --- | ---: | --- |
| SRC-09 | AIB902 Lecture 5 | 17 | Power BI and the Wide World Importers workshop, including an explicitly graded workshop and an explicitly ungraded advanced demonstration. |
| SRC-13 | AIB902 Lecture 6 | 22 | Prompting, the course's agent/agentic distinction, ML task selection and four practical activities, leading into the live dashboard. |
| SRC-12 | AIB902 Lecture 7 | 24 | Four-stage analytics workflow, stage artifacts and approval gates, live HTML dashboard architecture, and graded D3 refresh verification. |
| SRC-11 | AIB902 Lecture 8 | 18 | Implementation barriers, data and AI-output governance, risk, readiness, and implementation workshop deliverables. |
| SRC-17 | AIB902 Lecture 9 | 24 | Comprehensive analytics plan, final presentation and live demonstration, value measurement, and scaling. |
| SRC-19 | Ahmed Zaian Student Analytics Profile, Group 9226 | DOCX | User-stated professional context, learning goals, candidate rail problems, data constraints, and self-assessed skills. |

All five lecture cover pages display **AIB902** and the title **Data Analytics for Decision Making**. SRC-19 instead identifies **Data Analytics for AI Business**, **Group_9226**, academic year 2026, and programme **3_MBAE_S25_MK_AIB_A**. These are observed labels, not sufficient evidence that AIB902 is the formally approved course code for the current enrolment. Retain the user's course identity, preserve the lecture identifiers, and register the naming difference for confirmation. Do not substitute 9226 for the course code. Do not merge this material with course 9227.

### 2. Confirmed requirements and unresolved conflicts

The supplied materials contain more assessment detail than the earlier project summary that assessments/software were unconfirmed. The Course Control Sheet records **source-supported lecture instructions**, while preserving the distinction between those instructions and the final authoritative rubric.

| Item | Evidence | Treatment in handover |
| --- | --- | --- |
| Power BI WWI workshop is graded | SRC-09 pp.6-15 | Record as a stated graded classroom workshop. No weighting or due date is given. |
| Advanced DAX, drill-through, bookmarks/mobile and Service demonstration is not graded | SRC-09 p.16 | Do not describe these advanced demonstrations as mandatory workshop assessment outputs. |
| LDD is described as a capstone | SRC-13 pp.21-22; SRC-12 pp.21-24 | Record as a central course pathway, without assuming it is the only permitted project route. |
| Four stages and human checkpoints | SRC-12 pp.4,7-17 | Record cleaning review, technique choice, scope approval, build and verification. |
| D3 is a graded checkpoint with an end-to-end refresh target under one second | SRC-12 pp.19,21 | Record the target and requirement for measured, visible proof. This is not a proven performance result. |
| Final tool and case flexibility | SRC-11 p.18 | This slide permits Power BI, AI-directed work, or both, for a real or realistic analytics challenge. |
| WWI and LDD specified in final deliverables | SRC-17 p.7 | This slide names WWI, LDD, a written plan, a data story, and a live demo. Its narrower wording conflicts with L8's broader permission. Confirm applicability before replacing the Team 3 rail/asset project with WWI. |
| Final presentation | SRC-17 p.14 | 8-10 minutes total for story and demo; if slides are used, 5-7 maximum. |
| Workshop duration | SRC-17 p.6 | Heading says “Two Days”, but the body lists Days 1, 2 and 3. Treat as a source inconsistency; no calendar deadline is established. |
| Actual grading weights, marking rubric, calendar dates, submission location, full prompt-template files | Not established in the reviewed sources | Remain open. References to templates or example folders are not proof those assets have been supplied. |

The key slides establishing the D3 test, L8 tool flexibility and L9 WWI deliverables were also visually inspected: SRC-12 p.19, SRC-11 p.18 and SRC-17 p.7.

### 3. Lecture 5: Power BI workshop and the WWI star schema

#### 3.1 Knowledge to retain

The lecture introduces Power BI Desktop for building, Service for sharing and Mobile for viewing. It distinguishes factual transactions from descriptive dimensions and makes that distinction concrete using a multi-table sales model. It favours bar charts for comparisons, lines for time trends and tables for detail; colour should communicate category or magnitude, and excessive decorative elements should be removed. The slide warns against 3D charts, multiple pie slices, dual axes and excessive colours. These are teaching design principles rather than universal prohibitions. [SRC-09 pp.2-5]

The dataset roles are:

| File | Role |
| --- | --- |
| FactSale.csv | Sales-transaction fact table |
| DimCity.csv | City dimension |
| DimCustomer.csv | Customer dimension |
| DimDate.csv | Calendar/date dimension |
| DimStockItem.csv | Stock-item dimension |
| DimEmployee.xlsx | Employee dimension |

The workshop imports all six sources, connects each dimension to the fact table through matching keys, and checks one-to-many relationships with the filter direction from dimension to fact. The date column must have a date type, and the class builds a Year/Month hierarchy. The required visual sequence is sales by city, sales over time, and top stock items or customers, followed by a single page with all three views and at least one shared slicer/filter. Students give a two-to-three-minute walkthrough and receive feedback on clarity, confusion and KPI choice. [SRC-09 pp.6-15]

The advanced instructor demonstration covers one year-to-date sales measure, one margin-percentage measure, drill-through, bookmarks, mobile layout and publishing/sharing in a sandbox workspace. The slide explicitly says students watch rather than build, with approximately 20-30 minutes allotted. It does not give the DAX expressions or require those demonstrations in the graded workshop. [SRC-09 p.16]

#### 3.2 Supplementary application to RMD V2

For a railway implementation, first choose the grain: one work order, one fault event, one asset-period observation, or one project-period snapshot. Do not combine these as interchangeable rows. Candidate dimensions include asset, asset class, location, date, maintainer and approved priority; fact tables depend on the question and available evidence. Use dimension-key uniqueness, unmatched-key checks, reconciliation of totals and filtering tests before accepting the model.

A relationship displaying many-to-many can reveal the wrong key in the simple WWI exercise. In an operational system it can also reflect a legitimate bridge requirement, such as several assets associated with one incident. Investigate the business relationship before forcing one-to-many or deleting duplicate records.

The slide's informal dashboard/report distinction should not become a precise Power BI product glossary. The handover should preserve the intended audience-focused lesson while deferring formal product behaviour to the installed tools and current official documentation when implementation begins.

### 4. Lecture 6: prompting, machine learning and agentic analytics

#### 4.1 Prompting as a business specification

The lecture's prompt structure is practical: name the audience and business problem; specify background context, permitted inputs, output format, length and tone; then inspect and refine the answer. It frames iteration as expected work rather than proof that the first prompt failed. The same discipline prepares the student to direct the four-stage dashboard workflow. [SRC-13 pp.2-6]

A reusable RMD prompt specification should include: decision owner, planning period, asset scope, metric definitions, source version, confidentiality constraints, required evidence, intended output and a stopping condition when evidence is missing. A prompt can direct analysis but cannot establish the truth of input data or validate a result by itself. This extension is a proposed application, not extra assessment wording from the slides.

#### 4.2 Course terminology for agents

The course contrasts an **AI agent**, portrayed as a bounded reactive request-response tool, with **agentic AI**, portrayed as a system that plans and executes a sequence from one brief and checks in at defined milestones. The project-manager analogy illustrates coordinated, multistep work. The analytics example is cleaning, modelling, scoping and building a dashboard from one goal. [SRC-13 pp.7-11]

Preserve this comparison for course-aligned explanations. Add the qualification that it is the lecture's teaching convention, not a universal technical definition: an individual agent can itself plan and use several tools, and a workflow can be highly scripted. An RMD tool should describe its actual permissions, planning behaviour, tools and checkpoints rather than claim sophistication because it is named an agent.

#### 4.3 Method selection and activities

| Analytical task | Lecture treatment | Practical requirement for RMD use |
| --- | --- | --- |
| Supervised learning | Regression and classification with labelled examples. [SRC-13 p.13] | Define a prediction target, unit, time horizon and label availability. |
| Unsupervised learning | Clustering and anomaly detection without pre-existing outcome labels. [SRC-13 pp.13,18] | Treat groupings or unusual records as investigation aids until operationally validated. |
| Forecasting | ARIMA/exponential smoothing, regression with drivers, or ML depending on stability, horizon and drivers. [SRC-13 p.14] | Use time-respecting evaluation and compare with a simple baseline. |
| Ensemble methods | Combining models is introduced as an accuracy strategy. [SRC-13 p.13] | Improvement is empirical, not guaranteed; assess the combined system against the same baseline and holdout. |
| ML platform exploration | Compare AutoML capability, accessibility and tradeoffs in a 20-minute activity. [SRC-13 p.16] | Select from approved tools only after problem/data requirements are established. |
| Forecasting exercise | Compare ARIMA, regression and one ML algorithm using MAE, RMSE and MAPE; justify the selection. [SRC-13 p.17] | The lowest apparent error is insufficient if leakage, unstable data or unusable lead time explains it. |
| Segmentation exercise | Apply k-means or similar, describe group characteristics, size, behaviour and value, then propose actions. [SRC-13 p.18] | Preprocess scales and mixed data carefully; clusters are not automatically causal or priority classes. |
| Predictive case exercise | Churn prediction with confusion matrix, ROC, precision/recall, drivers and retention actions. [SRC-13 p.19] | Translate to failure investigation only after defining equivalent outcomes and false-alarm/missed-event consequences. |

The lecture's automation ladder progresses from repetitive-task automation to process automation, decision automation and agentic analytics. Treat that ladder as a capability discussion. In RMD it does not confer authority to automate safety acceptance or operational control. [SRC-13 p.15; SRC-19, Constraints, Risks, and Assumptions]

#### 4.4 Supplementary metric definitions

These formulas explain metrics named by the lectures; they are not transcribed formulas from these slides. For actual values `y_i`, predictions `yhat_i`, and `n` observations:

```text
MAE  = sum(abs(y_i - yhat_i)) / n
RMSE = sqrt(sum((y_i - yhat_i)^2) / n)
MAPE = 100 * mean(abs((y_i - yhat_i) / y_i))
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
```

MAE and RMSE retain the target's unit. RMSE penalises large errors more strongly. MAPE is undefined where the actual value is zero and can distort comparisons near zero; do not silently remove those observations. Precision measures how often flagged records are true positives; recall measures the share of actual positives found. A decision threshold changes that tradeoff. A confusion matrix must state the positive class and test-set counts, and a ROC curve alone does not establish useful maintenance prioritisation.

For RMD, validation should also include usable warning lead time, event-level detection, false alerts per asset-period, workload at the review threshold and calibration if probabilities drive expected-cost calculations. These are proposed operational checks, not reported results.

### 5. Lecture 7: the four-stage live dashboard workflow

#### 5.1 Course pipeline and artifacts

| Stage | Required analytical work | Artifact and gate | Source |
| --- | --- | --- | --- |
| 1. Cleaning | Report rows/columns, meanings, missingness, type errors, duplicates and implausible values with specific examples; propose reasoned treatments. | Cleaning worksheet, accepted/rejected/adjusted treatments and before/after record. Review at least one proposal critically. Apply only approved changes. | SRC-12 pp.7-9 |
| 2. Modelling and technique choice | State the question, dimensions, measures and grain; compare two or three fitting techniques and the decision each supports. | Model worksheet, options and selected technique with one-sentence justification. Wait for the choice. | SRC-12 pp.10-12 |
| 3. Scope | Establish a specific audience role, three to five primary KPIs, refresh need and one decision/action. | Scoping conversation and one-page approved scope brief, including chart fit and refresh justification. | SRC-12 pp.13-15 |
| 4. Build and verify | Generate a local watcher and an HTML/JS dashboard, run them and verify data-source-to-display change. | Working files, run instructions, D3 timing record and reflection. | SRC-12 pp.16-20 |

The source frames this as one continuous Claude Code or Claude Desktop project using the same dataset, not disconnected prompts. It references four reusable prompt templates and an example folder at `05_Deliverables_Final/.../Hands_On/Example_Live_Decision_Dashboard/`; the ellipsis is part of the source reference and is not a usable exact path. The actual template documents and runnable example have not been established from these PDFs alone. [SRC-12 pp.7,18]

#### 5.2 Reference runtime and engineering caveats

The described lab runtime has a source Excel/database file, a Python standard-library watcher polling approximately every 0.3 seconds, a generated `live_data.json` containing recomputed aggregates, and a single framework-free HTML page fetching JSON approximately every one second. It uses plain CSS/SVG, no external CDN or charting library, and no build step. The UI shows three to five KPIs, charts and live status. [SRC-12 pp.5,16-17]

Do not convert this description into a false performance guarantee. With independent source and display polling, detection delay can approach 0.3 seconds plus one second before computation, file access and rendering overhead. Meeting a strict sub-second measured target requires an appropriate implementation and a test; simply copying the illustrated intervals does not prove it. This is a timing deduction from the source's own parameters.

For a proposed implementation:

1. Choose a simple supported source format. CSV or SQLite is a straightforward standard-library path; native Excel handling must be explicitly designed and validated rather than assumed.
2. Preserve the raw file; process a controlled working copy and record its hash/version.
3. Write JSON atomically so the dashboard cannot read a partially written result.
4. Catch transient save locks and incomplete source writes, retain the last valid result, and report data age and failure status instead of silently stopping.
5. Serve the local dashboard and JSON consistently; specify actual launch commands after generating the files.
6. Distinguish source-change detection, calculation completion and on-screen rendering when measuring latency.
7. Avoid labelling old data “live” when the last source read failed.

These are supplementary design recommendations, not evidence that code or tests have been run. A polling dashboard can refresh deterministic calculations without calling an LLM on every edit. The agent directs the build; that fact alone does not make every runtime calculation an AI inference or imply that operational data must be sent to an external API.

#### 5.3 D3 and reflection

The actual D3 sequence is: run the watcher and dashboard; open the source; edit/replace one row; save; time the visible change; record the result; demonstrate it in class. The lecture explicitly warns that Excel save locks can crash an inadequate watcher, and says a correct implementation should continue polling. The course defines “live” here as under one second. [SRC-12 pp.19,21]

The final reflection asks which prompts/stages worked, what the student would direct differently and what production scaling would require. Source privacy, governance, larger files and executive communication carry into Lecture 8. [SRC-12 pp.20,22-24]

### 6. Lecture 8: implementation, governance and risk

#### 6.1 Business adoption and operating controls

The lecture identifies data quality/availability, skill shortages, organisational resistance, budget limits and legacy integration as recurring barriers. Its proposed response is a visible early use case, iterative delivery, stakeholder involvement, ongoing training and change management. Sustainable operation includes dataset ownership, authorised metric changes, data-quality checks, approval before publication and monitoring of latency, errors, costs and adoption. [SRC-11 pp.2,4-7]

The AI-specific risks include incorrect or over-trusted outputs, exposure of confidential data, changes in model behaviour and missing audit trails. The practical controls are prompt/model/output records, verification of calculations, data classification, versioning/rollback and a named human accountable for the published result. [SRC-11 pp.3,11]

Do not conflate separate failure modes. Forecast overfitting, an LLM inventing a fact, drift in input data and a provider changing a model version are different mechanisms and need different controls. The fixed code of an exported dashboard does not automatically change when an unrelated model provider releases a new version. Record actual dependencies and which stages run inference.

#### 6.2 Case activities and outputs

The WWI workshop uses three illustrative governance gaps: fragile legacy data handoff, insufficient ability to review AI-derived results, and unclear permitted data transfer to an external AI service. Students choose a barrier, diagnose its root cause, compare two or three mitigations with timelines/costs, rank them and name the funding decision-maker. Its narrative numbers, such as a 40% stock overpurchase or example staffing costs, are case assumptions, not validated evidence about a real company or RTA. [SRC-11 pp.8-9]

The governance policy answers five operational questions: who owns the domain; how often it refreshes and how outages are handled; who may access it; what transformations are permitted; and who approves a new dashboard. Students add an AI-specific governance rule. [SRC-11 pp.10-11]

The risk exercise produces a register with risk, probability, impact and mitigation, then a priority list and contingency decisions. A separate readiness assessment scores executive alignment, data infrastructure, skills, change appetite and use-case clarity on a 1-5 scale; a dimension below three triggers a proposed readiness sprint. The synthesis is an implementation checklist with readiness, quick win, governance, risk, success measures and a five-minute group presentation. [SRC-11 pp.12-17]

#### 6.3 Source issues to preserve

Pages 12 and 14-16 switch the case label from WWI to **TechCorp**, which appears to be inconsistent template language. Flag it; do not invent a second confirmed company dataset or silently treat all details as a coherent empirical case.

The probability/impact slide suggests comparatively limited investment for low-probability/high-impact risks. This is a classroom matrix, not a railway safety acceptance rule. RMD must use its approved hazard and risk process, escalation authority and engineering evidence; a rare catastrophic risk cannot be accepted because a generic quadrant labels it low probability. [SRC-11 p.13; SRC-19, Constraints, Risks, and Assumptions]

### 7. Lecture 9: final project, business value and implementation

#### 7.1 Required story and evidence

The lecture links analytics to operating efficiency, revenue/cost effects and measured business benefit. Its enterprise scaling themes are governed infrastructure, capability development, vendor/build decisions and oversight. It presents a hybrid enterprise direction: conventional BI for governed reporting and AI-directed work for exploration and decision support. This is the source's strategic framing, not proof that one product inherently cannot refresh quickly or that all AI-directed output is governed. [SRC-17 pp.2-5]

The written plan on p.7 covers analytics strategy, function-level readiness, a competency-centre operating model, risks/governance, success measures and a 90-day action plan. Other deliverables are the dashboard, a presentation data story and a live demonstration. Roles are analytics lead, data storyteller and implementation/operations, with overlap encouraged. [SRC-17 pp.7-8]

The presentation moves from business situation through insight to recommendation, with evidence and caveats. The final checklist calls for an active source connection, an observed refresh test, an 8-10-minute presentation, optional slides limited to five to seven, and the ability of each member to explain part of the process. The example timing is two to three minutes of business context and one to two minutes of recommendation, leaving the remainder for demonstration and explanation. Treat the source's example 0.8-second refresh and regional margin percentages as demonstration narration, not measured Team 3 results. [SRC-17 pp.14-18]

For the synthetic asset project, the equivalent executive question is which assets to prioritise for the next maintenance/renewal planning period and why. The story must link asset evidence to the action, capacity/resource implications, uncertainty and an outcome measure. A good dashboard is not itself evidence of avoided failures or realised savings.

#### 7.2 Source-supported adaptation checklist

1. Retain a written plan with strategy, readiness, ownership, governance, metrics and a 90-day implementation sequence.
2. Confirm whether the final assessed case must be WWI or may remain the Team 3 synthetic asset project, because L8 and L9 differ.
3. Choose the permitted delivery route and document why it supports the decision.
4. Demonstrate the actual source-to-display update when using the LDD pathway; record the test environment and measured result.
5. Give a short evidence-based data story with a specific accountable recommendation.
6. Prepare answers about wrong data, edge cases, seasonality, model choice, resource limits and uncertain benefit.
7. Record unresolved requirements and instructor feedback rather than inventing course policy.

### 8. User profile relevant to this knowledge transfer

The profile describes Ahmed Zaian as an ATC Chief Engineer and Dubai Tram project manager in the RTA Rail Agency, with railway experience since 2005. His stated work covers technical governance, lifecycle management, maintenance performance, risk, supplier/contractor coordination, acceptance recommendations and management reporting. The scenario is safety-critical public transport with continuity requirements. [SRC-19, Professional Background; Professional Role and Decision Authority; Organisational Context]

Three business directions are named: integrated contractor/project performance governance; risk- and lifecycle-informed renewal priorities; and prediction of signalling/ATC failures to improve maintenance planning. His preferred decision scenario prioritises critical assets using failure likelihood, service criticality, obsolescence, maintenance burden, lifecycle cost and implementation risk. [SRC-19, Managerial and Business Problems Requiring Analytics; Analytics Scenario Input]

Candidate data types include asset registers, fault/event/alarm history, work orders, inspection/test evidence, maintenance/reliability measures, costs, schedules, contractor KPIs, spares/obsolescence records and risk registers. These are possible inputs, not confirmation that all datasets are present, complete, approved or integrated. [SRC-19, Data Environment and Analytics Exposure; Potential Data Availability]

The profile states substantial fragmentation, inconsistent identifiers and granularity, missing history, rare/imbalanced failures, legacy integration difficulties, access/privacy requirements and a need for explainable results. It explicitly retains engineering validation and human accountability and permits synthetic data where official data cannot be used. [SRC-19, Challenges in Using Data or Analytics; Constraints, Risks, and Assumptions]

Learning goals include practical data cleaning/modelling, Power BI, all four analytics types, forecasting, anomalies, model evaluation, storytelling, responsible AI and change management. The self-assessment is intermediate managerial/applied analytics, basic working Power BI familiarity and intermediate conceptual/applied AI exposure, with deeper reproducible modelling still a development objective. These are self-reported learning needs, not independently tested scores. [SRC-19, Strategic Aspirations and Learning Objectives; Self-Assessment of Analytics Readiness]

Personal registration identifiers and unrelated private profile details are intentionally absent from this reusable RMD knowledge summary. The profile is context for tailoring help, not an operational dataset or approval to export real RTA records.

### 9. Proposed mapping to the new RMD V2 AI capability

This mapping is a design proposal. It does not describe verified current RMD V2 implementation.

| Knowledge capability | Course basis | Proposed output and check |
| --- | --- | --- |
| Define the maintenance decision | L6 prompting; L7 model/scope stages; SAP scenario | Decision brief with owner, horizon, scope, constraints and success measure. |
| Assess imported data | L7 cleaning | Versioned quality report with specific anomalies, treatment rationale and approval history. |
| Define asset measures and relationships | L5 schema; L7 modelling | Data dictionary, grain/keys and independently reconciled KPI samples. |
| Choose a defensible method | L6 methods; L7 technique selection | Baseline plus candidate comparison, uncertainty, holdout method and decision relevance. |
| Scope the executive view | L5 visuals; L7 scope | Three to five primary KPIs and a clearly named managerial action. |
| Explain a result with evidence | L8 human review; L9 data story | Source-linked answer separating calculated facts, model output, assumptions and recommendations. |
| Control publication and changes | L8 governance | Recorded reviewer, source/output versions, calculation checks and approved release status. |
| Track use and value | L8 improvement; L9 business value | Time saved, adoption, decision cycle, false-alert burden and observed outcomes against a baseline. |

Teach the assistant to answer “not established in the supplied evidence” when a source, threshold, dependency, current deployment status, approved SLA or realised saving is missing. Importing this Markdown as knowledge does not train a predictive model, recreate the source datasets, or verify current repository behaviour. Those require separate data ingestion, engineering work and validation.

### 10. Retrieved readiness report: Team 3 direction and authority status

Additional source: **SRC-26, Group_9226_Student_Analytics_Readiness.pdf**, 25 PDF pages. Its cover identifies the Student Analytics Profile Consolidated Analysis, Data Analytics for AI Business, Group 9226, academic year 2026 and coverage of 25 profiles. The report is course-planning and readiness analysis. Its own language repeatedly describes team formation, roles and project directions as **recommended**, **proposed** or **suggested**. A branded cover and a planning recommendation do not independently establish instructor approval of a final project, rubric or submission date. [SRC-26 pp.1,3-6,18-23]

#### 10.1 Project theme and contributions

Team 3's proposed title is **AI-Driven Predictive Maintenance and Asset Reliability Decision-Support System**. Its theme is reliability, maintenance and risk. Suggested methods are failure prediction, risk scoring, asset prioritisation, MTBF/MTTR and maintenance optimisation. [SRC-26 p.21]

The Team 3 contribution map is:

| Member name used in the report | Suggested contribution |
| --- | --- |
| Ahmed Rashed | Fleet maintenance, downtime, work orders and technician capacity |
| Ahmed Zaian | Asset criticality, reliability, obsolescence and lifecycle cost |
| Khaled Amer | Risk scoring, probability modelling and financial risk |
| Malak Philippe | IT change requests, resource allocation and project delivery |
| Ali Elraey | Medical-equipment maintenance, MTBF/MTTR and procurement |

These are suggested contributions in the report, not evidence of task completion or currently approved assignments. The table deliberately excludes student registration identifiers and individual readiness ratings. [SRC-26 p.22]

The report also proposes five generic team responsibilities: Business Problem Lead, Data Lead, Analytics Lead, BI/Visualization Lead, and AI & Decision-Support Lead. It does not, on the reviewed page, assign each role formally to a particular Team 3 member. [SRC-26 p.19]

#### 10.2 Common project pathway

The recommended common architecture starts with challenge, measurable problem and decision questions; proceeds through data requirements, cleaning and KPIs; performs descriptive, diagnostic, predictive and prescriptive analysis; then produces Power BI, a meaningful AI/ML component and managerial recommendations. The report allows a synthetic dataset when confidentiality prevents use of organisational records, provided the synthetic structure reproduces the business logic. AI should carry an identifiable analytical function rather than merely write the report. [SRC-26 pp.4-6,22-23,24-25]

That pathway supports an asset-maintenance project and offers a rationale for its intended components. It does not prove that all these components already exist or that the available synthetic data are suitable for every proposed method. In particular, a document calling data suitable for prediction cannot replace inspection of target timing, asset identifiers, label generation, leakage and independent validation.

#### 10.3 Implications for the handover

Maintain a three-way distinction:

1. **Readiness report recommendation:** Team 3 asset-maintenance theme and the proposed common architecture. [SRC-26 pp.21-23]
2. **Lecture pathways:** L8 permits Power BI, an AI-directed approach, or both; L9 explicitly describes WWI and an LDD. [SRC-11 p.18; SRC-17 p.7]
3. **Project implementation evidence:** publication, actual CSV/workbook contents, code and test outputs must be assessed independently. A recommended project direction, a publication narrative and measured implementation evidence have different authority.

The new RMD AI capability should retain those distinctions when answering questions about course requirements or project readiness. Instructor confirmation is still needed to settle the conflicting final-project case/tool wording and exact assessment rules. This uncertainty does not block preparation of the requested Markdown knowledge pack.
