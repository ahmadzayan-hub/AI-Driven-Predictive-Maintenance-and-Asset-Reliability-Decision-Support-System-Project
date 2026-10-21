# Visible performance status beside every displayed metric

Date: 2026-10-21

Status: accepted

## Context

The owner requested red for bad, blue for okay, green for good, and neutral
for unassessed or unavailable values, always accompanied by text. Governed
KPI assessments already follow the target policy in
[the performance-color decision](2026-10-20-semantic-performance-colors.md),
but the legend was plain prose and operations totals had no assessment label.

## Decision

Use the existing semantic theme tokens for both the value and a compact,
outlined status badge. The badge includes a decorative dot and visible English
or Arabic text. A shared wrapping legend shows all five meanings in executive
KPIs, asset intelligence, overview, general dashboard KPIs and operations. Both neutral states remain distinct
in words. No meaning depends on color, hover, or motion.

Overview counts, general aggregates and operations totals remain neutral and explicitly not assessed: a completed
order or an empty queue does not establish good performance. Prospective
validation readings likewise remain unassessed without a performance target;
missing readings are unavailable. Denominators and uncertainty remain visible.
The legend explains the target requirement and missing-measurement state.

Use logical layout and wrapping badges, with stacked summary cards on small
phones. Preserve existing calculations, thresholds, data, permissions, and
workflow status. No dependency, default target, or assessment rule is added.

## Verification

Check bilingual status labels, zero and absent measurements, and unchanged
workflow behavior. Run the existing contrast checks for light, dark and system
themes, type checking, build and interface budget; review the real operations
page and the existing synthetic performance-color browser scenarios.
