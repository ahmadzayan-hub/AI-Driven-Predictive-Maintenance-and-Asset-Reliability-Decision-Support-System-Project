## Appendix A. Core course concepts and business applications
<!-- kb: domain=analytics.9226.theory; limits=academic_case|not_rmd_operational_rule -->


All page references use physical PDF pagination. Interpret source content and supplementary RMD recommendations according to the evidence rules in section 1.

### Evidence conventions

All references below use the source IDs in section 12 and **one-based PDF page numbers**, not inferred lecture numbers. Content labelled **Course concept** paraphrases the supplied teaching material. Content labelled **Implementation recommendation** is an application of the concept to the requested AI tool. Content labelled **Source limitation** explains why a teaching example should not become an operational fact.

The review covers SRC-01 to SRC-08, SRC-10, and SRC-14 to SRC-16. Every page of the extracted text in those twelve documents was reviewed. Three selected graphics were additionally rendered and visually inspected. No external web verification was performed for this contribution.

### 1. Source map and version handling

| Source | Supplied file | Pages | Contribution and best reference locations |
| --- | --- | ---: | --- |
| SRC-01 | `1. Business Analytics for Decisions Making(1).pdf` | 21 | Introductory definitions of business analytics, big data, data science and data analytics, pp. 2-6; collection, cleaning, analysis and visualisation, pp. 9-12; constraints and governance, pp. 17-20. |
| SRC-02 | `5. Practical Applications in Various Business Sectors (1)(1).pdf` | 44 | A compendium of 21 teaching cases with problem, objectives, methodology, implementation and claimed outcomes. Cases are mapped individually in Section 8 below. |
| SRC-03 | `10. Creating Competitive Advantage through Analytics(1).pdf` | 27 | Analytics centre design, pp. 3-15; business optimisation, implementation, measures and iteration, pp. 17-26. Footer credits Dr. Yasser Yakout and Mr. Hossam Daoud, GSB Miami, 2024. |
| SRC-04 | `4. Building a Business Analytics Competency Center(1).pdf` | 29 | BACC definition, p. 4; seven establishment steps, pp. 5-11; readiness and strategic alignment, pp. 12-13; illustrative organisation cases, pp. 14-23; challenges and good practice, pp. 24-26. |
| SRC-05 | `5. Practical Applications in Various Business Sectors(2).pdf` | 35 | Slide outline for marketing, operations, customer service and logistics, pp. 4-11; governance and implementation challenges, pp. 14-19; industry, BI, IoT, sustainability and crisis applications, pp. 20-33. |
| SRC-06 | `8. Decision-Making Support through Analytics_V2_21122024(1).pdf` | 30 | Information generation and quality, pp. 3-11; communication and organisational adoption, pp. 12-15; decision support definition, p. 16; ten named company illustrations, pp. 17-26. |
| SRC-07 | `3. Business Analytics Strategies and Processes(1).pdf` | 45 | Strategy versus tactics, p. 9; analytics types/maturity, pp. 4-8; processes and governance, pp. 13-20; retail and healthcare teaching cases, pp. 23-38; challenges and improvement, pp. 39-44. |
| SRC-08 | `2. The Role of AI and Machine Learning in Business(1).pdf` | 33 | AI/ML definitions and learning paradigms, pp. 3-5; process redesign and business uses, pp. 6-19; implementation, governance, human collaboration and ROI, pp. 20-30. |
| SRC-10 | `1-Introduction-to-Business-Analytics(1).pdf` | 32 | Problem definition and decision process, pp. 7, 10-12; data preparation, modelling and prescription, pp. 13-17; ethical communication and implementation, pp. 18-21; value, lineage and roadmap, pp. 22-30. |
| SRC-14 | `3-Business-Analytics-Strategies-and-Processes(1).pdf` | 32 | Strategy and KPI design, pp. 2-7; data acquisition, integrity and versioning, pp. 8-10; four analytics types, pp. 11-15; workflow integration and adoption, pp. 16-25. |
| SRC-15 | `4-Building-a-Business-Analytics-Competency-Center(1).pdf` | 32 | Maturity and current capability assessment, pp. 5-6; target operating model, roles and governance, pp. 7-12; skill development, pp. 13-18; demand/capacity, agile delivery and service scaling, pp. 19-31. |
| SRC-16 | `2-The-Role-of-AI-and-Machine-Learning-in-Business(1).pdf` | 32 | AI business use cases, pp. 5-12; incremental integration, p. 13; people, risk and governance, pp. 14-19; operational, procurement, finance and sustainability applications, pp. 24-31. |

