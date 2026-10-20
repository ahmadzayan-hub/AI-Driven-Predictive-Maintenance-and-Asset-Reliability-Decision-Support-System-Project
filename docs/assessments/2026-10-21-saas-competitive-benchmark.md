# Commercial SaaS comparison: maintenance and asset reliability

Reviewed 21 October 2026. Source baseline: `main` at `4b193f0`.

Integration addendum: incoming `main` through `8d41121` was preserved. Its agent-rule, evaluation and limitation changes were reviewed; they add independent language-agent evidence but do not establish equipment prediction or customer outcomes. The assessed storage, authentication, connector and maintenance-model implementations are unchanged by that integration.

## Assessment

The platform has a substantive, governed analytics foundation: traceable figures, maintenance-specific model checks, bilingual reporting and human-controlled publication. The evidence supports developing it into a focused reliability decision-support service. It does **not yet establish an operational CMMS replacement, field-validated failure prediction, or commercially proven SaaS**.

The strongest near-term position is **Arabic/English reliability decision support connected to a customer's existing maintenance system**. The first product promise should be a reviewed, actionable maintenance decision with traceable evidence. More animated agents alone will not establish differentiation or customer value.

This recommendation is an inference from the source and product comparison below, not a finding from customer interviews or a measured market-size study.

## Scope and evidence rules

- Compared three related categories: maintenance execution/CMMS, machine-health services, and enterprise asset management/performance management. Their prices, implementation effort and scope are not interchangeable.
- Used official product documentation, published customer cases, one customer's own capability statement, NIST guidance and Google's SRE guidance. Named deployments establish published operational use; they do not prove audited profitability, current uptime, or causal savings.
- Inspected current code, documented limitations and previous verification records. A source capability is not automatically enabled or accepted in the hosted service. No competitor account was tested hands-on.
- The hosted platform could not be inspected through the web retrieval tool. That is an evidence limitation, **not evidence of an outage**. The prior local timeout repair is documented; it does not validate hosted latency or capacity.
- Historical defects repaired in the [20 October assessment](2026-10-20-project-review.md) are not counted again as current defects. No maturity percentage, comparative accuracy score, or customer ROI is invented.

## Operating products used as benchmarks

