# Dataset workspace composition and shared route alignment

Status: accepted for implementation; release verification recorded separately.

The Datasets screen inherited a centered 780px panel intended for short forms.
On desktop this separated its content from navigation with a large unused gutter.
Earlier Assistant/Overview-only fixture checks did not cover that defect.

Align panels at the content edge with a 32px desktop inset and 12px phone inset.
Wide and split workspaces can use 1400px; short forms retain a readable width.
Keep explicit Command Centre access outside the four work stages, without
duplicating it within the priorities submenu. Existing deep links are preserved.

Datasets uses a source-list column and a 320px usage/connectors column, collapsing
to one column below 1024px. Source cards retain server-provided row counts,
mapping status, format and fingerprint. Upload is primary; mapping and analysis
remain available. No arbitrary score, generated chart or model claim is added.
Compact metric typography avoids breaking storage units into oversized rows.
Remove decorative control glows; preserve contrast, focus and reduced motion.

Shared shell, spacing, typography, cards and controls cover Overview, Datasets,
Analyses, Asset Intelligence, Approvals, Operations, Reports, Assistant, evidence
workspace, Memory, Preferences and Activity. Their domain content is retained.
Operations/evidence layouts keep their existing logical responsive styles.
This is shared-system coverage, not a claim of individually redesigned charts.

Validation uses synthetic Datasets before/after fixtures in English/Arabic,
desktop/mobile and light/dark. Built-app route fixtures separately cover empty
and unavailable states. Fixture images are not evidence of the user's live browser
or actual operational data. Keep report pagination/navigation behavior intact.
