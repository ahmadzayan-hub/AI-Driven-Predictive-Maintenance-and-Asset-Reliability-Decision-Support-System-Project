## 10. Zapier workflow, controls and evidence history
<!-- kb: domain=mba.9227.g02.workflow; limits=academic_case|not_rmd_operational_rule|historical_not_current_verification -->


### 10.1 Presentation-reported architecture

Source: S05, slides 23 and 24.

| Stage | Reported component | Purpose and boundary |
|---|---|---|
| Trigger | Google Sheets synthetic order row | Simulates an order arriving at carrier handover |
| Decision | Code and filter | Recompute risk from raw fields using state P75 |
| AI drafting | AI by Zapier and parser | Five permitted input fields; eight-field Portuguese output |
| Approval | Second Zap and code gate | Require approved status, named approver and current draft |
| Send | Gmail to the team test inbox | Send approved text only |
| Record | Decision_Log | Record case, approver, time, email result and audit information |

The final eight-field schema and five exact technical input keys are not included in the inspected presentation text. Do not reconstruct them by treating the older six-field draft in S07 as current. Obtain the actual parser and final workflow specification.

### 10.2 Reported controls

- Calculate-Risk recomputes the rule and ignores prefilled risk labels.
- Parse-AI-Output accepts the specified eight-field object; invalid output goes to human review.
- Sending requires APPROVED status, an identified approver, the current draft and the permitted test recipient.
- The draft must not invent dates, refunds, compensation, completed shipping upgrades or carrier/seller commitments.
- Missing or ambiguous evidence prevents unsupported external action.
- The prototype uses synthetic orders, not real customer data.

The first three controls are reported in the final presentation. The prohibition on unsupported promises and the human-review path also appear in the earlier design. No current repository code was inspected. [S05, slide 24; S07, §§5.6 to 5.8]

### 10.3 Evidence chronology

| Source/date | What it establishes | What it does not establish |
|---|---|---|
| Historical user update dated 20 September 2026 | User reported a merged contribution and 70 accepted validation checks, with corrections still needed | Current repository status or the final set of test definitions |
| Section 05 draft stored 25 September 2026 | Workflow design, guardrails and evidence checklist; implementation evidence explicitly pending | Live execution, a passed test suite or a finished traceability matrix |
| Deck reporting runs on 29 September 2026 | Zap 1 v2 and Zap 2 v1 reported on; unapproved-draft gate tested; linked synthetic run Z1-CHAIN-002 reported | Independent access to Zapier run history in this task |
| Presentation dated 6 October 2026 | Reports 144/144 automated checks and the linked run; explicitly leaves live negative/failure testing open | A fresh pass on current code or production readiness |
| This handover, 5 November 2026 | Reconciles inspected artifacts and preserves their limitations | Fresh execution, current deployment, or subsequent assessment acceptance |

The 70-check and 144-check counts are not additive. They refer to different reported stages. Also, the older user-update date precedes the case approval dates in later documents; the exact chronology needs the original repository and approval records. Do not silently repair it.

### 10.4 Clean linked run

The presentation reports the following for **Z1-CHAIN-002**:

1. A synthetic CE order had late handover and 21 days remaining against P75 21.
2. The rule flagged risk due to late handover.
3. AI generated the Portuguese draft.
4. A human approved that draft unchanged.
5. Gmail delivered the approved message to the team test inbox.
6. Case and audit information were logged.

It reports a separate live refusal of an unapproved draft. Live negative and failure-path coverage remained incomplete. [S05, slides 23, 24]

### 10.5 Earlier draft: preserve only as design history

The inspected Section 05 draft contains a six-field example:

~~~json
{
  "risk_summary": "",
  "seller_chase_message": "",
  "shipping_upgrade_recommendation": "",
  "customer_message_draft": "",
  "reason_for_recommendation": "",
  "human_review_required": true
}
~~~

**Status: historical draft schema, not the final implemented contract.** Its early-warning condition is a team-input placeholder, it still references R1 to R8, and it says execution evidence is pending. [S07, §§5.5.2, 5.6.2, 5.12, 5.15, 5.19]

Draft audit fields include order_id, automation_triggered, risk_decision, ai_draft_status, approval_status, seller_chase_status, shipping_upgrade_decision, customer_message_status, automation_timestamp and run_result. A future implementation must inspect the final audit schema, including identity and version binding, rather than copying this list as complete.

### 10.6 Supporting artifacts referenced but not inspected in the repository

| Referenced artifact | Expected role |
|---|---|
| Zapier-Workflow-Spec.md | Implementation specification |
| AI-Agent-Prompt.md | AI drafting instructions |
| test-data.csv | Synthetic test inputs |
| Test-Cases.md | Functional and control scenarios |
| Traceability-Matrix.md | Requirement-to-implementation/test mapping |
| Evidence-Checklist.md | Evidence collection record |
| Presentation-Notes.md | Speaking notes |
| Demo-Script.md | Demonstration and fallback sequence |
| SESSION_LOG.md | Section activity and decisions |
| MEMORY.md | Cross-section decisions |
| PLAYBOOK.md | Team roadmap |
| PROJECT_PROGRESS.md | Progress record |

The filenames are referenced by S07 to S09. Listing them does not prove their current contents or existence in the target RMD repository.
