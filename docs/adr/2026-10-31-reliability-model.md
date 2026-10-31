# Reliability model: failure pattern per asset class (R1)

Date: 2026-10-31 · Status: Accepted (the owner asked for slice R1 on
31 October 2026, after the stage review ranked it first).

## Context

The maintenance profile measured MTBF, MTTR and availability and screened
records for risk, but nothing said how failures behave over time. Whether
failures come early in life, at random or with wear decides whether a
scheduled replacement helps, adds failures or wastes money. The readiness
list in `server/rmd_analytics.py` marks remaining useful life as unavailable;
that stays true, because this change estimates a pattern for a class of
assets, not one asset's remaining life.

## Decision

1. **A new opt-in stage, `reliability_model`** (`server/maintenance/reliability.py`),
   registered in `config.json` and on the `maintenance` profile only. It runs
   after `sensitivity`, like the other maintenance specialists.
2. **Times from the records.** It needs `Asset_ID`, `Record_Date` (to the day)
   and `Failure_Count` (contract names and aliases). Per asset, the clock
   starts when the asset is first seen and restarts at each record with a
   failure; the days in between are failure intervals. The time from the last
   failure, or from the first record for an asset that never failed, to the
   latest date in the data is a running interval, treated as censored. If
   fewer than 90% of records carry a usable date, asset and whole count, the
   stage claims nothing.
3. **The fit.** A two-parameter Weibull by maximum likelihood with right
   censoring, standard library only. The likely range of the shape comes from
   the profile likelihood at 95% for one parameter. Each asset class
   (`Asset_Class` when present) is fitted on its own, up to 8 classes with
   the most failures, each needing at least 10 failure intervals; the rest
   are named as not fitted.
4. **What is claimed, in both languages and in plain words:** the shape and
   its likely range, the days by which about 10% fail (B10) and the average
   life. The pattern is named early-life or wear only when the whole range
   is below or above 1. Otherwise the claim says the data cannot tell the
   pattern from random and is marked unverified, as is any fit whose range
   reaches the search bounds.
5. **Stated assumptions:** calendar days, not operating hours; each repair
   returns the asset to as good as new; a record with several failures is
   one failure; the counts of failures that gave no interval and of records
   holding several failures.
6. **Found while wiring it:** the governance stage's *uneven periods* finding
   listed each year's record count without citing it, and its Arabic text
   dropped every figure, so any maintenance run spread unevenly over years
   failed validation. The detector now carries the listing, governance cites
   text values as evidence, and the Arabic text states the same figures.

## Consequences

- A maintenance run now says, per asset class, whether time-based
  replacement is supported by the evidence, and by when about 10% of units
  fail.
- No interface change and no script budget change. The stage's report
  section and claims reach the existing run views.
- Calendar days understate life for assets that run part time; operating
  hours per interval would be better and need a reliable exposure field.
- The as-good-as-new assumption can be wrong for repairs that restore only
  part of the condition. The claim says so; a repairable-system model is a
  later option.

## Verification

`tests/test_reliability_model.py` (13 tests): known shapes 0.7, 1.0 and 2.5
recovered within 10% with censoring and named correctly; ignoring running
assets understates life; B10 and the mean follow from the fit; no fit without
spread or failures; intervals restart and the tail is censored; two classes
fitted apart; every claim cites its figures, avoids jargon and states the same
figures in Arabic; a random pattern stays unverified; a thin class is named
not fitted; missing fields or month-level dates give no claim; profile
registration; the governance regression; and a governed maintenance run that
reaches approval with the validator passing in English and Arabic.
