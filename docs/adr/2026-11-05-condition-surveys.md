# Condition surveys: averaged scores, observation dates, condition measures

Date: 2026-11-05 · Status: Accepted · Owner request, 5 November 2026

## Context

The owner ran a real station electrical condition survey (12 stations, 372 lines,
353 scored on a 1 to 9 scale, 19 not applicable) through the platform. The generated
dashboard was not decision-grade:

- the designed page showed "Total Condition_Score 2,476.1" and ranked equipment by
  summed scores, so a type with more scored lines looked better;
- the Breakdown page ranked stations by total, putting the station with 9
  not-applicable lines last although its average was joint best, and counted 31
  records where 22 held a score;
- `Survey_Date` was read as text, so the brief had no period;
- the KPI register knew only work-order measures, so the brief showed
  "0 controlled measures".

## Decision

1. **A score is averaged, never added up.** `query.additive(name)` is false when a
   column's name has a word such as score, level, rating, index, pct, rate, ratio,
   share, probability, health, temperature or age. `/api/runs/{id}/fields` carries
   the flag. The designed page, Overview, Breakdown and Trend use the average for such a
   measure; the Breakdown hides "Totals" for it and says why.
2. **Condition layout.** A table whose names point to a condition survey
   (`condition_score`, `ageing`, `rams`, `survey`, ...) gets: lines surveyed, lines
   with a score, average score, and the three weakest groups by average, lowest first.
   An average tile states how many records it is over.
3. **Not applicable is counted apart.** `count` with a `column` counts records that hold
   a value. The Breakdown adds a "Not applicable or blank" column when any group has one.
4. **Observation dates.** When no column is named exactly "Date", "Month" and the like, a
   two-word name such as `Survey_Date`, `Inspection_Date`, `Assessment_Date` or
   `Reading_Month` is the time axis. Event dates (`Failure_Date`, `Due_Date`,
   `Install_Date`) and `Record_Date` are left out, keeping the 3 November decision that
   an event date must not become the axis.
5. **Condition measures in the register**, on the 1 to 9 scale (9 New to 1 Failed):
   average condition score; share Poor or worse (score below 5, so 5 is Average);
   share with recurring CM faults (intrinsic RAMS level 6 or below). Not-applicable
   lines are unmeasured, never zero. If any measured value is off the 1 to 9 scale the
   measure is not computed, rather than read on the wrong scale.

## Validation

The owner's survey was re-run after the change (private, not in Git) and checked
against an independent calculation from the tidy table: 50 of 50 checks agree,
covering the three measures (7.014, 0%, 64.02% over 353 lines, 19 unmeasured), the
period (7 to 28 July 2025), every station's average, line count and scored count, the
station ranking, the weakest three equipment types (6.818, 6.825, 6.842), and both
designed tiles. `tests/test_condition_survey.py` holds the same rules on invented rows.

## Consequences

- The executive priority rule still reads the 19 not-applicable lines as "missing
  measurements" and proposes resolving them. For a survey that is a review prompt, not
  a defect in the data; separating not-applicable from missing is a later change.
- The weights behind a survey's score are not inferred by the platform. The owner's
  survey score was found to be 0.6 ageing, 0.2 intrinsic RAMS, 0.1 operating RAMS and
  0.1 maintenance impact by hand; that stays outside the product.
- Script budget: 284.7 of 286 KB after this change.
