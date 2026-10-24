# Reviewed hosted-schema catch-up candidate

This artifact is not permission to apply SQL, activate a database, change credentials, merge a PR, or deploy. It targets the portable application schema at merged main commit `ff2ea3f4aa60d7817a41bbe0dd42e081c196c2d3`, not a database selected by name alone.

## Scope

The existing candidate `asset-reliability-ai-saas` was inspected read-only on 23 October 2026: nine application tables exist. Their estimated row counts are not proof of emptiness. The prepared migration brings a matching old shape to the current **32-table** contract by adding 23 missing tables and five nullable columns (three on `runs`, one on `approvals`, one on `connectors`). It preserves rows and owners, creates the request-idempotency and task-queue indexes, requires existing application tables to already deny PUBLIC/anon/authenticated effective access, and fails closed without revocation if unexpected existing client grants are found. It enables RLS and revokes default client grants only after that preflight; these restricted defaults govern the new application tables too. Existing service-role privileges are not revoked or expanded. Backend authorization remains mandatory; this is not tenant RLS policy implementation or hosted identity acceptance.

The SQL file was created using the existing official Supabase CLI's `migration new` command. It does not modify or reapply previously recorded migration files. A read-only preflight rejects incompatible columns, nullability, primary/unique/foreign keys, ownership gaps, unsupported newer schema versions and conflicting named indexes. It never assigns historical rows to `local-owner`, rebuilds legacy memory, deletes an old table, grants a new user access, or changes an unrelated table. Unknown additional columns on application tables deliberately require review.

A single transaction and advisory transaction lock protect the update. Lock timeout is five seconds; statement timeout is sixty seconds. These are conservative safeguards, not a scalability benchmark. A failure requires diagnosis, not automatic retries or timeout increases.

## Review and backup gate

1. Owner confirms the exact existing project and whether it is the intended Team3 system of record. The inactive older `agentic-os` project and its users/clients remain preserved and must not be silently replaced.
2. Refresh metadata, applied migration history, application source, active clients/workers and grants. Compare the target to the reviewed shape. Inspect custom triggers, policies and application-specific extensions before approval; this script does not certify those.
3. Operator approves an owner-controlled encrypted backup location and a full database/schema/role-grant export or existing provider backup. Do not purchase backup service or copy secrets into reports. Record backup identifier, time, source, checksum and restore instructions without storing credentials.
4. Restore that backup to an already authorized isolated target. Verify row counts, owner mappings, datasets, artifacts and relationships, then run the candidate migration and startup validator there. Do not use the production target as a rehearsal. Tests here contain synthetic data only.
5. Confirm current database connections can be quiesced safely and obtain approval for any maintenance interval. Check in-flight work, review/publish state and retry keys. A frontend deployment alone does not start a worker. Vercel Daemons may host the PostgreSQL-backed worker, subject to account quota, container shutdown/restart testing and explicit activation; no daemon is configured by this patch.
6. Review the exact SQL hash and matching application commit, and obtain explicit approval before one operator applies the migration. Do not start old auto-DDL code as a shortcut. Configure existing credentials only through an approved secure path.
7. Verify the non-mutating startup contract, authenticated owner/tenant isolation, upload, analysis, human review, publication and restart/restore with isolated acceptance accounts before a separately approved production promotion. External providers remain disabled unless specifically approved.

## Rollback

Before commit, PostgreSQL rolls the migration back atomically. The tests inject a failure after DDL to verify baseline data survives. After commit, do not automatically drop added tables, columns or the schema marker: newly written data and idempotency receipts could be lost. Prefer a reviewed forward fix or restore the approved matching backup after explicitly stopping writes and reconciling all post-backup records. Old application code may itself run schema DDL on startup, so merely reverting a deployment is not a safe rollback plan. Keep all historical documents and the inactive source database intact.

## Reproduce isolated verification

- `python scripts/schema_release/generate.py .` generates the manifest and refreshes the already CLI-created SQL file from reviewed portable DDL; it has no network/database client.
- `python scripts/schema_release/test_migration.py . /path/to/postgresql17/bin /outside/repository/rehearsal` creates disposable local clusters and uses PostgreSQL single-user mode. It does not listen on any socket or contact a hosted database.
- `python scripts/schema_release/check_validator.py . /path/to/postgresql17/bin /outside/repository/rehearsal` executes the actual Python validator against those catalogs, wrapping every query in a read-only transaction.

The test cases cover fresh/repeated application, the old nine-table schema with one owned sentinel record per table, preserved historical values, wrong type, ownerless records, missing owner column, wrong index, wrong foreign-key action, deferred keys, existing direct/inherited client grants, injected post-DDL rollback and unrelated-table preservation. PUBLIC and authenticated roles are exercised as genuine non-superuser/non-BYPASSRLS roles. These are schema and data-preservation checks, not multi-session concurrency, PostgREST/JWT, provider, browser or production acceptance.

## Column-grant startup gate (24 October 2026)

The SELECT-only runtime preflight additionally checks explicit PUBLIC column
ACLs and effective anon/authenticated column privileges (SELECT, INSERT, UPDATE,
REFERENCES), including inherited custom-role grants. A table-level REVOKE does
not remove column ACLs. Unrelated tables and standalone backend/custom-role
column grants are not rejected merely for existing. This check covers effective
INHERIT access, not a general audit of SET ROLE paths or provider policy.

The reviewed migration file and its hash are unchanged. This is a startup
refusal, not a new pre-migration SQL guard, automatic revocation, or proof of
migration readiness. Operators must inspect column ACLs before approval as well
as table grants; the original migration itself can still commit with column ACLs
present. Snapshot/restore completeness and the PostgreSQL17 drill remain separate.

The existing hosted-schema unit module and disposable PostgreSQL CI test cover
column access rejection and preservation. The single-user migration/validator
scripts also include column ACL fixtures; those scripts require PostgreSQL17
and do not run as part of ordinary CI. Local sparse-source checks are not a full
suite or real PostgreSQL result.
