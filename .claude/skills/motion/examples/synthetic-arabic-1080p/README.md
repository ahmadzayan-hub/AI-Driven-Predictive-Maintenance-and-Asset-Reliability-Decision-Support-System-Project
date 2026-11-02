# Synthetic Motion example

Synthetic review example, prepared 2026-11-02. It reuses Miyaar's existing
renderer; it is not another
video application or an installed agent plugin.

The silent Arabic clip is 4 seconds, 1920 x 1080, 30 fps, H.264/yuv420p.
Its only figure, 42, is fabricated test data recorded in `synthetic-values.csv`.
The spec, transcript, poster and MP4 contain no operational dataset.

## Use with an existing Miyaar checkout

Read that checkout's `AGENTS.md`, `CLAUDE.md` and
`.claude/skills/motion/SKILL.md` first. The existing Claude agent definition is
`.claude/agents/motion-designer.md`. A compatible local coding agent can read
these files explicitly; this does not grant execution permissions or prove that
any agent has adopted the workflow. Do not replace global agent configuration.

With already installed Node, FFmpeg and ffprobe on PATH, run this from PowerShell:

```powershell
& './verify.ps1' -MiyaarRoot '<existing Miyaar checkout>'
```

Use this folder as the current directory, or supply the full path to `verify.ps1`.
The command validates the fixture against the existing source checker, inspects
the MP4 streams and decodes the existing video. It does not render or download.
The checker and renderer must be the trusted project files reviewed locally.

Example request for a compatible local agent:

> Read the repository instructions and existing Motion skill. Validate this
> synthetic example using `verify.ps1` and the existing Miyaar checkout. Inspect
> its supplied poster and clip. Keep all outputs local and use only the installed
> tools. Report exactly which checks ran; do not call another model.

## Validation and limits

Original validation matched the fixture figure, decoded the full MP4 and inspected
the poster, review sheet and two decoded frames. The settled value was 42 and the
inspected Arabic text was connected and aligned. Full visual playback and audio
listening were not performed; the clip has no audio. This is one synthetic sample,
not a general Arabic or production-readiness certification.

The original run used Node 24.14.0, Playwright 1.62.1, Chromium 151.0.7922.34
(revision 1234), and an installed FFmpeg 8.0 Gyan Essentials build. These versions
are evidence, not an installer. No runtime binaries are redistributed here.
The FFmpeg build reported GPL-3.0-or-later. Runtime and project licenses retain
their own terms. Remotion was not installed; its runtime license is not MIT.

For a later new render, review the current renderer and use a fresh output path:
its CLI accepts `<spec> <mp4>` or `<spec> --check`, and overwrites an existing
output. It has no `--audio` flag. Render one job at a time; no model or browser
downloads are needed for the already reviewed local setup. If execution is denied,
report the denial rather than bypassing it. Controlled real-data videos must use
the project's authenticated draft, independent review and approved-render workflow.

This folder follows the existing Motion examples convention. The other examples
are English/Arabic sales specs; this one adds a tiny self-contained synthetic
source, an already rendered silent clip, its poster/transcript and a decode check.
It does not duplicate or replace the renderer, Motion Studio or agent instructions.

## Provenance and licenses

Project instructions, composition and renderer remain governed by the repository
root LICENSE (Ahmad Zayan, all rights reserved), not MIT. The owner authorized
publishing these synthetic project deliverables. No third-party source, browser,
codec runtime or font binary is included in this folder.

The reviewed renderer is Git blob `818363c8f247f37dc70c34a1eedbfb1b07164054`;
the composition is `e38452c4a9f2fc15bfe0c668940af66d9a9c94c3`. The renderer can
embed installed Fira Sans Latin weights during rendering. The inspected
`@fontsource/fira-sans` 5.3.0 package declares OFL-1.1; its license SHA-256 is
`18aabf190848725e2576eefb5c29ba06aac1029d02132252a7f312eac2e50cf3`.
The dark composition uses a Fira Sans / Noto Sans Arabic / Segoe UI / DejaVu Sans
fallback stack. The actual Arabic platform-font choice was not captured, so
this record does not assert an exact resolved typeface. The outputs contain
rasterized text, not embedded fonts. See the [OFL output FAQ](https://openfontlicense.org/ofl-faq/)
and [Microsoft's bitmap/video guidance](https://learn.microsoft.com/en-us/typography/fonts/font-faq).

Playwright 1.62.1 declares Apache-2.0. The installed FFmpeg 8.0 Gyan Essentials
build reports GPL-3.0-or-later, including its enabled optional components; see
[FFmpeg's license explanation](https://ffmpeg.org/legal.html). These are runtime
provenance records, not a license granted for redistributing those binaries.
Remotion, GSAP and external video/model services were not used for this fixture.

No production promotion, real-data upload or provider activation is included.
