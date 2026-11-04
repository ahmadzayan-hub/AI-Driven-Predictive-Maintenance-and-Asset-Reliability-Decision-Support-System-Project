## 9. Claude Code handover
<!-- kb: domain=rmd.product; evidence=PROPOSED -->


### 9.1 Where to put this file

Suggested repository location:

~~~text
docs/knowledge/RMD_V2_Data_Analytics_Project_Knowledge.md
~~~

This is a proposed destination, not an existing path verified in RMD V2. Keep the repository's current CLAUDE.md/AGENTS.md guidance and add a concise pointer to this reference file where appropriate.

Anthropic's current documentation recommends concise CLAUDE.md instructions and explains that imported files consume context together with the importing file. Keep this large knowledge pack available for targeted reading/retrieval rather than loading every page as standing instructions. This guidance was checked on 5 November 2026. [WEB-01]

A possible short repository note is:

~~~markdown
## Analytics project knowledge

For analytics, KPI, predictive-maintenance or Group 9226 work, read the relevant
sections of docs/knowledge/RMD_V2_Data_Analytics_Project_Knowledge.md.

Preserve source IDs and evidence labels. Keep synthetic course examples separate
from operational RMD data. Verify current code and dataset versions before making
implementation or performance claims. Use the existing authentication, data and
evidence services.
~~~

The note guides Claude Code. It does not by itself connect the RMD V2 runtime to the knowledge.

### 9.2 Ready-to-paste implementation prompt

~~~text
Work inside the existing RMD-V2 repository.

Read docs/knowledge/RMD_V2_Data_Analytics_Project_Knowledge.md, starting with
sections 0, 4, 5, 6, 8 and Appendix D. Use the other sections as needed.

Objective:
Implement a source-grounded Analytics and Decision Support capability in the
existing RMD V2 AI tool. It should explain project/course knowledge, inspect
authorised datasets, calculate defined KPIs, and prepare justified maintenance
review findings in English or Arabic.

First inspect the current repository instructions, architecture, AI entry points,
authentication and permission model, evidence/case/action services, existing
knowledge retrieval, metric calculations, UI conventions and test commands.
Reuse the actual stack and existing integrations.

Implement a working vertical slice:
1. Ingest or index this Markdown with coherent chunks, source IDs, evidence
   status, version, synthetic label and the repository's access scope.
2. Add a query path that retrieves relevant evidence and returns citations,
   limitations and source conflicts.
3. Add or reuse deterministic KPI tools. Validate the original Team 3 CSV by
   its hash if it is supplied. Match the documented formulas and reconciliation
   results. Keep any fixture clearly synthetic.
4. Show the answer, relevant sources, active data/filter scope and proposed
   follow-up action in the existing bilingual interface.
5. Connect findings to existing cases/evidence/actions where supported.
6. Add meaningful integration checks from Appendix D, including stale sessions,
   access isolation, incorrect metric definitions and missing evidence.
7. Run the relevant checks and build. Fix failures caused by this change and
   document any pre-existing or environment limitations.

Preserve these facts:
- Original Asset_ID values do not form valid longitudinal asset histories.
- Failure_Probability and priority/health scores are synthetic source fields,
  not proof of a trained or calibrated future-failure model.
- Full-dataset availability is 96.9625%; mean record availability is 96.7798%.
- The service-target met rate is 46.12%; 75.782986% is the mean capped SLA score.
- 3,950 rows have overdue work, while the total overdue work-order count is 5,940.
- The 12.0-hour measure is a downtime-per-failure proxy until repair-time
  semantics are validated.
- Historical PR, deployment and AUC statements require current evidence.

If a needed dataset, source, model artifact or permission is missing, identify
the exact gap and complete the portions that can be implemented from available
evidence. Do not invent rows, model results, approved thresholds or source facts.

Deliver:
- Working code consistent with the repository architecture.
- Ingestion/versioning and metric-definition documentation.
- The acceptance-check results and remaining limitations.
- A concise change summary describing the user-visible result.
Follow the current repository's authorised review and release workflow.
~~~

### 9.3 Runtime ingestion

For the deployed assistant to answer from this knowledge, the application needs an actual ingestion/retrieval path. Add the canonical file or its section chunks to the existing knowledge store, persist source metadata and ensure the request handler retrieves authorised content. Validate a sample query through the real interface. Do not claim runtime integration because Claude Code read the file while developing.

Raw-data calculation needs the actual CSV or a verified equivalent snapshot. Source links in this file are traceability links for the owner; they are not application credentials or guaranteed machine-accessible endpoints.
