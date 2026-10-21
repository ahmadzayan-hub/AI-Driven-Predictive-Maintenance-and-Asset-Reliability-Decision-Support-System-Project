# Prospective maintenance validation and first CMMS adapter

Date: 2026-10-21. Status: accepted for implementation; external acceptance remains open.

## Problem and decision

The competitive assessment found that retrospective analytics, report approval
and a successful demo cannot establish actionable maintenance predictions or an
operating customer service. Add an organization-scoped prospective ledger and
a bounded, read-only MaintainX adapter. The proposed first pilot is reviewed
pumps and motors at one facility; this is a recommendation, not an enrolled
customer or an assertion that their data supports prediction.

The ledger registers an immutable model version, declared training cutoff,
baseline, failure/cohort definitions, horizon and threshold before predictions.
Predictions use server timestamps, registered assets and nonoverlapping windows
per asset. Both model and baseline probabilities are recorded together.
Creation and prediction retries are idempotent; changed retry payloads and stale
revisions fail. Authorization is checked again inside the organization's
transaction, the same boundary used by maintenance mutations and erasure.

Only a matured window with full declared follow-up and an evidence reference
can receive an immutable adjudication. Pending windows are excluded from both
model and baseline metrics, never treated as successful nonfailures. Results
include denominators, Wilson intervals for proportions, warning lead time,
false alerts per observed asset-month, Brier score and calibration bins.
Failure-window recall describes registered windows, not all fleet failures.
Repeated asset observations are not independent trials; the simple intervals
do not model clustering. A different adjudicator identity does not establish
independence. Evidence and declared training dates require human verification;
there is no causal savings or field-validation claim.

## Source integration

MaintainX is selected for its documented REST contract. Credentials remain in
operator environment variables behind an owner/host/port-scoped alias. The
existing connector egress boundary pins DNS, requires allowed public HTTPS
destinations and refuses redirects. The adapter only performs GET requests.

The reviewed machine-readable OpenAPI specifies cursor pagination for assets
and work orders. Some prose still describes asset offsets; an unknown response
contract fails closed instead of guessing. Work orders request `expand=asset`
and preserve nullable `asset.id`; an undocumented `assetId` is not accepted.
Filters stay constant across pages, records deduplicate by ID and newest
timestamp, and successful collection advances the watermark with a five-minute
overlap. This overlap does not guarantee recovery of arbitrarily late records.
Absence does not imply deletion; only explicit tombstones are recorded. Comments
need separate reconciliation because they do not necessarily advance updatedAt.

The private CLI snapshot is locked across read, fetch and replacement. Unique
temporary files and atomic replacement preserve the old file on failure. Locks
are not automatically stolen after crashes; an operator verifies the owning
process before recovery. A separate asset import requires explicit source
location, selected asset IDs, internal site and reviewed criticality. Remote
work-order snapshots are review evidence, not automatically authorized local
repairs. Outbound CMMS writes and credentials are not supplied by this change.

## Alternatives and evidence

Reusing retrospective scores would hide time leakage and incomplete follow-up.
A complete replacement CMMS or general integration marketplace would broaden
scope before one pilot workflow is verified. The chosen adapter and ledger use
the standard library and the existing storage, identity and API contracts.

Regression coverage includes tenant isolation, permission intersection,
prospective chronology, overlap, repeat requests, immutable outcomes, matched
baseline denominators, backup preservation, source drift, partial pagination,
asset expansion and concurrent snapshot admission. Browser tests exercise the
actual maintenance authorization flow; canonical results belong in README.
The [pilot runbook](../PILOT_RUNBOOK.md) names external release gates separately.

Primary references, reviewed 2026-10-21:

- [MaintainX API guide](https://help.getmaintainx.com/build/build-with-maintainx)
- [MaintainX OpenAPI](https://api.getmaintainx.com/v1/openapi.json)
- [MaintainX polling guidance](https://help.getmaintainx.com/build/polling-for-changes)
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) for deployment-relevant evaluation and monitoring, not certification.

Revisit this decision if the live contract differs, recovery cannot preserve
provenance, the cohort lacks sufficient outcomes, or operators require a
different source or offline work execution.
