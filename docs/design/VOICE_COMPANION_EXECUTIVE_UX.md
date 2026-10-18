# Asset Reliability AI | Voice Companion and Executive Command Centre

Status: MVP implementation for GitHub code review. Not live railway authorization.

## User value
An engineer can dictate a natural-language question, correct its transcription and use the existing governed assistant, without learning another interface. An executive can listen to a chosen reply, inspect the analysis behind a result, and open the decision queue.

## What is implemented in this PR
- Opt-in browser microphone, recognition locale English (US) or Arabic (UAE).
- Explicit browser speech-service disclosure before capture.
- Live voice state, stop button, unsupported-browser and denied-microphone messages.
- Draft-only transcription. **Never** automatically send, execute, approve or publish.
- User-clicked speech playback of an agent reply, with stop; no autoplay.
- No application recording, hosting, uploading or retention of raw audio.
- Executive decision shortcuts with real actions: dataset upload, existing dashboard, approvals.
- Managed auth, Hermes, source-backed analytics and human review remain unchanged.

## What is NOT implemented
No JARVIS code was cloned. There is no always-listening hotword, voice print, continuous surveillance, desktop control, new LLM or voice-originated engineering action. This is a browser-native voice UI, not an autonomous agent. A browser's speech engine may use remote services and its own retention policy. Do not use for confidential or regulated records until approved provider data processing is implemented.

## UX review checklist
- Use the primary upload → analyze → validate → dashboard → approve path.
- Distinguish sampled/demo metrics from actual records.
- Preserve dark/light layouts, RTL Arabic and labels for statuses.
- Controls min 44px, tab/focus access, logical CSS spacing.
- Voice consent reachable by keyboard; browser microphone permission separately enforced.
- Navigation buttons do not invent endpoints; all actions use existing routes.
- The accessibility and voice behavior should be tested against real browsers, not only jsdom.

## Next deliberate milestones
1. Test actual Chrome/Edge/Safari speech recognition in English and Arabic including noisy environments.
2. Determine provider privacy contracts and an on-premise or on-device ASR/TTS fallback for railway or public-sector records.
3. Add validated read-only voice navigation intents with display of recognized command and an explicit confirmation.
4. Add source-backed audible executive brief from approved reports, with optional replay but no raw dataset access.
5. Implement configurable enterprise-grade speech pipeline only when cost, Arabic quality, security and latency improve on browser-native MVP.

## Repo philosophy
Hermes remains the single orchestrator and the existing action contracts remain authoritative. The UI cannot upgrade the caller's role or bypass application authorization.
