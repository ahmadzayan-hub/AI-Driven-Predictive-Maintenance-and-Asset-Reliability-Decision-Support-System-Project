# The live pipeline names the stage running now, and announces its progress

Date: 2026-10-28 · Status: Accepted (the "live timeline" item of the
interface list in `project-progress.md`, after the 28 October stage-report
decision; the timeline itself is `frontend/src/features/runs/RunTimeline.tsx`).

## Context

The run timeline lists every stage with its state, and the run screen refreshes
it by polling the run about every 2.5 seconds while work is in progress, so
the timeline already moves without a reload. Three things were missing for a
reader and for a screen reader. The stage running now was not named or marked,
so the reader had to scan the list. The progress count changed silently, so a
screen reader user heard nothing as the pipeline advanced. And the run's
approval wait was shown only by a mark, not in words.

## Decision

1. **The stage running now is named and marked.** A line above the list reads
   *Now: {stage}* in the run's language, and that stage's row carries an
   outline and `aria-current="step"`. When no stage is running, no line is
   shown.
2. **The progress count is a live status.** The header count has
   `role="status"`, so a change in completed stages is announced politely.
3. **Approval waits are left to the existing signals.** The stage's mark
   shows the wait, and the approvals inbox lists it. A line for this was
   written and then removed, because the rest of the interface already says it
   and the script budget had no room for a duplicate.
4. **Transport is unchanged.** Progress still arrives by the run's existing
   poll. The owner's live event stream (`/api/events`, ADR 0034) is not used
   for this view, so the timeline does not depend on it.

## Not in this slice

- **Agent cards per stage.** A card per stage with its agent's role, its
  outputs, and its evidence would be a new visual layer. It needs a decision on
  what each card shows and a budget for it; the script total has 0.1 KB of
  headroom now, so it cannot be added without trimming first. It is the next
  slice.

## Budget

The script total is 256.9 of 257 KB after this slice. The timeline's additions
were trimmed to fit (the approval line, described above); no ceiling was
raised.

## Tests

- `frontend/src/features/runs/RunTimeline.test.tsx`: the stage running now is
  named and marked, in English and Arabic.
- `runs.spec.ts`, `a11y.spec.ts` and `arabic.spec.ts` pass on desktop and phone
  (18 cases).
