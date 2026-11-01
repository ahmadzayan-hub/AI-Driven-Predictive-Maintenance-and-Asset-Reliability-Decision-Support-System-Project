# Period exports stack under one table, with a source column

Date: 2026-10-27 · Status: Accepted (the "Unions" gap of the 16 October
code audit, `project-progress.md`; the second slice of the platform-building
programme, after `2026-10-27-dataset-deletion.md`).

## Context

A run could join up to four stored lookups onto its main dataset on
declared keys (ADR 0030), which brings columns beside each row. It could
not bring rows: an operator with a monthly export per period, the usual
shape of a maintenance or sales extract, had to concatenate the files by
hand before uploading, and the run never knew which period each row came
from. The cleaner already drops exact repeats within one dataset; two
overlapping exports would have counted their overlap twice.

## Decision

1. **A third join type, `stack`.** A declared join with `how: "stack"`
   appends the dataset's rows under the main table instead of joining them
   and needs no key (`JoinIn.keys` may be empty; `normalise` still refuses
   a left or inner join without one). Stacks and joins apply in the order
   declared, so a stack can be followed by a lookup on the stacked table.
2. **Exactly the same columns, or a refusal that names the difference.** The
   stacked dataset must have the main table's column set (ignoring the
   source column an earlier stack added); the problem names up to five
   missing and five extra columns, in English and Arabic, before the run
   starts (the preview and the run share the code).
3. **Read the way the main table was read.** A stacked table is cleaned
   with the main dataset's mapping, not its own, so its measures are
   numbers by the same rule and its dates become period labels at the main
   grain and order. A main date that did not read (order "as-recorded") is
   left as written.
4. **Counted once.** A stacked row identical to a row already in the table
   (from the main dataset or an earlier stack) is dropped and counted as
   `duplicates_dropped`, consistent with the cleaner's policy inside one
   dataset. A stack may not take the table past 50,000 rows, the ceiling
   one dataset has (`STACK_MAX_ROWS`, asserted equal to `analytics.MAX_ROWS`).
5. **A source column.** The first stack adds a text column `source`
   (`source_2` and so on when the name is taken) holding the main dataset's
   name on the main rows and the alias (or name) of each stacked dataset on
   its rows. It is a breakdown choice like any text column, so period
   totals by export are one preview away. A stacked row has no position in
   the main file, so its source index is `None` and the maintenance reader
   falls back to cleaned values, as it already did when indices were missing.
6. **Evidence.** The merge stage records rows before, rows stacked, repeats
   dropped and rows after as calculations, a fact claim naming the source
   column, a limitation claim when repeats were dropped, and a check that
   rows out equal rows in plus rows stacked. The Validation Expert's
   independent recount expects a stack to add exactly the rows it reported.
7. **The builder.** A third segmented option, *Stack its rows underneath*,
   hides the key pairs and explains the rule; the preview line says how
   many rows were stacked and how many repeats were dropped. Strings ship
   in English and Arabic.
8. **Budget.** The total script ceiling moves from 253 KB to 254 KB gzipped
   (`scripts/verify.py`, `tests/test_verify.py`). The slice trimmed first:
   the merge preview reuses the upload preview's table component and the two
   key selects became one map, which recovered part of the cost; the rest is
   the third join type and its strings in two languages. First load stays
   at 99.6 of 100 KB.

## Consequences

- `tests/test_joins.py` gains 10 cases: the declaration (no key, the
  ceiling equals the dataset limit), the merge (rows and source column,
  mismatched columns named in both languages, dates at the main grain, a
  taken source name, two stacks sharing one column followed by a join, the
  row ceiling), the preview (the main mapping reads the stacked table) and
  the API on SQLite and PostgreSQL (a governed run that groups by source and
  reconciles, the cleaned CSV with the source column, a refusal before the
  run in Arabic, the preview).
- Dataset deletion (`2026-10-27-dataset-deletion.md`) already counts a
  stacked dataset as read, since it parses the declared joins.
- Not done: a stack with columns in a different order is accepted (the set
  is compared), but a renamed column is refused rather than mapped; column
  aliases for stacks, a tolerance for extra columns, and stacking files at
  upload time are later decisions. The Android client does not offer stacks.
