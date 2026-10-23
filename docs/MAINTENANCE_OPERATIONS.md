# Maintenance operations pilot contract

The Operations view adds shared organizations and a maintenance queue beside
personal analyses. Data and audit records persist in the configured store.
Use the managed identity provider for any shared hosted deployment. In local
mode there is one local owner; switching organizations is not a sign-in flow.

## Start an organization

Create an organization, a site with an explicit code, then register each asset
using its stable external identifier and source system. An organization owner
can add a colleague's managed identity subject and choose owner, manager,
technician or viewer. The existing platform role still applies: an
organization owner whose managed token permits only reading cannot write.
Grants do not send invitations or search an external directory.

An owner manages membership, sites and assets. Owners/managers authorize
maintenance. Technicians start and complete assigned work. The interface
shows only permitted controls, and the API enforces the same boundary.

## From analysis to outcome

1. Finish a personal analysis containing the registered asset's real external
   identifier. Review its evidence and limitations.
2. Draft a work order referencing that run, the exact source asset column and
   registered asset identifier. Supply the proposed work, rationale, priority,
   assignee and due date. This deliberately shares source metadata with the
   organization; it does not share the dataset or grant access to the run.
3. An authorized owner/manager explicitly authorizes the maintenance work.
   Publishing the report does not perform this step.
4. The assignee starts work and records the actual outcome, notes, labor hours
   and any parts used before completing it. These are observed operational
   records; they are not proof that an AI prediction was accurate.

Rescheduling or reassigning authorized work returns it to draft. Started
work must be cancelled and replaced if its approved execution details change.
Closed orders cannot be rewritten. The audit records the original managed
subject of every action. An open assignment must be handled before removing
its member's execution role.

The queue prioritizes active work, criticality/priority and due date. Its
bounded initial result includes `work_order_count` and
`work_orders_truncated`; use the export to inspect the full record set.

## HTTP contract

Base: `/api/operations`. All routes require the existing principal. Add
`?language=en` or `?language=ar` for domain error messages. Domain errors use
`{"detail":{"code":"stale_version","message":"..."}}`; invalid request
schemas use FastAPI validation responses. Clients should translate validation
recovery text. Errors do not disclose whether another tenant owns a resource.

| Method and path | Request / result |
| --- | --- |
| GET `/organizations` | `{organizations:[...]}` for current memberships |
| POST `/organizations` | `{name,idempotency_key}`; returns organization |
| GET `/organizations/{org}/overview` | Organization, principal subject, permissions, members, sites, assets and bounded work queue |
| POST `/organizations/{org}/members` | `{subject,role,expected_version,idempotency_key}`; version is the organization's version; `role:"removed"` removes a membership |
| POST `/organizations/{org}/sites` | `{code,name,idempotency_key}` |
| POST `/organizations/{org}/assets` | Asset fields below plus `idempotency_key` |
| POST `/organizations/{org}/work-orders` | Draft fields below |
| GET `/organizations/{org}/work-orders/{id}` | Work order, evidence metadata, completion and audit |
| PATCH `/organizations/{org}/work-orders/{id}` | `{expected_version,idempotency_key,status?,assignee?,due_date?,priority?,completion?}` |
| GET `/organizations/{org}/export` | Versioned JSON export, with `external_actions_performed:false` |
| POST `/organizations/{org}/import/assets` | `{schema_version:1,idempotency_key,assets:[...]}`; atomic asset registration |
| POST `/organizations/{org}/import/work-orders` | `{schema_version:1,idempotency_key,work_orders:[...]}`; atomic draft creation, never external execution |

Asset fields:

```json
{
  "site_id": "existing-site-id",
  "external_id": "PUMP-001",
  "source_system": "plant-master-register",
  "name": "Feed pump",
  "criticality": "high"
}
```

Draft fields (illustrative identifiers; use actual authorized records):

```json
{
  "asset_id": "registered-asset-id",
  "title": "Inspect bearing",
  "rationale": "Engineer-reviewed evidence warrants inspection",
  "run_id": "actor-owned-finished-analysis",
  "asset_column": "Asset",
  "source_asset_id": "PUMP-001",
  "priority": "high",
  "assignee": "managed-subject-id",
  "due_date": "2026-11-01",
  "idempotency_key": "client-generated-distinct-request-key"
}
```

Priority and criticality accept `low`, `medium`, `high` and `critical`.
Work status is `draft`, `authorized`, `in_progress`, `completed` or `cancelled`.
To complete started work, include
`completion:{outcome,notes,labor_hours,parts:[{part,quantity}]}`. Parts are
optional; hours and quantities must be finite and nonnegative/positive
respectively. A work order begins at version one. Refresh after a conflict
and review the current record before issuing a new request.

Every mutation needs a distinct request key. Keep the same key and exact
payload only to retry an interrupted request. For batch work import, use
distinct keys for the batch and each draft. An unsuccessful batch rolls back
all rows, audits and receipts. Unknown fields are rejected: import cannot
inject authorization, completed status, another actor, or an audit history.

Exports are a read model, not a blind restore payload. An integration maps
exported asset fields or work draft fields back to the documented import
schema and supplies new request keys. Existing assets with the same source
identity are reported as conflicts; imports do not silently overwrite them.
Work imports require evidence belonging to the current caller and always
start as drafts. Backup restoration is the separate operator recovery path.

## Operational boundaries

No route fetches arbitrary attachments, sends data to a model, purchases
parts, contacts a technician or writes to an external CMMS. Such integration
requires a separately configured adapter and explicit authorization.
Current record and batch limits live in `server/operations.py` and the API
schemas; capacity errors are visible rather than unbounded growth.

Backups include organizations, memberships, sites, assets, work, audit and
request receipts. Personal erasure deletes sole-member organizations. In a
shared organization it removes membership and receipts while retaining
business outcomes, evidence metadata and original actor audit identifiers,
which the erasure report explicitly names. Transfer final ownership and
reassign or close open work first. Downloaded exports and prior backups
remain outside the personal erasure command's reach.

See [the decision](adr/2026-10-21-maintenance-operations.md) for validation,
retention implications and the remaining enterprise and CMMS limitations.
