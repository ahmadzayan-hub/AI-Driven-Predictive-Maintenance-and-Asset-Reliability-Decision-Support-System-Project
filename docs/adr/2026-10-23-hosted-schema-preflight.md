# Hosted startup validates reviewed schema, never migrates it

Date: 2026-10-23 · Status: Proposed for owner-reviewed release

## Context

The API and worker previously called a PostgreSQL constructor that created,
modified and migrated tables before serving requests. The RMD service also
ran its own DDL and permission pass. Merely adding an existing DATABASE_URL
could therefore write to production without a reviewed migration. A healthy
connection and an edited historical SQL mirror are not proof of a complete
current schema. The existing hosted candidate has only the older core shape;
no deployment target is selected by this decision.

## Decision

API and worker PostgreSQL entry points explicitly select `schema_mode="verify"`.
The constructor and subsequent RMD service initialization perform SELECT-only
catalog checks, refuse missing or incompatible tables/columns/keys, require
backend-only RLS/privilege boundaries and the matching schema version, and
close the pool on failed preflight. They never create objects, assign old row
ownership, revoke/grant privileges, or migrate as a side effect of startup.

The portable expected contract is derived from the current storage definitions
in an isolated in-memory SQLite database. PostgreSQL checks include types and
nullability, primary/unique/foreign keys (including target namespace and
non-cascading behavior), unfiltered valid unique indexes, enabled RLS and
absence of effective anon/authenticated or explicit PUBLIC table grants.
This is schema compatibility, not proof of tenant authorization or data quality.

Local SQLite retains zero-setup behavior. Direct library/operator initialization
retains `schema_mode="migrate"` for compatibility with isolated test tools; it
is a mutating operation and must never be used to bypass production approval.
Its existing initialization now applies the backend-only RLS/revoke boundary
to every application table, consistent with the reviewed SQL mirror. Runtime
entry points do not expose an environment flag to opt back into that DDL.

A new additive, transactional catch-up SQL file is prepared separately for
operator review. Historical SQL migrations and existing records are preserved.
Ownerless legacy data, incompatible drift or a newer marker is not guessed
into compliance. Backup/restore rehearsal, target selection, schema application,
existing credential configuration and deployment each retain their approval gate.

## Verification and limitations

Synthetic tests exercise missing objects, column/key drift, RLS/grants, version
mismatch, non-mutating constructor/RMD initialization, pool cleanup and unchanged
local startup. A disposable PostgreSQL test enforces read-only sessions for the
real constructor and RMD preflight. Isolated catch-up tests are documented in
the release runbook. No production database was modified or connected by the
application, and no live provider was called.

Catalog access requires the runtime database role to be able to inspect its
schema; a read error fails startup. Application roles remain server-side
managed-identity/tenant checks, not direct PostgREST access. Production identity,
worker hosting, current-data restore, real-device and domain acceptance remain
separate. Roll back code only to another verify-only version; reverting to the
old startup behavior restores the unreviewed-DDL risk.

## Platform reference

[Supabase's API security guide](https://supabase.com/docs/guides/api/securing-your-api)
distinguishes grants from RLS and documents public-schema defaults. Both are
checked here; the existing backend-only architecture is preserved rather than
adding direct client access. The current [changelog](https://supabase.com/changelog)
was checked on the decision date; no new Supabase SDK or API feature is introduced.
