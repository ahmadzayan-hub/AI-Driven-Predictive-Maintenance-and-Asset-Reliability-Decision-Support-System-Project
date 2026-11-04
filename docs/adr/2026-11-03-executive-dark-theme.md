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

## Slice 6: the owner's review of the demo (2026-11-04)

The owner reviewed the deployed demo against the latest code and asked for five
changes. Each is taken as stated; nothing new is invented to fill a gap.

1. **The decision leads.** With an analysis to read, the Command Centre opens with a
   one-line next step, then the decision brief. The greeting card follows the brief
   instead of sharing the first screen. Four measures show; the rest sit under "More
   measures (n)". The decisions list shows the top three.
2. **Filters say what they are.** Above the filter panel, even when it is folded, the
   applied filters show by name ("Site: North"), with "Showing 60 of 240 records" and
   the Clear button. With none: "No filters: all records".
3. **The report travels with the question.** "Ask about this report" now opens
   `#/assistant/<run>`: Ask Miyaar opens its calculated workspace with that report
   selected through the same permission-checked call as a manual choice. Every answer
   shows its scope: data, records and filters. The view-only demo has no assistant
   session, so the link is not shown there rather than leading nowhere.
4. **Only supported questions are suggested.** "Predict failures tomorrow" is no longer
   offered. A note says what a reliable forecast would need: a validated model, dated
   failure history per asset and a stated horizon. Typed, the question still declines.
5. **The answer before the numbers.** A one-line answer ("Maintenance cost: 1,517,510.23,
   from 1,500 of 1,500 selected records.") comes before the figure tiles; references stay
   one click away. Figures show grouped, with at most two decimals; the full value stays
   in the references. This also fixed a raw float (`1517510.2300000011`) seen on a
   generated 1,500-row file.

**Not done, and why.** Two charts on the Command Centre: the brief carries no series,
so a chart would need a new query; the executive overview, one click away, has them.
The period of the data is not in Ask Miyaar's scope line because the data context
does not record it; it is not inferred.

**Verification:** verify 8 of 8; Ask Miyaar e2e 16 of 16; overview, task-first, demo,
responsive, accessibility, dashboard, metric colours and executive e2e 68 passed. Live
check on the local servers, desktop 1440 px and iPhone 13, English and Arabic: the
North filter, the report hand-over and the answer order, with no sideways scroll.
Voice: the consent and denied-permission paths are covered by e2e; real speech was not
tested in a headless browser.

## Slice 7: stage one of the owner's three-stage plan (2026-11-04)

1. **The period, from the data's own date column.** `server/period.py` reads the column
   the pipeline marked with the date role, and only ISO dates (YYYY-MM or YYYY-MM-DD).
   The brief's scope and Ask Miyaar's data context now carry `period` (from, to, dated
   records), computed over the selected records, so a filter narrows it too. With no date
   role it is null and the screen says "period not recorded"; it is never guessed from a
   column name. Tests: `tests/test_period.py`.
2. **Three lines a manager reads first.** Under the decision on the Command Centre: what
   is happening (the brief's scope line), the biggest risk or opportunity (the first
   calculated priority; the line is left out when there is none), and the decision needed
   (the first proposed decision).
3. **The analysis state, said plainly.** The Command Centre says whether a validated
   forecast exists: only a model that beat its baseline counts; otherwise "No validated
   forecast: observed data only". Each Ask Miyaar answer opens with its kind: calculated
   result, not enough data for part of it, or not supported (no calculation made). Load
   errors keep their existing message.
4. **Scope everywhere.** Ask Miyaar's scope line now reads data, records, period and
   filters. Dates are isolated as left-to-right so they read correctly in Arabic.

**Verification:** verify 8 of 8 (2,568 Python tests); Ask Miyaar e2e 16 of 16; live
path on desktop and iPhone 13 in English and Arabic: the period 2025-01-01 to
2026-04-01 on a generated 1,500-row file, the three lines, the forecast state.
