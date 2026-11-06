## 01. Evidence model and scope
<!-- kb: domain=meta.evidence -->


### 01.1 Knowledge domains

| Proposed namespace | Intended content | Boundary |
|---|---|---|
| mba.9227.course | Course identity, verified briefs, learning preferences and course control | Private academic context; no invented grading rules |
| mba.9227.theory | Original explanations of BI, analytics, AI and decision frameworks | Distinguish textbook concepts from added managerial applications |
| mba.9227.g02 | Olist case, datasets, requirements, thresholds, workflow and evidence history | Academic parcel-delivery domain only |
| mba.9227.individual | Existing customer-churn report and assignment constraints | Preserve the individual assignment's AI-use restrictions |
| rmd.product | User-requested product behaviour and dated technical history | Requirements and history do not establish current functionality |
| rmd.operations | Future authorised operational sources | This handover does not populate official operational rules |
| research.miyaar | Separately labelled synthetic research context, if later supplied | Never treat synthetic results as actual RTA performance |
| owner.preferences | Relevant language, writing and coaching preferences | Exclude unnecessary personal details from general users' retrieval |

These are proposed logical categories. They do not imply that RMD V2 currently implements namespaces, a particular database or a retrieval engine.

### 01.2 Evidence labels

| Label | Meaning |
|---|---|
| USER_INSTRUCTION | Direct instruction or preference supplied by Ahmed |
| DOCUMENT_VERIFIED | The cited document was inspected and contains this statement |
| DOCUMENT_REPORTED_RESULT | A document reports an empirical or technical result; its underlying data or execution was not reproduced |
| HISTORY_REPORTED | Available conversation history reports the statement; the primary source was not rechecked |
| ARITHMETIC_CHECKED | Arithmetic was recomputed from stated figures, without independently verifying the input dataset |
| PROPOSED_APPLICATION | New design or application proposed in this handover |
| PENDING_CONFIRMATION | Required source, definition, approval or current state is unavailable |
| SUPERSEDED | Preserved for correction history and excluded from current-answer retrieval |

Do not collapse DOCUMENT_VERIFIED and DOCUMENT_REPORTED_RESULT into a single claim that the real system has been verified.

### 01.3 Source priority and conflicts

For academic work, use: professor and applicable brief/rubric; official course materials and feedback; textbook and assigned readings; official templates; current peer-reviewed or authoritative primary sources; then credible professional sources. [S01]

For RMD operations, applicable authorised operational documents and current system evidence govern their own domain. An MBA brief does not establish RTA policy. A public product page does not establish the organisation's deployed capability.

When sources conflict:

1. Identify the exact disputed statement, domain, source dates and versions.
2. Prefer applicable authority, not merely whichever text is newest.
3. Preserve the earlier value as superseded when the correction is established.
4. Keep unresolved conflicts visible, with the evidence needed to resolve them.
5. Do not fill a missing requirement with plausible wording.
