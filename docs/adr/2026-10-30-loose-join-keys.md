# Join keys that differ only in case or spaces

Date: 2026-10-30 · Status: Accepted, server side (gap analysis, *Several
datasets* row; extends ADR 0030). The interface control is a later slice.

## Context

A join compared text keys exactly, after trimming the ends. Maintenance data
often spells one asset differently in two systems: `PUMP-01` in the
maintenance system, `pump-01 ` or `Pump  01` in an export. Those rows found no
match, and the run only said how many rows went unmatched, not that most of
them were near misses. The gap analysis listed case-insensitive keys as
missing.

## Decision

1. **A join may declare `"match": "loose"`.** Text keys are then compared
   ignoring letter case (Unicode case folding) and runs of spaces, inside and
   at the ends. Numbers and dates compare exactly as before, as numbers and as
   periods. `"exact"` is the default; any other value is refused in both
   languages. A stack takes no key and ignores the setting.
2. **Nothing saved before changes.** Only a loose join records `match` in its
   declaration, in the run's stored joins and in the run's response. An exact
   join's declaration is byte for byte what it was, and a request that does
   not name `match` hashes as before, so idempotent replays still agree.
3. **A loose join cannot count a row twice.** Its lookup is checked for
   repeated keys after loosening: `P1` and `p1` in the joined dataset are one
   key repeated, and the join is refused with a message that says the keys
   were compared ignoring case and spaces, as an exact join refuses `P1` twice.
4. **Every join says what the comparison did.** Each join record carries
   `match`, `loose_matched` (rows that matched only because the join was loose)
   and `near_matches` (unmatched rows of an exact join that a loose one would
   have matched). The Data Merge Agent turns them into evidence, each claim tied
   to its calculation:
   - loose: a fact, "Keys were compared ignoring letter case and spaces: N of
     the M matched rows matched X only because of that";
   - exact with near misses: a limitation, "N of the U unmatched rows would
     match X if letter case and spaces were ignored; the keys were compared
     exactly".
   The join preview returns the same counts.
5. **The interface is unchanged in this slice.** `POST /api/runs` and
   `POST /api/joins/preview` accept `match`; the join builder does not offer it
   yet. A control needs new strings in both languages, and the script total is
   at its 257.1 KB ceiling. Until then, an exact run's report names the near
   misses, so the reader knows the keys need attention.

## Consequences

- A user whose keys differ only in case or spacing learns it from the report,
  and an API client can join them now.
- Unmatched key examples are shown as written in the main table, not
  case-folded.
- Fuzzy matching (typos, different separators such as `PUMP-01` against
  `PUMP_01`) is not part of this decision and remains open.

## Tests

`tests/test_joins.py`: the declaration (loose recorded, exact and stack not,
an unknown value refused in both languages); loose key text against numbers;
an exact join counting its near misses; a loose join matching across case and
spaces with its count and the main totals unchanged; keys repeated only under
a loose comparison refused; the preview's counts; and a run through the API on
SQLite and PostgreSQL in which the exact run reports its near misses and the
loose run its loose matches, with every validator check passing.