The corresponding topic files are **different versions**, not duplicates. Binary hashes and extracted-text hashes differ for SRC-01/SRC-10, SRC-04/SRC-15, SRC-07/SRC-14 and SRC-08/SRC-16. SRC-02 is a detailed case compendium; SRC-05 is the corresponding sector lecture outline. Preserve each file's identity. Topic overlap alone does not establish that a file supersedes another.

No official rubric, deadline, marks allocation, confirmed course code, AI use rule, or submission specification was found in these twelve documents. Session objectives and illustrative case objectives are not assessment requirements. This finding is limited to this reviewed subset.

### 2. Foundations: what the AI tool should understand

#### 2.1 Business analytics and its neighbouring disciplines

**Course concept.** Business analytics applies data, statistical analysis and quantitative methods to business decisions. Its value comes from improving a choice or an action, such as allocating maintenance resources, addressing a service failure, or deciding whether to renew an asset. Data analytics describes the examination and interpretation of data; data science combines statistical, computational and domain expertise across data preparation and modelling. The terms overlap, but the business decision gives an analytics project its purpose. [SRC-01, pp. 2, 4-6; SRC-10, pp. 4-7]

The course's big-data introduction uses the three Vs: **volume, variety and velocity**. Variety includes structured, semi-structured and unstructured data. This is a description of data-management demands, not a fixed record-count threshold. A 5,000-row maintenance dataset does not need a big-data platform merely because an AI feature is planned. The latter is an implementation judgement, not a numerical rule in the slides. [SRC-01, p. 3; SRC-05, p. 21]

The course contrasts **business analytics** with **technical analytics**. SRC-01 p. 6 emphasises infrastructure, storage and processing on the technical side; SRC-10 p. 6 also includes algorithmic and modelling implementation. Preserve the teaching distinction as a matter of emphasis. Do not represent these as mutually exclusive, universally standard professional disciplines.

#### 2.2 The decision remains central

**Course concept.** The decision process begins with a defined problem, evaluates alternatives, and selects a course of action while considering strategic alignment, constraints and impact. Performance gaps, relevant KPIs and domain expertise help identify useful analytics problems. [SRC-10, pp. 7, 10-12]

**Implementation recommendation.** For RMD V2, represent each analytical request using:

1. Business challenge and measurable problem.
2. Decision owner, decision date and time horizon.
3. Options being considered.
4. Scope, asset population and resource constraints.
5. Baseline, target and KPI definition.
6. Required evidence and its timestamp.
7. Analysis, uncertainty and limitations.
8. Recommendation, authorised action and subsequent outcome.

This expanded record implements the user's project workflow. A request to “build an AI dashboard” is incomplete until the underlying decision and success measure are stated. A dashboard, model, answer or video is a delivery format; improvement in the decision or service is the intended business outcome.

### 3. Four analytical questions

| Analytics type | Plain meaning | Appropriate output | Proposed railway example | Main interpretation limit |
| --- | --- | --- | --- | --- |
| Descriptive | What happened, or what is happening? | Totals, distributions, trends, comparisons, KPI status. | Downtime by asset class and month. | Accurate reporting does not itself explain a cause. |
| Diagnostic | Why might it have happened? | Drill-down, comparison, relationships, hypotheses and supporting evidence. | Examine whether repeat faults coincide with parts delays, environment or work quality. | Association alone does not establish a root cause. |
| Predictive | What may happen within a specified horizon? | Estimated outcomes, probabilities or forecasts with validation evidence. | Probability of a defined failure within the next month. | Predictive performance depends on the population, horizon, data available at prediction time and validation design. |
| Prescriptive | Which feasible action best serves the objective? | Ranked alternatives, resource allocations or a constrained plan. | Select a monthly maintenance work package subject to budget, staffing, possessions and parts. | “Optimal” means optimal for the stated model, objective and constraints, not a guarantee of the best real-world outcome. |

