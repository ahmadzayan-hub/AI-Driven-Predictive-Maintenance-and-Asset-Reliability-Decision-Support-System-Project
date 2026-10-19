# Miyaar / معيار — frontend handoff

## ما الذي تم تسليمه؟

واجهة «موثوقية الأصول» بهوية معيار: ألوان كحلية وسماوية، تنقل يدعم RTL،
مساحة محادثة، شاشة ترحيب صناعية، بطاقات إجراءات، لوحة سياق، وبحث بالأوامر.
العربية والإنجليزية متاحتان، مع وضع داكن افتراضي ودعم الوضع الفاتح واختيار النظام.

تعرض المحادثة السؤال فور إرساله، ثم حالة الانتظار والرد الفعلي ومصدره.
تُحفظ المسودة عند الفشل، وتُمنع الطلبات المكررة، وتُهمل الردود التابعة
لجلسة سابقة أو منتهية. تبقى الموافقات والتحليلات ومجموعات البيانات ضمن
المسارات الحالية.

الصوت اختياري: إذن الميكروفون، الاستماع، معالجة الكلام، معاينة النص،
ثم تحريره وإرساله يدويًا. القراءة الصوتية تبدأ بطلب المستخدم وتُظهر
حالة الانتظار والتشغيل والخطأ. لا يعني مؤشر الجاهزية أن الميكروفون مفتوح.

## Implementation map

| Area | Source | Responsibility |
| --- | --- | --- |
| Shell, navigation, context | `frontend/src/app/App.tsx` | Existing routes and identity; Miyaar presentation |
| Visual system | `frontend/src/shared/styles/tokens.css`, `frontend/src/features/chat/miyaar.css` | Theme, surfaces, logical properties, responsive layout |
| Welcome and conversation | `frontend/src/features/chat/ChatView.tsx`, `MessageBubble.tsx` | Real workflow actions, source labels, pending/error/follow-up states |
| Chat continuity | `frontend/src/app/store.tsx`, `shared/api.ts` | Same session endpoint; duplicate and stale-response protection; bounded request timeout |
| Voice input/output | `VoiceInput.tsx`, `VoiceServerDictation.tsx`, `VoiceDictation.tsx`, `VoicePlayback.tsx` | Optional local Whisper, browser fallback, consent, cancellation, editable drafts and playback ownership |
| Deferred pages | Feature CSS and `messages.ts` packs | Keep secondary view assets off the initial load |

The product remains **Asset Reliability / موثوقية الأصول**; the assistant
is **Miyaar / معيار**. Internal Agentic OS identifiers, persisted keys, server
transcripts and API response evidence are preserved. The follow-up installation
request adds an optional authenticated transcription endpoint and local model
launcher ([ADR 0055](../adr/0055-opt-in-local-model-and-whisper-runtime.md));
existing authentication, data models and orchestration contracts are preserved.

Welcome actions open the existing upload/analysis, asset intelligence and
approval flows. “Compare assets” opens asset evidence; this change does not add
a new comparison engine. The industrial graphic is a lightweight decorative
SVG, explicitly labeled as an illustration. No asset health score, alert,
prediction, KPI or system heartbeat is fabricated.

## Voice and model boundaries / حدود التشغيل

- The optional local Whisper adapter records after explicit permission and
  transcribes on the server using preinstalled CPU/int8 weights. It discovers
  availability before selecting this transport and otherwise retains browser
  speech. Recording stops below the server's duration ceiling; audio is neither
  persisted nor sent to a cloud provider by this adapter. Transcriptions become
  editable drafts. See [local setup](../LOCAL_AI_SETUP.md) for exact limits.

- Browser speech recognition needs a supported browser, microphone permission
  and a secure context (HTTPS or localhost). The permission API is optional.
  The UI handles unavailable APIs, denied permission, no microphone, network
  failure, no speech and missing start/end events.
- The animated bars indicate recognition state; they are not measured audio
  amplitude. Final text becomes an editable draft. Nothing is auto-submitted.
- Read-aloud uses the browser's installed voices. It is opt-in, permits only
  one active reply and retains the existing character limit with a visible
  notice. Hardware capture and voice quality require a real-device check.
- Chat still consumes the existing JSON endpoint. It shows pending/waiting
  feedback, not simulated token streaming. Client waiting is bounded at
  sixty seconds.
- A `rules`/`chat` reply is identified as limited mode. Full conversational
  intelligence depends on a configured server model/runtime; this frontend
  does not invent a model reply. The local launcher selects the installed
  Ollama provider. Local acceptance evidence is recorded in README; it does not
  validate a deployed cloud provider.
- The status card describes session/request connectivity. It is not a new
  asset telemetry feed. Maintenance findings retain their existing evidence
  and limitations.

## Validation

See [README — Testing](../../README.md#testing) for the actual counts and
environment-specific results. New regression coverage lives in
`frontend/src/tests/chat-store.test.tsx`, the voice component tests, the
existing dictionary parity tests and `frontend/e2e-miyaar/workspace.spec.ts`.

Run the built-app visual suite with:

```sh
cd frontend
npm run build
npx playwright test --config=playwright.miyaar.config.ts
```

It uses explicitly synthetic API and recognition fixtures for reproducibility.
The normal `npx playwright test` suite exercises the real FastAPI adapter,
including auth, uploads, runs and approvals. CI runs both suites separately.
Axe checks do not replace a screen-reader or hardware voice review.

The first-load download ceilings remain unchanged. Total cross-view budgets
increase explicitly for the requested visual/voice features; measured values
and rationale are in [ADR 0054](../adr/0054-miyaar-workspace-and-honest-voice.md)
and [ADR 0055](../adr/0055-opt-in-local-model-and-whisper-runtime.md).
No new browser runtime dependency or font was added. Server voice dependencies
are explicitly optional in `requirements-voice.txt`.

## Screenshots

Screenshots are actual Chromium renders with synthetic test sessions.

| View | Evidence |
| --- | --- |
| English desktop | [Workspace](../screenshots/miyaar-en-desktop.png) |
| Arabic desktop | [مساحة العمل](../screenshots/miyaar-ar-desktop.png) |
| English phone | [Phone](../screenshots/miyaar-en-phone.png) |
| Arabic phone | [الهاتف](../screenshots/miyaar-ar-phone.png) |
| Light theme | [Light](../screenshots/miyaar-en-light.png) |
| Conversation/error | [Conversation](../screenshots/miyaar-conversation.png) |
| Voice preview | [Voice](../screenshots/miyaar-voice-preview.png) |

## Review and next steps

The owner subsequently requested "merge all". PR #15 merged into `main` on
19 October 2026 at `893986d`, preserving both parents and the tested feature
tree. This records a source merge; no production deployment was performed.
Confirm the visual direction on
actual target devices, test microphone capture and Arabic playback with the
deployment's supported browsers, and validate multi-turn answers against the
chosen server provider. Real-time streaming or hands-free voice would require
a separate backend/audio design and explicit product scope.
