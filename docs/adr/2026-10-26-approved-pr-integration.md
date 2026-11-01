# Approved integration of the remaining review branches

Date: 2026-10-26. Status: approved for branch publication and merge after verification; no deployment.

## Context and decision

The owner explicitly instructed: “Approved and merge all PR”. Scope is the six open
Miyaar pull requests #29, #30, #31, #45, #61 and #63. Integrate their histories into
one review candidate based on main `9fa13b4240c64be78669ed09b630ad5929ea26d4`, then
merge the verified tree through #63. Preserve every original PR head as an ancestor;
retarget #45 from its obsolete feature base to main. Never force-push or delete branches.

- #29/#31: retain the real Arabic frame/H.264/AAC synthetic integration check.
  Current main already implements sequential Pydantic tools with compatibility
  fallback and localized motion errors; retain those newer implementations.
- #30: current main already contains the release behavior and subsequent fixes.
  Preserve canonical API errors, durable storage, specialist publication guards,
  owner-scoped evidence and current UI. Retain the historical portfolio briefing
  with an explicit historical label and the compatible API assertions.
- #45: keep all visual alternatives inside test fixtures; no theme selection is implied.
- #61: integrate complete phone chart labels and the actual saved-report inspector.
  Preserve current approved tokens; archive the older Stitch brief separately.
  Desktop report tabs are vertical at 900px and above, with Up/Down navigation;
  smaller widths retain horizontal, RTL-aware arrows. Resize updates ARIA orientation.
- #63: retain the reviewed statistical and forecast wording, with all calculations,
  evidence, persisted reports and human approval unchanged.

## Test and deployment boundaries

The media script is outside normal test discovery. A dedicated CI job explicitly
requires RAQM, FFmpeg, ffprobe and DejaVu before running it. Pillow 12.3.0 is an
isolated test dependency, not a new core application dependency. The generated tone
checks encoding, not spoken Arabic quality. Browser regressions exercise English
and Arabic keyboard navigation while resizing the real report journey. Consolidate
redundant tab CSS instead of raising any bundle ceiling.

Local verification and its skips are recorded in README. Hosted checks must run on
the published integration head; old PR green checks do not validate the new tree.
Production and exact review-branch automatic Vercel deployment remain disabled.
No production database, private data, report approvals, live restart or model calls
are authorized by this merge instruction.
