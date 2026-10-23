# The report says who chose the breakdown

- Status: accepted
- Date: 2026-10-20
- Adds two bilingual limitation claims and one calculation to the preparer
  (`server/analytics.py`), and makes the automatic-grouping helper return
  every column that qualified rather than only the first. No change to which
  column is chosen.
- Builds directly on the parallel session's
  [automatic grouping decision](2026-10-20-domain-models-and-automatic-grouping.md)
  and its
  [refusal of a single-dataset breakdown](2026-10-20-reject-unsupported-single-dataset-breakdown.md),
  both of which landed first. This record also retires two decisions this
  session had reached independently, and says why.

## Problem

The 20 October review ran the capstone dataset through the pipeline unmapped —
5,000 rows, 60 columns — and the product's headline advice was:

> Protect the leading `Record_ID`: T3-01626.

Detection had taken the first non-numeric column as the breakdown, which in
that file is the record number, so the analysis had 5,000 groups of one row
and the prescriptive stage recommended acting on one of them. The parallel
session fixed the selection itself: a breakdown is now a repeated non-numeric
column within a display limit, excluding identifier-like, date-like and
detected-personal columns, and a file with no such column gets an ungrouped
report. Measured here against the same file, that lands on `Asset_Class`, 5
groups, and the recommendation names an asset class.

What remained is that **nothing tells the reader who chose `Asset_Class`.**
The report, the dashboard and the recommendation all present the leading group
as a finding, and a reader has no way to know that the column defining
"leading" was picked by this product from the file's column order, out of 14
columns that would have served, while 4 others were passed over as
identifiers, dates or personal data. A reader who is not told that reads a
fact about the file as a fact about the business. The same is true in reverse
for an ungrouped report: the breakdown is simply absent, with no statement of
why.

That gap is the reason this product's own decision record for the selection
calls it a "conservative display heuristic, not domain approval of a
grouping". The heuristic was documented in the repository. It was not
disclosed in the output.

## Decision

Where no mapping and no declared breakdown chose the column, the preparer
publishes one limitation claim, cited to a new calculation
`c_breakdown_candidates` — the number of columns that could have grouped the
rows:

| Situation | Claim |
| --- | --- |
| A column was detected | `cl_breakdown_detected` — nothing in the dataset declares what to compare, so this product chose it; it is the first of N candidates in the file's own column order; the other candidates are named, and a report on any of them answers a different question with the same figures; a saved column mapping names the breakdown instead |
| No column qualified | `cl_breakdown_none` — every non-numeric column identifies records, holds dates, reads as personal data or has too many distinct values to compare, so the report describes the whole population and no segment of it |

A breakdown an owner mapped, or a joined run declared, gets neither claim: it
was chosen by somebody, and saying otherwise would be false.

The other candidates are named in full rather than counted. That follows
`cl_gov_ambiguous`, which names every other column a glossary metric defines,
for the same reason: the alternatives are the information. On the capstone
file the claim names thirteen columns, which is long and is the honest length.

`_automatic_group` keeps its name and signature, so the selection tests that
landed with it still exercise exactly what they exercised. It now delegates to
`_automatic_groups`, which returns the qualifying columns in order.

## What this session decided and then withdrew

Both halves of this session's own work on these two defects were reverted in
favour of the versions already on `main`. Recording that is the point of this
section: the alternatives were implemented and measured, not merely imagined.

**Withdrawn: detection by measured repetition and date parsing.** This session
had detection skip a column whose distinct values exceeded 0.9 of its filled
rows, or whose values parsed as dates at the suggester's bar — measurements
from the rows, chosen over name lists because ADR 0011 settled that this
product does not guess a column's job from its name. It worked, with twelve
tests. It is also worse on the real file: it lands on `Quarter`, because
`Quarter` holds bare `Q1`–`Q4` labels that neither repeat a year nor parse as
dates, where the landed rule reaches `Asset_Class`. The landed rule also
screens columns that read as personal data, which this session's did not
consider at all, and that is a privacy property, not a presentation one.
Keeping two cardinality rules would have been worse than keeping the better
one.

**Withdrawn: honouring a `breakdown` declared without joins.** This session
had `analytics.check_breakdown` validate such a parameter against the
dataset's real columns at creation and the preparer honour it, on the argument
that refusing a documented parameter pushes a caller towards saving a whole
column mapping, and that mapping a dimension has side effects — in this
repository's own measurement, roles marked `ignore` starve the maintenance
models. The landed decision refuses the parameter instead, directing a
single-dataset caller to the mapping.

The argument for honouring it does not survive what landed beside it: the
same parallel session made the maintenance stage read its types from the
domain contract rather than from the presentation mapping, so saving a mapping
no longer changes what the models see. With that cost gone, refusing is the
narrower change, it keeps ADR 0030's scope as written, and it was already
tested to refuse before quota and before any write. Two sessions reached
opposite answers on the same day; this one defers, and the implementation and
its tests are in this session's transcript rather than in the tree.

## What this is worth, measured

Five new tests in `tests/test_analytics.py`
(`WhoChoseTheBreakdownTestCase`), each watched failing first — five errors
against the unchanged tree:

- a detected breakdown names the product as the chooser, says the choice came
  from column order, names the other candidate, and cites a candidate count of
  2;
- where only one column qualifies, the claim does not say others could have
  been used, and the count is 1;
- an ungrouped report carries `cl_breakdown_none`, a candidate count of 0, and
  no claim that something was detected;
- a mapped breakdown carries neither claim;
- both claims ship Arabic citing the same figures as the English.

Measured in the project venv: `tests.test_analytics` **89 tests**,
`tests.test_report_language`, `tests.test_model_privacy_boundary` and
`tests.test_breakdown_contract` beside it, all passing, and the whole suite at
**1,418 tests, 0 failures, 0 errors, 142 skipped** for want of a local
PostgreSQL. Counts and what was not run are in
[README testing](../../README.md#testing).

Live over the capstone file through the real stages, unmapped: the breakdown is
`Asset_Class` with 5 groups, the reconciliation check passes on 5 recomputed
group totals, and the report now carries, in both languages, that the product
chose `Asset_Class` as the first of 14 candidates in column order and names the
thirteen others.

## Consequences

- Every unmapped run gains one limitation claim it did not have, so every
  unmapped report is one claim longer. That is the intended cost: the claim
  exists to be read.
- On a wide table the claim is a long sentence naming a dozen columns. A
  shorter form that counted them instead would read better and tell the reader
  less.
- The claim says the choice came from column order. It does not rank the
  candidates, because this product has no measure of which breakdown a reader
  would want, and inventing one would be the guess the selection rule exists to
  avoid.
- Nothing in the interface surfaces the claim differently from any other
  limitation. A reader who reads only the recommendation still reads the
  leading group as a finding; this makes the correction available, not
  unavoidable.
