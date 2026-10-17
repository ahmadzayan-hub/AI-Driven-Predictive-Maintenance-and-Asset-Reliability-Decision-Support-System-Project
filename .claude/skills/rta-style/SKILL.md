---
name: rta-style
description: The user's house style for agent outputs, taken from their own executive-dashboard work: a red brand bar, navy and grey charts, tiles with a coloured leading edge, system fonts with Arabic support, light and dark. Colours, type and layout only, never a logo, name or data of any organisation. Use when a dashboard, evaluation report, clip, page or Claude Dashboard should look like the user's RTA-style work, or when the user asks for "RTA style".
---

# rta-style

A theme, not a brand. It reproduces the look of the user's own executive dashboards (colours, type and layout motifs) so agent outputs match their work. It carries **no logo, wordmark, emblem, organisation name (in any language) or data** of the authority whose palette inspired it. Nothing made with it may say or imply that it comes from, or is endorsed by, that authority.

## Files

| File | What it is |
| --- | --- |
| `tokens.json` | The single source: light and dark palettes, font stack, radius, shadow, and the contrast pairs the tests check |
| `build.py` | Writes `tokens.css` from `tokens.json` (run it after any edit) |
| `tokens.css` | CSS variables (light, dark by the reader's setting, `data-theme` to force one) and shared components: `.brandbar`, `.page`, `.grid`, `.card`, `.tile`, `.pill`, `h2` with a leading bar |

`tests/test_rta_style.py` fails when `tokens.css` is stale, when a text pair falls below 4.5:1 or a chart colour below 3:1 (WCAG 2.2 AA) in either mode, or when a themed output carries a name or logo.

## The look

- **Brand bar:** red (`--bar`), a 4px deeper-red edge, white text; a small upper-case kicker (`.org`, for the *project or team name*, never an authority's) and a period line.
- **Headings:** `h2` with a 4px red bar on the leading side (it flips in Arabic).
- **Tiles:** white cards with a 5px leading edge in navy, red for the lead figure, or a status colour.
- **Charts:** red, navy, grey, amber, teal, green, in that order. Red marks the figure the reader should look at; navy carries the rest.
- **Status:** green, amber, red pills with on-colour text that passes contrast in both modes.
- **Type:** `system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Noto Naskh Arabic", Tahoma, sans-serif`. No web fonts to fetch.

## Where it is wired in

- **Offline dashboards:** `python .claude/skills/dashboards/render.py --spec spec.json --theme rta --out d.html`, or `"theme": "rta"` in the spec.
- **Motion clips:** `"theme": "rta"` or `"rta-dark"` in the clip spec (`.claude/skills/motion`).
- **Agent evaluation report:** `python scripts/evaluate_agents.py --html report.html` uses `tokens.css`.
- **Claude Dashboards:** map the variables onto the dashboard's own tokens (`--color-panel` ← `--surface`, accents ← chart colours), keep the brand bar and leading-edge tiles, and keep every figure's `data-source`.

## Rules

1. No logo, emblem, wordmark, name or abbreviation of any authority in a themed output, in English or Arabic, in text, alt text, file names or metadata.
2. No data that belongs to an authority unless the user supplied it for that piece of work, and then only where the work needs it.
3. Never present a themed page as official, and never use the theme to imitate an organisation's site, form or document.
4. Change colours only in `tokens.json`, run `build.py`, then run the tests.
