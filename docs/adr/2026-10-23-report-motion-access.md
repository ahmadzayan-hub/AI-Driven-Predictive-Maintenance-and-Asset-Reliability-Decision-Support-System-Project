# Selected reports and source-bound Motion review

Date: 23 October 2026

## Decision

An explicit assistant run_id selects that report or returns the same unavailable
answer as a missing report. It never silently falls back to the newest run.
The actual requester is checked rather than inheriting a conversation owner's
permissions. RMD evidence remains in the ephemeral authorized panel, not ordinary
retained chat or model tools.

Motion derives a storyboard from a validated report and binds the complete report
content hash, artifact ID and version. Generic validator requirements remain
unchanged. Recorded pipeline validation is not an independent LLM review.
A distinct RMD adapter requires successful recorded snapshot assurance,
a fresh deterministic snapshot replay, source existence, fingerprint agreement,
and an exact match to the generated immutable report. It does not manufacture a
predictive-accuracy certificate or authorize operational work.

Every Motion status, preview, submission and decision rechecks existing run/pack
access. An independent reviewer can inspect a submitted video only with existing
source read and review authority. Organization membership is required even for a
platform administrator; private owner-only packs remain inaccessible to another
reviewer. No role, membership, production setting or schema migration is added.
The author cannot approve their own video. A source/report change invalidates the
current derivative for review; create a new video draft, preserving old files and
hashes rather than silently overwriting the report or media. Hashless historical
jobs need a new draft rather than automatic approval migration.

## Boundaries

This is not full-duplex voice, a creative-agent loop, external publication or a
production renderer deployment. Browser voice remains consented dictation/manual
playback. The existing local queue retains explicitly uploaded narration as an
asset; conversational raw audio must not be repurposed. Rendering remains opt-in,
local only, and internal approval still returns publication_allowed=false.

## Verification

Synthetic tests cover selected older reports, missing/wrong-owner context, full
content changes with an unchanged headline, RMD replay/tampering, source deletion,
organization revocation (including the video author), admin without membership,
private-pack isolation, legitimate existing reviewer preview, unsubmitted-draft
isolation and self-approval refusal. Media bytes in authorization tests are
synthetic; these tests do not claim real MP4, microphone or Arabic audio quality.

Authorization is rechecked at request/decision time. Already delivered or
in-flight file bytes cannot be recalled; no mid-download revocation guarantee
is made. Private responses are marked no-store.
