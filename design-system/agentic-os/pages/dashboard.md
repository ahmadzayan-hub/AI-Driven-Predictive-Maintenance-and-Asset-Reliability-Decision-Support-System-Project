# Dashboard Page Overrides

> **PROJECT:** Agentic OS
> **Generated:** 2026-10-16 19:56:32, then edited for this product (see `docs/UI_PLAN.md` §5)
> **Page Type:** Dashboard / Data View

> ⚠️ **IMPORTANT:** Rules in this file **override** the Master file (`design-system/agentic-os/MASTER.md`).
> Only deviations from the Master are documented here. For all other rules, refer to the Master, starting with its *Agentic OS decisions*.

---

## Page-Specific Rules

### Layout Overrides

- **Max width:** 1400px, or the full width of the main column
- **Grid:** 12 columns on desktop, collapsing to one column below 768px
- **Order:** title with the updated and live state → filter chips → page tabs → KPI bullets → charts in pairs → "Drill to rows" table

### Spacing Overrides

- **Content density:** high. 8 to 16px between related items, 24px between sections

### Typography Overrides

- KPI values in Fira Code 500 with tabular numerals; labels in Fira Sans 500 at `--text-s`

### Color Overrides

- **Performance semantics (the 20 October performance-color decision):** bad uses `--danger` red; okay uses `--metric-okay` blue; good uses `--success` green. A visible status label accompanies the number. Missing or unassessed values use `--text-muted`, never a guessed result.
- Only configured, sourced per-analysis targets establish a maintenance KPI status. Respect the desired direction, exact result scale and inclusive boundaries; comparisons happen before display rounding. Counts and raw changes remain neutral without a named rule.
- Brand/actions and entity chart colors retain their own meanings. Amber remains workflow attention or provisional evidence, not the okay performance band.

### Component Overrides

- Filter chips wrap and never clip, with a "Clear all" control
- Every chart has a "View as table" toggle

---

## Page-Specific Components

- KPI bullet (value, target, qualitative ranges labelled in text)
- Trend line with a labelled history–forecast boundary
- Contribution bars that extend both sides of zero
- Segment heatmap with the value printed in each cell

---

## Recommendations

- Effects: tooltips on hover and on focus, row highlight on hover, a 140ms filter transition, skeletons while loading
- No marketing CTAs on application pages
