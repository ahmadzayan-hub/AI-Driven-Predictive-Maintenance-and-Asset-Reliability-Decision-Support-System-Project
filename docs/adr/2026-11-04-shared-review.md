# One review step for every executive output

Date: 2026-11-04 · Status: Accepted

## Context

The owner asked for one persistent, auditable review across the dashboard, slides,
PDF, Word and video, recording reviewer, decision, comment, time and the exact
version, with any later change needing a new review. Until now each export was a
download marked "Draft for review" and nothing recorded that anyone had looked at it.

## Decision

1. **`export_reviews` table, append-only.** One row per decision: run, brief
   snapshot, output (`dashboard`, `html`, `docx`, `slides`, `video`), language, the
   SHA-256 of the exact bytes reviewed, decision (`approved` or `changes_requested`,
   the latter needing a comment), comment, reviewer (the signed-in subject) and time.
   Rows are never updated or deleted; they are the audit trail.
2. **A decision counts only for the exact file.** The dashboard's digest is the brief's
   snapshot id; the HTML, Word and slide digests are the digests of their renders,
   which are byte-identical for the same snapshot (checked); the video's is the
   digest recorded when it was rendered. Status per output is `draft`,
   `approved`, `changes_requested`, `changed_since_review` (an earlier decision no
   longer matches: new data, filters, language or file), `not_rendered` or `failed`.
   PDF is the HTML report printed by the browser, so it is reviewed as the HTML.
3. **API.** `GET /api/runs/{id}/executive/reviews` (read) returns the state of every
   output for the reader's language and filters, the history and whether this host
   can render video. `POST` (the `approve` permission) records a decision only if the
   snapshot and the digest still match what the server produces now; otherwise 409.
4. **A review is not release.** It publishes nothing; the run's own approval gate
   still decides publication. Every export keeps its "Draft for review" label.
5. **Interface.** A review panel, loaded on demand under the export controls, lists
   the five outputs with their state, reviewer, time and comment, offers Approve or
   Request changes (comment required) to readers who may review, and the history.

## Consequences

Status reads render the three documents to digest them (about 0.25 s for this run
size). Tests: `tests/test_export_reviews.py` (state rules, permissions, invalidation
after a data change, per-language state, the digest equals the downloaded bytes) and
`ReviewPanel.test.tsx`.
