# Understanding the data and cleaning it, said plainly

Date: 2026-10-30 · Status: Accepted (gap analysis, *Prep and cleaning* row;
the owner asked to develop the dataset understanding and the cleaning and
preparation stages).

## Context

The Data Profiling Agent reported completeness, duplicate rows and which
columns are numeric. It did not say what a maintenance analyst checks first:
a cost far above the rest, a negative downtime, a column that is mostly empty
or holds one value throughout. The cleaner read `N/A`, `-` or `غير متوفر` in a
number column as text that failed to read, so the report called them
unreadable, and a column with many of them was not recognised as numeric at
all. Category names spelled two ways (`North`, `north`) became two groups
without a word. The gap analysis listed imputation and outlier treatment as
missing.

## Decision

1. **The profile describes each column and each measure** (`server/analytics.py`,
   `profiler`). Every column gains `missing_share` and `constant`. Every
   measure gains `measure`: count, minimum, maximum, median, negative and zero
   counts, and the values beyond 1.5 times the interquartile range from the
   quartiles (Tukey's fences, with at least four values), with the fences and
   up to five source rows.
2. **What a reader should check becomes a claim tied to a calculation:**
   - columns at least half empty (limitation, `c_sparse_columns`);
   - columns holding one value throughout (fact, `c_constant_columns`);
   - values far outside a measure's usual range (limitation, `c_outliers`),
     said in plain words: the validator refuses "interquartile" and "Tukey" in
     a claim, and the method is in the calculation;
   - negative measure values (limitation, `c_negatives`).
3. **Missing-value markers are missing.** In a number column, `N/A`, `NA`,
   `-`, `—`, `null`, `none`, `nan`, `#N/A`, `not available`, `غير متوفر`,
   `غير متاح` and `لا يوجد` read as empty, are counted apart
   (`c_missing_markers`, a fact) from text that genuinely fails to read
   (`c_coercion`), and stay in the record of emptied values, so the cleaning
   can still be reversed (A18). They no longer count against the 90% rule that
   decides whether an unmapped column is numeric. In a text column they are
   values, because "None" can be a real category.
4. **Spelling variants are named, not merged.** Text columns with at most 200
   distinct values are checked for values that differ only in letter case or
   spacing; each such category is listed with its counts (limitation,
   `c_spelling_variants`). Merging them would move group totals, so the owner
   of the data decides.
5. **Nothing is imputed or removed.** Unusual values are kept, and missing
   values are not filled. Both change figures; they need a policy the owner
   sets (which method, for which measure, shown how), recorded as open below.

## Consequences

- Reports and agent cards now carry these checks in English and Arabic; the
  data, every total and every group are what the data says.
- A dataset whose numbers include `N/A` is now analysed as numeric where it
  was not, and its report says how many markers it read.
- Open, for an owner decision: imputation (method per measure, and whether a
  filled value is ever shown as a figure) and outlier treatment (flag only, or
  exclude from named figures with both versions shown).

## Tests

`tests/test_data_understanding.py`: a measure's range, median, outliers and
negatives with source rows; their claims and calculations, with the total
unchanged; mostly empty and single-value columns; a tidy dataset making none
of these claims; both languages passing every validator check; spelling
variants named and not merged; markers making a mostly numeric column
numeric; marker words kept as values in a text column; the Arabic markers.
`tests/test_p2_slice_three.py`: the reversal record now uses a truly
unreadable value, and a marker is recorded, counted apart and not called
unreadable.