| Product and category | Published capability evidence | Named operational evidence | Most relevant lesson |
| --- | --- | --- | --- |
| **MaintainX — maintenance execution** | [Plan comparison](https://www.getmaintainx.com/pricing) documents maintenance workflows, inventory and integration packaging. [Mobile offline documentation](https://help.getmaintainx.com/offline-mode) explains cached work and synchronization. | Its [Cottrell case](https://www.getmaintainx.com/case-studies/cottrell-mcdonalds-case-study) describes deployment across a McDonald's franchise operator's restaurants. This is not a claim about every McDonald's location. | The product helps a technician complete a job and a manager follow its outcome. |
| **Fiix — industrial CMMS** | [ERP/BI integration](https://fiixsoftware.com/cmms/it-integrations/) and [mobile app documentation](https://helpdesk.fiixsoftware.com/hc/en-us/articles/4413567981076-About-the-mobile-app) connect maintenance with assets, parts and work orders. | The [Bush Brothers case](https://fiixsoftware.com/resource-center/case-studies/bush-brothers/) describes an operating multi-site deployment and maintenance adoption. Future intentions in the case are not counted as deployed functionality. | Connect operational records and existing business systems, rather than maintaining another isolated reporting destination. |
| **Augury — machine health and reliability service** | [Machine Health Critical](https://www.augury.com/machine-health-solutions/cr/) combines monitoring, diagnostic intelligence and reliability expertise. Its [Reliability Agent](https://www.augury.com/reliability-agent/) describes evidence gathering, analysis and proposed maintenance actions. | Its [Colgate-Palmolive/Hill's case](https://www.augury.com/success-stories/colgate-palmolive-optimizes-maintenance-using-ai-insights/) attributes operational machine-health use to a named customer. | Prediction needs domain evidence, an action and feedback from the repair. |
| **IBM Maximo — enterprise EAM/APM** | [SaaS packaging](https://www.ibm.com/products/maximo/pricing) distinguishes Essentials, Standard and Premium; [APM](https://www.ibm.com/products/maximo/asset-performance-management) addresses asset performance and maintenance decisions. | [IBM's Downer case](https://www.ibm.com/case-studies/downer) and [Downer's own capability statement](https://www.downergroup.com/Content/cms/media/28613_Capability_Statement_Mk17_updated_HR_bleed_1__39_.pdf) connect TrainDNA with Maximo and an operational rail fleet. They do not establish which current SaaS edition that customer uses. | Asset hierarchy, lifecycle context and integration matter as much as an analysis screen. |

Vendor case-study savings are deliberately not used as targets for this project. Definitions, dates, asset populations, service bundles and attribution differ. An advertised feature is not evidence that every customer uses it successfully.

## Current capability assessment

**Present** means implemented in the inspected source; **partial** means a narrower foundation exists; **not evidenced** means the reviewed source and records do not establish it; **field-unverified** means real operational performance remains unproved. These are evidence labels, not grades.

| Customer need | Current platform evidence | Assessment and commercial consequence |
| --- | --- | --- |
| Explain and reproduce a figure | Calculations, claims, provenance, reconciliation and scoped evidence in the analytics/report pipeline | **Present.** Useful for review and approval; requires independent checking against customer definitions. |
| Arabic/English management reporting | Translation resources, RTL presentation and scoped executive exports | **Present.** A potential positioning advantage for bilingual teams; comparative usability and willingness to pay are unmeasured. |
| Govern publication | Approval records bound to an artifact; optional models phrase controlled facts | **Present.** Human review is meaningful, but report approval is not maintenance-work authorization. |
| Predict maintenance outcomes | Known-before feature checks, chronology handling, held-out model/baseline comparisons and weak-model disclosure | **Present; field-unverified.** This is more than a generic chart demo, but does not establish useful warning lead time or failure prevention. |
| Maintain asset and work history | Asset-oriented dataset analysis and run tasks; no first-class operational asset/work-order schema in the reviewed storage model | **Partial.** An analytical asset view is not a maintained asset registry, job assignment or repair history. |
| Ingest operational data continuously | Owner-scoped HTTPS file snapshots and scheduled refresh | **Partial.** Current connectors fetch public files; authenticated CMMS/historian integration and continuous sensor ingestion are not established. |
| Run reliably without an open tab | Durable run records, optional lease-based worker, pause/cancel/recovery | **Partial; hosted acceptance unverified.** Default browser-driven advancement and long stage execution need a measured deployment design. |
| Support a customer organization | Managed identity adapter, permissions and owner-scoped records | **Partial.** Organization membership, shared site/team administration and scoped organization roles are not established by those controls. |
| Work offline on the shop floor | Responsive/PWA foundation | **Partial.** No demonstrated offline maintenance edits, attachments, inventory actions and conflict-safe synchronization comparable to the documented mobile workflows above. |
| Inspect agent collaboration | Restrained status motion, workflow links, evidence and observed activity | **Present for workflow observation.** Durable sender/recipient message history is a proposed contract, not demonstrated by graph edges. |
| Purchase and operate a supported service | Usage quotas and implementation documentation | **Partial.** Quotas are not subscriptions; verified paid adoption, entitlement administration, support delivery and renewal evidence were not supplied. |
| Trust hosted security and continuity | Authentication/tenancy controls, backup tooling and regression records | **Present foundations; operational assurance unverified.** Source tests do not establish hosted isolation, an exercised recovery objective, independent assurance or certification. |

Local evidence: [analytics](../../server/analytics.py), [maintenance targets](../../server/maintenance/targets.py), [storage](../../server/storage.py), [identity](../../server/auth.py), [connectors](../../server/connectors.py), [worker](../../server/worker.py), [quota policy](../../server/quota.py), [known limitations](../KNOWN_LIMITATIONS.md), [asset scope decision](../adr/2026-10-20-asset-evidence-scope.md), [collaboration design](../design/AGENT_COLLABORATION_MOTION.md), and the dated validation entries in [README](../../README.md#testing).

## Strong points worth preserving

1. **Traceable decision evidence.** Deterministic figures, explicit denominators and populations, calculation references and reconciliation give reviewers a way to challenge a conclusion. Preserve that path through every future integration and export.
2. **Honest model limitations.** Maintenance models restrict inputs by decision-time availability, compare against informative baselines on the same eligible cohort, and disclose weakness. These are useful foundations for validation; synthetic agent evaluation and software tests are separate from predictive performance on operating equipment. Incoming blind language-agent evaluations still report intent and causal-wording misses, so the presence of a wording guard cannot guarantee a correct interpretation or supported causal statement. See [known limitations](../KNOWN_LIMITATIONS.md).
3. **Bilingual delivery with restrained motion.** English/Arabic reporting, RTL and reduced-motion behavior can support mixed-language management and operations teams. Validate actual task completion with those users before calling this an advantage over another product.
4. **Human control and limited model access.** Publication approval is bound to the reviewed artifact; raw rows remain server-side and optional narration works from controlled evidence. Detection-based personal-data controls still need assessment against the actual customer data.
5. **An adaptable engineering base.** Managed authentication, owner isolation, quotas, recoverable runs, an optional worker, custom stages and MCP interfaces reduce some implementation work. They do not by themselves establish organization-level SaaS operations.

**Competitive caution:** Augury already describes evidence-backed analysis and human approval before a generated work order is sent to a CMMS. These are valuable product practices, but claiming that agents or approval make this platform unique would be unsupported. The opportunity is a particular customer's workflow, language needs, integration effort and demonstrated decision quality. [Augury Reliability Agent](https://www.augury.com/reliability-agent/)

## Highest-priority gaps and acceptance evidence

Priorities are recommendations for a focused pilot, not measured customer demand. P0 protects credible pilot delivery; P1 establishes operational value; P2 supports repeatable sales and expansion.

| Priority | Gap and customer impact | Recommended next step | Evidence needed to close it |
| --- | --- | --- | --- |
| **P0** | **Hosted completion and recovery.** An interrupted request can leave users unsure whether analysis completed. The local request-deadline correction does not resolve host limits, queue contention or concurrent model requests. | Run a durable worker on a suitable host; return a job reference promptly; make reconnection and status recovery explicit. Measure completion and queue time separately. | On the actual deployment, representative concurrent jobs survive browser closure and worker restart without duplicate work; alerts and a restore exercise meet agreed objectives. |
| **P0** | **Customer data and domain acceptance.** An imported column or apparently accurate model can answer the wrong maintenance question. | Select one asset class and decision; agree asset IDs, time semantics, source grain, failure labels, censoring and KPI definitions with a reliability specialist. | An independent reviewer reconciles the exported figures and eligible population against the customer's source; unsupported conclusions are withheld. |
| **P0** | **Tenant and release assurance.** Owner-level permissions are not a complete shared customer workspace, and implementation is not deployed assurance. | Define the pilot's membership/access boundary, verify it on hosted storage, rehearse backup/restore and retention/deletion, and resolve the documented repository-data release gate. | Cross-customer negative access tests cover datasets, runs, artifacts and notes; restore and deletion evidence exists; the release checklist is accepted. Avoid certification claims without an audit. |
| **P1** | **Recommendation-to-repair loop.** The platform can report findings but does not demonstrate assignment, execution and closure of maintenance jobs. | Integrate one existing CMMS first. Link approved recommendations to stable asset IDs and work orders, then import completion, parts/labor and confirmed failure findings. | A real pilot case travels from evidence to authorized work order to recorded outcome, retaining provenance and handling retries without duplicate orders. |
| **P1** | **Operational connectors.** Public snapshot refresh cannot replace authenticated production records or sensor streams. | Build one authorized CMMS/ERP connector with incremental reads, schema-change handling and freshness reporting. Add historian/IoT ingestion only if the chosen use case needs it. | Authentication, expired credentials, late/duplicate records, deletion and schema drift are exercised; users see stale-data warnings. Compare with [Fiix integration workflows](https://fiixsoftware.com/cmms/it-integrations/). |
| **P1** | **Prospective predictive value.** A retrospective baseline comparison does not establish an actionable alert. | Evaluate in shadow mode on later unseen operating periods; choose thresholds using the customer's false-alarm and missed-failure costs. Keep technician outcomes independent of model training until evaluated. | Report actionable-alert precision, missed events, warning lead time, false alerts per asset-month and calibration where probabilities are shown, with sample sizes and uncertainty. |
| **P1** | **Daily role-based use.** A run/stage interface exposes how analysis happens but can obscure what a planner should do next. | Lead with assets needing review, why, owner and next action; retain evidence and agent details as expansion. Test the bilingual planner journey. | Intended users find, explain and act on a priority without coaching. Add offline work execution only if the target workflow requires it. |
| **P2** | **Repeatable commercial service.** Usage limits do not define a sellable package or support commitment. | Define the buyer, onboarding, included assets/sites/usage, support owner and service terms; measure support effort. Add billing automation when justified; a controlled pilot can use manual invoicing. | Documented onboarding and observed repeat use, a real purchase/renewal decision and support cost. Enterprise SSO/provisioning follows buyer need; [MaintainX documents SAML SSO as an enterprise feature](https://help.getmaintainx.com/about-sso-for-maintainx). |

The prediction gate follows NIST's emphasis on deployment-relevant evaluation and monitoring; it is not a claim of NIST certification. Service objectives should describe the user's successful journey, not only a healthy API endpoint. [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), [Google SRE: implementing SLOs](https://sre.google/workbook/implementing-slos/)

## Recommended positioning and delivery sequence

**Proposed buyer hypothesis:** a maintenance/reliability manager who already has asset and work-order records, needs defensible bilingual reviews, and spends substantial effort reconciling exports and explaining priorities. Validate that problem with prospective customers; Arabic support alone does not establish demand.

1. **Prove one useful review.** Choose one asset class, source system and recurring decision. Establish the data contract, independently accepted figures and hosted pilot gates. Initially promise evidence-led prioritization only where supported.
2. **Close one action loop.** Import records from the selected CMMS, produce an approved recommendation, link the authorized work order and collect its outcome. Prove this journey before implementing a complete competing CMMS.
3. **Earn the predictive claim.** Run a prospective shadow evaluation with a domain reviewer and an agreed operational threshold. Distinguish classification quality, warning lead time and realized maintenance benefit.
4. **Make delivery repeatable.** Add organization administration, dependable onboarding, monitoring, support and pricing based on observed customer use. Extend asset classes and integrations after the first workflow is repeatable.

**Animations and agent connections:** retain the professional motion already selected. Show observed status, handoffs, freshness, retries and expandable evidence. For actual agent communication, first persist authorized event IDs, sender/recipient, timestamp, event type, result and trace linkage. Do not render an invented transcript. The [React connection study](../design/REACT_AGENT_CONNECTIONS_STUDY.md) remains applicable: native React/SVG/CSS for compact workflow views; an optional React Flow explorer when navigation needs justify it. More nodes are not a maturity metric.

## Proposed pilot measurements — no results yet

| Question | Definition to agree before measurement |
| --- | --- |
| Does onboarding produce value? | Time from first authorized import to the first independently accepted, usable report; report incomplete onboarding separately. |
| Does the service complete its job? | Successful eligible runs divided by started eligible runs, with failures/cancellations classified; report completion latency and queue wait, including slow and failed cases. |
| Is the evidence current? | Age of the latest successfully ingested source record relative to that source's expected delivery schedule; distinguish ingestion delay from genuinely old source data. |
| Do people act? | Approved recommendations linked to a recorded maintenance action divided by approved recommendations, within an agreed follow-up period. Completion is distinct from approval. |
| Are alerts useful? | Confirmed actionable alerts divided by evaluated alerts, missed eligible failure events, lead time and false alerts per asset-month. Define adjudication, exposure, censoring and delayed outcomes first. |
| Does value persist? | Repeat use by the intended operating role, support effort and actual purchase/renewal decisions. Do not infer willingness to pay from a successful demo. |
| Did maintenance improve? | Agreed downtime/cost definitions compared over an appropriate exposure and follow-up period, accounting for production mix and concurrent changes; simple before/after change alone does not establish causation. |

No competitor SLA, prediction score or case-study savings rate is adopted as this project's target without a comparable workload and definition.

## Review boundaries and next decision

This is a documentation and source assessment, not a new security audit, load test or full software test run. Prior software validation remains dated in README. Hosted acceptance, independent maintenance-domain validation and customer/commercial evidence remain open.

The next useful decision is the **first customer workflow and source system**. The recommended scope is a bilingual reliability-review layer with a demonstrable work-order feedback loop. That exploits the current evidence and governance strengths while addressing the most consequential gaps shown by operating products.
