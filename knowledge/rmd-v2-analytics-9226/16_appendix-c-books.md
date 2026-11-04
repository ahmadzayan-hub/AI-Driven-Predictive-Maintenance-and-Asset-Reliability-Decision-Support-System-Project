## Appendix C. Reference books and complete topic lookup
<!-- kb: domain=analytics.9226.theory; limits=academic_case|not_rmd_operational_rule -->


All page references use physical PDF pagination. Interpret source content and supplementary RMD recommendations according to the evidence rules in section 1.

### 1. Bibliographic identity and deduplication

| Canonical source | Alias | Verified identity from title/copyright pages | PDF pages | Use in the knowledge base |
|---|---|---|---:|---|
| SRC-18 | SRC-20 | Francesco Corea, *An Introduction to Data: Everything You Need to Know About AI, Big Data and Data Science*, Studies in Big Data 50, Springer, copyright 2019. Title/copyright evidence: PDF pp.1, 4-5. DOI printed in source: `10.1007/978-3-030-04468-8`. | 131 | Data strategy, AI concept map, organisational maturity, accountability, managerial vocabulary. |
| SRC-21 | SRC-22 | Bernard Marr, *Key Business Analytics: The 60+ Business Analysis Tools Every Manager Needs to Know*, first edition, Pearson, 2016. Evidence: PDF pp.6-7. The contents actually enumerate 67 topics. | 276 | Business question to analytical method lookup, data-collection choices, functional applications. |
| SRC-23 | None | Gert H. N. Laursen and Jesper Thorlund, *Business Analytics for Managers: Taking Business Intelligence Beyond Reporting*, second edition, Wiley. Title evidence: PDF p.7. Copyright page p.8 says 2017; its cataloguing-in-publication description says 2016. Retain the discrepancy and use 2017 as the copyright year when constructing a provisional reference. | 291 | Strategy-to-data operating model, lead/lag information, analytics method selection, warehouse design, BACC, business cases. |
| SRC-24 | SRC-25 | Judah Phillips, *Building a Digital Analytics Organization: Create Value by Integrating Analytical Processes, Technology, and People into Business Operations*, Pearson. Title evidence: PDF p.3. Copyright p.4 says 2014 and also records first printing in July 2013. Use 2014 as the copyright year while retaining the first-printing note. | 354 | Analytics delivery workflow, team roles, KPI definitions, reports, dashboards, governance, experimentation and business value. |

Exact file hashes establish the following duplicate groups. Alias files add no independent corroboration and should not create duplicate retrieval chunks.

| Exact duplicate group | SHA-256 |
|---|---|
| SRC-18 = SRC-20 | `178c3a1be3debcf11537cb0a54e7f3e4cbadc981297a876d35e454e497a622ab` |
| SRC-21 = SRC-22 | `ce95d994b7c8037cdd0fa93fd2c692680377c4268e1093e2e1ffad46c431df82` |
| SRC-24 = SRC-25 | `5d3d17f6ff1603d5ea6b0f020b4972e7b757fdfa8a6c295d5fd0887162fad036` |
| SRC-23, unique file | `3fec5924d9ebe38e1988291f1bd199ab8b05b0f1beea93729b32249a916b4f44` |

The seven supplied files therefore represent **four unique reference books**. They are supplementary conceptual sources, not an official assessment rubric, a validated railway safety method, or direct evidence of RMD operational performance. Current laws, software features, vendor capabilities and market statistics cannot be established from these historical editions.

### 2. Corea: data and AI strategy

#### 2.1 Concepts worth retaining

**Data value depends on its decision use.** More data can increase storage, preparation and interpretation costs without improving a decision. Data selection should follow a useful question, and proof of value can start with a small internal dataset. Noise, selection bias, overfitting and spurious correlations can undermine impressive-looking results. The source discusses these concerns in PDF pp.13-15. Its numerical company-performance and anecdotal market examples are historical claims and are not imported as RMD evidence.

