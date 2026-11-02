# Validity limits per measure

Date: 2026-10-31 · Status: Accepted (the owner approved a four-point data
policy on 31 October 2026; this record is point 1, on the server).

## Context

The 30 October change flags unusual and negative values but changes nothing
(`docs/adr/2026-10-30-data-understanding-and-cleaning.md`). That is right for a
value that is merely unusual: a repair costing 9,000 may be real. It is wrong
for a value that cannot be true: 30 hours worked in one day, or negative
downtime. Such a value is a recording error, and keeping it moves every total
and average built on it. Only the person who knows the data can say where the
possible range ends, so the platform cannot guess it.

## Decision

1. **A mapping may declare limits per measure** (`server/mapping.py`):
   `"limits": {"hours": {"min": 0, "max": 24}}`. Either side may be left out.
   Validation refuses, in English and Arabic, limits on a column not mapped as
   a measure, limits that are not plain numbers (text, booleans, infinities),
   and a lowest value above the highest. The saved mapping holds `limits` only
   when some are declared, so existing mappings and their hashes are unchanged.
   The API accepts the field on `PUT /api/datasets/{id}/mapping`.
2. **The cleaner leaves a value outside its limit out of every figure**
   (`server/analytics.py`). The cell becomes empty, and the row, column, value,
   the side it broke and the limit are recorded in `invalid_values` (capped as
   the unreadable values are), with the full count in `invalid_count`. So the
   exclusion can be checked and reversed, and nothing is silently lost.
3. **The exclusion is stated:** calculation `c_invalid_values` and a
   limitation claim `cl_invalid_values` per measure and side, in both
   languages, with the Arabic display names added.
4. **The profile no longer counts such a value** as a measure's minimum,
   maximum, negative or unusual value, so the profile describes the data the
   analysis uses.
5. Without declared limits nothing changes.

## Consequences

- An analyst can remove impossible values without editing the source file,
  and the report says how many and which.
- A wrong limit would drop real values. The claim names each limit and count,
  so a reviewer sees it before approval; the gate is unchanged.
- The mapping panel offers the control for the chosen measure as *Allowed
  range* (added the same day, `docs/adr/2026-10-31-data-policy.md`).
- Points 2 to 4 of the policy (outliers per group and on a log scale,
  transparent imputation in modelling only, and each report stating the
  policy) are separate records.

## Verification

`tests/test_validity_limits.py` (11 tests): validation and refusals in both
languages, the side a value breaks, exclusion with the record kept, the claim
and calculation, the profile, no change without limits, both languages through
the validator, the Arabic display, and the API saving and applying limits.
