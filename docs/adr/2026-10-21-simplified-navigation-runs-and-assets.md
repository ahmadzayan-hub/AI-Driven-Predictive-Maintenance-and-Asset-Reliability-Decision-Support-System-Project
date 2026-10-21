# Simpler navigation; Runs and Assets get the KPI-first treatment

Date: 2026-10-21 · Status: Accepted

Follows the [colourful KPI-first dashboard decision](2026-10-21-colourful-kpi-first-dashboard.md)
and amends the sidebar grouping in ADR 0023.

## Context

The owner asked for the same treatment on Runs and Assets, a simpler
navigation, and a size audit first, because the interface budget had almost
no headroom (JS total 184.8 of 185 KB, CSS total 23.3 of 23.5 KB, CSS first
load 9,973 of 10,000 bytes).

## Size audit

Measured with the build's own gzip (level 9) and a source map of the main
bundle:

- **The main bundle is mostly React DOM** (170 of 246 KiB before compression).
  Replacing it is out of proportion to the gain and is not done.
- **Unused strings:** 18 keys in each language had no reader (an old greeting,
  three old suggestions, two run messages, and others). Removed; JS total
  fell by 0.8 KB. Keys built at run time (`event.*.failed`) were checked and
  kept.
- **Unused CSS:** none. Every class without a literal use is a modifier built
  at run time (`badge--${status}` and similar).
- **Moving view-only rules out of the first-load sheet** was tried and
  reverted: the first load fell 0.3 KB but the total rose 0.6 KB, because small
  files compress worse.
- **Duplicate rules:** `miyaar.css` re-declared eleven properties that
  `app.css` already set for the sidebar, rail, navigation buttons, search
  button and panel titles. Merged where no media query depended on the
  override; the header was left alone because its phone padding does.
- **One token for each category hue** (`--violet`, `--magenta`) replaces six
  literal copies.

The CSS limits are unchanged. Room for new styling came from removing
interface (group headings, an eyebrow, three capability blurbs), not from a
higher limit.

## Decision

1. **Navigation** has three groups, by task, with a colour and a divider
   instead of a heading: decide (Overview, Asset Intelligence, Dashboards,
   Approvals), prepare (Datasets, Analytics), assist (Workspace, Memory,
   Activity, Preferences). Preferences joins the assist group. Every view keeps
   its own icon; Dashboards gains a chart icon and Activity uses the clock.
   The phone bar holds Overview, Assets, Dashboards and Workspace, with More;
   it shows "Assets" because the full name wrapped onto two lines.
2. **Runs** replaces its introduction and the flow sentence with four coloured
   steps: Upload, Check columns, Run the agents, Approve and explore. The
   model and file-limit notes fold under "Files, limits and models".
3. **Assets** shows measures as family-coloured tiles with the value first. A
   reason stays on a tile only when it explains a verdict; "not assessed" is
   explained once, in "About these figures". The eyebrow and the three
   capability blurbs, which repeated the subtitle, are removed.
4. **The executive card keeps a unit with its number** (a non-breaking space),
   so "399.65 h" no longer wraps "h" onto its own line.

## Consequences

Measured on the same fictional 240-record runs, old build against new:

| View | Visible words | Key element from top (desktop / phone) |
| --- | --- | --- |
| Runs | 182 → 79 | Goal field: 321 → 233 px / 345 → 298 px |
| Assets | 533 → 300 | First KPI: 902 → 750 px / 1,695 → 1,216 px |

On Assets the repeated "no display target" sentence went from 14 to 0. On a
phone the first Assets KPI is still below the first screen, because the
screening findings come first.

Budget after the change: JS total 183.6 of 185 KB, CSS total 23,449 of 23,500
bytes, CSS first load 9,989 of 10,000 bytes. The CSS margins are about 50 and
10 bytes. The next visual change must remove something first.

## Verification

Unit tests: Assets family tiles and the folded "no target" note; the Runs steps
and the folded limits. Each was watched failing on the old component.
End-to-end: the phone bar's five labels, and the sidebar's three groups, no
headings and unique icons. Counts for the full run are in README.md under
Testing.

## Not done

Native iOS or Android packages (see the
[reading-test protocol and native note](../design/2026-10-21-manager-reading-test-protocol.md));
Datasets, Memory and Activity views; a reading test with managers.

## Addendum, 2026-10-21: Assets on a phone

The first KPI was still below the first screen on a phone. The measures now
come straight after the dataset and state boxes, before the screening and
model notes that qualify the run, and on screens up to 800 px the dataset
name spans the row with the two state boxes side by side beneath it. On the
same fictional run the first KPI moved from 1,216 to 633 px on a 390 × 844
phone (fully visible) and from 750 to 454 px on desktop. At 320 px it is
still below the first screen. No horizontal overflow at 320 or 375 px in
English or Arabic. Paid for by removing a dead selector guard and a margin
left from the removed eyebrow: CSS total 23,499 of 23,500 bytes.

Seen while checking, not changed here: the population label ("all records")
arrives from the server in English on the Arabic page, and Assets formats
values with Arabic-Indic digits while the rest of the interface uses Latin
digits.
