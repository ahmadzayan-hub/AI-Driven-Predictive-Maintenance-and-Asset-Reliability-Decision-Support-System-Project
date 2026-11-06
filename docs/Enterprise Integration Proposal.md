# Enterprise integration proposal: one read-only source

Date: 6 November 2026 · Status: Proposed, not built, not connected · Owner brief, Phase 6

## Recommendation

Connect one source first: a scheduled, read-only export of **work-order and failure history**
from the organisation's own maintenance management system (CMMS or EAM). Use the connector
already in the product (`server/connectors.py`, ADR 0034). No new integration code is needed
to start, and nothing is written back to the source.

This source is chosen because every reliability feature already reads it. The field contract
needs `Asset_ID`, `Record_Date` and `Failure_Count`, with criticality and cost optional. The
Weibull fit, the risk ranking, its backtest and the work-order evidence check all read those
columns. A sensor or SCADA feed would need a new streaming path and a feature-timing model
that do not exist. A finance or ERP feed adds cost columns, but does not say when assets fail.

RMD and RTA systems are excluded, as the brief requires.

## How it works with what exists

| Step | Existing control |
| --- | --- |
| The source publishes a CSV, Excel or JSON export at an `https://` address | Connector formats; 4 MB per snapshot; 15-second fetch limit |
| The operator lists the export's host in `AGENTIC_OS_CONNECTOR_HOSTS` | Fetches to any other host are refused; private, loopback and metadata addresses are always refused; redirects refused |
| The operator registers a credential alias in `AGENTIC_OS_CONNECTOR_CREDENTIALS`, pointing to a secret held in an environment variable | The secret is never stored in the connector, a record, a backup or an API response. The alias works only for its owner, host and port. Rotation takes effect on the next fetch |
| The connector refreshes on a schedule of 15 minutes to a week | Content-addressed: an unchanged export does nothing. A new one becomes a dataset with its previous column mapping, when that still fits |
| Each new snapshot starts the connector's analysis | It stops at the approval gate. Publishing never authorizes work. A work order is drafted by a person and authorized by another when separation is on |

The credential the source issues must be **read-only** on the source side. The connector only
issues GET requests, but the guarantee belongs to the source's own permissions, not to this code.

## What must be verified before connecting (not known here)

1. Whether the source system can publish a scheduled export at an `https://` address, or
   offers a read-only reporting API. This must be checked with its administrator. No vendor
   API is assumed in this proposal.
2. That the export holds no personal data beyond what is needed. Technician names are
   personal data: drop them at the source, or pseudonymise them.
3. The export's size. Above 4 MB, either filter it at the source (for example a rolling
   window) or decide on a larger limit. A larger limit is a separate decision.
4. How failures are coded: which work-order types or failure codes count as a failure, so
   that `Failure_Count` means the same thing every time.
5. Where the data may be held. The hosted database region must match the organisation's
   data-residency rules.

## Rollout, each step reversible

1. **Synthetic rehearsal:** the same export shape, generated, served from `AGENTIC_OS_CONNECTOR_FIXTURES` on a local or test deployment. This
   proves mapping, schedule, analysis and approval without real data. No owner approval
   needed.
2. **One-off manual upload** of a real, de-identified export by the owner. This checks the
   field contract and failure coding. No connector yet.
3. **Scheduled read-only connector** on a non-production deployment, at the daily interval.
   Needs the owner's approval, the host on the allowlist and a read-only credential from the
   source's administrator.
4. **Production** only with the owner's explicit approval, after steps 1 to 3 and a review of
   the first month's refresh log.

Removing the host from the allowlist, or deleting the credential alias, stops every fetch at
once. Snapshots already taken stay as datasets and can be deleted, along with their audit.

## Risks

| Risk | Control |
| --- | --- |
| Credential leakage | Never in Git, records or backups; an alias bound to its owner, host and port; rotate at the source |
| Personal data in the export | Removed at the source before connection; raw rows are never sent to a model |
| Failure coding drifts between exports | The mapping is re-checked on each snapshot and the refresh says when it no longer fits; drift is reported |
| Over-trust in the ranking | The backtest and the shadow ledger state limits; publishing never authorizes work; separation of duties |
| Cost | No new service; one fetch per interval; the analysis runs on the existing worker |

## Owner decisions needed

1. Which maintenance system, and who administers it.
2. Approval for step 3 (non-production connector) and, later, step 4 (production).
3. Whether to raise the 4 MB snapshot limit, if the export cannot be filtered.

Write-back of any kind (work-order creation in the source system, status updates) is out of
scope. It would need its own decision record, the source owner's authorization and
separation of duties on every write.
