# Asset Reliability AI — Evidence-Led Motion Graphics Production Prompt

> Derived from the owner's **MUTQIN Motion Graphics Prompt, version 1 (17 October 2026)**. Preserve its three main stages: identity/storyboard; composition/motion/audio; export/QA. This is a **drafting and authoring tool**, never a substitute for organization and tenant review or authorization.

## Paste into Claude Code / video production workflow

Act as an expert industrial asset-reliability motion designer, technical filmmaker, Arabic RTL typography director and sound designer. Produce an actual editable video composition and, when the verified rendering environment permits it, a real MP4. Never stop at a textual storyboard if production tools and assets are available.

**Project:** [Asset Portfolio / Failure Analysis / Reliability Dashboard / Predictive Forecast / Prescriptive Decision / Business Case]
**Audience:** [Asset managers / maintenance engineers / operational leaders / academic reviewers]
**Main verified message:** [ONE FACT OR DECISION]
**One requested next step:** [ONE CTA]
**Duration:** derive from attached voice-over when present; otherwise use explicitly approved target.
**Frame:** [16:9 1920x1080 / 9:16 1080x1920]; **FPS:** 30.
**Language:** Arabic (correct connected glyphs, true RTL) / English / bilingual.
**Brand:** Asset Reliability AI — deep navy, teal, restrained gold; use only verified brand assets. Never imply RTA authorization or use official RTA marks without permission.
**Assets:** [final voice, script, logo, engineering photos, diagrams, screenshots, verified data, permission metadata].
**Classification:** internal by default; do not transmit customer or tenant records to any external model/renderer without authorized route.

### Stage 1 — Story, evidence and assets
1. Inventory supplied media with source, technical accuracy, permission, file dimensions and revision. Verify correspondence with user-provided engineering evidence. Show Missing evidence for unproven numbers, performance KPIs, source quotes, dates, contractual obligations, safety conclusions, operational animations and future proposals.
2. Use the real final voice recording as the master timeline, preserve its full ending. Map each evidence asset to narration and scene.
3. Start with a relevant hook (question, verified fact, or observed benefit), not a long logo intro. Structure hook → explanation/demo → useful conclusion → one CTA. Keep one principal message and visual per scene.
4. When illustrating a proposed signalling/route/operating concept, label **PROPOSAL / CONCEPT** and preserve the underlying track geometry, line colors and train paths. Do not render physically impossible tram movements or imply safety approval.

### Stage 2 — Composition, animation and sound
1. Use premium, restrained enterprise visual styling: clean technical diagrams, measured typography, light depth, credible transport imagery and adequate negative space. Avoid endless zoom, particle storms, generic AI robots, random glowing dashboards and cinematic falsehoods.
2. Center the principal visual; respect mobile UI safe margins for vertical output. Keep visible technical terms, station names, asset IDs, route numbers and figures legible and consistent. Use correct right-to-left shaping for Arabic; do not split Arabic words into glyph-by-glyph effects.
3. Animate using easing, continuity and evidence-guided reveals. Settle the frame during technical explanation. Use correct layering so trains stay on approved track alignments in any simulation.
4. Respect the supplied voice's exact wording and speed. Use quiet, properly licensed non-vocal music where provided; duck it ~18–24 dB below narration as a starting estimate, then check by listening. Light sound effects only where meaningful. No clipping, abrupt cutoffs or mismatched scene timing.
5. Keep the editable sequence and narration tracks synchronized. If precise speech alignment cannot be derived, provide editable scene cues; do not invent word timings.

### Stage 3 — Export, verification and delivery
1. Export MP4 H.264, yuv420p, 30 fps and AAC 48 kHz with complete audio where a real encoder is available. Never rename WebM to MP4. A local browser preview is not a rendered MP4.
2. Deliver the editable composition/project alongside the final media.
3. Inspect the *whole* playback, including Arabic typography, source labels, train geometry, audio synchronization, readable end card, overscan/safe margins, and correct source attribution.
4. Report which tests were ACTUALLY executed, which were blocked and whether final output is a WebM preview, MP4 deliverable, or editable composition only.
5. Do not publish, send correspondence, assert government endorsement or move any controlled engineering record without recorded human authorization.

