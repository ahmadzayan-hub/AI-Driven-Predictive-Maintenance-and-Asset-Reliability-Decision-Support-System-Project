# ADR 0049 — The KPI register reaches a run

**Status:** Accepted
**Date:** 2026-10-18

## Context

`server/maintenance/kpis.py` has been right and unreachable. It holds eight
controlled measures, each a ratio of sums over a named population rather than a
mean of row rates, each refusing an infinity or a NaN, and since ADR 0042 each
counting a record only when every column its arithmetic reads holds a finite
number. It was also imported by nothing outside its own package and its tests.

So the product had two maintenance surfaces and they disagreed about what is
real. The engine computed defensible numbers that no caller could fetch, and the
executive view at `?design=maintenance` read `SAMPLE_ASSETS` — fictional
fixtures. The charter calls this P2, and ADR 0042 said plainly that the next
milestone binds these KPIs to a run and that the first thing an unbound view
would publish is zeros presented as measurements.

A date forced the order. The team demonstrates Agentic OS and the SaaS platform
on 25 October, so the choice became: show the view labelled as a design preview,
or make it real.

## Decision

1. **`GET /api/runs/{run_id}/kpis` computes the register on a run's cleaned
   table.** It joins the four endpoints ADR 0031 added — `data.csv`, `fields`,
   `query`, `records` — and shares their contract exactly: owner-scoped through
   the same `run_table` helper, 404 for another owner, 409 while the table is
   still being cleaned, and the reader's language as a query parameter.

2. **Every measure carries the counts that make it auditable.** `records` is
   what the figure was computed on, so dividing the reported numerator by it
   reproduces the printed value by hand — asserted by a test, not merely
   intended. `records_excluded` and `records_unmeasured` sit beside it, with
   `missing_policy` and `undefined_reason`.

3. **`records_unmeasured` is returned for every measure, always.** ADR 0042
   warned that a card hiding the exclusions re-creates the defect one layer up.
   Returning it unconditionally means a consumer has to decide to drop it rather
   than never receive it.

4. **A measure the data cannot support is named, not omitted.** `unavailable`
   maps each unsupported KPI to the columns it needed. An absent card teaches a
   reader nothing; a named gap tells them what to collect.

5. **Titles come back in the reader's language** and `title_ar` is not leaked
   beside them, matching ADR 0022's rule for reports.

6. **The register is read, never re-implemented.** The endpoint converts the
   analysis table's tuples into row dicts and calls `compute_all`. No arithmetic
   lives in the API layer, so the figures an endpoint serves and the figures a
   stage computes cannot drift.

## Consequences

The executive maintenance view can stop reading `SAMPLE_ASSETS`. That is the
next change and it is not this one: this record ships the endpoint and its
tests, and the view still shows fixtures until it is pointed here.

Checked against the real 5,000-row course dataset, every figure that could be
cross-checked agreed with numbers verified independently and recorded earlier:
preventive share 75.16% against 75.2, first-time fix 76.56% against 76.6 over
4,015 corrective records with 985 excluded, repeat repair 23.44% against 23.4,
loss per downtime hour $2,513.14 against $2,513, cost per operating hour $21.19.
Availability returns **79.39%**, the ratio of summed operating hours to summed
planned hours — not the 96.8% mean of the stored `Availability_Pct` column. The
two are different measures and the register computes the one it declares.

The conversion to row dicts is O(rows × columns) and runs in a threadpool, as
the other table endpoints do. On 5,000 rows and 60 columns it is not noticeable;
a dataset large enough to make it so would need the register to read tuples by
index, which is a change to make when measured, not before.

Six endpoint tests cover the auditable division, the disclosed gap, the named
unavailable measure, both languages, the required fields on every measure, and
an unknown run. The endpoint also joins the existing tenancy tuple in
`tests/test_query.py`, so it is held to the same cross-owner isolation as the
four endpoints beside it. Across the query, API, authorization, tenancy and
maintenance suites: 137 tests, 0 assertion failures.
