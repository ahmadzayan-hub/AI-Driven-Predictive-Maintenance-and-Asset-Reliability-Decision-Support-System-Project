# A fiscal year: quarters and years named by the month the year starts in

Date: 2026-10-27 · Status: Accepted (the "fiscal years" half of the
dynamic-inputs gap in the 16 October code audit, `project-progress.md`;
the slice after `2026-10-27-derived-columns.md`). Amends ADR 0025.

## Context

Quarter and year labels followed the calendar. A budget-holder whose
year starts in April read "2025-Q1" as January to March and had to
translate every quarter in their head, and the forecast's "next quarter"
crossed their year-end unmarked.

## Decision

1. **`fiscal_start` is a field of the mapping**, a month from 1 to 12;
   January, or a mapping saved before the field existed, means the
   calendar year and changes nothing. Any other month changes only the
   quarter and year grains: labels read `FY2026-Q1` and `FY2026`, named by
   the calendar year in which the fiscal year ends (April 2025 to March
   2026 is FY2026), so they still sort as time. Day, week and month labels
   are unchanged.
2. **A calendar value written in the data fits a fiscal period only when
   it falls inside one.** A calendar quarter fits a fiscal quarter when the
   fiscal year starts on a quarter boundary (January, April, July or
   October); a calendar year never fits a fiscal year that is not the
   calendar. Such values count as unreadable at that grain, as a year in a
   month does.
3. **Forecasts continue the fiscal calendar**: `FY2026-Q4` is followed by
   `FY2027-Q1`. The seasonal model reads the grain from the label shape
   for unmapped data too.
4. **Joined and stacked tables follow the main table's fiscal start**, as
   they follow its grain and order.
5. **The mapping panel** shows *Fiscal year starts in* with the date
   options; month names come from the browser's locale data (`Intl`), not
   a string list, so Arabic and English cost no dictionary bytes.
6. **A refusal says why** in both languages when the month is outside 1 to
   12 or is not a whole number.

## Consequences

- `tests/test_mapping.py`: `FiscalYearTests` (labels by fiscal quarter and
  year across the year-end, week and month precision, calendar quarters
  and years that fit or do not, forecast labels, the saved field and its
  refusals, labels from a column) and an API case (a run trends by fiscal
  quarter; 13 is refused). `frontend/src/tests/mapping.test.tsx`: the
  control, its locale month names and the body sent.
- The fiscal year is not a 52/53-week year or a 4-4-5 calendar; those are
  separate decisions, as is a fiscal label on the week grain.