**Use an iterative data strategy.** The source's lean approach starts with business processes and the analytical framework, then data construction, modelling and validation, implementation at scale, and measurement. Feedback must reach the business process so that models lead to changed action. Consistent integration, shared reporting definitions and validation support this loop. Source: SRC-18, PDF pp.18-23, especially the framework on p.19.

**Assess capability across several dimensions.** The Data Stage of Development Structure uses four stages, Primitive, Bespoke, Factory and Scientific, against culture, data, technology and talent. In managerial terms, this progresses from isolated reporting efforts through bespoke pilots to repeatable delivery and organisation-wide analytical use. The stages are a book-specific discussion framework, not an RTA certification or mandatory maturity ladder. Source: SRC-18, PDF pp.19-23; table on p.20.

**Choose AI by the kind of problem and the method available.** The AI Knowledge Map places method families on one axis and problem domains on another. Method families include logic-based approaches, knowledge-based approaches, probabilistic methods, machine learning, embodied intelligence, and search/optimisation. Problem domains include reasoning, knowledge representation, planning, communication and perception. This is a useful catalogue for distinguishing document retrieval, statistical prediction, scheduling and speech interaction. It is not a performance ranking of algorithms. Source: SRC-18, PDF pp.34-37; map on p.35.

**Keep accountability explicit.** The ethics discussion addresses data and interaction biases, conflicting objectives, explanation, responsibility, accuracy and auditability. A model can optimise the wrong target or reproduce a bias even when the dataset appears clean. The source uses hypothetical scenarios to explore these issues; the numerical accuracy values in those scenarios are not measured results. Source: SRC-18, PDF pp.87-95, particularly pp.88-92.

#### 2.2 Complete chapter and appendix lookup

| Topic | Starting PDF page |
|---|---:|
| Introduction to data | 13 |
| Big-data management and data strategies | 18 |
| Introduction to AI, definitions and history | 25 |
| AI Knowledge Map | 34 |
| Developments in machine learning, neuroscience and hardware | 39 |
| AI business models | 48 |
| Hiring a data scientist | 54 |
| AI and speech recognition | 59 |
| AI and insurance | 63 |
| AI and financial services | 68 |
| AI and blockchain | 74 |
| New organisational roles in AI | 82 |
| AI and ethics | 87 |
| AI and intellectual property | 96 |
| AI and venture capital | 104 |
| AI accelerators and incubators | 114 |
| Appendix A: managerial terminology | 122 |
| Appendix B: data-science maturity questionnaire | 125 |
| Appendix C: data-scientist skills | 128 |
| Appendix D: personality questionnaire | 129 |

Appendix B has ten items scored from 1 to 4, so the possible sum is 10 to 40. The prose on PDF p.127 incorrectly gives a lower bound of 1, while its classification table begins at 10. The book's bands are Primitive 10-15, Bespoke 16-25, Factory 26-35 and Scientific 36-40. Preserve these only as the source's bands. The questionnaire explicitly requires further discussion and investigation; it is not a validated diagnostic of RMD. Source: SRC-18, PDF pp.125-127.

### 3. Marr: matching questions to analytical methods

#### 3.1 Core method choices and limits

The book is a managerial reference with short entries covering definition, business questions, use, examples and common traps. It helps identify a suitable method but does not supply the entire statistical, engineering or governance specification needed for deployment.

