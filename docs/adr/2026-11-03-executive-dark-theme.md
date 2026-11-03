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

## Slice 2: the Command Centre after the references (2026-11-03)

The owner approved raising the interface ceilings to 282 KB of script and
41 KB of style ("موافق", 3 November 2026). This slice uses part of that room.

1. **KPI tiles with icons.** Each controlled measure shows an icon for its
   kind: a pulse for percentages, a clock for hours, a chart for money. Each
   tile also has a cyan-to-violet top edge and a soft glow.
2. **Options as cards.** The decisions that need attention appear as
   numbered cards, each marked "Proposed" (مقترح). The words and the order
   still come from the run.
3. **Jarvis beside the brief.** A glowing cyan and violet orb, with "Ask
   about this report" (اسأل عن هذا التقرير), sits next to the recommendation
   and opens the assistant. The orb is decoration only. It stops turning when
   reduced motion is set.

**Measured:**

| | Before | After | Change |
| --- | --- | --- | --- |
| Script total | 277,617 B | 277,913 B | +296 B |
| Style total | 38,019 B | 38,537 B | +518 B |

The ceilings are now 282 KB and 41 KB.

**Still not done:** the options do not yet show scope, downtime, trade-off and
impact rows; the run does not record those fields, and they will not be
invented. The baseline comparison table and the shorter navigation labels also
remain. The navigation change touches every route test, so it gets its own
slice.

**Verification:**

- The overview unit tests pass.
- Screenshots were taken on the synthetic demo server, in English and Arabic.

## Slice 3: shorter navigation labels (2026-11-03)

The workflow groups take the short names of the reference sidebar. The order,
the numbering and the items inside each group are unchanged.

| Before | After | Arabic before | Arabic after |
| --- | --- | --- | --- |
| Data sources | Data | مصادر البيانات | البيانات |
| Analysis & evidence | Analysis | التحليل والأدلة | التحليل |
| Priorities & actions | Actions | الأولويات والإجراءات | الإجراءات |
| Reports | Reports | التقارير | التقارير |

"Ask Miyaar" keeps its name: renaming the assistant is a product decision for
the owner. The reference's Predictions, Assets, Studio and Settings entries
are not added; they would be links to pages that do not exist as separate
routes. Strings only, so the bundle size barely moves.

**Verification:** the overview and task-first end-to-end tests check the new
labels on desktop and phone, in English and Arabic.

## Slice 4: Jarvis conversation view (2026-11-03)

Style only, no new strings and no new markup. The input and output panels get a
glass look with a thin cyan edge; the asked question shows as a chat bubble;
the answer's measures become glowing tiles with a cyan top edge and a larger
value; the quick questions become pills. Every figure and sentence still comes
from the calculated answer.

**Measured:** style total 38.5 KB to 38.7 KB of the 41 KB ceiling; script
unchanged at 277.8 of 282 KB.

**Not done:** a separate answer card with metric chips and a baseline table, as
in the reference, needs fields the answer does not carry; they are not invented.

**Verification:** the Jarvis workspace and dashboard end-to-end tests pass (7 of
7, with axe, English and Arabic); screenshots taken on the synthetic demo
server.

## Slice 5: the assistant is "Ask Miyaar" everywhere (2026-11-03)

The owner decided the assistant carries one name. Every visible "Jarvis" and
"Jarvis OS" becomes "Ask Miyaar" (اسأل معيار): the workspace title, the dashboard
open, refresh and close buttons, the launch button, the selection notes on the generated
page, and the orb labels (now MIYAAR). Code names, file names, routes and the
hackathon documents keep "Jarvis" as history. Strings only.
