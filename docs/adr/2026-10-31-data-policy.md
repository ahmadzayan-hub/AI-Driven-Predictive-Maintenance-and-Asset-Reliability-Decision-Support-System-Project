# The data policy: unusual values, filling gaps, and saying so

Date: 2026-10-31 · Status: Accepted (the owner approved the four-point data
policy on 31 October 2026 and asked for the rest of it to be applied. Point 1
is `docs/adr/2026-10-31-validity-limits.md`; this record covers points 2 to 4
and the interface control for point 1).

## Context

The 30 October profile flagged unusual values with one set of fences over all
rows (`docs/adr/2026-10-30-data-understanding-and-cleaning.md`). Two kinds of
maintenance data defeat that. First, groups of very different size: a value
ordinary for a large fleet hides an unusual one in a small fleet. Second,
positive measures that lean far to the high side, such as repair cost or
downtime, where plain fences flag every expensive job. Nothing said how much
the flagged values move the figures. Gaps in a column beside the measure
silently shrank the rows the association model reads, and no report stated
the rules applied to the data.

## Decision

1. **Unusual values per group and by ratio** (`server/analytics.py`, profiler).
   Fences are computed within each group of the breakdown (the mapped
   dimension, or the column the product would choose) that holds at least 4
   values; rows in smaller groups use the overall fences. A measure whose
   values are all positive and whose quartile skew,
   (Q3 + Q1 − 2 × median) / (Q3 − Q1), is at least 0.25 is judged on a log
   scale. Each measure records `scale` and `grouped`. The claim says how the
   values were judged. They are still kept, never removed.
2. **Both figures when the effect is material.** Each measure records its
   average with and without its unusual values. When they differ by 10% or
   more, a limitation claim (`cl_outlier_effect`, calculation
   `c_outlier_effect`) gives both, in both languages.
3. **Filling gaps for the model only.** In the association model (diagnostic
   stage), rows that have the measure but lack the other column are given the
   median of their group, or of the column when the group holds fewer than 3
   values. This applies only when at most 30% of those rows lack the value.
   The association is then computed on the filled rows. A limitation claim
   per column (`cl_fill_n`) states the count, names the flag column
   `<column>_filled`, and gives the result with and without the fill. It says
   the result is weak when they differ by 0.1 or more, or when only one of
   them reaches the 0.5 the report treats as moving closely. The measure
   itself is never filled, and no stored or downloaded row changes. The
   diagnostic output carries `filled_for_model`.
4. **Each report states the policy.** The full report gains a *Data policy
   applied* section in the run's language. It covers the declared limits and
   how many values they left out, the unusual values and how they were
   judged, which averages are shown both ways, and what was filled for the
   model, with the two rules that never change.
5. **The limits in the mapping panel.** The panel offers *Allowed range*
   (lowest, highest) for the chosen measure, and the transport sends `limits`.
   A refused limit is shown at the measure field it belongs to.

Short-gap interpolation along time was considered and not applied. The
association model reads rows, not one series per asset, so the neighbours a
gap would be interpolated from are not defined there.

## Consequences

- Fewer false alarms on cost-like measures, and unusual values that hide
  inside a small group are found.
- Counts of unusual values change for data with a breakdown or a skewed
  positive measure. The claim says how they were judged, so the number can
  be understood.
- A filled association can differ from the observed one. Both are shown, and
  the weak label covers the case where the fill decides the answer.
- **Budget:** total script is 257,099 of 257,100 bytes, with no ceiling
  raise. The room came from shortening three help strings in both languages,
  the derived columns, the fiscal year and the models profile, and from
  reporting limit errors at the measure field. The next interface change must
  trim first or record a raise.

## Verification

- `tests/test_data_policy.py` (13 tests): grouped fences, ratio scale, plain
  scale with negatives, both averages when material and not otherwise; the
  fill, its flag and both correlations, no stored change, never the measure,
  the 30% ceiling; the policy section in both languages; the validator and
  Arabic display names.
- `frontend/src/tests/mapping.test.tsx`: two tests. The range is sent, a
  refusal is shown at the measure, and nothing is sent when no range is set.
