# Colourful, minimal dashboards on desktop and phone

Study and first delivery, 2026-10-21. Decision record:
[ADR](../adr/2026-10-21-colourful-kpi-first-dashboard.md).

## 1. The ask and what it means here

The owner asked for colourful dashboards, less text, a simpler interface, and
strong mobile and desktop applications. Read against this product's rules:

- **Colour must not lie.** Red, blue and green already mean bad, okay and good
  against a declared target. New colour can name a group; it cannot suggest a
  verdict nobody set.
- **Less text means less on first view, not less evidence.** Every figure still
  links to its formula, population and coverage, one click away.
- **"Mobile and desktop applications"** means the existing installable web app
  (PWA) on both form factors. Native store packages would double the code to
  maintain and add nothing a pilot needs yet; they are out of scope.

## 2. Measured starting point

Method: a fictional 240-record fleet dataset, one governed run, the executive
overview opened at 1440 × 900 and 390 × 844 in Chromium with reduced motion.
A script records where the first KPI card starts, how many cards fit whole on
the first screen, and how many words are visible without opening anything.
The "before" build is commit `efb6eb1`; "after" is this change, against the
same run.

| Measure | Before | After |
| --- | --- | --- |
| First KPI, phone (px from top; screen is 844) | 1,322 | 696 |
| First KPI, desktop (px from top; screen is 900) | 818 | 659 |
| Visible words, desktop | 666 | 454 |
| Cards repeating "no display target is configured" | 14 of 14 | 0 |

On desktop the first row's figures and statuses are now on the first screen;
the cards' evidence links still fall just below it. These are one dataset and
two viewports, not a usability study: they show what moved, not how much
faster people read.

## 3. Principles applied

1. **Figures first.** Filters fold until one is active. The hero is one band:
   title, readiness, and the record count on one line.
2. **Group, then colour the group.** The KPI register names each measure's
   family (reliability, work execution, cost and consequence). Each family has
   one hue for its band, heading and meter, in light and dark themes.
3. **Say a thing once.** Shared notes (scope, colour legend, snapshot) move to
   one "About these figures" fold. A reason stays on a card only when it
   explains that card's verdict.
4. **Show proportion without reading.** Percent measures get a thin meter in
   the family hue. It shows the value's share of 100%, not progress to a target.
5. **Phones are not small desktops.** Two KPI columns, scrollable tabs, a
   compact hero and smaller secondary buttons.

## 4. Constraints honoured

- WCAG 2.2 AA: axe and a rendered-contrast check pass in both themes, both
  languages and both viewports.
- English and Arabic for every string, with right-to-left layout.
- The interface budget. The CSS total limit rose from 23 to 23.5 KB; the
  ADR records why. JS total is 184.8 of 185 KB, so the next feature needs
  room made first.
- No new dependency and no change to any calculation.

## 5. Second phase, delivered 2026-10-21

Navigation, Runs and Assets, after a size audit
([decision](../adr/2026-10-21-simplified-navigation-runs-and-assets.md)):
Runs visible words 182 → 79, Assets 533 → 300, the repeated "no target"
sentence on Assets 14 → 0, and the sidebar in three coloured groups without
headings. A protocol for testing whether this helps managers is in
[the reading test](2026-10-21-manager-reading-test-protocol.md).

Third phase, the same day: Datasets, Memory and Activity
([decision](../adr/2026-10-21-datasets-memory-activity-treatment.md)): visible
words 126 → 78, 103 → 88 and 107 → 75. The CSS total now has 7 bytes left.

## 6. Next phases (not started)

1. **Readers:** run the reading test with three or four maintenance managers on
   their own data.
2. **Budget:** any further visual change needs something removed first, or a
   decision to raise the CSS limit.
3. **Arabic Assets:** the KPI population label arrives in English from the
   server, and Assets uses Arabic-Indic digits where the rest of the app uses
   Latin. (The first Assets KPI is now on a phone's first screen at 390 px.)
