# Two-way breakdown matrix on the designed page

Date: 2026-11-06 · Status: Accepted · Owner request: "Continue next developments", choosing the two-way breakdown matrix

## Context

The owner's station electrical survey was read as a matrix: condition grade against a
proposed criticality, counted in lines. The designed page could rank one breakdown at a
time but could not cross two. The query engine already groups by two columns.

## Decision

1. **A registered `matrix` component** in `server/layout_plan.py`: two different text
   columns with 2 to 50 groups each, never a date, exactly one figure per cell, and at
   most 120 cells (`MAX_CELLS`). Anything else is refused with a reason, like every
   other binding. The cells are the query engine's own groups; the planner computes
   nothing.
2. **The rule planner proposes one only when it tells something.** It crosses the main
   breakdown with the drivers column and counts records ("a count, not a risk ranking").
   `crossed(table, a, b)` refuses a nested pair, where each value of one column sits
   inside a single value of the other (an asset ID inside its class), because that
   fills one cell per row and shows nothing new. The matrix comes after the
   "not available" notices, so with ten sections it is the one dropped, never a stated gap.
3. **A model planner may propose a matrix** with another measure (a sum or an average);
   the same contract applies.
4. **On the page** the matrix is a table: rows and columns in both languages, each
   cell shaded by its size, an empty pair shown as 0 for a count and "No value"
   otherwise, and a row header that filters the page to that group.

5. **In the brief and its documents** (added the same day). The executive brief carries
   `crosstab`: the same pair the rule planner picks on the whole run, so a filter never
   changes which columns are crossed, counted over the brief's own scope by the query
   engine, with one cited evidence item for the total (`executive.crosstab.records`). It
   is part of the snapshot digest, so a review binds to it. The HTML report and the Word
   file add a section "Records across two breakdowns" with every cell; the narrower
   breakdown becomes the columns, and a matrix wider than 8 columns either way is left out.

6. **Slides, video and picking** (completed the same day). The deck stays six slides: the
   "Biggest risks or opportunities" slide adds the matrix when it has at most 6 rows and 6
   columns, and otherwise one line pointing to the report. The video adds a `matrix` scene
   after the priorities: a grid of at most six rows, with no numbering because a row is not a
   rank, and narration that says only the cited total. On the page the reader can change the
   two columns (text columns with 2 to 50 groups; one column twice is ignored), and a pair
   with more than 120 cells says so instead of drawing a cut-off table.

## Consequences

- Tests: 4 server cases (proposed on crossed data, not on a nested pair, cells add up to
  the records, bad bindings refused) and 1 page test (every pair, an empty pair as zero,
  a row picks its group).
- Interface: total scripts 285.3 of 286 KB, inside the approved ceiling; styles 39.3 of 41 KB.
- Brief and documents: 4 cases (cells count the scope and are cited, a filter narrows the
  counts not the columns, no informative pair gives no matrix, both documents show every
  cell in English and Arabic).
- Contrast: cell text against the strongest shade is at least 8.75:1 in the light theme
  and 6.94:1 in the dark theme, calculated from the theme tokens (not an axe run).
- Slides and video: 2 cases (six slides with every cell in both languages; the scene cites
  the total and is absent without a matrix). Films rendered in English and Arabic from the
  synthetic survey and the grid checked by eye; the first render showed only the first row
  and the second placed the grid in the background layer (a class-name clash), both fixed.
- Page: 1 more case (changing a column re-queries; the same column twice is refused).
- Not done: a picked pair is not saved with the layout; the HTML, Word, slides and video
  use the planner's pair, not the reader's pick.
