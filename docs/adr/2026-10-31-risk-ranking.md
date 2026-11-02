# Risk ranking: which assets first (R2)

Date: 2026-10-31 · Status: Accepted (the owner asked for slice R2 on
31 October 2026, after R1).

## Context

R1 (`docs/adr/2026-10-31-reliability-model.md`) says how failures behave for
each asset class. A manager still has to decide which assets to look at
first. The executive brief describes and does not rank assets by risk.

## Decision

1. **A new opt-in stage, `risk_ranking`** (`server/maintenance/risk_ranking.py`),
   on the `maintenance` profile only, after `sensitivity`. It fits the same
   classes as R1 with R1's own functions (at least 10 failure intervals, up
   to 8 classes with the most failures), so the two never disagree.
2. **Chance per asset.** Given the days since an asset's last failure (or
   since it was first seen), its chance of failing within the next 90 days
   is 1 − R(t + 90) / R(t) under its class's Weibull pattern.
3. **Expected cost.** The chance times the class's average recorded cost per
   failure: `Maintenance_Cost_USD` plus `Production_Loss_USD` on records with
   a failure. When any ranked class lacks complete costs, assets are ranked
   by chance alone and the claim says why.
4. **Criticality is shown, never weighted.** Turning a consequence class
   into a multiplier would invent a number. The owner can declare weights
   later; until then the ranking does not use them.
5. **Claims.** The top 3 assets each get a recommendation claim, in English
   and Arabic: review for planned work, with the days running, the chance
   and the expected cost. A claim is unverified when the asset has run longer
   than any failure interval seen in its class (the figure is an
   extrapolation, and the claim says so) or when the class's fit reached the
   search bounds. One assumption claim states the basis, that production
   loss is the source's own valuation, the assets not ranked, and that this
   is a proposal for engineering review, not a work order. The top 10 appear
   in the report table.

## Consequences

- A maintenance run now ends with a ranked, evidence-tied list of assets to
  review, which is the step from analysis to decision.
- It carries every R1 assumption (calendar days, repairs as good as new),
  and the 90-day horizon is fixed. A declared horizon and criticality
  weights are the next options; both need the owner's numbers.
- No interface change and no script budget change.

## Verification

`tests/test_risk_ranking.py` (11 tests): the chance equals the survival ratio
computed by hand; wear raises it with age and a random pattern does not; ages
count from the last failure; assets ranked by expected cost with the class's
cost per failure; ranking by chance when costs are missing, stated in the
claim; every claim cites its figures in both languages; an age beyond the
data is called an extrapolation and left unverified; a thin class is counted,
not ranked; missing fields rank nothing; profile registration; and a governed
maintenance run that reaches approval in English and Arabic.