| Decision or analytical need | Appropriate starting method | What the RMD tool must explain | Source |
|---|---|---|---|
| Compare an intervention with an alternative | Controlled experiment or a justified evaluation design | The comparison, outcome, allocation rule and possible confounders. A before/after chart alone does not isolate causation. | SRC-21, PDF pp.20-24 |
| Explore status, trends, distributions and exceptions | Visual analytics | Grain, denominator, timeframe, filters, uncertainty and access to underlying data. | SRC-21, PDF pp.25-28 |
| Check whether variables move together | Correlation | Association may reflect confounding, shared trends or selection. It does not establish a cause. | SRC-21, PDF pp.29-32 |
| Explore plausible operating conditions | Scenario analysis | Inputs are assumptions and outputs are conditional results, not forecasts with measured probabilities unless those probabilities have a basis. | SRC-21, PDF pp.33-37 |
| Estimate future demand, workload or downtime | Time-series methods | Time ordering, trend, seasonality, baseline performance and the usable forecast horizon. | SRC-21, PDF pp.38-40 |
| Predict a numeric outcome | Regression | Outcome and predictors, model assumptions, residual errors, validation and limits on extrapolation. | SRC-21, PDF pp.45-47 |
| Extract themes from incident descriptions or reports | Text analysis | Text quality, domain terminology, classification rules, original context and source references. | SRC-21, PDF pp.48-51 |
| Summarise opinions in feedback | Sentiment analysis | It measures an estimated expression of opinion, with language and context limitations. It is not a reliable measure of a person's inner state. | SRC-21, PDF pp.52-54 |
| Quantify uncertain cost or duration ranges | Monte Carlo simulation | Input distributions, dependencies, assumptions and sensitivity. More simulation runs do not correct wrong input assumptions. | SRC-21, PDF pp.66-69 |
| Allocate constrained resources | Linear programming; a different optimisation formulation when decisions are discrete or non-linear | Objective, decision variables, constraints, feasibility and what the formulation excludes. | SRC-21, PDF pp.70-74 |
| Compare groups with a common starting characteristic | Cohort analysis | Cohort definition, exposure period, differences in context and whether the groups are comparable. | SRC-21, PDF pp.75-77 |
| Reduce correlated measures into latent dimensions | Factor analysis | Scaling, assumptions, interpretability and retained information. Factors do not independently establish causes. | SRC-21, PDF pp.78-80 |
| Learn complex predictive patterns | Neural networks where justified by data and validation | Training data, comparison with simpler models, out-of-sample error and operational cost. | SRC-21, PDF pp.81-83 |
| Combine existing research evidence | Structured literature synthesis and, when suitable, meta-analysis | Search criteria, comparability, study quality, bias and heterogeneity. | SRC-21, PDF pp.84-85 |

The explanatory limits in the table are professional safeguards added for this handover, not claims that the book provides a full RMD deployment protocol.

#### 3.2 Data collection is a design choice

Choose data sources by the question: standardised surveys, contextual interviews, observation, text, images, sensors or machine records. Sensor metrics need units, calibration, timestamps and coverage. Sources: SRC-21, PDF pp.88-121; sensor data p.115 and machine capture p.119.

#### 3.3 Full topic lookup for the 67 entries

The following page starts were checked directly against the extracted source pages. They support retrieval without reproducing the full text.

| No. | Topic | PDF page |
|---:|---|---:|
| 1 | Business experiments, experimental design and A/B testing | 20 |
| 2 | Visual analytics | 25 |
| 3 | Correlation analysis | 29 |
| 4 | Scenario analysis | 33 |
| 5 | Forecasting and time-series analysis | 38 |
| 6 | Data mining | 41 |
| 7 | Regression analysis | 45 |
| 8 | Text analytics | 48 |
| 9 | Sentiment analysis | 52 |
| 10 | Image analytics | 55 |
| 11 | Video analytics | 58 |
| 12 | Voice analytics | 62 |
| 13 | Monte Carlo simulation | 66 |
| 14 | Linear programming | 70 |
| 15 | Cohort analysis | 75 |
| 16 | Factor analysis | 78 |
| 17 | Neural-network analysis | 81 |
| 18 | Research synthesis and meta-analysis | 84 |
| 19 | Quantitative surveys | 88 |
| 20 | Qualitative surveys | 92 |
| 21 | Focus groups | 96 |
| 22 | Interviews | 100 |
| 23 | Ethnography | 104 |
| 24 | Text capture | 108 |
| 25 | Image capture | 112 |
| 26 | Sensor data | 115 |
| 27 | Machine data capture | 119 |
| 28 | Predictive sales analytics | 126 |
| 29 | Customer profitability | 130 |
| 30 | Product profitability | 134 |
| 31 | Cash-flow analytics | 138 |
| 32 | Value-driver analytics | 141 |
| 33 | Shareholder value | 144 |
| 34 | Unmet needs | 150 |
| 35 | Market size | 153 |
| 36 | Demand forecasting | 156 |
| 37 | Market trends | 159 |
| 38 | Non-customers | 162 |
| 39 | Competitors | 165 |
| 40 | Pricing | 169 |
| 41 | Marketing channels | 172 |
| 42 | Brand analytics | 175 |
| 43 | Customer satisfaction | 180 |
| 44 | Customer lifetime value | 185 |
| 45 | Customer segmentation | 188 |
| 46 | Sales channels | 192 |
| 47 | Web analytics | 195 |
| 48 | Social-media analytics | 199 |
| 49 | Customer engagement | 203 |
| 50 | Customer churn | 207 |
| 51 | Customer acquisition | 210 |
| 52 | Workforce capability | 216 |
| 53 | Workforce capacity | 219 |
| 54 | Employee churn | 222 |
| 55 | Recruitment channels | 225 |
| 56 | Competency acquisition | 228 |
| 57 | Employee performance | 231 |
| 58 | Corporate culture | 234 |
| 59 | Leadership | 237 |
| 60 | Fraud detection | 242 |
| 61 | Core competencies | 246 |
| 62 | Supply-chain analytics | 249 |
| 63 | Lean Six Sigma analytics | 253 |
| 64 | Equipment and plant capacity utilisation | 257 |
| 65 | Project and programme analytics | 259 |
| 66 | Environmental impact | 262 |
| 67 | Corporate social responsibility | 265 |

