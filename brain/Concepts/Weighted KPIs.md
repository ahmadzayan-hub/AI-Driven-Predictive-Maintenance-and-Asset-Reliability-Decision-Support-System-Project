---
type: concept
aliases: [KPI register, Ratio of sums]
tags: [measurement]
status: active
updated: 2026-10-16
review_every_days: 60
sources: [server/metrics.py, project-progress.md]
---

# Weighted KPIs

Every rate is computed as a summed numerator over a summed denominator, never as an average of row rates. Averaging rows gives a small record the same weight as a large one, and it can change the story.

## The example that proved it

On the [[Team 3 maintenance dataset]]:

| KPI | Average of row rates | Ratio of sums |
| --- | --- | --- |
| SLA met | 75.8% | 46.1% |
| First-time fix | 64.7% | 76.6% |
| MTBF | 342.5 h | 313.3 h |

The supplied reference material mixed both methods. One register of definitions, used by the report, the deck and the dashboard alike, keeps the numbers reconciled.

## In the product

The metric glossary (`metrics.json`) gives each metric a definition, an owner and optional arithmetic checks. The [[Governed pipeline]] fails a run that stays silent about an undefined measure.

## Related

- [[Soul]]: evidence before claims starts with measuring correctly.
- [[Team 3 Capstone]]: where the register was first written.
- [[Analytics OS roadmap]]: dashboard measures must follow the same rule.
