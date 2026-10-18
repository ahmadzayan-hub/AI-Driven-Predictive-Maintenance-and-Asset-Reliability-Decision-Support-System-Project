# ADR 0042 — An unmeasured cell is not a zero

**Status:** Accepted
**Date:** 2026-10-18

## Context

The maintenance KPI register (`server/maintenance/kpis.py`) already got the hard
part right: every measure is a ratio of sums over a named population, never a
mean of row rates, and `_num` refuses an infinity or a NaN because both come from
a broken upstream calculation. Its docstring said a missing value "is never
silently treated as zero".

The arithmetic did the opposite. `_total` summed `(_num(cell) or 0)`, so a blank,
an `n/a` or a dash entered the sum as a measured zero. Reproduced on 18 October:
`downtime_per_record` over one record of 10 hours and one record with no reading
returned **5.0 hours per record**, with `records_excluded: 0` and no
`undefined_reason`. Nothing in the result told a caller that half the evidence
was absent, and the direction of the error is the dangerous one — an unrecorded
outage reads as a perfect one, so the gap looks like good news.

The register has no runtime consumer yet: its only importers are its own package
and its tests. That is why this was a latent defect rather than a published wrong
number, and it is also why it had to be fixed now. The next milestone binds these
KPIs to a run and to the executive view, and the first thing that view would have
published is zeros presented as measurements.

A related gap in `computable` — a KPI reported as available when a column its
*population* predicate reads was absent — was closed earlier by having
`source_columns` cover population columns as well as formula columns. This record
covers what remained.

## Decision

1. **A record counts towards a KPI only when every column that KPI's arithmetic
   reads holds a finite number.** `Kpi.measurable(row)` decides this, and
   `compute` sums over the measurable records alone. `_total` no longer contains
   an `or 0`: whether a gap is a zero is a policy decision, and it is made above
   the arithmetic, once, where it can be stated.

2. **The policy is declared per KPI, and `EXCLUDE` is the default.** `EXCLUDE`
   drops an unmeasurable record from the sums and from the record count.
   `ZERO` declares that for this measure a blank is the source's way of writing
   "none happened". `ZERO` is a fact about a particular source, so it is never
   assumed: all eight shipped KPIs are `EXCLUDE`, and an unknown policy raises at
   definition time rather than producing a quiet wrong number at compute time.

3. **A half-measured pair is withheld, not halved.** A ratio of sums needs both
   terms from the same records. Where a record has a numerator reading but no
   denominator reading, it contributes to neither.

4. **`records` is the count the figure was computed on.** Dividing the reported
   numerator by the reported `records` reproduces the printed value, so a card
   can be audited by hand. Two counts sit beside it and keep the exclusions
   legible: `records_excluded`, outside the population, and
   `records_unmeasured`, inside it but without a complete measurement. The policy
   itself is reported as `missing_policy`.

5. **When nothing is measurable, the measure is undefined and says why.**
   `undefined_reason` distinguishes the two absences: a denominator that summed to
   zero over real measurements, and no record carrying a measurement in every
   column of the formula at all.

## Consequences

The 18 October reproduction now returns **10.0 hours per record over one measured
record, with `records_unmeasured: 1`** — the same value as the table with the
blank row deleted, differing only by the disclosed count. The figure no longer
moves when an unrelated record is left unmeasured.

Figures will read worse on incomplete data than they did, and higher than a
zero-filled average where the gap was in a numerator. That is the correction, not
a regression. A dashboard binding these KPIs must show `records_unmeasured`
wherever it is non-zero; a card that hides it re-creates the defect one layer up.

All 69 existing maintenance, detector and governance tests pass unchanged, which
says the previous behaviour was never relied on. Eight new tests in
`tests/test_maintenance.py` cover the per-record average, the counts, the
auditable division, the withheld pair, a NaN, a declared `ZERO` policy, an
unknown policy and the shipped register's policies.

What this does not do: it does not decide which real maintenance columns use a
blank to mean zero. That is a question for the data's owner, and answering it for
a given source is a one-line change to that KPI's definition plus a test, not a
new decision record.
