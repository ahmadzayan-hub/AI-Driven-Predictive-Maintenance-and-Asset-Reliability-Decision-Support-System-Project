# A colourful, KPI-first executive dashboard

Date: 2026-10-21 · Status: Accepted

## Context

The owner asked for colourful dashboards, less text and a simpler interface on
desktop and phone. Measured against a fictional 240-record run (the
[study](../design/2026-10-21-colourful-minimal-dashboard-study.md) has the
method), the executive overview before this change:

- placed its first KPI 1,322 px down the page on a 390 × 844 phone, so a phone
  reader saw no figure without scrolling;
- placed it 818 px down on a 1440 × 900 desktop, with no card whole on the
  first screen;
- printed the same "no display target is configured" sentence on all 14 cards,
  inside 666 visible words.

## Decision

1. **The register names a family for each measure.** `Kpi(family=...)` takes
   `reliability`, `execution`, `cost` or `other`, is validated against
   `FAMILIES`, and is returned with each result. The grouping is part of the
   measure definition, not a browser guess.
2. **Family colours name a group, never a verdict.** Reliability is violet,
   work execution teal, cost and consequence magenta, other neutral. They
   colour the card's top band, the family heading and the coverage meter, and
   tint the card at 9%. Good, okay and bad keep their own colours and always
   carry a text status, as before.
3. **Text moves behind disclosure.** The eyebrow, the agent and attention help
   paragraphs, the footnote and the hero's "Selected records" label are gone.
   KPI scope, the colour legend and the snapshot note sit in "About these
   figures". A "no target" reason moves into the card's evidence; a reason that
   explains a verdict stays on the card.
4. **Filters fold until a filter is active,** on every screen. The count of
   active filters shows on the folded heading, and "Showing N of M records"
   still states the scope.
5. **Phone layout:** two KPI columns, a compact hero, scrollable tabs and a
   two-column filter grid.
6. **Overview tiles** take a hue per tile and per finding type, by the same
   rule: decoration names a category, the text states the value.

All new strings ship in English and Arabic.

## Budget

The CSS total limit rises from 23 to 23.5 KB gzipped. The family colours,
meter and phone rules cost about 0.3 KB after flat tints replaced gradients and
a dead rule was removed. Measured after this change: CSS total 23.3 KB, CSS
first load 10.0 of 10 KB, JS total 184.8 of 185 KB. Headroom is now thin on
both totals; the next visual change must pay for itself.

## Consequences

- On the same run, the first KPI starts 696 px down on the phone, inside the
  first screen, and 659 px down on desktop, where the first row's figures and
  statuses are visible. Visible words fell from 666 to 454 on desktop; the
  repeated sentence appears on no card.
- A server older than this change sends no family; every card then falls under
  "Other measures". Nothing is lost, but the grouping disappears.
- Tinted cards resolve to `color(srgb …)`, which the rendered-contrast check
  read as 0–255 channels and so as near black. The check now scales that
  format correctly; the okay blue on the tinted card measures 5.87:1, above 4.5.
- Charts stay single-colour on purpose: a series colour would compete with the
  verdict colours.

## Verification

`test_every_measure_names_a_dashboard_family_and_it_is_not_a_verdict` and
`test_the_register_holds_fourteen_measures` (Python); a unit test for family
grouping, the meter and the folded "no target" reason (Vitest), watched failing
on the old component. Counts for the full run are in README.md under Testing.

## Not done

Native iOS or Android packages (the product is an installable web app); the
sidebar and navigation; the Runs, Datasets and Assets views; the MTBF unit
wrapping onto its own line on narrow cards.
