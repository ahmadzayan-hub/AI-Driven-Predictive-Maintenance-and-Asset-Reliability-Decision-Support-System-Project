## 0. Read this first
<!-- kb: domain=meta.handover -->


This file is the master knowledge handover for **Data Analytics for AI Business, Group 9226**, with the **Team 3 predictive maintenance and asset reliability project** and relevant RMD V2 application context. It covers the 25 supplied course files and four recovered Team 3 sources. Three book pairs are exact duplicates, leaving 26 distinct source files.

The file contains original summaries, source locators, the complete 60-field schema, recalculated results, a conflict register and a proposed implementation contract. The original books and all 5,000 CSV records remain in the linked source files. This is a comprehensive project knowledge pack, not a verbatim reproduction of every source page.

Use this document as reference knowledge. Loading it into Claude Code provides context; it does not fit a prediction model or automatically make the deployed RMD V2 assistant retrieve it. Application ingestion, calculators, permissions and evaluation must be implemented and verified separately.

### 0.1 Essential findings the receiving AI must preserve

1. **The dataset is synthetic.** None of its monetary values, failures, incidents or asset scores represents verified RTA performance.
2. **Original asset identity is defective for longitudinal analysis.** Every one of the 180 nominal Asset_ID values appears with multiple asset classes, industries, manufacturers and sites. Each ID has only one unique record date. There are 4,820 excess repeated Asset_ID plus Record_Date keys. A valid Record_ID does not make Asset_ID a reliable physical-asset key.
3. **Aggregation changes the answer.** The full-dataset availability calculation is 96.9625%, while the mean stored record availability is 96.7798%. Both can be calculated, but their definitions differ.
4. **The service-target met rate is 46.12%.** The mean SLA_Compliance_Score is 75.782986%; it is a capped ratio score, not the share of observations meeting the target.
5. **MTTR requires a definition decision.** Total downtime divided by failure count is 11.9881 hours per failure. The stored MTTR_Hours field averages 11.7087 hours and does not reconstruct downtime. Use the former as a clearly labelled downtime-per-failure proxy until repair-time semantics are confirmed.
6. **The workbook is a static source snapshot.** Its six worksheets contain no Excel formulas. All 300,000 Dataset body cells are text, and the first field name contains a byte-order-mark character.
7. **There are five industries**, although one publication passage says four.
8. **Course assessment evidence exists, but conflicts remain.** Lecture 8 allows Power BI, AI-directed analytics or both; Lecture 9 specifies WWI and a Live Decision Dashboard. The Team 3 report proposes the asset-reliability project. No supplied evidence resolves the final applicability of those pathways.
9. **Source claims of approval do not establish independent approval.** The publication and workbook contain approval labels, but those labels do not prove instructor acceptance, validated physical-asset histories or suitability for operational deployment.
10. **Historical software and model claims require current evidence.** Prior chat summaries about MIYAAR and RMD V2 are retained as dated context. This handover does not certify a current branch, deployment, model or connector.

Evidence: SRC-11 p.18; SRC-17 p.7; SRC-26 pp.21-23; SRC-27 §§1,3,5,11; SRC-28; SRC-29; CALC-01; HIST-01 to HIST-03.

### 0.2 Navigation

- Section 1: scope, evidence and confidentiality.
- Section 2: user, project and course control.
- Section 3: business decision and Team 3 project.
- Section 4: complete dataset schema and ingestion rules.
- Section 5: verified calculations and interpretation.
- Section 6: data-quality findings and repairs that need a separate version.
- Section 7: modelling and maintenance prioritisation.
- Section 8: proposed RMD V2 capability and implementation contract.
- Section 9: Claude Code handover prompt and loading guidance.
- Section 10: historical project context.
- Section 11: open decisions, next actions and maintenance of this knowledge.
- Section 12: source register, canonical copies and reproducibility.
- Appendix A: core course knowledge and business applications.
- Appendix B: practical lectures, assessment evidence and Team 3 readiness context.
- Appendix C: reference-book knowledge and topic/page lookup.
- Appendix D: application acceptance cases and evidence-aware answer contract.
