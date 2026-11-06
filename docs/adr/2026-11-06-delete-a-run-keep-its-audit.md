# Delete an analysis, keep its audit

Date: 2026-11-06 · Status: Accepted · Owner request: "Continue next developments till complete the platform"; the gap analysis listed deleting a run and the datasets only it reads

## Context

Runs were never deleted, so a stored dataset an analysis had read could never be
removed either, and a workspace kept every trial run. Approvals and reviews are an
append-only record that must survive.

## Decision

1. `DELETE /api/runs/{id}` (write permission, the run's owner) turns the run into a
   tombstone: the row stays, marked `deleted`, with its dataset copy, mapping, joins,
   assumptions and source link emptied; its stage outputs, artifacts, layout versions,
   saved view and rendered films (rows and files) are removed.
2. Approvals, export reviews and KPI policy history stay. The deletion itself is added to
   the approvals table as a `recorded` entry naming who deleted it and when, with a digest
   of what was removed. No schema change, so the hosted database needs no migration.
3. Every route reads a deleted run as missing (404); the run list leaves it out. A queued
   or running analysis is refused (409, English and Arabic). A second delete is a 404.
4. With `datasets=true`, each dataset the run read that no other analysis reads is removed
   in the same transaction; the reply lists what was removed and kept. The datasets view's
   refusal now says "Delete those analyses first, or keep the dataset".
5. The run view has a "Delete analysis" control (not in the demo) with the shared
   confirmation and an option to delete the datasets too, in English and Arabic.

## Consequences

- Tests: 4 API cases on SQLite and PostgreSQL (data and outputs gone, audit kept with the
  deletion recorded; datasets only it read go with it; another owner, a viewer and a second
  delete; a running analysis refused in both languages) and 3 interface cases.
- A published vault note stays: publication is a separate, approved record.
- Not done: reading a deleted run's audit through the API (it stays in storage, readable
  by the operator); the daily run quota still counts a deleted run, since the work was done.
