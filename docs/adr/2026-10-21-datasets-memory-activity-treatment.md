# Datasets, Memory and Activity get the same treatment

Date: 2026-10-21 · Status: Accepted

Follows the [navigation, Runs and Assets decision](2026-10-21-simplified-navigation-runs-and-assets.md).

## Context

The owner asked for the colourful, low-text treatment on the three remaining
working views. The CSS budget had about 50 bytes of headroom in total and 10
on first load, so every added rule had to be paid for by a removal.

## Decision

1. **Shared coloured tiles.** The hued tile rules move from the Overview sheet
   to the shared `kpi.css`, keyed by hue name (`teal`, `violet`, `magenta`)
   instead of tile name. The plain amber "attention" background, always
   overridden by the hue rule, is dropped; its border colour moves into the
   hue rule. Nothing changes on Overview.
2. **Datasets.** The introduction is removed. The allowance sentence becomes
   two tiles (datasets stored, storage used), and the file limits fold under
   "Files and limits". A dataset row now wraps its buttons below the name
   on a phone instead of breaking the name letter by letter.
3. **Memory.** The subtitle, the internal keys (`memory_1` and so on) and the
   "destructive actions require confirmation" note are removed; the
   confirmation itself is unchanged, and the keys still label the edit and
   delete buttons for assistive technology. Category tags take a hue: profile
   and preferences violet, work and projects magenta, others teal.
4. **Activity.** A health line is explained only when something is wrong; the
   two storage notes under the meters are removed; the three meters take one
   hue each, and the near-limit warning colour still wins. The statement that
   the feed shows "status only, never private reasoning" stays: it is a
   guarantee, not decoration.

Memory and Activity share one pair of hue rules in `session.css`. Five strings
per language were removed and two added.

## Consequences

Measured on the same fictional data, old build (`fe27c2c`) against new:

| View | Visible words | First item from top (desktop / phone) |
| --- | --- | --- |
| Datasets | 126 → 78 | First dataset: 320 → 363 px / 400 → 351 px |
| Memory | 103 → 88 | First entry: 372 → 348 px / 639 → 616 px |
| Activity | 107 → 75 | First event: unchanged (258 / 298 px) |

On desktop the first dataset sits 43 px lower because the tiles now come
first; that is the trade for showing the allowance as figures.

Budget after the change: JS total 183.2 of 185 KB; CSS total 23,493 of 23,500
bytes; CSS first load 9,984 of 10,000 bytes. **The CSS total has 7 bytes
left.** No further visual work fits without removing something or a decision
to raise the limit.

## Verification

New unit tests: Datasets tiles and folded limits; Memory category hues and
hidden keys; Activity health explanations only on a fault, and meter hues.
Each was watched failing on the old views. Full counts are in README.md under
Testing.