General methods and operational topics have the strongest RMD relevance. Commercial and workforce topics remain supplementary and do not introduce new operational scope.

### 4. Laursen and Thorlund: analytics as an organisational system

#### 4.1 Five-layer business analytics model

The book connects five layers: strategy; business processes and information use; reporting and analytical processes; data warehouse; and source systems. Requirements move from strategic goals towards data. Data and derived information move towards decision makers. The analyst connects business needs to technical delivery. Source: SRC-23, PDF pp.28-32.

#### 4.2 Strategy, critical success factors and indicators

The Rockart-inspired process links objectives to an operational strategy, critical success factors, and the lead and lag information required to develop and control a process. Source: SRC-23, PDF pp.85-98; the overview figure is on p.86. Lead information supports action before an outcome; lag information records realised outcomes. The later BACC chapter adds learning as knowledge accumulated through using and reviewing information. Sources: SRC-23, PDF pp.80-85 and 228-231.

#### 4.3 Method selection as three questions

The source's three selection questions, paraphrased, are:

1. Is the need to retrieve and present information, or to perform quantitative analysis?
2. Does a theory-led hypothesis test or a more exploratory/predictive method fit the decision better?
3. For a data-driven method, is there a target outcome to model, or is the task to discover structure without an outcome label?

This leads to four broad work types: descriptive reporting, hypothesis-based analysis, prediction with target variables, and exploratory methods. Source: SRC-23, PDF pp.140-148. This is a useful business conversation framework, with limitations: statistical analysis and machine learning overlap, predictive modelling can be reproducible, and both require sound validation.

#### 4.4 Data foundation

The warehouse chapter separates source systems, a staging area, quality controls, integrated data, data marts and business access. The purpose is consistent historical information across systems, without making every report depend on heavy direct queries to operational systems. Source: SRC-23, PDF pp.179-188; architecture diagram p.181.

Dimensions place facts in context. Time, organisational unit, asset or other entities make an otherwise isolated number interpretable. The book introduces the star schema and dimensional hierarchies on PDF pp.188-190. The proposed RMD interpretation is to specify the fact-table grain first and then choose appropriate dimensions. Failure events, asset-period summaries and work-order events have different grains and must not be joined as if each were one interchangeable observation.

Data-quality measures should identify missingness, invalid formats, inconsistent definitions, duplicates and other rule violations. The book discusses profiling and correction on PDF pp.185-188. For this handover, preserve original data and transformation lineage; do not automatically delete anomalies simply because they are extreme or inconvenient.

#### 4.5 BACC and organisational learning

