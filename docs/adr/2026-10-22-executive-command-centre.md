# The Executive Command Centre on the Overview

Date: 2026-10-22 · Status: Accepted (owner brief, 22 October: "a unified,
source-backed Executive Decision Intelligence Command Centre" as the first
implementation priority; assessment finding U5)

## Context

The decision brief for a run (`GET /api/runs/{id}/executive`: a
recommendation, decisions with owner and gate, controlled KPIs with verdicts,
model cards, findings, evidence, questions, limitations) existed since 20
October, but was reachable only through Dashboards, then a run, then the
executive section. The Overview showed four counts, the latest headlines and
the approval queue; the same figures were spread over four screens. The
interface size gate had 1.6 KB of JavaScript headroom.

## Decision

1. The Overview becomes the **Command Centre** (navigation label and title in
   both languages). Above the counts it shows the decision brief of the latest
   analysis that has findings, read from the existing executive endpoint:
   the recommendation and readiness; decisions requiring attention with the
   proposed owner and gate; up to six controlled measures (every one with a
   verdict first, then the first of each family) with the server's verdict;
   predictive readiness per model card with one shared reading
   (`shared/modelTone.ts`, also used by the executive overview); the
   recommended action with its stated assumption; data quality, freshness and
   the limitations to read first; the questions for the approver. Every tile
   links to the run's executive overview, where the evidence table and the
   drill-downs are.
2. **Nothing is computed in the browser.** Every figure, verdict and sentence
   is the server's; an absent one is shown as unavailable. If the brief cannot
   be loaded the counts and lists stand and the brief says it is unavailable.
3. **Counts are counts.** The four tiles no longer carry a performance status;
   a status reads only where a target exists (assessment finding U7).
4. On the way: the live-source panel and the KPI-policy button are hidden in
   the view-only demo (U2), and "See all analyses" opens the list (U6).
5. The design is the existing card system: no new library, no new colour, no
   motion. Verdict colour comes from the shared performance component.

## Loading allocation

The production build measured 98.0 KB initial JavaScript, 211.7 KB total
JavaScript, 18.9 KB largest lazy chunk, 10.0 KB initial CSS, 28.7 KB total CSS
and 119.4 KB fonts (gzip for scripts and styles). The Command Centre is in the
Overview's lazy chunk, so the initial load is unchanged. Allocate at most
**214 KB total JavaScript and 29.5 KB total CSS**; the initial-load, lazy-chunk
and font ceilings stay as they were. As before, this is a recorded
feature-capacity trade-off, not a performance score.

## Consequences

- One screen answers what to decide, on what evidence, and what to ask, in
  English and Arabic, in the demo as in a signed-in workspace.
- The orchestrator and consultant notes are not on it yet: the run detail
  does not expose them (the report does). Roadmap item.
- A portfolio view across runs still needs a server endpoint (roadmap).

## Verification

`frontend/src/tests/views.test.tsx` (`Command Centre`): every tile renders
from a served brief; the counts carry no verdict; the executive link carries
the run id; "See all analyses" opens the list; the brief failing leaves the
rest standing; the demo hides live-source controls. `frontend/e2e/overview.spec.ts`
renamed to the Command Centre. The message pack is in the parity test.
