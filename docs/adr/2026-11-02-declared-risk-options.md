# Declared horizon and criticality weights for the risk ranking (R6)

Date: 2026-11-02 · Status: Accepted (the owner asked for the next development
step on 2 November 2026; the R2 record named these two options as next).

## Context

R2 (`docs/adr/2026-10-31-risk-ranking.md`) ranks assets by the chance of
failing within a fixed 90 days times the class's recorded cost per failure.
Criticality is shown but never weighted, because a weight is a judgement of
how much a consequence class is worth, and only the owner can give it. The
record left both as the next options, waiting on the owner's numbers.

## Decision

1. **Two stage options on `risk_ranking`**, set in `config.json` as
   `{"path": "server.maintenance.risk_ranking.RiskRanking", "options": {…}}`:
   - `horizon_days`: a whole number of days from 1 to 3,650. Default 90,
     so a run without the option is unchanged.
   - `criticality_weights`: up to 12 criticality labels, each mapped to a
     positive multiplier, matched without regard to case. Default none.
2. **Weights apply only when complete.** If any ranked asset has a
   criticality label without a declared weight, or no criticality recorded,
   nothing is weighted. The ranking stays as R2 ranks it, and the basis claim
   names the missing labels and the count of unrecorded assets. A missing
   weight is never filled in with 1 or any other number.
3. **What a weight does.** It multiplies the ranking value: the expected cost
   when costs are complete, otherwise the chance. Each asset carries its
   `weight` and `score`, and the declared weights are a calculation
   (`c_weights`) cited by the claims that use them. The chance and the
   expected cost shown are never changed by a weight.
4. **The horizon is cited.** The `c_horizon` calculation says whether the
   horizon is the default or was declared. Every claim, method and table uses
   the same horizon.
5. **Invalid options fail at load.** A zero, negative, fractional or boolean
   horizon, or a weight that is not a positive number, raises at stage load,
   so a bad setting is never silently ignored.

## Consequences

- The owner can set the horizon and weights in configuration with no code
  change. Until then, behaviour is exactly as in R2.
- There is no interface control yet. As with R3's declared intervals, the
  setting lives in `config.json` until there is script room for a control.
- The remaining owner inputs are the numbers themselves: the horizon, the
  weights, R3's intervals and R5's drift thresholds.

## Verification

`tests/test_risk_ranking.py` adds 6 tests (17 in all):

- a declared horizon is used, cited and lowers the chance compared with 90 days;
- options are validated;
- complete weights reorder by score and are stated with their evidence;
- incomplete weights are not applied, and the missing label is named;
- claims stay valid in English and Arabic under three option sets;
- options load from configuration.
