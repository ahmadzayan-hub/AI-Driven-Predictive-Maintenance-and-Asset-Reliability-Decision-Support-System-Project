# Organization-scoped maintenance work with explicit authorization

Date: 2026-10-21
Status: Accepted

## Context

The SaaS comparison found that analytics stopped before assigned maintenance
work and repair outcomes. The owner's request to implement the assessment
authorizes a pilot operational layer. It does not authorize external CMMS
actions, production deployment, or claims of demonstrated customer value.

Personal runs are currently owned by managed identity subjects. Treating a
new organization membership as ownership of all members' previous analyses
would silently disclose their data. Report publication approval also has a
different scope from authorizing someone to perform maintenance.

## Decision

Add organizations, explicit managed-subject memberships, sites, and a stable
asset register. Asset identity is the organization, source system and external
identifier; importing duplicate identities or foreign site references fails
atomically. Registration is an explicit declaration of master-data identity,
not an inferred identifier created from an analysis row number.

Every access requires both current membership and the existing platform
permission. Platform administration does not imply organization membership.
Owners manage members, sites and assets; managers and owners can authorize
work when their platform principal also has approval permission. Technicians
can progress their own assigned work; viewers can read. The last owner
cannot be removed. A member with open assigned work must be reassigned or
have that work closed before their execution role is removed.

Work starts as a draft with a registered asset, named member assignee,
controlled priority, due date, title, rationale, and server-generated source
evidence metadata. The source run must belong to the actor and have reached
review or completion. Its explicit source asset column must contain the exact
registered external identifier. Ambiguous column names and identifiers used
by multiple source systems are refused. This proves an identifier match,
not the predictive correctness or causal validity of the rationale. Only
the dataset hash, run/version metadata, selected identifier and matching
record count are shared; dataset rows and report bodies remain private.

The lifecycle is draft -> authorized -> in_progress -> completed, with
explicit cancellation available to authorized managers/owners. Publication
approval cannot transition a work order. Completion records an outcome,
notes, finite labor hours and optional part quantities. A material schedule,
priority or assignee change invalidates prior authorization. Work already
started cannot be rescheduled: cancel it and create a replacement. Closed
orders retain their immutable recorded outcome.

All mutations serialize at the organization boundary, recheck access within
the transaction and commit their audit and idempotency receipt with their
state. Optimistic versions reject stale decisions. A replay with the same
actor, key and payload returns its original response; reusing the key for
different input fails. Import batches are transactional. Record counts and
input lengths are bounded. The initial queue is bounded and discloses any
truncation; the authorized export contains the full organization's records.

Interoperability uses a versioned JSON contract. Importing work creates
drafts and revalidates the current actor's source evidence. Imported state,
authorization, outcome or audit claims are never accepted as executed work.
Exporting or importing makes no outbound request to a CMMS, model or vendor.

All tables are registered with backup and restore ordering. Personal erasure
deletes sole-member organizations and their operational records, including
prospective-validation trials. Shared business records and original actor
identifiers remain organization records, explicitly reported as retained;
the erased subject's membership and replay receipts are removed. The final
shared owner must transfer ownership first, and open assigned work must be
reassigned or closed. The database deletion is atomic; external backups,
downloaded exports and synced copies retain the existing erasure caveats.
Worker heartbeat metadata is service state and is not attributed to a person.

## Consequences and limits

This implements an internal pilot work queue and master-data contract. It is
not a full CMMS replacement: inventory purchasing and valuation, preventive
maintenance scheduling, mobile offline execution, directory provisioning,
automated invitation delivery and authenticated vendor writeback remain
separate integrations. A part quantity records consumption reported by the
technician; it does not decrement an inventory balance. A managed subject
grant is an owner-entered identifier, not verification against a directory.
Local identity mode remains a single local owner, not a hosted identity test.

Original actor audit identifiers and shared outcome notes are deliberately
retained when a member leaves. An organization-level retention/deletion policy
and reviewed legal basis are still required before real customer onboarding.
Erasure should run during a controlled maintenance window with active intake
stopped; this change does not establish global account suspension across every
pre-existing personal-run writer. No customer uptime or model efficacy is
claimed by unit or synthetic operational tests.

## Validation

`tests/test_operations.py` covers platform/membership intersection, tenant and
personal-run isolation, exact evidence identity, draft-only publication,
explicit authorization and completion, last-owner and assignment protection,
stale writes, two-connection concurrency, replay, bounded and atomic imports,
backup restoration, erasure and the HTTP/localization boundary. Existing
backup and erasure tests exercise compatibility. Optional PostgreSQL checks
require the configured test database and must be reported separately.

API contract: [maintenance operations](../MAINTENANCE_OPERATIONS.md).
