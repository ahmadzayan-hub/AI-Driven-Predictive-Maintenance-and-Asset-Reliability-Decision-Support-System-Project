# Mobile bar-chart category legibility

Date: 2026-10-25
Status: draft review candidate, not merged or deployed

## Context
On `main` after the verified merges of PRs #59 and #60, the native executive comparison chart shows actual grouped totals and a table equivalent. However, `dashboard.css` applies `white-space: nowrap; overflow: hidden; text-overflow: ellipsis` to every category, including phones. A long group name may be reduced to an ambiguous prefix. The companion Power BI reference uses labelled comparisons and drill-through; decision users must be able to recognise the category without relying on hover or guessing.

The desktop opening (1280×720) has a closely controlled fit of four KPI cards and five bars. Changing its row height would regress a tested fit. No backend, analytics measure, API, currency mapping or aggregation change is warranted.

## Decision
At widths up to 479px only, lay out each horizontal bar in two logical rows: the full category label plus the original exact number, followed by a bar spanning the available width. Permit long words to wrap. Preserve the left-to-right data axis even inside Arabic RTL pages. Do not hide labels, abbreviate figures, or add touch-only tooltip dependencies. Keep the accessible full-numbers table and drillthrough unchanged.

Reuse the existing Miyaar design tokens, React chart rendering, and responsive CSS. No dependencies or new backend pathways. At tablet/desktop keep the merged PR #60 layout.

## Verification required before merge
The existing `frontend/e2e/executive.spec.ts` now provides a five-site real FastAPI fixture with one deliberately long *fictional* category. Its existing opening test additionally asserts the 320px category is visible, wraps, does not overflow, and leaves the measured bar width usable. It still checks all five bars, complete currency figure, no viewport overflow, and desktop opening placement, with saved captures before the assertions.

Run the final-head locked-dependency CI, `python scripts/verify.py --quick`, `python scripts/verify.py --e2e`, bilingual RTL/English browser checks, and compare screenshots at the same dataset/viewports. Observe the unchanged bundle budgets. No test execution is asserted by this ADR; reviewer must attach exact results.

## Rollback
Revert this branch's changes to `frontend/src/features/dashboard/dashboard.css` and `frontend/e2e/executive.spec.ts` with a new commit. Do not force push or rewrite `main`. The reference study can remain for traceability.
