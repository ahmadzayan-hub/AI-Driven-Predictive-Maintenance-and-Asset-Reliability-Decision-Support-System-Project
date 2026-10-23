# Decision inputs in the interface and the decision record on the run

Date: 2026-10-22 · Status: Accepted (the interface half of assessment
findings A2 and A13 in `docs/audits/SAAS_PLATFORM_ASSESSMENT.md`; the item
carried forward from the [third release-gate slice](2026-10-22-release-gate-slice-three.md),
which delivered the API and the record but collected nothing in the
interface).

## Decisions

1. **The Analytics form collects the decision inputs.** Under "Improvement
   and cost (optional)" the analyst names a group as the data spells it, an
   improvement in percent and a cost in the measure's units, one row per
   group, and may change the lowest and highest improvement the sensitivity
   stage explores (5% and 20% unless changed). Blank rows send nothing. The
   improvement range travels only when it differs from the server's
   default, so a run that states nothing about it carries nothing about
   it. The form turns percentages into the fractions the API takes; the
   server validates every field as before and refuses the run with the
   reason in the report's language. A form that cannot be read as numbers
   says so inline and the run does not start.
2. **The decision record is a card on the run.** Once the prescriptive
   stage has written the record, the run view shows it under the approval
   card: the recommendation and its basis (net value, or size of change
   with the reason), the scope, the expected impact across the explored
   range with "from the stated improvement" or "illustrative" as the
   record labels it, every option compared with its improvement and whether
   it was stated or assumed, its cost or "not stated", and its net gain,
   the sensitivity verdict with the flip point when the ranking is a close
   call, and the gate: awaiting the approver, or who decided and when. Every
   figure is the report's own calculation; the card computes nothing. A
   one-time publication (`approved_once`) reads as approved.
3. **Both languages.** The strings ship with the Runs chunk in English and
   Arabic. The record's data (group names, the recommendation text) is the
   audited English and is marked as such; the labels follow the interface.

## Why

The third slice made uplift and cost inputs rather than assumptions, and
every option now says which it used. With no way to state them, every
hosted run kept the assumed 10% and the honesty was invisible to the
reader. The record existed in the API but not on the screen the approver
reads before deciding.

## Interface budget

The form, the card and their strings add 3.1 KB gzipped to the Runs
chunk, which is loaded on demand. The measured script total is 219.4 KB
against the 218 KB allocation of the same day, so the allocation is
**220 KB of scripts in total**; first-load limits (100 KB scripts, 10.5 KB
CSS), the 30 KB chunk limit and the 30.5 KB CSS total are unchanged.

## Tests

- `frontend/src/features/runs/DecisionRecordCard.test.tsx`: the card names
  stated and assumed inputs, the flip point and the pending gate; names
  the approver and the date in Arabic for an `approved_once` gate; the form
  turns its fields into the API's shape and sends nothing for nothing;
  unreadable input is reported inline.
- `frontend/e2e/decision.spec.ts`: a stated improvement and cost for the
  sample's groups reach the record on desktop and phone, the Arabic card
  renders, and the approval completes the record with the approver.
- `frontend/src/tests/api.test.ts` and `intake.test.tsx`: the run request
  carries the field.
