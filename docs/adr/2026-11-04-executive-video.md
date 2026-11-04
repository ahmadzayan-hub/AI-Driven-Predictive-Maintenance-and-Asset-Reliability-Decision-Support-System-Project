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
