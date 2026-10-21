# KPI register aligned with the team's Power BI report

Date: 2026-10-21 · Status: Accepted (owner request, 21 October: "review the
Power BI file to get the correct KPI definitions and correct the platform
dashboard")

Follows the [register correction](2026-10-21-register-availability-and-pooled-reliability-measures.md)
and uses the [definition stamp](2026-10-21-targets-held-when-a-measure-is-redefined.md).

## Context

The owner saw availability shown as `sum(Operating_Hours) /
sum(Planned_Operating_Hours)`, 2,380,296.37 / 2,998,339.904 (79.39%), and
pointed out that this is utilisation. The current register already defines
availability as `1 - sum(Downtime_Hours) / sum(Planned_Operating_Hours)`;
that figure is the one the register published before its correction earlier
the same day. The hosted Vercel deployment is from 2 October and
`vercel.json` keeps pushes to `main` from deploying, so the hosted site still
shows the old formula. A redeploy, with the owner's approval, fixes that.

The owner then asked for the report's definitions to be the reference. The
report file (`roles/02-rashed-bi-dashboard/…pbix`) is a thin report on a live
Power BI dataset, so it holds no DAX. Its PDF export has a "Method,
Definitions and Data Governance" page that states each measure as a weighted
sum over sum. Compared with the register:

| Measure | Power BI Method page | Register before | Now |
| --- | --- | --- | --- |
| Availability | 1 - sum(Downtime h) / sum(Planned h) | same | same |
| Utilisation | sum(Operating h) / sum(Planned h) | same | same |
| MTBF | sum(Operating h) / sum(Failures); blank if no failures | same | same |
| MTTR | sum(Downtime h) / sum(Failures) | downtime on records with a failure only | **all records, definition 2** |
| First-time fix | sum(FTF count) / sum(Corrective WO) | records typed "Corrective" only | **all records, definition 2** |
| Repeat repair | sum(Repeat count) / sum(Corrective WO) | records typed "Corrective" only | **all records, definition 2** |
| Cost per operating hour, downtime cost rate, preventive share, overdue rate, SLA on-target | as stated | same | same |
| Downtime per 1,000 planned hours, failures per record, loss per record, loss to maintenance ratio | on the report's pages | missing | **added** |

## Decision

1. **MTTR follows the report**, by the owner's choice: all recorded downtime
   over all failures. The card's notes say what this costs: downtime on a
   record with no failure, such as planned work, is counted, so where planned
   downtime is recorded the figure overstates time to restore a failure. The
   earlier population (records with a failure) was closer to EN 13306 time
   to restoration; it was offered and not chosen.
2. **First-time fix and repeat repair sum over every record.** These are
   counts of work orders, so a record typed preventive that carries
   corrective counts adds them. Records with no corrective work add 0 to both
   sums and do not dilute the rate.
3. **Each redefined measure is stamped definition 2.** A display target saved
   before today gives no verdict until it is reviewed, as for availability.
4. **Four measures added**, each a ratio of sums: downtime per 1,000 planned
   hours (`1,000 × sum(Downtime) / sum(Planned)`), failures per record,
   loss per record, and loss to maintenance ratio (`sum(Production loss) /
   sum(Maintenance cost)`, a new "ratio" scale shown as ×). The Method page
   does not spell these four out; the formulas follow from their names and
   from the report's summary ("production loss is 4.5x the repair spend").
   The register has 18 measures.
5. **A number never breaks across lines on a card.** Checking the new cards
   showed "4,332.03" split at the decimal point and "source currency" split
   mid-word, because the value allowed a break anywhere. The number is now
   unbreakable and sized to its card; a short unit stays beside it, a long
   one wraps whole.

## Consequences

- On the same data the platform and the Power BI report now print the same
  figure for every shared measure.
- Stored runs are recomputed from their data, so an existing analysis shows
  the new definitions; nothing stored is rewritten.
- The hosted site keeps the old formulas until it is redeployed, which needs
  the owner's explicit approval.

## Verification

Python: definition tests rewritten around the report's formulas, including
the case where old and new first-time fix part (a preventive-typed record
with corrective counts) and MTTR with downtime on a no-failure record; the
four new measures checked by hand, with downtime per 1,000 planned hours
reconciled to 1,000 × (1 − availability). Target-assessment tests now stamp
first-time fix targets, and one asserts an unstamped target is held.
Browser: no KPI number broken or overflowing at 1440 px in English and
Arabic, or at 390 px. Counts are in README.md under Testing.

## Not done

- Economic exposure, maintenance cost, production loss and the watchlist
  measures: totals or model outputs, with no definition on the Method page.
- The report file's own placement: it is course material in the repository,
  which `CLAUDE.md` says belongs in `private/`. Moving it out of history
  needs a history rewrite, which only the owner can authorise.
