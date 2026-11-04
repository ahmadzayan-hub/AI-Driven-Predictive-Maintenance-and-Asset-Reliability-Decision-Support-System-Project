# A synthetic dataset generator, and the outlier claim it exposed

Date: 2026-11-03 · Status: Accepted

## Context

The owner asked for a synthetic dataset to test the database. Until now the tests
used files of a few dozen rows written by hand, which never exercised storage,
the row limit or the validation stage at the sizes a real fleet export has.

## Decision

1. **`scripts/generate_synthetic_dataset.py`** writes a fleet-maintenance file from a
   seeded random generator: 94 assets in five classes, monthly records from
   January 2025, failures that cost money and cause downtime, and a few weak assets so
   the data has something to find. The same seed gives the same file. Rows range from
   1 to 50,000, the pipeline's own limit. `--defects` adds blanks, text cells, a
   negative count and a duplicate row, to test the dirty case. Every value is invented.
2. **`tests/test_synthetic_dataset.py`** checks the generator (repeatable, plausible,
   bounded) and runs the round trip on SQLite and, when a database is available,
   PostgreSQL: upload, store, upload again (same bytes, same dataset), run the pipeline
   to the approval gate. With `--defects` the validation stage must refuse to call the
   file clean.
3. **Fix found by the first large file.** The outlier claim named a count per column, but
   its evidence held only the total. With three or more digits in a per-column count the
   figures check (`claim_figures_match_evidence`) rejected the claim and the run ended as
   `partially_completed` on clean data. Each named count is now its own cited calculation
   (`c_outliers_0`, `c_outliers_1`, ...). No figure changed; the claim now cites every
   figure it states.

## Not done

No real data is used or implied. A load test beyond 50,000 rows is not possible by design:
the pipeline refuses more.

## Verification

- `tests.test_synthetic_dataset`: generator tests plus the round trip on SQLite and PostgreSQL.
- The clean 1,500-row file reaches the approval gate; before the fix it did not.
