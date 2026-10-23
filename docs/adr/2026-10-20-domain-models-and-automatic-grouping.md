# Domain models do not inherit presentation types or chart grain

Date: 2026-10-20
Status: Accepted

## Reproduced problems

A synthetic maintenance table with 500 distinct record IDs and two sites was
automatically grouped into 500 single-record groups. Separately, changing only
`Asset_Age_Years` from a measure to a dimension removed it from maintenance
model inputs and changed held-out balanced accuracy from 0.97 to 0.50.
The chart's mapped date grain could also change the model's evaluation split,
and unmapped `Record_Date` was not used for chronological evaluation.

## Decision

- Without a saved mapping, choose a repeated nonnumeric category with at most
  200 distinct filled values and at least two filled records per distinct
  value on average. Exclude identifier-like, date-like and detected personal
  columns. If no candidate remains, produce an ungrouped report. An explicit
  saved dimension or declared join breakdown remains authoritative.
  These are conservative display heuristics, not domain approval of a grouping.
- The maintenance risk stage reads numeric types from the maintenance domain
  contract, independently of whether a field is displayed as a measure or
  dimension. Its finite-number parser is the same for mapped and unmapped
  inputs. Unknown, outcome and derived fields remain excluded as before.
- Explicitly ignored columns remain excluded from features and target
  construction. Joined lookup exclusions follow their renamed output columns.
  Detected personal values in known-before categorical fields are also
  withheld. Exclusion reasons are returned with the stage evidence.
- A contract date is reserved for chronological evaluation, not categorical
  prediction. Parse it at its recorded precision, independently of chart
  rollups. An explicit date-order choice still controls ambiguous formats.
- Cleaning stores the retained source-row positions. Joins carry those
  positions through their row selection using a temporary internal marker
  that is removed before the result is stored. This restores original
  primary-source values for domain evaluation without assuming record IDs
  are unique or adding internal columns to cleaned-data downloads.
- Experiment planning now supplies its own bilingual assumption claim.
  Previously its recommendation depended on an unrelated prescriptive
  assumption, so a legitimate ungrouped run could fail validation.

## Compatibility and limits

The standard analytics mapping still controls displayed measures, dimensions,
date parsing and trends. This decision changes automatic breakdown selection
and maintenance model preparation; it does not silently save a suggested
mapping. Explicitly choosing a high-cardinality grouping remains possible.

Stored runs without source-row positions retain their existing cleaned values;
rerun an older coarsened dataset to obtain evaluation at source date precision.
Different ignored fields, explicit date-order interpretations or joined
populations may legitimately change a model. Missing/ambiguous dates still
use the disclosed non-temporal holdout, which does not establish prospective
failure prediction. The privacy scan remains pattern-based and bounded.

Source positions add one integer per retained primary record to server-side
stage evidence. Raw source values remain server-side and no model gateway is
called by maintenance evaluation.

## Verification

Synthetic regressions compare full model cards across unmapped, measure and
dimension presentations, and daily, monthly and yearly chart grains. They also
cover ignored target/features, personal values, duplicate record identifiers,
empty/duplicate record cleaning, inner-join chronology and ignored lookup
fields. Automatic-grouping checks cover identifiers, unique notes, personal
categories, date-named columns, 2/3/12/200-category cases and the 201-category
boundary, ungrouped English/Arabic reports and an explicit identifier mapping.
Existing high-cardinality reconciliation fixtures now declare their grouping
explicitly, preserving their arithmetic checks.
