# Designed-page layouts kept on the server

Date: 2026-11-04 · Status: Accepted

## Context

Layouts, their history and pinned sections lived in one browser only
(`layoutHistory.ts`). The owner asked for server persistence with per-user
permissions, restore, audit and conflict handling, keeping the browser copy as a
fallback with its status shown.

## Decision

1. **`layout_versions` table.** Per reader (signed-in subject) and run, each save is a
   new numbered version with its action (designed, layout chosen, pinned, unpinned,
   restored) and time: the history is the audit trail. A unique key on
   (reader, run, version) means two writers from the same version cannot both win.
2. **API.** `GET /api/runs/{id}/layout/history` (read) returns the newest version and
   the trail. `PUT` (write, like saved views) stores a document naming the version it
   started from; a stale start is refused with 409 and the latest version, in the
   reader's language. `POST .../{version}/restore` copies an earlier version forward.
   Every layout is validated again against the run's table and schema fingerprint
   before it is stored, so a stored history never holds a section the planner refuses.
3. **Interface.** The designed page shows the account's layout when there is one, saves
   each change to the account and to this browser, says "saved to your account ·
   version n", "kept in this browser only" when the account cannot be reached, or that
   another tab or device changed it and the latest is shown; saved versions can be
   restored.

## Consequences

History is per reader, not shared across a workspace; sharing a layout with colleagues
is a separate decision. Tests: `tests/test_layout_history.py` and three cases in
`DesignedPage.test.tsx`.
