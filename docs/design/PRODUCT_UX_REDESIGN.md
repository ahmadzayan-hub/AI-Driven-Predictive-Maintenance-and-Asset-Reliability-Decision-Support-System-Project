# Product UX redesign

Date: 22 October 2026 · Grounded in the interface audit in
`docs/audits/SAAS_PLATFORM_ASSESSMENT.md` (U1 to U20) and the view inventory
the audit produced.

## 1. The journey around five questions

| Question | Where it is answered today | What changed in this pass | What is next |
| --- | --- | --- | --- |
| What is happening? | Command Centre (decision brief, KPIs, freshness); Dashboards breakdown, trend, distribution, records | Command Centre built on the Overview | portfolio KPIs across runs (server endpoint) |
| Why is it happening? | Dashboards; the diagnostic report in the run cockpit; the executive findings | findings surfaced on the Command Centre | signed driver shares (A16) |
| What is likely to happen next? | the predictive report; model cards on the executive overview | predictive readiness tile | forecast baseline (A5), card versions (A14) |
| What are our best options? | the prescriptive report; the executive decisions with owner and gate | recommended action with its stated assumption | decision record, illustrative labels, cost input (`docs/analytics/PRESCRIPTIVE_DECISION_FRAMEWORK.md`) |
| What should the decision-maker do, and why? | the executive overview and export; Approvals | decisions requiring attention and questions for the approver, one click from evidence | approve after reading (U3), queue not capped (U1) |

## 2. Information architecture: keep, merge, add

The brief's six-group navigation was not reproduced. Most of its items would
be empty screens or duplicates; the audit found the opposite problem, the
same figures on four screens. The simplest coherent structure:

| Keep | Role |
| --- | --- |
| Command Centre (was Overview) | the executive home: brief, counts, evidence status, approvals waiting, recent analyses |
| Dashboards | the drill-down: executive overview with evidence table and export, breakdown, trend, distribution, relationship, records |
| Asset Intelligence | asset screening and KPIs from the latest qualifying run |
| Approvals | the human gate |
| Datasets | sources, mapping, live connectors |
| Analyses (rename from Analytics, U14) | the run list, the cockpit, the agent workflow |
| Operations (move to an Administration group, U14) | organisations, work orders, registry, trials |
| Workspace (rename to Assistant, U14) | chat and voice |

Add later: a portfolio view across runs (needs a server endpoint), the
orchestrator and consultant notes on the run detail, a model registry view
once cards carry versions (A14).

## 3. Journeys to fix

1. Upload to insight to approval: route every upload entry to the Datasets
   flow with preview and mapping (U15); approve only after the report is
   opened (U3); never cap the approval queue (U1).
2. Returning managers land on the Command Centre; Approvals in the phone bar
   (U12, owner decision).
3. Every figure states its as-of time (U16); money states its currency (U4).

## 4. Accessibility and bilingual

Keep WCAG 2.2 AA as the gate. Fix the silent loading states (U9), scan Assets
and Approvals with axe and at 320 px (U13), fixed labels on voice toggles
(U17). Arabic parity holds by construction; keep every new pack in the parity
test (done for the Command Centre).

## 5. What not to do

No decorative tiles, no fabricated metrics, no animation for its own sake, no
glass effects, no second design system. The one visual decision open for the
owner is the navy navigation rail from the brand system (U20).