The four-stage terminology is explicit in SRC-07 p. 7 and SRC-14 pp. 12-15. Some introductory slides list only descriptive, predictive and prescriptive information, including SRC-06 p. 5 and SRC-07 pp. 4, 6. Retain their scope when discussing that slide, and use the full four-type framework for the project. SRC-14 p. 12 loosely associates “why” with descriptive patterns; p. 13 explicitly assigns explanatory analysis to diagnostic analytics. The distinction in the table resolves this overlap for implementation.

**Implementation recommendation.** A risk-score formula or threshold rule is not automatically a trained prediction model. A narrative recommendation is not automatically mathematical optimisation. A model can contribute to a decision without deciding it. Label the method that actually generated each output.

### 4. The analytics workflow

The core teaching workflow covers collection, preparation, analysis, visualisation and delivery. Later slides emphasise implementation, monitoring and refinement. [SRC-01, pp. 9-10; SRC-03, pp. 20-25; SRC-07, pp. 13-21; SRC-14, pp. 8-19, 25]

| Stage | Course teaching | RMD V2 implementation recommendation |
| --- | --- | --- |
| Business understanding | Establish objectives, performance gaps and KPIs. | Capture the decision record before choosing a model or interface. |
| Source selection | Identify relevant internal and external data. | Record source owner, intended use, access scope, version and reporting period. |
| Acquisition | Extract and integrate data across systems. | Retain raw imports; create explicit mappings instead of silently replacing source fields. |
| Preparation | Clean, standardise, transform and combine data. | Profile missingness, duplicates, units, definitions and joins; document each transformation. |
| Exploration | Examine structure, distributions, trends, anomalies and relationships. | Use stratified views so an aggregate does not conceal a weak asset class or location. |
| Analysis/modelling | Select methods appropriate to the business objective. | Start from a useful baseline, declare the target and eligible features, and preserve reproducibility. |
| Validation | The introductory workflow is brief; BACC governance includes model validation. | Test data, calculations, leakage, out-of-sample performance, business usefulness and limitations. |
| Communication | Use charts, dashboards, storytelling and discussion. | Show the answer, calculation/source, uncertainty, relevant alternatives and next action. |
| Delivery/action | Embed insights into business processes. | Link advice to cases, evidence and responsible owners; record a human decision where required. |
| Monitoring | Continuously evaluate, obtain feedback and refine. | Monitor outcomes, input quality, stale data, model deterioration, adoption and exceptions. |

SRC-10 p. 15 presents a predictive-modelling sequence that ends with training. Treat it as an introductory explanation, not a complete validation protocol. SRC-15 p. 8 explicitly places model validation within governance. The user's course instructions also require baselines, leakage controls and suitable validation.

#### 4.1 Data quality and lineage

**Course concept.** Quality requires accurate, complete and consistent data. Integration must reconcile disparate sources. Governance assigns ownership, policies and controls. Lineage traces how data moves and changes. Versioning, archiving and recovery preserve continuity. [SRC-06, pp. 7-8; SRC-10, p. 26; SRC-14, pp. 9-10]

**Implementation recommendation.** Retain a trace from every management result to the source record and calculation version. Investigate outliers before excluding them. An unusual rail failure can be the central case, not an error to remove. Distinguish missing data from zero, “not applicable” and “not yet reported”. Never let a join multiply cost or downtime by duplicating rows.

#### 4.2 Visualisation and communication

**Course concept.** Select a chart that fits the analytical task, reduce clutter, use colour deliberately, add context and allow useful exploration. Findings should lead to actionable recommendations and a two-way discussion with business users. [SRC-06, pp. 12, 14; SRC-10, pp. 14, 19; SRC-14, pp. 16-17]

**Implementation recommendation.** In an executive RMD view, prioritise status, trend, variance, major contributors, exceptions and the required action. Show units and periods beside values. Use consistent denominators across comparisons. Do not imply causation with a ranked driver chart. Distinguish the source's reporting date from the dashboard refresh time.