A Business Analytics Competency Center combines business, analytical and IT skills. It may be a formal unit or a virtual cross-functional forum. Its role includes keeping information aligned with business needs, coordinating shared definitions and delivery, developing users, sharing knowledge and prioritising analytical initiatives. Source: SRC-23, PDF pp.227-238, particularly the information wheel p.230 and competency diagram p.235.

The book makes an important distinction on PDF p.232: a BACC works with system owners to align information architecture and technology with the business information strategy; it does not automatically take ownership of every system-design decision. Applied to RMD V2, a new AI tool does not itself establish a new organisational authority or transfer accountability away from approved owners.

#### 4.6 Business cases and value

The source evaluates implementation cost, ongoing cost, increased value to users and resource savings. It uses a before/after process view, including SIPOC, to identify changes in suppliers, inputs, process, outputs and customers. Benefits arise when better information changes action and improves outcomes. Source: SRC-23, PDF pp.249-256, especially pp.250-253.

For an RMD project, separate measured benefit from expected benefit. Avoided downtime is not automatically cash saving; released staff capacity is not automatically a payroll reduction; and a useful model metric is not a realised maintenance benefit. The business case must state the counterfactual, accounting basis, evaluation period and actual action taken. These are handover evaluation requirements, not claimed financial results.

#### 4.7 Chapter lookup

| Chapter | Starting PDF page |
|---|---:|
| 1. Business analytics model | 27 |
| 2. Strategic level | 43 |
| 3. Functional information development and deployment | 73 |
| 4. Analytical level | 129 |
| 5. Data warehouse | 175 |
| 6. Source data collection | 211 |
| 7. Business Analytics Competency Center | 225 |
| 8. Assessment and prioritisation of analytics projects | 247 |
| 9. Future perspectives | 273 |

### 5. Phillips: delivering useful analytics repeatedly

#### 5.1 Nine organisational considerations

Phillips organises analytics delivery around nine terms: people, pre-engagement, planning, platform, process, production, pronouncement, prediction and profit. In practical language, these cover skills, understanding stakeholders, planning work, choosing technology, defining the process, doing the analysis, communicating it, developing predictive capability where useful, and demonstrating value. Sources: SRC-24, PDF pp.30-35.

#### 5.2 Six-phase analytics value chain

The source's value chain has six phases:

1. Understand the decision and what needs analysis.
2. Define, collect, verify and govern the relevant data.
3. Present relevant reports and dashboards.
4. Analyse and communicate findings with stakeholders.
5. Optimise, predict and automate where useful.
6. Demonstrate the resulting economic value.

The source explicitly allows iteration between phases rather than requiring a rigid one-way sequence. Source: SRC-24, PDF pp.55-64. A particularly useful discovery question is what decision the stakeholder would make if the requested analysis were already available. The handover should paraphrase this idea as a required decision field, rather than reproduce unnecessary book text.

#### 5.3 Three levels of definition

The book distinguishes:

| Definition level | Purpose | Proposed RMD availability example |
|---|---|---|
| Business | State what the measure means to the decision maker. | Whether an asset was available for the agreed service requirement. |
| Operational | Define inclusion rules, period and conditions. | Specify asset scope, required hours, relevant downtime categories and treatment of overlaps. |
| Technical | Specify exactly how systems compute the value. | Identify timestamp fields, event rules, aggregation logic, query version and denominator. |

Source: SRC-24, PDF pp.167-169. The availability example is a design illustration, not an approved contract definition or a ready-made formula.

#### 5.4 Reporting and dashboards

The detailed chapter uses **RASTA for reporting** and **LIVES for dashboards**.

RASTA covers relevance to the audience, accuracy and actionability, simple goal-specific structure, timeliness, and annotations or explanation. Source: SRC-24, PDF pp.196-198.

LIVES covers links to detail, interaction, visual communication, a hierarchy matched to audience priorities, and connection to strategy. Source: SRC-24, PDF pp.201-202. The book's term for the hierarchy is *echeloned*. For RMD V2, this supports drill-through to an engineering case or evidence record, visible filters and concise trend or exception explanations.

