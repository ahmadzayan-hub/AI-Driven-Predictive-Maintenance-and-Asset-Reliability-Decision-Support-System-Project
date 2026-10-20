# ADR 2026-10-20 — Published notes retain their run's tenant boundary

**Status:** Accepted
**Date:** 2026-10-20

## Context

The run endpoints checked ownership, but `/api/vault` listed every published
note and `/api/vault/note` returned any known path to any authenticated reader.
A synthetic reproduction returned 404 for another tenant's run while returning
200 for that tenant's published report. Publication approval authorizes a vault
write, not disclosure to every customer.

An authenticated browser on an allowed separate origin also failed its CORS
preflight: `Authorization` was absent from the allowed request headers.

## Decision

- A published note inherits ownership from its existing `run_id`. SQL joins
  notes to runs and filters by the authenticated subject for both listing and
  reading, so old published notes gain protection without a data migration.
- Platform administrators retain cross-owner access. An ordinary owner, viewer
  or auditor cannot list another owner's paths or retrieve its report or log.
  A missing note and a note owned by someone else both return 404.
- Local mode remains the single `local-owner`. Trusted operator code may read
  the whole store; each HTTP request supplies its scope explicitly.
- Files in the configured vault are not a read fallback. A local file without
  an authorized database record remains inaccessible through the API.
- CORS allows the Bearer `Authorization` header on origins already explicitly
  allowed. The origin policy and the requirement to authenticate do not change.

## Validation

`tests/test_published_note_access.py` publishes through the real API, checks
owner/viewer/auditor isolation and administrator access, exercises storage
filtering on existing notes, checks that local files cannot bypass the store,
and verifies allowed and refused CORS preflights. The same tests run against
SQLite and, when configured, PostgreSQL. Existing local publication tests remain
the compatibility check. No live customer data or deployment is required.