### 5. Strategy, KPIs and business value

#### 5.1 Strategy versus tactics

**Course concept.** Strategy sets the long-term direction and alignment with organisational objectives. Tactics are the specific short-term actions used to pursue that direction. An analytics strategy coordinates people, processes, data and technology. [SRC-07, pp. 9-12; SRC-14, pp. 2-7]

**Proposed RMD application.** A strategy could improve how maintenance priorities are set and reviewed. Tactics could include reconciling a monthly fault extract, creating a repeat-failure analysis, and piloting one priority list with planners. Installing a chat interface is a tactic; its value depends on the operational problem it helps resolve.

#### 5.2 KPI design

**Course concept.** KPIs must be measurable and tied to business objectives. Use both lagging indicators, which describe outcomes already observed, and leading indicators intended to anticipate later performance. [SRC-14, pp. 6-7]

**Implementation recommendation.** Each KPI needs a name, definition, numerator, denominator, unit, grain, aggregation rule, reporting period, exclusions, source, target authority and action owner. For example, a maintenance-completion percentage is incomplete without defining which work orders were due, how cancelled orders are treated, and when the status was frozen. A leading indicator is not automatically a validated predictor.

#### 5.3 Value realisation

**Course concept.** Analytics value can include efficiency, service quality, better allocation, cost reduction and strategic improvements. The metrics must match the initiative and be reviewed over time. [SRC-03, p. 13; SRC-08, p. 29; SRC-10, p. 22; SRC-15, pp. 20-21]

**Implementation recommendation.** Maintain a benefits register with baseline, comparison method, implementation cost, recurring cost, measured outcome, accountable owner and evidence period. Separate an estimate of potential savings from verified savings. Time released from reporting is capacity, not automatically a cash saving. A maintenance intervention that reduces failures may also increase planned maintenance effort; evaluate the combined service and cost effect.

If calculating a simple ROI, define all inputs. An illustrative convention is `ROI = (incremental attributable benefit − total incremental cost) / total incremental cost × 100`. This formula is an added explanation, not a formula extracted from these slides. Do not add multiple benefit lines that count the same avoided downtime twice.

### 6. Business Analytics Competency Center

#### 6.1 Purpose and establishment sequence

**Course concept.** A BACC coordinates analytical expertise, standards, reusable processes, technology and adoption. Its purpose is to improve organisational decisions and ensure that analytics contributes to business priorities. [SRC-04, p. 4; SRC-15, pp. 3-4]

SRC-04 pp. 5-11 gives a seven-step establishment sequence:

1. Define mission and vision.
2. Assemble a skilled, cross-functional team.
3. Define processes and workflows.
4. Establish data governance and quality assurance.
5. Select suitable technology.
6. Develop skills and training.
7. Establish KPIs for the centre's performance.

SRC-15 extends this into an operating model: assess the current state; define the target state; set governance and organisational placement; define roles; establish leadership sponsorship; build capability; manage demand and capacity; deliver iteratively; and evolve the roadmap. [SRC-15, pp. 6-16, 21-29]

#### 6.2 Roles and responsibilities

The teaching material distinguishes leadership, analytics practitioners and a delivery team. It also emphasises data engineering, business analysis and domain expertise. [SRC-04, p. 6; SRC-15, pp. 11-13]

**Proposed RMD operating model.** Define responsibilities before assigning named personnel:

| Role | Proposed accountability |
| --- | --- |
| Business sponsor | Set priorities, resource boundaries and expected benefits. |
| Decision owner | Accept, reject or amend the recommendation and own the resulting action. |
| Rail domain specialist | Validate asset meaning, engineering plausibility, criticality and operational constraints. |
| Data owner or steward | Confirm definitions, completeness, source authority and access rules. |
| Analytics practitioner | Implement transparent calculations and validated methods. |
| Platform owner | Maintain integration, permissions, availability and support. |
| Independent reviewer | Challenge assumptions, reproducibility and conclusions. |

These are proposed responsibilities for the tool's workflow. They do not establish RTA's official organisation, appoint individuals or change delegated authority.

