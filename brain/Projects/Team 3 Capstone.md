---
type: project
aliases: [Capstone, Group 9226 capstone]
tags: [project, course]
status: active
updated: 2026-10-16
review_every_days: 3
sources: [project-progress.md]
---

# Team 3 Capstone

The course capstone of the [[User]]'s team: an executive analytics package on predictive maintenance and asset reliability, built from the [[Team 3 maintenance dataset]].

## Deliverables and dates

| Deliverable | Format | State on 2026-10-16 |
| --- | --- | --- |
| Executive dashboard | Power BI `.pbix` | Build kit ready: Power Query, DAX, theme, 30 expected values. Not yet built |
| Executive presentation | `.pptx`, 12 to 15 slides | 15 slides with speaker notes and final figures |
| Analytical report | `.pdf`, 20 to 25 pages | Full draft with computed figures; team-owned items still to add |

- Moodle submission closes on 22 October 2026, and the team uploads on 21 October 2026 to keep a buffer.
- The team presents to the instructors on 25 October 2026.

The plan, the report draft and the deck draft are private documents shared with the team. Roles, names and registration numbers stay there, never in this public repository.

## What carries over to the product

- **Measuring correctly:** averaging row rates overstated SLA compliance by 29.7 points. This is the [[Weighted KPIs]] rule.
- **Checking identity before analysis:** the dataset's asset IDs repeat every 180 rows, so the record, not the asset, is the unit of analysis.
- **Honest models:** a classifier beat the supplied score by only 0.02 AUC, and in the top 10% of the queue condition score alone did as well (86% against 85%). So the recommendation is a pilot, not a rollout ([[Soul]]).
- **Look past the obvious cut:** failure modes were a flat Pareto, but stockouts doubled outages, and reactive maintenance was worst at the same asset age.
- **Dashboard expectations:** landing page, slicers, drill-through and a ranked action queue, which feed the [[Analytics OS roadmap]].

## Related

- [[Agentic OS]]: the product whose methods the analysis reuses.
- [[Team collaboration]]: how the five members share work.
