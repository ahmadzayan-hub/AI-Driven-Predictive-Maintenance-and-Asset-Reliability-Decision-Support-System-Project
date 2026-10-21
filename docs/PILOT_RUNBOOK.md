# MaintainX and maintenance validation pilot

Recommended scope: one facility, explicitly selected pumps and motors, a
maintenance planner, an authorized supervisor and an outcome reviewer. Verify
that the facility actually has suitable asset/work history before enrolling it.
The software adds a maintenance action loop and prospective evidence ledger;
an account, production deployment and predictive results are not included.

## 1. Configure and prove execution

Use managed identity for a shared deployment. Configure the API and separate
worker with the same database and model settings, and set
`AGENTIC_OS_RUN_EXECUTION=worker` on the API. Supervise both processes. For the
local demonstration, `python scripts/local_runtime.py start --worker` selects
worker execution and starts its child worker. The documented existing local
model must be installed. Client mode remains a compatibility option.

In worker mode the browser polls persisted run state. The advance endpoint
returns 202 promptly; refresh/reconnect does not replay a long model POST.
`/api/health` reports execution mode and bounded worker heartbeat freshness.
An absent or stale worker is a visible readiness failure, not proof that a
model is slow. A heartbeat is not a hosted availability measurement.

Select Operations and create an organization, site and asset register. Add
known managed identity subjects with the least role needed. Organization
membership and managed token permissions both apply. Test a different
organization's negative access before any customer data enters the service.
See [maintenance operations](MAINTENANCE_OPERATIONS.md) for roles and API fields.

## 2. Configure the first read-only source

MaintainX documents bearer authentication and places REST API access on its
Premium plan. Verify entitlement and the exact customer's API permissions before
connecting; no purchase is made by this runbook. Configure the following in the
operator's secret manager/environment, never in Git or chat:

```text
AGENTIC_OS_CONNECTOR_HOSTS=api.getmaintainx.com
AGENTIC_OS_CONNECTOR_CREDENTIALS={"maintainx-pilot":{"owner":"MANAGED_SUBJECT","host":"api.getmaintainx.com","token_env":"MAINTAINX_API_TOKEN"}}
MAINTAINX_API_TOKEN=<operator-supplied secret>
```

The credential alias is not the token. An alias is restricted to the configured
subject and exact HTTPS host/port; it grants no organization membership.
Use an OS-protected private output directory outside the repository. Run:

```text
python scripts/maintainx_sync.py assets --owner MANAGED_SUBJECT --credential maintainx-pilot --output PRIVATE_PATH/assets.json
python scripts/maintainx_sync.py workorders --owner MANAGED_SUBJECT --credential maintainx-pilot --output PRIVATE_PATH/workorders.json
```

The same snapshot path enables incremental reads. Boundaries are explicit:
page/record/byte/deadline limits fail without committing a partial snapshot.
The adapter uses the current OpenAPI cursor contract, ignores nextPageUrl,
deduplicates source IDs and overlaps the previous watermark. Unexpected schema
or pagination changes stop ingestion. Reconcile explicitly deleted records;
missing records and comment-only updates do not imply deletion or freshness.
Inspect `checked_at` separately from `watermark`: recent polling does not make
old source records new. Agree the acceptable source schedule with the operator.

For initial registration, supply the reviewed site, location, asset selection
and criticality, for example with placeholders replaced by real reviewed values:

```text
python scripts/maintainx_sync.py assets --owner MANAGED_SUBJECT --credential maintainx-pilot --output PRIVATE_PATH/assets.json --site-id INTERNAL_SITE --location-id 7 --asset-ids 101,102 --criticality high --import-output PRIVATE_PATH/reviewed-assets.json
```

Review and import the separate JSON through Operations. It creates assets;
it is not a silent update/restore of existing records. Split mixed-criticality
selections into reviewed batches. A CLI lock file prevents overlapping writes.
After a crash, confirm its recorded process is stopped before removing only
that output's lock. Snapshot and import files are individually atomic; if the
second write fails, retry from the committed snapshot to regenerate the payload.

