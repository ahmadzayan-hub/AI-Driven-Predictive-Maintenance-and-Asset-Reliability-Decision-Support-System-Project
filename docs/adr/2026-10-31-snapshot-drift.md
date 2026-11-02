# Drift alerts between live-source snapshots (R5)

Date: 2026-10-31 · Status: Accepted (the owner asked for slice R5 on
31 October 2026).

## Context

A live source (ADR 0034) snapshots into a new dataset and starts an analysis
whenever its content changes. A changed file is not always a changed
business: an export can lose half its rows, rename a column, or switch a
unit. Before this change the analysis ran on it silently, and the reader had
no way to tell a real movement from a broken feed.

## Decision

1. **`server/drift.py` compares each new snapshot with the previous one**
   (`Connectors._drift`), using four rules with stated thresholds:
   columns added or removed; the row count at or below half, or at or above
   double; a numeric column's median moving by at least half its previous
   interquartile spread (any move when the spread was zero); a column's share
   of empty cells moving by 10 percentage points or more. A column is numeric
   when 90% of its filled cells read as numbers in both snapshots.
2. **The alert is a note, never a block.** The run starts as before. The
   note, in the connector's language, lists up to five findings and asks the
   reader to check the source before approving the results. It is stored
   where the connector already keeps its notes (`last_error`, shown beside a
   successful refresh, as the mapping note is), after any mapping note.
3. **The refresh result carries `drift`**, the findings with their figures,
   for the API and any later view.
4. No new table, column or interface string.

## Consequences

- A feed that breaks is named at the moment it arrives, before anyone
  approves a report built on it.
- The thresholds are fixed and simple, so an alert can be recomputed by
  hand; they are not tuned to any source and may be too strict or too loose
  for some feeds. Per-source thresholds would need the owner's numbers.
- Only consecutive snapshots are compared, not a longer history.
- The live path still has not been exercised against a real external host
  from this environment (its proxy blocks direct egress); the tests use
  recorded snapshots through the existing fetcher seam.

## Verification

`tests/test_drift.py` (9 tests): a stable snapshot raises nothing; columns
added and removed; rows halved and doubled, with the boundary; a median
shift at and below half the spread, computed by hand; empty cells moving ten
points and not one; the note in English and Arabic; and through the
connector engine: no drift on the first snapshot, a shrunken snapshot flagged
and still analysed with the note stored, and a steady refresh with no note.
