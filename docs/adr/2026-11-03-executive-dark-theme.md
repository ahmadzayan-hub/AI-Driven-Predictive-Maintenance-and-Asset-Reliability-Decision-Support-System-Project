# Executive dark theme by default, after the owner's reference designs

Date: 2026-11-03 · Status: Accepted (first slice)

## Context

On 3 November 2026 the owner sent five reference designs and asked for the
interface to match or exceed them. Four are Miyaar concept screens: Executive
Command, Recommended Actions, Jarvis Conversation and Motion Studio. One is a
generic AI assistant dashboard. All five share the same look:

- a deep navy background with cyan and violet glows;
- glass-like panels with thin bright borders;
- cyan for actions and violet for the second accent;
- a glowing Jarvis orb.

The product already had a dark theme, but it was muted and showed only when
chosen or set by the system. The light theme was what a first visit saw.

## Decision

1. **Dark is the default.** When no theme has been saved, the pre-paint
   script in `index.html` sets `data-theme="dark"`. Light and "follow the
   system" remain choices in Preferences and are remembered as before.
2. **New dark palette** (`frontend/src/shared/styles/tokens.css`, both dark
   blocks):
   - background `#050E1C` under cyan and violet radial glows;
   - panels `#0A1A2F` with cyan-tinted `#1E3A5A` borders;
   - accent cyan `#22D3EE`, with `#04121F` text on cyan buttons;
   - a hero gradient from navy to violet;
   - a header and navigation in deep navy with a cyan active state;
   - a soft cyan edge on cards.
3. **Jarvis accents move from gold to violet** (`#a78bfa`) in the core's
   stars, ring and waveform and in the agent map, to match the cyan and violet
   orb of the references.
4. **The content policy hash** for the pre-paint script is updated in
   `server/app.py` and `vercel.json`. `tests/test_content_policy.py` checks
   that it matches the source and the built page.

The figures, the words and the human approval gates are unchanged. The
references' sample numbers are not copied: every value on screen still comes
from the run.

## Not done yet

The references also show:

- KPI tiles with icons and sparklines;
- the Jarvis orb on the Command Centre with a question box;
- recommended actions laid out as option cards with scope, downtime,
  trade-off and impact;
- a baseline comparison table;
- a shorter navigation (Overview, Predictions, Actions, Assets, Data,
  Reports, Studio, Settings).

These need new markup and styles. The interface budget is at its limit (script
277.7 of 278 KB, style 38.1 of 38.1 KB), so they wait for the owner's decision
on a budget raise.

## Verification

- `tests/test_content_policy.py`: the new hash matches the source and the
  built page.
- Screenshots were taken on the synthetic demo server in English and Arabic:
  Command Centre, the designed page and a run, each in the new dark theme.
  The automated end-to-end suites still set their theme explicitly.
