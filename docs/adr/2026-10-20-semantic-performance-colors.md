# A performance color needs a target

Date: 2026-10-20

Status: Accepted

## Context

The owner requested a consistent dashboard vocabulary: bad in red, okay in
blue, good in green. The controlled maintenance register defines arithmetic,
population, units and missingness, but has no accepted performance targets.
A high percentage is not always good: repeat failures and first-time fix have
different desired directions; preventive share need not be monotonic. Some
ratios can exceed 100%. Counts, currencies and changes alone establish no
performance verdict. Evidence readiness and approval state are separate facts.

The W3C explanations for [use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html),
[text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
and [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
support visible text alternatives, 4.5:1 for small text and 3:1 for required
graphics. These accessibility requirements do not define maintenance targets.

## Decision

Use one shared semantic value component and explicit server assessments:

| Meaning | Light token value | Dark token value | Visible label |
| --- | --- | --- | --- |
| Bad | danger, `#b3323f` | danger, `#fb7185` | Bad / غير مرضٍ |
| Okay | metric-okay, `#1d4ed8` | metric-okay, `#93c5fd` | Okay / مقبول |
| Good | success, `#0f7a55` | success, `#34d399` | Good / جيد |
| No configured target | text-muted | text-muted | Not assessed / غير مقيّم |
| Missing/non-finite measurement | text-muted | text-muted | Unavailable / غير متاح |

Keep brand/actions, entity chart colors, data-quality grades and amber workflow
attention separate. Positive deltas do not automatically become green. The
fictional preview retains its declared condition bands; its middle Monitor
state becomes blue. Those fixture bands are not default maintenance targets.

Expose **Performance targets / أهداف الأداء** in the executive dashboard.
For each supported measure the authorized operator can configure higher-is-better,
lower-is-better or a good interval nested inside an okay interval. Inclusive
boundaries use the controlled result scale and the unrounded value. Percent
targets use percentage points, not fractions. There are no universal defaults,
0–100 clamps, hidden inferred directions or invented approved targets. Every
rule requires a bounded source/rationale. Removing a rule returns the value to
not assessed. Missingness and excluded population stay disclosed.

Persist per-analysis policy history in its own `kpi_policies` table. An
idempotent schema initialization adds it to existing SQLite/PostgreSQL stores;
backup/restore and owner erasure include it. Rules never enter report artifacts
or the publication vault. Reuse existing run ownership, read/write permissions,
cleaned-table readiness and bounded request handling. Atomic optimistic saves
reject concurrent replacement; history records actor and timestamp. Target
edits do not advance tasks, approve, publish or change the underlying figures.

Include the complete policy in the executive content revision, even for a rule
whose measurement is absent. A changed policy invalidates a prepared export.
The UI cancels/discards a prepared brief when it refreshes after saving. HTML,
Word and browser PDF output share the same assessment, status words, legend,
thresholds, units and source. Formal headings remain black; Word explicitly
declares both LTR and RTL as required by ADR 0059.

Visual review also exposed a Word technical-cell defect: a Latin formula in
an Arabic paragraph could display its denominator before the parenthesized
numerator. Table cells now choose their paragraph direction from the first
strong Unicode character, like HTML `bdi dir=auto`. Numeric-only text falls
back to the document language. Titles, headings, section direction and Arabic
table column order remain explicit; an entire Latin formula stays in one
LTR run, including leading brackets and operators.

## Delivery and performance bounds

This adds a persisted target configuration API and a bilingual target editor,
in addition to semantic styling. The editor and its CSS load on demand, and
the value component is shared by lazy views. No runtime dependency or font is
added. The preceding business-export delivery measured 174.8 KB total gzip JS
against 175 KB; it had no allowance for this requested configuration workflow.

Allocate up to 10 KB aggregate JavaScript and 1 KB aggregate CSS for this
feature, setting the aggregate ceilings to 185 KB and 22 KB. First-load JS
100 KB, first-load CSS 10 KB, largest deferred chunk 30 KB and fonts 120 KB
remain unchanged. The first integrated feature build measured 179.6 KB total
JS and 21.2 KB total CSS, with 98.4 KB initial JS and 10.0 KB initial CSS.
This records the cost of the additional workflow, not a new load-speed claim.
Actual release measurements and test counts belong in README.

## Verification

Pure-rule tests cover inclusive boundaries, directions, nested ranges, exact
units, unrounded values, invalid input and missing evidence. Persistence/API
checks cover ownership, read-only users, lost updates, history, backup/restore,
erasure, unchanged approvals and policy-only stale exports. Browser checks use
explicitly fictional targets and verify actual values, text status, computed
colors/contrast, filters/reload, both languages/themes and phone/desktop.
Generated business exports retain the same evidence and status vocabulary.

Real maintenance targets still require the asset owner's domain judgment.
Color is a display convention, not a safety assessment or maintenance action.