There is an internal source inconsistency: the introductory overview on PDF p.29 reverses the reporting/dashboard labels. The detailed chapter definitions above are the relevant authority for this synthesis.

#### 5.5 KPI ownership and dashboard users

The KPI discussion links measures to defined business goals, audiences, systems, and connected dashboards. It recognises that both operational staff and managers make decisions and need suitable information. Source: SRC-24, PDF pp.202-209. RMD V2 should therefore avoid giving every role an identical screen or treating executive summary cards as a replacement for an engineer's evidence view.

#### 5.6 Chapter lookup

| Chapter | Starting PDF page |
|---|---:|
| 1. Creating business value with digital analytics | 21 |
| 2. Analytics value chain and organisational considerations | 30 |
| 3. Analytics organisation and roles | 72 |
| 4. Tool selection, build/buy and maintenance | 104 |
| 5. Analytical methods | 134 |
| 6. Data definition, collection and governance | 164 |
| 7. Reporting, dashboards and KPIs | 187 |
| 8. Optimisation and testing | 219 |
| 9. Qualitative and voice-of-customer evidence | 240 |
| 10. Competitive intelligence | 265 |
| 11. Targeting and automation | 279 |
| 12. Omnichannel data integration | 294 |
| 13. Future perspectives | 315 |

### 6. Source caveats the receiving AI must preserve

| Issue | Evidence | Handling |
|---|---|---|
| Exact duplicate books | File hashes in Appendix C, section 1 | Keep one canonical text and alias metadata. Do not count duplicate copies as multiple sources. |
| Historical publication dates | Copyright pages listed in Appendix C, section 1 | Treat product names, vendor lists, forecasts, market figures and descriptions of the future as statements from that edition. |
| Corea AI definition is narrower than the broader field | SRC-18, PDF p.26 describes learning-based AI in broad terms; pp.34-37 later include logic, knowledge, search and other approaches | Do not turn that single definition into a rule that every AI system must learn or rewrite its own algorithms. |
| Corea maturity-score lower-bound error | SRC-18, PDF pp.125-127 | Ten scores of 1-4 give a total of 10-40. Source bands are illustrative, not validated RMD thresholds. |
| Maturity does not require a specific technology | SRC-18, PDF pp.126-127 assigns high scores to certain architecture choices | Do not equate cloud/NoSQL/automation with maturity without assessing fitness, controls and actual value. |
| Significance language is oversimplified | SRC-23, PDF pp.143-144 calls 5% a confidence level and uses certainty language | A significance level is a long-run false-positive control under stated assumptions, not the probability that a conclusion is true. Report effect sizes, uncertainty, assumptions and multiple-testing considerations. |
| Reproducibility distinction is overstated | SRC-23, PDF p.145 suggests data mining cannot be recreated because it uses sampling | Do not inherit this as an operating rule. Preserve data, code, versions, seeds and validation splits for reproducibility in both statistics and ML. |
| Causal language can overreach | SRC-21, PDF pp.45-47 and 78-80 use examples that can suggest causal interpretation from regression or factors | Associations, latent dimensions and predictive importance are not proof of causal effects. |
| Dashboard/report mnemonic labels conflict | SRC-24, PDF p.29 versus pp.196-202 | Follow detailed definitions: RASTA reporting, LIVES dashboarding. |
| Hypothetical examples are not empirical results | Especially SRC-18, PDF pp.89-91; also example business cases throughout | Label examples explicitly. Never transfer their numbers to RMD or MIYAAR. |
| Commercial value framing needs adaptation | SRC-24, PDF pp.30-31 and 56-57 | State public-service and operational objectives explicitly; do not force all outcomes into profit. |

### 7. Proposed retrieval metadata

Retain `source_id`, `canonical_source_id`, `alias_source_ids`, title, author, edition, copyright year, PDF page range, section title, topic tags, evidence type, source date and caveat IDs. Classify source content as `reference_book`; classify added RMD examples as `proposed_rmd_adaptation`. Do not mix either with live operational facts.

These are proposed integration fields. The review did not inspect the RMD V2 codebase, verify current connectors, train a model or deploy a feature.
