# Risk ranking backtest

Date: 2026-11-06 · Status: Accepted · Owner brief, Phase 4: a defined future-failure target and horizon, a chronological holdout, calibration and false alerts per asset-month

## Decision

The risk ranking stage now checks its own method on the past. The target is the one the
ranking already states: a failure recorded within the horizon (90 days unless the owner
declares another). The cutoff is one horizon before the latest record. Class fits, both the
Weibull and a constant failure rate used as the baseline, are made from records up to the
cutoff only. Each asset seen by the cutoff gets its chance from its age at the cutoff. It
is scored when it is recorded failing in the window, or recorded at the window's end. An
asset whose records stop earlier is left out and counted, never taken as a survivor.

Reported, with each figure in a calculation the claim cites:

- assets scored, failures in the window and assets left out;
- the Brier score of the chances against the constant-rate baseline;
- five calibration bands (mean chance against observed rate);
- failures among the top ten chances, against the number expected at the window's rate;
- false alerts per asset-month, treating the top ten as alerts.

The rule (the top ten, the 90-day horizon) is fixed before the outcomes are read; no
threshold is chosen from them. Fewer than 20 assets scored or fewer than 5 failures gives
no result, and the claim says the chances are not backtested.

The claim says whether the chances did better than the flat rate on this data, as a
calculation when they did and as a limitation when they did not. Either way it states that
this is one past window, not a prospective validation.

## Evidence

On the synthetic fleet in `tests/test_risk_ranking.py` (wear-out pumps, early-failure
signals, 80 assets, cutoff 2 October 2025):

- 27 of 80 assets failed in the window;
- the chances scored a Brier of 0.197, against 0.240 for the constant rate;
- 8 of the top 10 failed, against 3.4 expected at the window's rate;
- the sum of the chances was 34.1, so the method overstated failures on this data.

Tests also prove three things:
- turning every record after the cutoff into a failure changes the outcomes and leaves the
  chances unchanged;
- an asset not observed to the end is left out;
- a history shorter than the horizon gives no result.

## Limits

- One window, on the same assets the fit learned from: a chronological holdout, not an asset
  or site holdout.
- Assets in one class share a fit, so they are not independent.
- Feature availability timestamps are not modelled: the only input is the failure history,
  which is known at the cutoff.
- Field performance still needs the prospective shadow ledger (`server/reliability_validation.py`)
  with outcomes adjudicated independently. Nothing here claims savings or field accuracy.
