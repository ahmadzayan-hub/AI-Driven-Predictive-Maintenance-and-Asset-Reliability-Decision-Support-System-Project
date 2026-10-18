# ADR 0054 — Miyaar workspace and observable voice interaction

Status: Accepted for implementation, 2026-10-19.

## Context

The owner requested a frontend redesign on feature/miyaar-ui-redesign with
a reviewable pull request against main. This request takes precedence over
the older automatic session-end merge instruction and the flat-only visual
direction in ADR 0023. The backend, identity and approval contracts stay intact.

The current voice component claims listening immediately after start(), does
not show interim speech, and can deliver late results after stop/session change.
Chat waits for the existing JSON response; a rules reply is not an LLM response.

## Decision

- Asset Reliability / موثوقية الأصول remains the platform. Miyaar / معيار is
  its presentation-layer assistant name. Backend identifiers and response
  evidence are retained.
- Use midnight surfaces, cyan/teal action tokens, restrained glass and rounded
  panels. Retain locally bundled fonts and the Arabic system fallback.
  New visits default to dark; explicit light and system preferences remain.
- Keep existing routing, business views, lazy loading, APIs and authentication.
  Welcome actions open actual workflows, with no invented asset metrics.
- Show the submitted message immediately, preserve follow-up drafts, prevent
  duplicate sends and ignore replies belonging to an obsolete session.
  Mark rules, command, model and runtime results honestly. Chat requests receive
  a bounded 60-second client wait; there is no simulated token streaming.
- Voice remains opt-in and review-before-send. Distinguish permission request,
  actual listening, finalization, transcript review and failure. Show interim
  speech separately, commit only final results, and never auto-send.
  Stop requests a final transcript; cancel/disable/unmount/language changes
  invalidate callbacks. A bounded timer
  resolves browsers that never report start or end.
- Read-aloud remains user-triggered. Queued speech and actual playback are
  distinct; only one reply can own playback. No always-on microphone claim.

## Verification and limits

Regression coverage must exercise delayed and failed requests, multi-turn chat,
stale-session replies, microphone permission failures, late speech events,
interim/final results, playback ownership, RTL/LTR and narrow viewports.
Browser automation uses clearly identified synthetic fixtures; it cannot
prove hardware microphone quality or a deployed model provider's continuity.
Human review, auth and backend tests remain separate.

Browser event semantics:
- https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/start_event
- https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/result_event
- https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisUtterance/start_event

## Download budget decision

The original main build measured 98.6 KB initial JavaScript, 157.6 KB total
JavaScript, 10.0 KB initial CSS and 16.0 KB total CSS (gzip level 9).
Keep the 100 KB initial JavaScript, 10 KB initial CSS, 30 KB chunk and 120 KB
font ceilings. Move secondary view translations and styles into their existing
lazy chunks and remove obsolete welcome styles. No dependency or font is added.
The total ceilings become 165 KB JavaScript and 20 KB CSS to accommodate
the bilingual voice state machine and the requested visual layer. This is an
explicit increase in total downloaded bytes across all views, not a claim of
zero performance cost. Initial transfer remains within the existing ceilings;
actual device interaction/paint performance still needs field measurement.