#### 6.3 Maturity models are planning aids

SRC-07 p. 7 arranges maturity through descriptive, diagnostic, predictive and prescriptive analytics. SRC-15 p. 5 uses the labels **Basic**, **Intermediate**, **Advanced** and **Optimized**. The latter associates basic work with spreadsheets and silos, intermediate capability with reporting and dashboards, advanced capability with predictive models, and optimised capability with analytics embedded in operations.

The image on SRC-07 p. 8 adds raw and cleaned data, standard and ad hoc reports, self-service BI, smart/augmented analytics, predictive ML, prescriptive analytics and alternative paths towards autonomous systems or human-machine interaction. It is a conceptual illustration of capability and productivity, not an empirical measurement or a requirement that all operations become autonomous.

**Implementation recommendation.** Assess capabilities individually rather than assigning RMD an unsupported overall score. Strong forecasting does not compensate for weak data ownership. A reliable descriptive dashboard may be the most valuable solution for a particular decision. The example maturity ratings in SRC-15 p. 6 are teaching examples, not an assessment of RMD or the user.

### 7. AI, machine learning and decision support

#### 7.1 Learning paradigms

**Course concept.** AI is the broader field; ML is one approach within it. The course also covers natural language processing and computer vision. Supervised learning uses labelled input/output examples; unsupervised learning looks for patterns without an established target label; reinforcement learning learns actions through interaction and rewards. [SRC-08, pp. 3-5]

**Implementation recommendation.** Select a method from the analytical question and available evidence:

| Intended question | Suitable method family | Required distinction |
| --- | --- | --- |
| How much downtime or cost is expected? | Regression or time-series forecasting, depending on grain and target. | A prediction for a record differs from a forecast for a monthly aggregate. |
| Is a defined failure likely within the next horizon? | Classification or an appropriate time-to-event approach. | Requires a credible future outcome label and features known at prediction time. |
| Which assets have similar observed profiles? | Clustering. | Groups describe similarity; they are not automatically validated risk categories. |
| What does this maintenance document say? | Retrieval and document extraction, with citations. | A retrieved statement is source evidence, not a newly trained failure model. |
| Which work package fits our capacity? | Constrained optimisation, scenario comparison or a transparent ranking rule. | State the objective, constraints and method actually used. |

The family selection and rail examples above are supplementary implementation recommendations. These introductory slides do not specify a validated model, training dataset, hyperparameters, production architecture or maintenance failure horizon for RMD V2.

#### 7.2 Implementation and human judgement

**Course concept.** AI adoption needs data, integration, appropriate skills, organisational change and governance. The material explicitly recommends assessing compatibility, designing architecture and deploying incrementally. Decision-support systems augment human expertise. [SRC-08, pp. 21-23, 27-30; SRC-16, pp. 12-19]

**Implementation recommendation.** Start with a bounded, reviewable analytical capability. For a new RMD V2 assistant, useful first capabilities include explaining an existing KPI, retrieving evidence for a case, reconciling reported and recalculated results, and drafting an action summary. Verify the repository and available interfaces before specifying code changes. Do not assume that an installed chat model has learned the project merely because this Markdown file is present.

The slides sometimes describe AI as continuously learning. A deployed model does not necessarily retrain itself. Treat retraining, data approval, versioning and release as explicit governed processes. This is an implementation clarification, not a contradiction of the general learning concept. [Relevant course wording: SRC-16, pp. 3, 7, 11]

#### 7.3 Governance themes

The recurring course themes are privacy, security, transparency, explainability, fairness, accountability, monitoring and ongoing human skills. [SRC-01, pp. 17-20; SRC-08, pp. 20, 23, 30; SRC-10, p. 18; SRC-16, pp. 16-19]

**Implementation recommendation.** Preserve user and organisational access permissions when retrieving documents. Link the answer to the evidence used. Report stale or conflicting evidence. Test Arabic and English answers using the same underlying facts. Human review must remain attached to the exact version of a recommendation or report where the business process requires approval.

