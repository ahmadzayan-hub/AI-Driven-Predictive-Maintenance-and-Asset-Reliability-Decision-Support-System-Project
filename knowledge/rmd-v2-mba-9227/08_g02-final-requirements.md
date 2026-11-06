## 08. Final requirements recorded in the presentation
<!-- kb: domain=mba.9227.g02; limits=academic_case|not_rmd_operational_rule -->


Source: S05, slide 17. The wording below preserves the substantive requirement in concise form. Inspect the final Section 03 source for implementation-level wording and acceptance details.

| ID | Requirement | Priority | Originating gap |
|---|---|---|---|
| R1 | Run the at-risk rule daily and at carrier handover using state-specific limits | Must | Detection |
| R2 | Create one case per at-risk order with owner, due date and status | Must | Ownership |
| R3 | AI drafts in Brazilian Portuguese using only order ID, first name, dates and reason | Must | Communication |
| R4 | A named person approves, edits or rejects every message before sending | Must | Governance |
| R5 | Send from a monitored mailbox with approved templates and retain the message ID | Must | Communication |
| R6 | Record action, approver, time and outcome in a source Power BI can read | Must | Logging |
| R7 | Refresh pilot KPIs daily and alert when the late rate spikes | Should | Detection |
| R8 | Provide access control, audit trail, vendor data agreement and DPO LGPD sign-off | Must | Governance |
| R9 | Create a seller-chase task when handover was late | Must | Ownership |
| R10 | Request faster shipping within a per-order cost cap | Should | Ownership |
| R11 | Accept carrier tracking events by API in Phase 2 | Should | Data |
| R12 | Hold the satisfaction survey while a delay case is open | Could | Communication |
| W1 | Complaint and review triage is outside this pilot and belongs to a later phase | Won't in pilot | Scope |

Count: **8 Must, 3 Should, 1 Could, plus 1 Won't**.

The presentation identifies R1 to R6 as the steps modelled in the Zapier demonstration. That does not prove complete production fulfilment of every requirement, including daily execution, case ownership, failure recovery or security. Confirm the actual implementation and requirement-to-test links.

Portuguese support and LGPD handling were used as pass/fail filters in the academic tool evaluation. The handover records those project decisions; it does not provide current legal advice or a compliance certification.

An updated traceability matrix should contain: requirement ID, authoritative source/version, business rationale, implementation location, test ID, evidence locator, result date and unresolved gap. Do not claim that such a complete matrix was inspected here.
