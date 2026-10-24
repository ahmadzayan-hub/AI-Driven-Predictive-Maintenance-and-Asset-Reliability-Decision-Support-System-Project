# Decision support, scenarios and action — دعم القرار

## Source-backed decision process

The course connects problem definition, alternatives, analysis and decision making. Its prescriptive workflow moves from the business problem and data to a model and action. [S035](SOURCE_INDEX.md#s035), pp7,12,16. The final project lecture asks for a recommended action, confidence and caveats, and a way to measure impact. [S043](SOURCE_INDEX.md#s043), p17.

The books distinguish several ways to reason about alternatives:

| Method | What it contributes | Source |
|---|---|---|
| Scenario analysis | Develop plausible futures by separating relative certainties from uncertainties and examining implications | S003 pp33–37 |
| Forecasting | Estimate a future pattern from time-indexed history and relevant information, subject to changed conditions | S003 pp38–40 |
| Monte Carlo simulation | Explore an outcome range by repeatedly drawing uncertain inputs from specified distributions | S003 pp66–69 |
| Linear programming | Optimize a linear objective over a feasible region constrained by limited resources | S003 pp70–74 |
| Business experiments | Test a specified intervention and compare outcomes using an explicit design | S003 pp20–24 |

These are different reasoning tools. A scenario is not automatically a calibrated forecast, a simulation is not observed evidence, and an association is not proof that an action will improve the outcome. The source's correlation caution is explicit. [S003](SOURCE_INDEX.md#s003), p32.

## Verified linear-programming example defect

The example states that each unit of X takes six hours and contributes £12, and each Y takes four hours and contributes £6, with 1,700 hours available and production limits of 400 units of each. [S003](SOURCE_INDEX.md#s003), PDF p72, printed p55. The resource constraint must be checked separately from the contribution calculation.

PDF p73 (printed p56) presents `x=400, y=250` with a £6,300 contribution. The contribution calculation is arithmetically consistent, but the candidate consumes `6×400 + 4×250 = 3400` hours, exceeding the stated limit by 1,700. It is infeasible under the printed constraint. The graph's intercepts also do not match the labelled constraint. Both pages were visually checked. [Source issue E02](09_SOURCE_ISSUES.md#verified-arithmetic-and-layout-errors). The underlying local audit is not republished.

This knowledge base does not quietly replace the source with an invented corrected exercise or claim that an optimizer ran. It retains the stated constraint, identifies the contradiction and blocks use of the printed candidate as a valid solution.

## Proposed Miyaar decision record

For each material recommendation, record:

- **Decision:** owner, deadline, objective and the current baseline action.
- **Evidence:** input hashes, verified calculations, model evaluation if any, and relevant course references.
- **Alternatives:** feasible actions, including maintaining the baseline where appropriate.
- **Constraints:** budget, capacity, time, safety and approval boundaries, with confirmed units.
- **Uncertainty:** assumptions, ranges, sensitivity and what evidence could change the ranking.
- **Recommendation:** expected consequence conditional on the evidence, residual risks and unresolved conflicts.
- **Approval and follow-up:** human decision, artifact version/hash, and a plan for evaluating actual impact later.

For predictive maintenance, a predicted failure risk becomes actionable only after the cost of intervention, consequences of missed failure, capacity and timing are understood. These are proposed decision requirements; this task has not established those quantities for Team 3.

## Proposed prioritization versus optimization

A weighted risk score or ranked list is a prioritization rule. Record its weights, units, rationale and sensitivity. Label it as a rule unless an objective and feasible set have been solved and independently checked. A prescriptive claim should show which alternative improves the stated objective while respecting constraints, and how robust that choice is to plausible changes.

Do not attribute a simulated cost saving to the real organization. Distinguish expected, scenario-based and realized impact. Track realized outcomes only when the later observation and comparison design support the claim.
