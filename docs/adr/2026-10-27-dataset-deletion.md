# A stored dataset can be removed, unless an analysis reads it

Date: 2026-10-27 · Status: Accepted (the dataset lifecycle gap named in the
16 October code audit, `project-progress.md`, and the first slice of the
platform-building programme after the assessment backlog closed).

## Context

Datasets are stored content-addressed per owner (ADR 0024) and counted
against the owner's allowance (datasets and bytes, ADR 0031 quotas), but
nothing removed one short of erasing the whole owner (`server/erasure.py`).
An owner who uploaded the wrong export, or a superseded one, kept paying
for it in the allowance and saw it in every picker. Runs are never deleted:
a published result points at its table, and a run whose dataset vanished
could not be reopened, re-read for its cleaned table or queried.

## Decision

1. **`DELETE /api/datasets/{id}`** removes one stored dataset of the
   caller's, with its mapping, and answers the name and the allowance
   after. It needs the write permission (a viewer and the view-only demo
   get the usual refusal). Another owner's dataset is a 404, never a 403,
   as every dataset endpoint already answers.
2. **A dataset an analysis reads stays.** The engine looks for the owner's
   runs that read the dataset as their main table (`runs.dataset_id`) or
   as a joined one (the declared joins in `runs.joins_json`, ADR 0030) and
   refuses with 409 `dataset_in_use`, naming up to three analyses by goal
   in the reader's language and listing every run id. The check and the
   deletion run in one owner transaction, so a run created meanwhile
   cannot lose its table. The `LIKE` narrows candidates; the parsed joins
   decide, so an id that merely appears in a goal never counts.
3. **A live source forgets the snapshot it last stored.** A connector whose
   `last_dataset_id` was the dataset has that and `last_sha256` cleared,
   so its next refresh stores and analyses the fetched table again rather
   than calling it unchanged. (In practice the run that snapshot produced
   keeps the dataset, so this only matters when no run was made.)
4. **The Datasets view offers Remove** beside Analyse, hidden in the
   view-only demo, behind the shared confirmation dialog. The server's
   refusal is shown as it is, in the reader's language; a removal says so
   and refreshes the list and the allowance. Strings ship in English and
   Arabic.

## Consequences

- `tests/test_dataset_deletion.py`: 7 cases on SQLite and the same on
  PostgreSQL (removal and the allowance, another owner's 404, a viewer's
  403, the refusal named in both languages, a joined dataset counting as
  read with a decoy id that does not, the live-source pointer, the
  mapping going with the dataset). `frontend/src/tests/views.test.tsx`
  covers the confirmation, the refusal and the demo.
- Erasure (`server/erasure.py`), backup and restore are unchanged: a
  deleted dataset is simply absent. A backup taken before the deletion
  still holds it, which the erasure report already says about backups.
- The Android client does not yet offer removal; its dataset list reads
  the same endpoint and is unaffected. Removing a run, and with it the
  datasets only it reads, is a separate decision: a published note cites
  the run, and the approval record is the audit trail.
