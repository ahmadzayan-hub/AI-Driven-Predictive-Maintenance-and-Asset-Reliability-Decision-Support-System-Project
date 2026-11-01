# A week grain: chosen by the owner, labelled by ISO week

Date: 2026-10-27 · Status: Accepted (the "Weeks" half of the dynamic-inputs
gap in the 16 October code audit, `project-progress.md`; the third slice of
the platform-building programme, after `2026-10-27-stacked-datasets.md`).
Amends ADR 0025.

## Context

A column mapping summed dates by day, month, quarter or year. Maintenance
and operations reporting runs on weeks: crew rosters, backlog ageing and
depot plans are weekly, and a year of daily records is 52 points by week
against 365 by day or 12 by month. Weekly exports (`2025-W03`) did not even
read as dates.

## Decision

1. **`week` is a grain** of the mapping (`GRAINS`, `FINEST_FIRST` between day
   and month). Its label is the ISO 8601 week, `YYYY-Www`, Monday to Sunday,
   so labels sort as time and a week that straddles the new year belongs to
   the year of its Thursday (30 December 2024 is `2025-W01`).
2. **A week value in the data reads as a period** of week precision:
   `2025-W03`, `2025W03`, `2025-w3`. It cannot be placed in a day (the label
   is None, counted as unreadable at that grain like a year in a month), and
   it rolls up to the month, quarter and year of its Thursday, the same
   anchor ISO uses for the year.
3. **The owner chooses weeks; `auto` never does.** The automatic roll-up
   keeps going from days to months to quarters to years (`AUTO_GRAINS`), so
   no analysis made before this decision changes its periods. The guide and
   the mapping panel say so.
4. **Forecasts continue the calendar**: `next_period_labels` steps ISO weeks
   across the year boundary (`2024-W52`, `2025-W01`). The seasonal model's
   season for weeks is 52, so it needs three years of weekly history, as it
   needs three years of months.
5. **Strings** in English and Arabic: the grain option *Week (ISO, Monday to
   Sunday)* and the validation wording that lists the grains.

## Consequences

- `tests/test_mapping.py`: week values and days labelled by week, the year
  boundary, roll-up to the Thursday's month, a month that cannot be placed
  in a week, the automatic choice skipping weeks, an explicit week mapping
  validated and summed, forecast labels across the year; `tests/test_modelling.py`:
  a weekly season of 52 with the forecast continuing the ISO weeks.
- A fiscal year, the other half of the gap, is a separate decision: it needs
  a start month in the mapping and touches every label and the forecast
  calendar.
- Week labels in the dashboard and reports are the ISO strings; a reader's
  locale does not change them, as it does not change `2025-Q1`.
