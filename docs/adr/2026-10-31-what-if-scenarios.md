# What-if scenarios: planned replacement against run to failure (R3)

Date: 2026-10-31 · Status: Accepted (the owner asked for slice R3 on
31 October 2026, after R1 and R2).

## Context

R1 gives each asset class its failure pattern and R2 ranks assets. The
remaining question is what a change of policy would do: if a class is
serviced or replaced every T running days, how many failures and how much
cost follow, against running each unit until it fails?

## Decision

1. **A new opt-in stage, `what_if_scenarios`** (`server/maintenance/scenarios.py`),
   on the `maintenance` profile only, after `sensitivity`, fitting the same
   classes as R1 with R1's functions.
2. **The age-replacement model.** For an interval T: failures per day
   F(T) / L(T), planned jobs per day R(T) / L(T), cost per day
   (Cp R(T) + Cf F(T)) / L(T), where L(T) is the integral of survival to T
   (Simpson's rule). Run to failure is the limit: 1 / mean life failures per
   day and Cf / mean life cost per day. Figures are per 1,000 asset-days.
3. **Costs from the records.** Cf is the class's average maintenance cost plus
   production loss on failure records (as in R2); Cp the average on
   `Preventive` records without a failure. Without both, failures and planned
   jobs are compared and no interval is recommended on cost.
4. **Intervals.** The owner's, as the stage option `intervals_days` (up to 6
   positive numbers, in `config.json`), or by default a quarter, a half and
   three quarters of the class's average life. When both costs exist, the
   lowest-cost interval is searched over 240 points up to three average lives
   and named only if it saves at least 1% per day against run to failure.
5. **Only wear can gain.** A class whose pattern is not wear (R1's rule: the
   whole likely range above 1) gets a limitation claim: planned replacement
   does not reduce its failures, so look at installation, repair quality or
   condition checks. Its table still shows the effect, which for an
   early-life class is more failures.
6. **Found while wiring it:** on data with work-order types and costs, two
   existing claims failed the validation gate. The governance *split* finding
   stated its value counts without citing them and left them out of the
   Arabic text; an unanswered maintenance-risk target stated its record
   counts without citing them. Both now cite what they state, in both
   languages. Any real export with a `Work_Order_Type` column was affected.

## Consequences

- A maintenance run now answers "what if we service on a schedule" per
  class, with failures, planned jobs and cost side by side, and the
  lowest-cost interval when the evidence supports one.
- It carries R1's assumptions; replacement or service is taken to restore a
  unit to as good as new, and costs are recorded averages.
- No interface change and no script budget change. Declared intervals are
  set in `config.json` until there is room for an interface control.

## Verification

`tests/test_what_if_scenarios.py` (14 tests): a random pattern gains nothing
at any interval; a long interval tends to run to failure; the running-time
integral matches the mean life at the limit; the lowest-cost interval meets
the Barlow and Proschan optimality condition; costly planned work names no
interval; declared intervals are validated and used; without costs no
interval is recommended; wear gets an interval and early life is told no;
every claim cites its figures in both languages; missing fields compare
nothing; profile registration; the governance and risk regression; and a
governed maintenance run that reaches approval in English and Arabic.
