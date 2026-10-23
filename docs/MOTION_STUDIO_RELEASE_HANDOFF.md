# Motion Studio — implementation and release handoff

**Status:** Implemented source on main, with an opt-in local MP4 queue. Not a deployed production video-release service. See [the source-bound review decision](adr/2026-10-23-report-motion-access.md).

## What is implemented

- Browser editor at `/motion-studio/index.html` with local voice-over, 3-scene composition, 16:9/9:16, scrub/preview, editable JSON, source-manifest import and real WebM capture where browser supports it.
- The editor stores no source records on its own backend and makes no external media upload.
- Source export from the authenticated host application: RMD Knowledge source/chunk, or the SaaS executive run that passed the existing independent validation checks.
- Evidence manifest `motion-evidence-v1`: exact source IDs, revision, locator, source status, language, scene roles, duration and explicit unissued draft state.
- Local Python frame renderer `scripts/motion_studio_frames.py`: PNG sequence at 30fps with an owner-supplied font (Arabic requires Pillow RAQM).
- Local MP4 worker `scripts/motion_studio_render.py`: FFmpeg H.264, yuv420p, constant 30fps, AAC 48kHz when audio is supplied, and duration parity within one frame. Never calls a remote encoder, issues a letter, sends a message or publishes.

## Running locally

Requirements: Python 3.11+, Pillow (with libraqm for Arabic), a locally approved font file, ffmpeg, ffprobe. Verify all binaries and legal rights to font/audio before proceeding. The command must run on an **approved local or isolated worker** with sufficient disk and CPU; not the static Vercel frontend.

1. Sign in to the actual parent platform.
2. In RMD Knowledge choose the authorized cited excerpt, or in SaaS Executive Overview select an evidence-checked analysis; download the motion JSON. This is a draft, not proof the prose is objectively correct.
3. Open `/motion-studio/index.html` and import that JSON with the **Trusted application evidence pack** control. Edit visually, record local narration and preview.
4. Export an updated `motion-evidence-draft.json`. Have an engineer/analyst **independently confirm every statement and figure against the source**, since the manifest's source pointers are not themselves proof that edited prose is accurate.
5. For local MP4 encoding, save the manifest to a controlled workspace and run:

```bash
python scripts/motion_studio_render.py \
  --manifest /secure/workspace/motion-evidence-draft.json \
  --font /approved-fonts/approved-font.ttf \
  --audio /secure/workspace/approved-narration.wav \
  --output /secure/workspace/draft-video.mp4
```

Omit `--audio` only for a deliberately silent video. Alternatively provide trusted pre-rendered `--frames` instead of `--font`. Do not use both. Adjust paths for Windows. Audio duration takes precedence over manual duration and must be 3–180 seconds.

**Output is a DRAFT**, not a release authorization. Check all scenes against the narrative and watch the *full* exported MP4 with audio. Validate Arabic shaping, subtitles if any, 16:9/9:16 sizing, narration sync, no empty frames, licensed media, and source citations. Sign-off and official distribution must use the parent app's existing human authority workflow, not a new self-approval toggle.

## Validation commands

```bash
python scripts/test_motion_studio_render.py
npm --prefix frontend test
npm --prefix frontend run build
```

For RMD also run `uv run pytest -q` and the documented RMD authenticated browser suite. For SaaS also run its Playwright checks and tenancy suites. **These commands are instructions, not claims that they passed.**

## Outstanding release blockers

- Each new release still requires CI on its exact commit; historical passes do not validate later changes.
- An opt-in local queue, persistent local media, authenticated preview and independent internal review now exist in `server/motion_local.py` and the Motion API. These are not a durable distributed production worker or externally authorized publication service. Rendering remains disabled unless explicitly configured; no infrastructure is enabled by this change.
- Rendering final videos with multimedia overlays, per-word captions, transitions and source-verification overlays still requires additional work.
- The internal review gate checks a different authorized reviewer and the current report/source hashes. An existing reviewer must already have live source access; platform admin does not grant private-pack membership. Official issuance/distribution remains separate and `publication_allowed` stays false.
- Real-device Arabic playback and exported-audio end-to-end QA remain unverified.
- Do not claim this is a finished enterprise MP4 production system until those are closed.
