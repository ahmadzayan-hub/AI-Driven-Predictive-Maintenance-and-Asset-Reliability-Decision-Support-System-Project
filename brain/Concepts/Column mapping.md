---
type: concept
aliases: [Mapping, Column roles]
tags: [analytics, data]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [docs/adr/0025-column-mapping.md, server/mapping.py, frontend/src/features/datasets/MappingPanel.tsx, docs/adr/2026-10-20-who-chose-the-breakdown.md, docs/adr/2026-10-20-domain-models-and-automatic-grouping.md]
---

# Column mapping

The owner of a dataset says once what each column is: a measure, a dimension, the date, or ignored. Every run of that dataset follows the mapping instead of guessing from column names (ADR 0025).

## Facts

- **Four roles, one per column.** The owner also chooses the measure analysed, an optional breakdown, how dates write day and month, and the grain dates are summed by (day, month, quarter or year). Automatic grain allows at most 36 periods.
- **The server suggests and the owner decides.** Each column gets a suggested role with a reason. A suggestion is never applied until it is saved, which follows the [[Approval gate]] habit of people deciding.
- **Checked against every row.** A refusal names each problem by field, in English or Arabic, and the interface shows it as an error summary that links to the fields.
- **Generous reading for mapped measures:** currency signs and codes, `(300)`, and Arabic digits. A decimal comma is refused rather than misread.
- **Dates become sortable period labels.** Trends are therefore ordered by time, and forecast labels continue the calendar.
- **A run copies the mapping when it starts**, so a later change never alters a finished report.
- **Unmapped data uses conservative automatic selection.** The report names an automatically chosen breakdown and its alternatives, or explains why no candidate qualified. These candidates are not ranked by business relevance.
- **Presentation roles do not define every domain-model input.** Maintenance targets and features retain their own contract and source chronology.
- **The capstone shows why it matters.** Its date column is `Record_Date`, which the old name rule never found. Mapped, it trends by month over 36 periods ([[Team 3 maintenance dataset]]).

## Related

- [[Home]]
- [[Analytics OS roadmap]]: milestone A2, built on the dataset API.
- [[Governed pipeline]]: profiling, cleaning, governance and preparation honour the mapping.
- [[Weighted KPIs]]: the glossary still defines and checks the mapped measure.
- [[Soul]]: no guessed periods and no silent misreads; refused values are counted.
- [[Data quality contracts]]: defines meanings and units beyond display roles.
- [[Dataset joins]]: copies declared mappings into the combined analysis.
