# ADR 0044: Bounded voice companion rather than cloning JARVIS

Status: Proposed for review, 2026-10-18.

## Context and evaluation
The SaaS has a React 19 frontend, FastAPI API, Hermes pipeline and typed role/approval contracts.
Open-source Jarvis-like voice projects were reviewed:
- `leon-ai/leon`, MIT, 2.0 developer preview. Full AI assistant would duplicate orchestration.
- `OpenVoiceOS/ovos-core`, Apache-2.0, mature but designed as an independent distributed voice pipeline.
- `PHENOMVALENCE/JARVIS-OS`, MIT, Windows desktop local-first voice, with machine control outside this SaaS mandate.

Licences do not make their entire applications safe, supported, or compatible with Vercel. No third-party code was copied or cloned.

## Decision
Deliver an opt-in browser-native Voice Companion in the existing chat experience:
1. Explicit push-to-talk only; consent disclosure before opening microphone.
2. English `en-US` and Arabic `ar-AE` locale; dialect/voice availability unverified.
3. Final transcription is inserted into the existing chat draft for correction before a separate, user-clicked Send.
4. Never execute a maintenance, database, work-order or safety-affecting action directly from a transcription.
5. Optional, user-triggered read-aloud of a selected reply; no autoplay, hotword, or audio files persisted by our application.
6. Retain existing permissions, authentication, session boundaries and Hermes backend. Browser recognition is unavailable in some clients; typing remains the primary fallback.
7. Browser engines MAY transmit audio to third-party speech providers. Explicitly disclose this. The feature must not be used for sensitive or confidential information unless approved speech processing and consent controls exist.
8. Vercel `Permissions-Policy` is updated from `microphone=()` to `microphone=(self)` so a click-initiated microphone request is technically possible. This does not bypass user/browser permission.

## Excluded
Always-on hotword listening; cloning a Jarvis voice or Marvel-branded likeness;
arbitrary desktop execution; direct access to raw railway/tenant data; impersonation; unreviewed auto-publish; guaranteed Arabic accuracy; claims that speech recognition is local on all browsers.

## Gates
- Unit tests for consent, unsupported browser, cancellation, transcript-only handling, and disabled sessions.
- Playwright smoke checks with mocked microphone recognition in supported browsers.
- Manual cross-browser EN/AR device tests, consent policy, and authenticated deployment checks before enabling for sensitive enterprise data.
- Maintain human review for all engineering recommendations and publication.

References: `https://github.com/leon-ai/leon`, `https://github.com/OpenVoiceOS/ovos-core`, `https://github.com/PHENOMVALENCE/JARVIS-OS`,
`https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition`.
