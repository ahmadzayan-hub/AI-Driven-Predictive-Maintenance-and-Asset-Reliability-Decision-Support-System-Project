# The register's availability is uptime, and reliability measures are pooled

- Status: accepted
- Date: 2026-10-21
- Amends [ADR 0049](0049-the-kpi-register-reaches-a-run.md), which published
  operating hours over planned hours under the name "Availability". That
  record is not edited; this one replaces the choice.

## Problem

ADR 0049 chose `availability = sum(Operating_Hours) / sum(Planned_Operating_Hours)`
and recorded that it differed from the stored `Availability_Pct` column
(79.39% against 96.8%), calling them "different measures". They are different
measures, but the register put the wrong one under the name.

- **Operating over planned is utilisation.** It falls when demand is low or
  time is deliberately idle, with no failure at all.
- **The stored field is the standard meaning.** On every one of the 5,000
  course records, `Availability_Pct` equals `1 - Downtime_Hours /
  Planned_Operating_Hours` to within 0.00005 (rounding). Pooled, that is
  96.96%.
- **The team's Power BI report already uses it.** Its Method page defines
  availability as `1 - sum(Downtime h) / sum(Planned h)` and prints 97.0%.
  The product's executive view therefore disagreed with the team's own
  dashboard by 17.6 points, on the headline reliability number.
- **The standards family has variants, and none of them is operating over
  planned.** EN 50126 describes inherent, technical and operational
  availability (from a secondary source describing it; the standard text was
  not read). Each is an uptime proportion with a stated downtime scope.

The same review found that MTBF and MTTR, the two measures that availability
is built from in the standards, were not in the register at all, and that the
register's overdue measure used a different denominator from the workbook and
the dashboard.

## Decision

Add and change register entries, each a ratio of sums over a declared
population, each printing its formula.

| Key | Formula | Notes |
| --- | --- | --- |
| `availability` (changed) | 1 - sum(Downtime) / sum(Planned) | Operational availability on planned time. Needs `Downtime_Hours` and `Planned_Operating_Hours`. |
| `utilisation` (new) | sum(Operating) / sum(Planned) | The old `availability` formula, under its own name. |
| `availability_inherent` (new) | sum(Operating) / (sum(Operating) + sum(Downtime)) | Equals MTBF / (MTBF + MTTR) when all downtime follows failures. |
| `mtbf` (new) | sum(Operating) / sum(Failures), all records | Censored: a record with no failure adds exposure and no failure. Undefined when there is no failure. |
| `mttr` (new) | sum(Downtime) / sum(Failures), records with a failure | Restoration-time variant: all recorded downtime per failure. Not active repair time. |
| `overdue_rate` (new) | sum(Overdue) / (sum(Preventive) + sum(Corrective)) | Matches the stored `WO_Backlog_Rate` and the dashboard. |
| `overdue_share` (kept, retitled) | sum(Overdue) / sum(Completed) | Unchanged formula. Retitled "Overdue as a share of completed work" so the two differ in words as in arithmetic. |
| `sla_attainment` (new) | count(Actual <= Target) / count(records) | Equality counts as met. A missing hour reading is unmeasured, not a miss. |

Two small mechanisms support these. `Kpi(..., complement=True)` computes one
minus a ratio of sums, so availability is still a pooled ratio and never an
average of row rates. `Count(predicate, columns, description)` is a term that
counts records meeting a condition, with its columns declared so a record
missing one is reported as unmeasured.

The `MTBF_Hours` and `MTTR_Hours` contract fields gain notes: a stored
`MTBF_Hours` on a record with no failure is a censored lower bound and must
not be averaged, and `MTTR_Hours` behaves as downtime per failure.

### Why MTBF treats a no-failure record as exposure

