# Explicit recovery after a local session or report disappears

Date: 2026-11-02. Status: accepted for the local Jarvis update.

## Problem and evidence

Replacing the disposable synthetic demonstration store left browser-cached session
and report IDs pointing at the previous store. Both stores passed SQLite integrity
checks, but they had no shared session IDs. The old report returned 404 from the
new store while its replacement was available. This is a store identity mismatch,
not evidence of corrupted reports or a reason to relax ownership checks.

## Decision

On reload, a missing chat session shows an explicit recovery action. It does not
silently create a replacement. Recovery first checks the old session again and
creates a new session only after a confirmed missing/ended session and a user
action. Authorization errors remain errors. The unsent, editable draft is copied
to the new session's tab-local draft key and retained under the old key. The old
conversation, if already visible in memory, remains accessible in this tab; it is
not moved into another server session. A page reload cannot reconstruct a transcript
whose server store is unavailable. Old database files are retained.

An uncertain send is never retried automatically. “Check conversation” only reads
the server session and displays any accepted reply. Manual resending is unlocked
only after that check and an explicit choice, with a duplicate warning. This is
conservative duplicate prevention, not an exactly-once server idempotency guarantee.

Jarvis verifies its cached session before binding the selected report and filters.
A missing session can be replaced during the explicit connect action, preserving
that exact requested scope. A missing report remains an actionable error and links
to available reports; no alternative is silently selected. Forbidden, incomplete,
and temporarily unavailable scopes have distinct bilingual messages.

ChatView loads on demand. Initial JavaScript remains capped at 100 KB and measured
96,058 bytes gzipped after the recovery change. The bilingual recovery UI and
state handling raise total script allocation from 268 KB to 272 KB (measured
270,724 bytes); all other limits stay fixed. This allocation must pass the same
strict boundary test as the earlier Jarvis allocation.

## Validation and boundaries

Unit coverage exercises explicit replacement, draft preservation, visible history,
uncertain send checks, ownership refusal, and scope renewal. Browser regressions
exercise reload with a missing ID, an accepted message whose response is lost,
and stale Jarvis session versus missing report recovery. Tests use disposable
synthetic local data. No authentication, hosted database, model, or voice provider
configuration is changed. Actual microphone and Arabic speech validation remain
separate from mocked browser-state tests.