References to GDPR, CCPA or HIPAA in the slides illustrate governance topics. They do not establish which laws apply to a specific RTA workflow. Any actual legal or regulatory interpretation needs current authoritative verification and the appropriate organisational review.

### 8. Sector case catalogue

SRC-02 supplies the following 21 case narratives. Their methodological patterns are useful for teaching and use-case discovery. Their named organisations, percentages, claimed financial results and causal claims have not been independently verified. The source does not supply reproducible datasets or primary references establishing those outcomes. Therefore, retain case results only as **claims made in the teaching material**, not as external benchmarks, demonstrated project outcomes or RTA targets.

| Case | Pages | Teaching decision or method | Transferable RMD learning, proposed |
| --- | --- | --- | --- |
| 1. Marketing campaign effectiveness, XYZ Retail | 3-4 | Combine channel data, analyse past performance, forecast results, allocate spend and test pilot campaigns. | Connect resource allocation to an explicit decision, baseline and measured outcome. |
| 2. Customer segmentation, ABC Corporation | 5-6 | Clean data, select demographic/behavioural criteria, cluster, tailor interventions and monitor. | Segment asset populations only when the groups support different actions; validate group stability. |
| 3. Supply-chain optimisation, GlobalTech Solutions | 7-8 | Integrate manufacturing, procurement and logistics data; forecast demand/disruption; optimise inventory and routing. | Combine parts demand, supplier lead times and maintenance priorities. |
| 4. Inventory management, HealthEquip | 9-10 | Forecast demand; determine inventory, reorder points and safety stocks; monitor outcomes. | Evaluate spares availability against carrying cost and service consequences. |
| 5. Service response, ServiCo | 11-12 | Aggregate requests; forecast workload; allocate staff across channels and periods; monitor response. | Separate acknowledgement, assessment, customer update and repair measures rather than collapsing them into one response time. |
| 6. Sentiment analysis, FoodieJoy | 13-14 | Use NLP to categorise sentiment, identify themes, trigger review and track changes. | Use complaint themes as supporting evidence; do not treat sentiment as engineering fault severity. |
| 7. Route optimisation, QuickDeliver Logistics | 15-16 | Combine locations, time windows, traffic and weather; forecast conditions; optimise and adapt routes. | Maintenance-team travel planning can use analogous constraints, with engineering access restrictions added. |
| 8. Warehouse management, StoreMax | 17-18 | Analyse stock layout, demand frequency and retrieval time; optimise placement and monitor inventory. | Review spares retrieval delays and depot storage arrangements. |
| 9. Data privacy, PrivacyGuard Solutions | 19-20 | Map and classify information, assess risk, detect anomalies and monitor controls. | Give the assistant only the evidence its current user is authorised to access. |
| 10. AI-supported strategy, TechInnovate Solutions | 21-22 | Integrate internal/external information; train models; compare decisions; pilot adoption. | Frame technical renewal options with assumptions and decision evidence. |
| 11. Big-data capability, DataEdge | 23-24 | Improve storage and processing, integration, governance and analysis of diverse data. | Scale architecture to observed data and latency requirements; avoid buying complexity in advance. |
| 12. BI implementation, EcoGreen Solutions | 25-26 | Select tools, consolidate data, create dashboards, train users and iterate. | Treat data integration, adoption and scalability as separate delivery workstreams. |
| 13. Sector-specific analytics, HealthVision Hospitals | 27-28 | Forecast resource demand, support professional decisions and improve flows using domain-specific data. | Adapt definitions and validation to rail assets and service constraints. |
| 14. International expansion, GlobalFashions | 29-30 | Evaluate markets, local preferences, supply chains and risk; monitor regional performance. | Compare options under contextual assumptions; do not transfer performance across different environments without checks. |
| 15. Revenue strategy, FinTech Innovations | 31-32 | Segment customers, evaluate pricing, forecast churn and monitor campaigns. | Separate predictive risk from the effect of an intervention intended to reduce it. |
| 16. Customer experience, LuxeTravel | 33-34 | Integrate interactions, model behaviour, analyse sentiment and personalise service. | Link service feedback to a traceable improvement action and its outcome. |
| 17. Talent retention, InnovateTech | 35-36 | Combine surveys, tenure and performance; estimate turnover risk; validate with employees and monitor intervention. | Use aggregate workforce-capacity analysis carefully; do not turn this teaching case into automated employee judgement. |
| 18. Marketing attribution, EcoStyle Apparel | 37-38 | Compare first-click, last-click, linear and data-driven attribution; test and reallocate resources. | Distinguish a rule for assigning credit from causal evidence that an action produced the result. |
| 19. Crisis response, SafeHarbor Insurance | 39-40 | Assess impact, forecast workload, allocate resources and target communications. | An incident dashboard should combine known facts, information gaps, responsible roles and response updates. |
| 20. Sustainability, GreenTech Solutions | 41-42 | Analyse demand and weather; measure resource usage and carbon impacts; monitor improvements. | Define energy and resource boundaries before claiming environmental benefit. |
| 21. CSR reporting, GlobalGood Enterprises | 43-44 | Integrate ESG data, measure outcomes, track trends, tailor reporting and obtain verification. | Link executive claims to traceable metrics and independently review material assertions. |

