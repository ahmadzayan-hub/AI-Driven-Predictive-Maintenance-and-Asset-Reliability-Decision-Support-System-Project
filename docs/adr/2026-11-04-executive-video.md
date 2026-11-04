# The executive video, rendered on this host from the brief

Date: 2026-11-04 · Status: Accepted

## Context

The owner asked for a professional video from the same verified snapshot as the
dashboard and slides, with Arabic and English narration and subtitles, previewable,
downloadable and traceable, using a real rendering and audio pipeline, with missing
values kept unavailable, and with no private data sent to an external service
without approval.

## Decision

1. **`server/executive_video.py`.** Six scenes from the brief only: title (dataset,
   period, records), the decision, four key measures (counting figures, a growing bar
   for percentages, "Not measured" with the brief's reason where a value is missing),
   the top priorities with their own figures, forecast and limits (each model's
   validation, as on the slides), and sources and review. Nothing is recalculated or
   written by a model.
2. **Local tools only.** Frames are drawn with Pillow (libraqm shapes Arabic, right to
   left) in the verified Dubai font; narration is synthesised with espeak-ng (GPL-3,
   offline, no cost); ffmpeg encodes H.264 video, AAC audio and a `mov_text` subtitle
   track. Each scene lasts its narration plus one second, the speech is padded to the
   scene exactly, and the subtitles are timed within the spoken span, so voice,
   subtitles and pictures share one timeline. Spoken numbers use the faithful rounding
   rule and dates are said in words.
3. **Traceability.** A manifest records the run, snapshot, language, filters, every
   scene's text and figures with their evidence ids, the engines and the SHA-256 of the
   MP4, WebVTT and SRT. Downloads are refused (410) if the stored file no longer
   matches its digest. A failed render is recorded and shown as a failed export.
4. **API.** `POST /api/runs/{id}/executive/video` (write) renders synchronously, one
   at a time, and answers 503 naming what is missing on a host without the tools (the
   Vercel functions have none) or in the view-only demo. Files are served to the run's
   owner only, inline for preview or as an attachment.
5. **Review.** The video is the fifth output of the shared review step.

## Consequences

The espeak-ng voice is intelligible but plainly synthetic; it is the honest local
option. A better voice needs either a licensed offline model or an external service
such as ElevenLabs, which would send report text off the host and costs money; both
need the owner's approval. The narration has not been listened to by a person in this
environment; phoneme output was checked instead. Rendering takes about 30 seconds for
a 90-second clip here. Tests: `tests/test_export_reviews.py`.

## Amendment 1, 4 November 2026: motion film and a human voice

The owner judged the first version a slide show with a robotic voice and asked for a
real executive video with motion and visual effects and a human voice, goals unchanged.

1. **A motion film.** `server/video/composition.html` is a time-driven composition:
   every frame is a pure function of time and the storyboard. It has a slow camera
   push, a wipe in from the reading edge with a focus pull, word-by-word headings,
   KPI cards that tilt in with counting figures and percentage rings, priority cards
   with the single measured figure each cites (none when a priority cites several),
   model-against-baseline bars that grow, drawn check marks, drifting light and a
   moving grid, and a chapter bar. Arabic runs right to left throughout.
   `server/video/render_film.mjs` renders it in the frontend's Playwright Chromium at
   1920×1080, in parallel slices joined by ffmpeg. About 3.5 minutes for a
   140-second film on four cores. The Pillow renderer stays as the fallback where
   Chromium is absent; `AGENTIC_OS_VIDEO_RENDERER=pillow|film` chooses explicitly.
2. **A human voice, with the owner's approval.** The owner approved ElevenLabs with
   Nasser (Modern Standard Arabic) and Peter (English), at about 930 credits per
   language per video. Narration text (KPI names and values, priorities, the
   recommendation; never data rows) goes to ElevenLabs only when the operator sets
   `AGENTIC_OS_VOICE_PROVIDER=elevenlabs` and `ELEVENLABS_API_KEY`; voices can be
   changed with `AGENTIC_OS_VOICE_ID_AR` and `AGENTIC_OS_VOICE_ID_EN`. Without them the
   offline espeak-ng voice is used and the manifest says so. Recorded narration made
   elsewhere can be supplied per scene, but only with the SHA-256 of the exact scene
   text, so the voice can never say what the screen does not.
3. **Speakable text.** Column names lose their underscores and currency codes are said
   in words; facts are unchanged, and the subtitles show the same text.

Consequences: the manifest (schema `executive-video-v2`) records the renderer, who
spoke and each scene's narration digest. In the build environment the ElevenLabs API
and its audio host are blocked by the network policy, so a video with the human voice
could not be produced here; the integration is tested against a mocked API.
