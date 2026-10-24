# Read-only hosted column-grant preflight

Date: 2026-10-24. Status: Proposed for owner-reviewed release.

## Context

The backend-only startup validator checks table ACLs, but PostgreSQL stores
column ACLs separately. Revoking table permissions does not clear column grants,
so a clean table check can miss effective direct-client access.

## Decision

Add SELECT-only checks for explicit PUBLIC column ACLs and effective
anon/authenticated privileges through has_column_privilege. Include SELECT,
INSERT, UPDATE and REFERENCES, and non-dropped user columns. Report only
application table/column names and refuse startup without changing permissions.
Custom roles are rejected only when they give a client effective inherited
access; unrelated relations and standalone backend roles remain untouched.
This follows the existing effective-INHERIT boundary, not SET ROLE-only paths.

Do not edit the reviewed catch-up migration or historical migrations. This is
not a replacement for the operator's pre-migration ACL review: that unchanged
SQL does not reject column grants itself. Do not revoke a discovered grant
silently or widen a service role. No new dependency or credential is required.

## Verification and release limits

Extend existing synthetic catalog and transactional disposable PostgreSQL tests.
Exercise each supported column privilege for PUBLIC and both client roles,
inherited custom access, permitted backend-only access and unrelated tables.
The separate single-user PostgreSQL17 rehearsal scripts have matching fixtures.
CI uses its existing disposable PostgreSQL version; it is not the current
provider's restore drill.

Local sparse-source unit checks passed. PostgreSQL binaries and psycopg2 were
unavailable locally, so no real SQL execution or complete suite is claimed.
Exact-head CI, current-data backup/restore, identity/tenant acceptance and
production approval remain required. No production data or grants were changed.