The repeated case architecture is useful: context, measurable problem, objective, data, analytical method, implementation, monitoring, claimed results and evaluation. For the MBA project, add explicit baseline, validation, uncertainty, alternative explanations and limitations so the narrative can be defended.

### 9. Source-quality and interpretation register

| Source location | Issue identified | Treatment in the new AI tool |
| --- | --- | --- |
| SRC-02, case results throughout | Many exact improvements are asserted without primary studies or reproducible calculations. | Tag as pedagogical case claims. Exclude from benchmark lookup and RTA business cases unless independently verified. |
| SRC-03, pp. 9, 22-24 | Several case-study slides contain instructions to present a case rather than an actual documented case. | Preserve the intended teaching topic; do not invent the missing company, data or outcome. |
| SRC-04, p. 3 | Unsourced 90%/92% adoption/value assertions and a historical forecast. | Do not present as current market statistics. |
| SRC-04, pp. 15-23; SRC-07, pp. 24-38 | XYZ/ABC organisation narratives are not supported by primary evidence in the supplied files. | Use as teaching scenarios, with no claim of externally verified organisational results. |
| SRC-06, pp. 17-26 | Named company examples are introductory descriptions, not primary technical or business evidence. | Verify separately before reusing precise company, product, configuration or outcome claims. |
| SRC-06, p. 21 | The Tesla example describes a camera/radar/LiDAR configuration. | Mark for technical verification; do not ingest this as a validated vehicle specification. |
| SRC-07, p. 8 | Image-only maturity graphic is conceptual and offers no empirical axis scale. | Use the categories for explanation; do not infer measured productivity gains. |
| SRC-10, p. 15 | Introductory model sequence ends at training. | Add a separately labelled validation stage, as required by project instructions. |
| SRC-10, p. 22 | Chart displays revenue growth, cost reduction and customer satisfaction on a dollar axis without a supporting dataset. | Exclude chart values. Retain only the principle of measuring initiative-specific value. |
| SRC-10, p. 29 | Anonymous company outcomes include 15%, 8% and 12% improvements without provenance. | Do not use these percentages as factual evidence. |
| SRC-14, pp. 12-13 | “Why” is loosely mentioned under descriptive patterns and then explicitly defined under diagnostic analytics. | Use descriptive for reporting and diagnostic for investigation; explain overlap when teaching the slide. |
| SRC-14, p. 24 | 30%, $2.7M and 45% benefit claims have no identified calculation or case. | Keep out of the project's baseline and ROI model. |
| SRC-15, pp. 5-6 | Maturity level labels and sample capability ratings are illustrative. | Do not infer the user's or RMD's actual maturity from these examples. |
| SRC-15, p. 20 | 300%, 35% and $47M benefits are unsupported by a named study or dataset. | Treat as illustrative source claims only. |
| SRC-16, p. 4 | Historical AI/ML market-growth assertion is unsourced; the chart plots year as a series. | Exclude market figures and chart data from knowledge claims. |
| SRC-16, p. 23 | Anonymous cases assert 20%, 30%, 15% and 40% improvements. | Require independent evidence before any factual reuse. |
| Governance slides across sources | Foreign regulations and general compliance statements are mentioned without jurisdiction analysis. | Do not infer legal applicability or claim compliance from the slides. |
| AI adoption and automation slides | Aspirational statements may sound like guaranteed accuracy, continuous learning or unrestricted action. | Qualify by actual system capability, validation, governance and authorisation. |