Of 5,000 records, 985 have no failure. The stored per-record MTBF gives each
of them its operating hours, as if a failure happened at the end. Averaging
that gives 342.5 h. Pooled, 2,380,296 operating hours over 7,597 failures is
313.3 h. The 9.3% overstatement is not noise: those 985 records hold 19.5% of
the exposure, and a record with no failure carries information about how long
the item ran without one, not about how long it took to fail. Under a
constant failure rate the pooled ratio is the maximum-likelihood estimate.

### What was deliberately not added

- **The SLA "compliance" score.** The mean of `min(1, target / actual)` is a
  performance score: a job ten times over target and a job exactly on target
  can both pull it toward 100%. It read 75.8% where attainment is 46.1%. It is
  not offered under any compliance name, and a test pins its absence.
- **Hours-based planned maintenance, wrench time, PM and schedule compliance,
  backlog in crew-weeks, and maintenance cost as a share of replacement
  value.** They need fields the exports here do not carry (hours by work
  type, hands-on time, scheduled-versus-done counts, weekly capacity,
  replacement value). A stand-in would be a guess presented as a measurement,
  so they remain named gaps and a test pins that none is registered.
- **A unique-asset count.** In the course data every `Asset_ID` appears under
  all five asset classes, so it is a row label. The register counts records.

## Consequences

- **Existing numbers move.** Availability on the course dataset changes from
  79.39% to 96.96%. On the Playwright fixtures it changes from 81.25% to 90%.
  Every consumer reads the register, so the executive view, the briefs and the
  exports change together. Briefs generated earlier carry the old figure and
  the existing stale-snapshot check already refuses to export them silently.
- **Stored target policies are not migrated.** A rule saved against
  `availability` now judges a different quantity. A target of 95% set when the
  figure was utilisation would now read as met. Anyone holding such a policy
  should review it. This record does not rewrite them: the intent behind a
  stored number is not knowable.
- **The register has 14 entries, up from 8,** and the target-policy limit
  follows `len(REGISTER)`; its error message now states the real number
  instead of "eight".
- **A record with no downtime reading** is excluded from availability and
  counted as unmeasured, as before, and not read as no downtime.

## Validation

- `tests/test_maintenance.py` (class `CorrectedMeasuresTest`): three records
  that can be checked by hand, covering pooled availability against
  utilisation, the inherent-availability identity, MTBF pooled against the
  naive row mean and the effect of adding censored exposure, undefined
  measures, MTTR population, the two overdue measures, SLA equality and
  unmeasured handling, absence of the SLA score and of the unsupported
  measures, bilingual titles, and what `computable` reports.
- Existing tests updated where they pinned the old formula: `test_maintenance`,
  `test_executive`, `test_query`, and two Playwright specs, `executive` and
  `metric-colors`, which pass on desktop and phone in English and Arabic.
- Checked against the 5,000-row course dataset outside the repository: the
  register reproduces the corrected workbook and the dashboard's printed
  figures (availability 96.96%, MTBF 313.3 h, MTTR 11.99 h, overdue rate
  14.15%, SLA attainment 46.12%, first-time fix 76.56%, repeat repair 23.44%).
  The course data and the workbook are private and are not in the repository.

## Limits

- The standards were not read; the availability and MTTR variants rest on
  catalogue entries and secondary sources, and are marked as such in the
  workbook's Sources and Limits sheet.
- The MTBF interval in the workbook assumes a constant failure rate and
  independent records. The register does not compute an interval.
- `mttr` is measured on records with a failure. On the course data this equals
  the dashboard's all-records definition because every downtime hour sits on a
  record with a failure. A source that records downtime on records without a
  failure would show a difference, which is intended: that downtime is not
  restoration after a failure.

## Erratum, 2026-10-21

This record first said the register has 15 entries. It has 14 (8 before this
change, counted from Git at `efb6eb1~1` and `efb6eb1`). The count is now
pinned by `test_the_register_holds_fourteen_measures`. No figure or formula
was affected.

## Follow-up, 2026-10-21

Stored availability targets are now held for review rather than left to
judge the new figure: [decision](2026-10-21-targets-held-when-a-measure-is-redefined.md).
