# Tier 2 release gate: Motion Studio authenticated MP4 with human release gate

Date: 2026-11-02 · Status: **Proposed, awaiting the owner's decision.** No
motion code changes ship with this record.

## Context

Motion Studio produces MP4 previews from analysis runs. Today the preview path
is unauthenticated and the release gate is a manual step. Issue #19 and
`docs/MOTION_STUDIO_RELEASE_HANDOFF.md` list "authenticated MP4 jobs and
human-controlled release gate" as a P0. The portfolio review calls this a
Tier 2 item needing an ADR plus a release gate.

The existing pieces: `docs/MOTION_STUDIO_GOVERNMENT_QUALITY_GATES.md`,
`docs/MOTION_STUDIO_IMPLEMENTATION.md`, and the motion tests under
`frontend/e2e/` (including the Arabic RTL frame and audio integration test).

## Release gate (all must hold before the MP4 path is called production)

1. **Authentication.** Every MP4 job request carries a valid managed-auth
   session (ADR 0002); anonymous generation is refused with a 401.
2. **Human gate.** A generated MP4 is never published or shared until a
   named owner approves it. The approval is recorded with the run id and a
   timestamp.
3. **Arabic correctness.** The real Arabic RTL frame and audio integration
   test passes on CI with RAQM and FFmpeg present (already added in PR #76).
4. **No fake evidence.** Synthetic renders are labelled as such; no MP4
   claim may cite a real site without an approved run behind it.
5. **Resource limits.** Generation is bounded by the worker limits
   (`tests/test_worker_limits.py`); a run that exceeds them fails cleanly.
6. **Rollback.** A bad MP4 can be unpublished without regenerating it.

## Decision requested

Approve building the authenticated MP4 path behind these six gates, or keep
Motion Studio labelled "preview only" in `KNOWN_LIMITATIONS.md`.

## Consequences if approved

- Work lands on a branch; merges only when all six gate items are evidenced.
- The existing Arabic frame/audio test stays the regression guard.
