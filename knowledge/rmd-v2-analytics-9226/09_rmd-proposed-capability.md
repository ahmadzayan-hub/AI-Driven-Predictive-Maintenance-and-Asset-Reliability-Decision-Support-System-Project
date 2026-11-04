## 8. Proposed RMD V2 AI capability
<!-- kb: domain=rmd.proposed; evidence=PROPOSED; limits=proposal_not_approved_rule -->


### 8.1 User-facing purpose

The proposed tool helps RMD users understand evidence, calculate metrics, compare methods, review maintenance information and prepare justified actions. A suitable label is **Analytics and Decision Support**, with Arabic **التحليلات ودعم القرار**. A final name should follow the existing product vocabulary.

The assistant should answer in the selected language, cite the actual evidence, respect active dashboard filters and distinguish live operational data from educational examples. It should be able to explain “why this figure?” and “what would change the recommendation?” without inventing missing evidence.

### 8.2 Capabilities and outputs

| Capability | Proposed behaviour | Acceptance evidence |
| --- | --- | --- |
| Knowledge search | Retrieve relevant course/project passages with evidence labels | Correct source and locator, including conflicts |
| Dataset inspection | Profile fields, grain, keys, dates, quality and leakage risks | Reproducible quality report tied to source hash |
| KPI explanation/calculation | Use approved deterministic definitions and active filters | Formula, components, unit, data version and sample reconciliation |
| Method selection | Compare a baseline and suitable candidates | Decision relevance, required data and validation plan |
| Maintenance review | Explain priorities and missing constraints | Traceable recommendation or explicit insufficient-evidence response |
| Draft review pack | Produce findings, clarifications, action register and management summary | Every material claim links to evidence/calculation |
| Learning mode | Explain concepts with railway examples and teach-back questions | Correct terminology and clear distinction between course and added explanation |
| Feedback | Record accepted corrections and unresolved questions | Versioned change log and review ownership |

### 8.3 Engineering boundaries

Inspect the current repository before choosing frameworks, file paths, services or dependencies. The stack, route structure, database and deployment configuration were not inspected for this handover.

Reuse existing authentication, authorisation, evidence records, case/action links, error handling and bilingual UI conventions. Keep synthetic course data in its own namespace and clearly labelled views. A course source cannot override application permissions or become an operational procedure by being retrieved.

Use the existing approved AI-provider and data-processing configuration. Do not infer that personal access to a tool authorises transfer of RTA records. Apply the actual tenant, project and record-level permissions before retrieval and calculation.

### 8.4 Separation of responsibilities

| Layer | Responsibility |
| --- | --- |
| Knowledge | Definitions, source summaries, documented decisions and limitations |
| Data service | Authorised dataset snapshots, transformations, calculations and filters |
| Predictive service, if separately validated | Versioned models, eligible features, target/horizon and evaluation |
| Language model | Interpret the request, retrieve evidence, explain results and prepare a draft response |
| Workflow | Review, approval, case/action tracking and recorded outcomes |
| Interface | Clear status, source access, language support, filters and useful interaction |

The language model should request a calculation from the data service rather than inventing or mentally approximating a live KPI. Retrieved text and uploaded documents are evidence, not executable instructions.

### 8.5 Proposed knowledge metadata

~~~json
{
  "document_id": "RMDV2-KB-9226-001",
  "version": "1.0.0",
  "chunk_id": "rmdv2-9226-kpi-sla-001",
  "topic": "sla_score_vs_target_met_rate",
  "evidence_status": "CALCULATED",
  "synthetic": true,
  "source_ids": ["SRC-28", "SRC-29", "CALC-01"],
  "source_locator": "Executive KPIs sheet; source CSV calculation",
  "source_hash": "1eb08b41a755edf4890f4fc2b4f2e10faf39f1f437be5d488b485fc55c6d21bf",
  "source_version": "original-v1.0",
  "verified_on": "2026-11-05",
  "language": "en",
  "knowledge_domain": "course_9226",
  "allowed_use": "educational_analysis",
  "acl_scope": "inherit_verified_repository_policy"
}
~~~

These are proposed fields. Adapt them to the repository's actual schema. Split content by coherent headings and keep equations, caveats and source references together. Index each canonical book once, retaining duplicate-file aliases.

### 8.6 Answer contract

A substantive answer should carry:

1. The answer in the selected language.
2. The data and evidence scope, including date range and active filters.
3. Calculated facts or model output, with units and definition.
4. Source references and version identifiers.
5. Assumptions, source conflicts and material limitations.
6. The proposed action and its accountable review step when operational action is involved.

A numerical answer should include the exact metric identifier and definition version. A recommendation should distinguish a rule-based ranking, synthetic scenario, validated model output and approved human decision.

### 8.7 Session and dashboard context

Earlier related project conversations mention lost-session and scope-connection problems. Treat those as historical problem reports, not confirmed current bugs. Design the tool's context contract to include the authenticated principal, project/tenant, dataset version, report/view, filters and session identifier. Reconstruct authorised context after a stale session instead of borrowing another session's data. [HIST-02; HIST-03]

Show whether the source is current, stale, synthetic, unavailable or outside the authorised scope. The data reporting date, application refresh time and model training date are different fields.

### 8.8 UI and export requirements

Use the existing RMD visual system and accessible, mobile-usable layouts. English mode should display English labels and names where approved mappings exist; Arabic mode must handle RTL, units and mixed numbers correctly.

For executive outputs, use concise findings, evidence, risk, action and owner. Export only formats actually implemented and tested in the repository. A request for PDF, Word, PowerPoint, HTML or video is an output requirement, not proof that a working exporter exists. Voice input/output is a separate capability requiring real device and language checks.

### 8.9 Proposed implementation sequence

| Phase | Main work | Completion evidence |
| --- | --- | --- |
| 1. Inspect and align | Read repository guidance, locate AI/auth/evidence patterns and confirm scope | Architecture map and specific implementation plan |
| 2. Ingest knowledge | Add this pack, canonical source metadata and retrieval | Correct source selection and evidence labels |
| 3. Add reliable calculations | Versioned schema parsing and KPI registry | Match CALC-01 on the original synthetic fixture |
| 4. Build the workflow/UI | Query, sources, filters, draft findings and action links | English/Arabic interaction checks in actual routes |
| 5. Evaluate | Run Appendix D cases and relevant repository tests | Recorded results, defects and untested limits |
| 6. Pilot and improve | Limited authorised use, reviewer feedback and benefit baseline | Evidence of useful decisions and manageable errors |

A 90-day academic plan may group these phases across approximately days 1-15, 16-30, 31-60 and 61-90. This is a planning illustration, not a funded RTA schedule or a course deadline.