### 10. Proposed retrieval-ready topic cards

The following are proposed knowledge units, not claims that RMD V2 already supports them. Each unit should retain topic, evidence status, source IDs, page references, scope and last-reviewed date.

| Topic key | Intended retrieval questions | Principal sources |
| --- | --- | --- |
| `analytics_foundations` | What is business analytics? How is it different from data science? | SRC-01 pp. 2-6; SRC-10 pp. 4-6. |
| `decision_framing` | What decision does this dashboard support? What is the measurable gap? | SRC-10 pp. 7, 10-12. |
| `analytics_types` | Is this descriptive, diagnostic, predictive or prescriptive? | SRC-07 pp. 4-8; SRC-14 pp. 12-15. |
| `analytics_workflow` | What steps are needed before producing an executive recommendation? | SRC-01 pp. 9-10; SRC-03 pp. 20-25; SRC-14 pp. 8-19. |
| `data_quality_lineage` | Can this number be traced? What cleaning and integration checks are required? | SRC-10 p. 26; SRC-14 pp. 9-10. |
| `kpi_strategy` | Which metrics align with the decision and how should they be defined? | SRC-07 pp. 9-10; SRC-14 pp. 6-7. |
| `business_value` | How do we separate potential value from measured benefits? | SRC-03 p. 13; SRC-08 p. 29; SRC-10 p. 22, with source-quality caveats. |
| `bacc_operating_model` | What capabilities, roles and governance sustain analytics? | SRC-04 pp. 4-13; SRC-15 pp. 6-16, 21-29. |
| `ai_ml_taxonomy` | Which learning paradigm matches the available target and decision? | SRC-08 pp. 3-5, with supplementary implementation guidance. |
| `decision_support_adoption` | How should AI fit into existing business workflows? | SRC-16 pp. 12-19; SRC-08 pp. 21-23, 27-30. |
| `sector_case_patterns` | What analogous application helps explain the concept? | SRC-02, pp. 3-44, individually marked as teaching cases. |
| `course_source_limitations` | Which claims or figures need verification before use? | Section 9 above. |

Recommended response structure for the new tool: **answer → evidence and calculation → managerial meaning → uncertainty or missing information → proposed action**. The tool should distinguish a course definition, a calculation on the project dataset, a historical conversation note and a current operational fact.

### 11. Learning checks and expected reasoning

These are original revision questions, not official examination questions or a grading rubric.

1. **Why is “build an AI dashboard” not a complete business problem?** It lacks a measurable gap, decision, owner, scope and success criterion.
2. **What separates prediction from prescription?** Prediction estimates an outcome; prescription selects or ranks feasible actions against objectives and constraints.
3. **Why is a failure Pareto not proof of root cause?** It identifies concentration; technical investigation must establish mechanism and rule out alternative explanations.
4. **Why preserve two files with the same lecture topic?** They contain different material and references; a title match does not prove duplication or supersession.
5. **Can a high-level AI example establish an RTA ROI target?** No. It is insufficient without relevant baseline, costs, outcome evidence and causal attribution.
6. **What makes a BACC more than a software team?** It coordinates business priorities, domain expertise, data standards, governance, capability development, delivery and adoption.
7. **Why must leading indicators be tested?** A plausible precursor may not predict the outcome reliably in the intended setting.
8. **When is a simple report preferable to a predictive model?** When it supports the decision reliably and more complex prediction has no demonstrated additional value.
9. **What is wrong with automatically removing all outliers?** Genuine rare failures can be the most decision-relevant observations; treatment needs a documented rationale.
10. **What does the phrase “AI continuously learns” fail to specify?** Whether retraining actually occurs, on which approved data, how performance is tested, and who authorises the new version.
