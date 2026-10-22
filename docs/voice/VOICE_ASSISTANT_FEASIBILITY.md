# Voice assistant feasibility

Date: 22 October 2026 · Scope: what the platform already does with voice,
what a conversational decision assistant needs on top, and the rule for
adopting any external project.

## 1. What exists

| Capability | Implementation | Status |
| --- | --- | --- |
| Dictation in the browser | `frontend/src/features/chat/VoiceDictation.tsx` (Web Speech API, English and Arabic) | shipped; a fixed label with `aria-pressed` is a minor fix (U17) |
| Server transcription, local only | `server/speech.py` with `faster-whisper` (optional extra, pinned model revision, bounded 30 s and 2 MB in-memory audio, nothing persisted) | shipped; Arabic word and name errors recorded in `docs/LOCAL_AI_SETUP.md` |
| Spoken playback of replies | `frontend/src/features/chat/VoicePlayback.tsx` (browser speech synthesis) | shipped |
| Text assistant | rules intent (10 actions) plus optional model intent and the agent runtime, through the same authorised API | shipped; rules plateau at 61% on the blind set |
| Security boundary | audio never stored; transcripts go through the same privacy guard and permission checks as typed text; destructive actions confirmed; publishing waits for approval | shipped |

The text interface is complete on its own; voice is an input and output
layer over it. That is the right architecture for the brief's requirement
that voice never bypasses a gate.

## 2. What the brief's questions need

"Which assets have the highest maintenance risk?", "Explain the reasons
behind this prediction", "Compare preventive and corrective options",
"Prepare a decision brief", "Explain this dashboard in Arabic", "Show the
evidence behind this recommendation". Each maps to data the API already
serves (the executive brief, model cards, findings, evidence, export). What is
missing is not voice: it is intent coverage for these sentences (the two
newest actions have no evaluation cases, G8) and a model intent path measured
in CI. Those come first; voice then inherits them.

## 3. Low-latency dialogue, turn-taking, interruption

Browser dictation and playback already give push-to-talk dialogue with
interruption (stop the playback, speak again). Full-duplex turn-taking with
barge-in needs streaming recognition and streaming synthesis; the current
server path is bounded, non-streaming and local-only by design. A streaming
path would mean either a hosted speech service (audio leaves the machine; a
privacy decision for the owner) or a local streaming model (device
dependent). Neither is justified by a measured need yet.

## 4. Adopting an external "JARVIS-style" project

No external repository was reviewed in this pass, so none is recommended.
Any candidate must pass, in this order, before a line is imported:

1. Licence compatible with this repository and its distribution.
2. Dependency tree inspected; no abandoned packages; pinned versions with
   hashes like the rest of `requirements.txt`.
3. Security review: no desktop automation, shell control or unrestricted
   tool execution; nothing that reaches the OS from a voice command.
4. Architecture fits as an input and output layer over the existing
   authorised API and the run engine; it cannot call stages or approvals
   directly.
5. Measured value over the minimal native path above on the brief's
   questions, in English and Arabic, with the text fallback intact.

## 5. Recommendation

Keep the native path. Spend the next effort on intent coverage and
measurement (G8), a fixed-label fix on the toggles (U17), and an Arabic
transcription quality check on device. Revisit streaming dialogue when a
customer workflow needs it.