## Asset Reliability AI built-in proof-of-concept
Open **/motion-studio/** from the locally served frontend or corresponding authenticated deployment. A stand-alone browser editor exists to load narration, edit three scenes, scrub/replay, save a JSON project and create a genuine WebM when browser capture is supported. The editor does not yet render MP4 itself, persist user projects on the backend, open source documents, generate narration, or represent a customer-controlled release.

### Local MP4 conversion (only if FFmpeg is installed)
\`\`\`bash
ffmpeg -i motion-draft.webm -c:v libx264 -pix_fmt yuv420p -r 30 -c:a aac -ar 48000 -movflags +faststart motion-draft.mp4
\`\`\`
Check the decoded output and full narration before publication. For voice-over audio, browser export requires Web Audio / MediaRecorder support; inspect the exported file, as recording behavior varies by browser.

## Next engineering implementation
Integrate a governed composition registry, upload validation, protected drafts, resource limits, an isolated FFmpeg/Remotion renderer, queued jobs, render-progress API, controlled download permissions, bilingual subtitle tracks and explicit human publishing approval. Evaluate Remotion licensing for commercial and enterprise use before installing it. Avoid expensive rendering inside the main synchronous request or unrelated Vercel static frontend.


## 22 October 2026: implementation status and real-data handoff

**Implemented in this draft PR (not merged):**
- Standalone responsive HTML editor: `frontend/public/motion-studio/index.html`.
- CSP-compatible local assets: `studio.js`, `studio.css`. No external audio/media upload.
- UI lets authorized users export a **source-linked** `motion-evidence-v1` JSON manifest, load it in Motion Studio, edit three scene texts, and export it for local rendering.
- Python CLI: `scripts/motion_studio_render.py`, `motion_studio_frames.py`. With a local TTF/OTF font, Pillow, FFmpeg and FFprobe, it builds sequential 30 fps PNG frames, then creates H.264 MP4 (yuv420p), AAC 48 kHz with full source audio and an output status of **DRAFT_REQUIRES_HUMAN_REVIEW**. Audio metadata determines final duration when supplied.
- For Arabic, use a font with Arabic glyphs and a Pillow build with libraqm. The script refuses Arabic rendering when shaping is unavailable, rather than producing disconnected letters.
- Browser preview/export remains WebM only. Browser WebM audio synchronization requires playback verification. MP4 uses an independent deterministic frame timeline and checks frame/audio duration within one frame.
- Human publication / official correspondence is **not implemented**; this software deliberately has no authorization-bypassing release route. Final controlled release needs a separate owner-approved workflow.

### Authoritative source connections

- **Asset Reliability AI:** an authenticated user opens the Executive Overview; the action becomes enabled only for a stored run with a report and an independent run-level evidence check. It exports a headline derived from the actual owned run and a citation to that report's version/ID. The video remains a draft and is not a certification of predictive accuracy.

No source file content or API token is sent to a cloud model/renderer by these flows. Imported snippets and project JSON remain on the user's device except for any deliberate user-controlled downloads. Local MP4 rendering requires the operator to run the commands in an approved environment.

### Local renderer command

```bash
python -m pip install Pillow
python scripts/motion_studio_render.py \
  --manifest motion-evidence-draft.json \
  --font "/path/to/approved-arabic-font.ttf" \
  --audio "/path/to/voiceover.wav" \
  --output motion-review-draft.mp4
```

Omit `--audio` for a silent draft using the manifest duration. Do not install licensed fonts from unapproved internet sources. The worker needs `ffmpeg`, `ffprobe`, available disk space for frames, and an encoding environment with libx264. Existing files will not be overwritten.

For an established frame renderer, replace `--font` with `--frames "/path/to/frame-directory"` containing sequential `frame-000000.png` etc. The encoder checks the exact total frame count and optional narration duration.

### Mandatory verification before PR approval

1. Run `python scripts/test_motion_studio_render.py` and platform frontend typecheck/unit tests.
2. Run browser smoke tests on the correct local preview/server with supported Chromium.
3. Execute a real render on both languages, inspect the full MP4 with sound, record codec/size/duration evidence and compare visual content with the source manifest.
4. Verify confidentiality, access control and downstream external processing restrictions. Video exports remain drafts.
5. Design a controlled, durable local/private render job runner with owner/tenant scoping and a human approval-linked publishing transition; do not run untrusted FFmpeg inputs inside serverless API functions.
6. Test failure/recovery, resource quotas, max three-minute videos, malformed audio, insufficient font shaping, and mixed Arabic/Latin technical IDs.

**Hosting constraint:** SaaS Vercel serverless requests cannot be assumed to perform long-running motion rendering; use a separately provisioned authorized worker. RMD Vercel preview is static frontend only; local RMD FastAPI/backend must be available for live data.

This is an integrated draft workflow and runnable local renderer, not a claim that a hosted one-click MP4 render or formal publication approval has been delivered.
