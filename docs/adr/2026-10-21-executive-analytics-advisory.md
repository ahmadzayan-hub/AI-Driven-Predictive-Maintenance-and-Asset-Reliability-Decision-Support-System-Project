# Executive Analytics Advisory Group decision brief

Status: accepted for implementation, 21 October 2026.

## Problem

The owner found the “Executive evidence brief” too technical and asked for the
AI-Driven Predictive Maintenance and Asset Reliability Decision-Support System,
covering condition, failures, work orders, downtime and economic impact, in an
Executive Analytics Advisory Group voice. The assigned CSV, analytics workbook
and dictionary are the analytical basis; the publication is context rather than
proof of new findings. The approved master must remain unchanged.

## Decision

- Lead the dashboard briefing and both document formats with the decision
  recommendation, domain scorecard and proposed accountable review roles.
  Keep scope, metadata, detailed KPI definitions and calculations available
  after the decision material. The product's full title replaces the generic
  document title. English and Arabic retain equivalent content.
- Compute domain totals from the controlled KPI's measured population and
  numerator. Show measurement coverage and explicit calculation references.
  Condition is the mean of finite recorded condition scores in the selected
  scope, without a health threshold or assumed scale direction. Missing values
  remain unavailable; observed totals without approved targets remain neutral
  and carry text status. Existing assessed KPI colors remain unchanged.
- Separate recommendations from actions: roles and decision gates are proposed,
  no staff are assigned, no approvals change and no maintenance is authorized.
- Show the required source roles and the limits of their verification. An
  arbitrary run cannot certify the approved master's identity, workbook
  reconciliation or dictionary sign-off. Those checks remain pending unless
  separately documented in a source-specific review. Do not infer certification
  from a file name, a successful run or a publication's assertions.
- Keep publication narrative, newly computed selected-scope aggregates and
  stored whole-run findings distinct. Model cards do not by themselves establish
  forward prediction. Require valid identity, feature timing, horizon and
  forward validation before operational use.
- Preserve the approved files. Transformations belong in a documented analytical
  copy or Power Query workflow. A material business-rule issue records the rule,
  evidence and decision impact and goes to instructors before scenario or source
  changes. This feature reads data only and does not silently revise values.

## Source-specific acceptance

The owner supplied a local course folder. A private, reproducible review copied
the assigned CSV byte-for-byte, hashed the source files, compared workbook cells,
checked dictionary coverage and independently reproduced the supplied KPI
summary. The private issue register distinguishes numeric reproduction from
business-definition acceptance and future-prediction validity. Course data,
publication content, personal details and the review artifacts stay outside Git.
No instructor decision is assumed and no message is sent on the owner's behalf.

## Validation and limits

Synthetic tests cover scope, missing readings, source immutability, evidence
links, neutral totals, bilingual framing and document order. Existing snapshot,
authorization and export-direction contracts still apply. Browser checks exercise
filtered documents, drill-through, Arabic RTL, print and stale-snapshot recovery.
Exact outcomes are recorded only in README.md. This change neither trains a new
model nor deploys production.
