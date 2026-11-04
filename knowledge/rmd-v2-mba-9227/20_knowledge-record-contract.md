## 20. Knowledge-record contract
<!-- kb: domain=rmd.product; evidence=PROPOSED_APPLICATION -->


Status: PROPOSED_APPLICATION. Adapt to the real repository's existing data model.

### 20.1 Suggested schema

~~~yaml
record_id: "g02.p75.rj"
namespace: "mba.9227.g02"
record_type: "historical_benchmark"
statement: "RJ P75 carrier-to-customer transit is 14 calendar days in the G02 presentation."
value: 14
unit: "calendar_days"
source_id: "S05"
source_locator: "Slide 29"
source_version: null
source_date: "2026-10-06"
observed_at: "2026-11-05"
document_statement_verified_at: "2026-11-05"
underlying_data_recomputed_at: null
evidence_status: "DOCUMENT_REPORTED_RESULT"
authority_scope: "G02 academic parcel-delivery benchmark"
approval_state: "not_an_operational_approval"
allowed_domains:
  - "mba.9227.g02"
disallowed_inferences:
  - "RMD maintenance SLA"
  - "Current carrier performance"
  - "Guaranteed delivery time"
supersedes:
  - "g02.p75.rj.provisional.8_days"
review_trigger: "Obtain the authoritative CSV or change the calibration dataset"
~~~

Do not mistake the inspection date for the event date or the effective date of a policy. Unknown fields remain null or Pending confirmation.

### 20.2 Record categories

Useful types include course fact, assessment rule, textbook concept, historical result, requirement, user preference, proposed application, correction, conflict and evidence gap.

Stable identifiers and a document content hash can support versioning. Importing the same version twice should not create duplicate facts. Importing an updated version should retire the correct stale record without deleting the audit history.

### 20.3 Minimal answer contract

For a material answer, return:

- The answer in the requested language.
- Applicable domain and time context.
- Source ID and specific page, slide, heading, record or cell.
- Whether the claim is reported, calculated, current, historical, proposed or uncertain.
- Missing information when it changes the decision.

Avoid unsupported numerical confidence scores. Explain evidence strength in words unless a calibrated method exists.