Before live acceptance, exercise an expired credential, duplicates, a late
update, explicit deletion, schema drift and an interrupted multi-page fetch.
The shipped synthetic tests establish local behavior only. This adapter does
not write remote work orders or continuously reconcile their completion.

## 3. Close a reviewed maintenance action

Analyze authorized data containing the registered external asset ID. In
Operations draft a work order from the finished analysis and source column;
review its rationale and the metadata shared with organization members.
A supervisor separately authorizes maintenance. The assignee starts it and
records actual outcome, notes, labor and parts. Publication approval has no
authority to trigger a repair. Material reassignment/rescheduling requires
new authorization. Inspect the audit and export after completion.

Use this first with explicitly labelled synthetic records in an isolated test
store. Production completion must come from actual work and supporting records.
Keep MaintainX as the source of operational truth until an authorized bidirectional
contract, conflict policy and reconciliation procedure have been implemented
and proven. Current snapshots and local work records need operator reconciliation.

## 4. Register shadow validation before prediction

Use Operations' validation panel to register model version, training cutoff,
comparison baseline, failure/cohort definitions, probability threshold and
warning horizon. Agree failure costs and adjudication criteria with the domain
reviewer before collecting results. The server fixes registration/prediction
time and refuses overlapping windows for one asset in a trial.

Record model and baseline probabilities before the operating interval starts.
Only after the full horizon has elapsed may an authorized reviewer attach the
failure outcome, full observation cutoff, evidence reference and optional
actionability label. Partial follow-up stays pending. Final outcomes are
immutable; corrections require a documented new trial, preserving the old one.

Review confusion counts, alert precision, registered failure-window recall,
actionable-alert precision, warning lead times, false alerts per observed
asset-month, Brier score and calibration bins. Read every denominator and
uncertainty interval. Pending outcomes are excluded from both matched models;
unregistered failures are outside this ledger's recall denominator. Repeated
asset windows are correlated, so simple Wilson intervals are descriptive and
need clustered/domain analysis for a formal study. Different actor IDs alone
do not prove independent adjudication. Do not infer savings or causal benefit
from this ledger. Export its evidence hash and records for independent review.

## 5. Hosted and commercial acceptance — still required

The readiness panel reports configuration and persisted progress. These items
require evidence supplied by their owners; none is automatically accepted:

| Owner | Required evidence before the corresponding claim |
| --- | --- |
| Deployment operator | Approved hosted release, managed identity/tenant negatives, representative load, queue latency including failed jobs, worker restart during a stage, duplicate-stage check, restore of a fresh backup, retention/erasure drill and source freshness alerts. Record workload, versions and actual results. |
| Maintenance domain reviewer | Agreed asset/failure definitions, no training leakage, later unseen windows, sufficient independently reviewed outcomes, operating exposure, false-alert/missed-event costs and limits of generalization. |
| Customer source administrator | Authorized test account, real API contract checks and observed import/reconciliation of the selected facility. Do not send credentials through chat. |
| Product/service owner and customer | Named buyer and support owner, onboarding checklist, included sites/assets/usage, escalation route, agreed support hours and terms, measured support effort, recurring use and an actual purchase/renewal decision. |

A controlled pilot can use manual invoicing; billing automation follows demand.
No price, SLA, legal acceptance, certification, customer or purchase is invented.
Offline execution and SSO provisioning remain buyer-dependent extensions; the
current UI preserves interrupted drafts in memory, not a durable offline queue.
The repository stays private until its separately documented historical-data
release gate is resolved. Work on `main` is not permission to deploy publicly.

Primary references: [MaintainX API](https://help.getmaintainx.com/build/build-with-maintainx),
[plans](https://www.getmaintainx.com/pricing),
[polling](https://help.getmaintainx.com/build/polling-for-changes),
[OpenAPI](https://api.getmaintainx.com/v1/openapi.json),
[NIST AI RMF](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/),
[Google SRE service objectives](https://sre.google/workbook/implementing-slos/).
