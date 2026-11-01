# Source-backed report inspector adapted from Stitch

Date: 2026-10-25
Status: draft review candidate, no production approval

## Context
The owner supplied three Stitch-exported HTML mockups and screenshots for the Decision, Data & Analysis, and Reports & Outputs destinations. The Reports reference gives one clear improvement over the current Runs view: a selectable left-hand index beside a full executive document preview. Its report values, signatures, agent quorum, and \"PDF/A-3\" labels are not connected to Miyaar's run/publishing APIs. Porting them verbatim would fabricate evidence.

## Options considered
- A: replace the full React interface with exported Tailwind HTML and illustrative values. Rejected for security, truthfulness, bundle limits, routing, RTL and provenance.
- B: reuse the existing `run.reports` data, ARIA tablist, `ReportDocument` and approval state, and change their presentation only. **Selected**.
- C: make a new reports service/provider to imitate the autonomous dossier. Rejected because this is a UI change, not a new authorized backend or autonomy requirement.

## Decision
The existing `RunsView` report tabs become a two-column inspector at larger viewports: actual section selection on one side, actual report content on the other. Below 900px the index and preview stack. Existing report language, `dir` tags, keyboard roving-focus semantics, evidence, publication gate, imports/exports and deep links are unchanged. Styles use existing tokens, no dependency or fake generated result.

The selected section is bound to `run.reports` and `openReport`, **never** to any illustrative content from the Stitch exports. This is not a new Reports route, so any existing bookmark continues to work. The comprehensive signed/published report is presented separately and is not relabelled as approved by the new inspector.

## Acceptance
- Execute exact-head `python scripts/verify.py --quick` and `python scripts/verify.py --e2e` with the same resource budgets.
- Existing `frontend/e2e/runs.spec.ts` now selects a second actual report tab and checks that the only preview panel is correctly labelled and that the page does not overflow.
- Validate English/Arabic, keyboard tab interactions, 320/390/tablet/desktop and persisted report/approval after reload.
- Capture rendered before/after screenshots on same run and viewport. Do not treat supplied Stitch images as live Miyaar screenshots.
- Never claim effective industrial control, standards certification, signed PDF or achieved savings without separately verified mechanisms.

## Rollback
Revert `RunsView.tsx`, `report-document.css`, and the additive `runs.spec.ts` test in a new commit. No force-push or changes to `main`.
