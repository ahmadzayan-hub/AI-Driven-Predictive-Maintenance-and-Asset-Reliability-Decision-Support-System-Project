# Connected agent workspace and asset inspection

Date: 2026-10-21

Status: accepted for implementation by the owner.

## Context

The owner requested implementation and a local launch of the animated SaaS
design brief, with professional restraint, visible agent connections and
expandable evidence. The existing React application already records governed
stage state and organization-scoped maintenance work. The new presentation
must preserve these boundaries and the subsequent changes on main.

## Decision

- Keep React, HTML, SVG and CSS. A bounded stage map does not justify a graph
  editor or motion dependency. Use existing semantic tokens and bundled fonts.
- Put Hermes and the actual workflow bands on a responsive graph. Provide
  bounded zoom, fit, keyboard selection, previous/next-stage inspection and a
  separate pause-live-view control. Phones use a vertical sequence.
  On compact or short viewports the run header scrolls away, so a wrapped title
  cannot cover the graph and its controls.
- Animate a single directional handoff only after a newly observed stage event.
  Initial snapshots do not replay events. Pausing the view, interruption,
  document visibility and either reduced-motion preference suppress motion.
  There is no simulated agent conversation or inferred execution duration.
- Keep the overview's figures prominent and add action cards below the evidence
  summary. Workflow inspection opens an observed active run where available,
  otherwise the most recently updated run. An empty workspace has no workflow
  shortcut. The connection motif is decorative and inaccessible to screen readers.
- Present actual registry coverage and queue counts, with scope disclosure when
  the queue is truncated. Asset inspection shows only that asset's recorded work,
  captured evidence, audit history and completion outcomes. Configured criticality
  is not measured asset condition. Viewing records performs no authorization or
  publication action, and existing draft forms remain mounted.
- Ship equivalent English and Arabic controls, responsive layouts, visible focus,
  focus restoration and accessible dialogs. Use short transform/opacity transitions
  rather than continuously moving decoration.

## Validation

Unit coverage exercises real navigation targets, unavailable actions, bounded
zoom, actual event direction, held observations, keyboard inspection, asset
record isolation, queue scope and preservation of drafts. Browser checks exercise
the production build with English/Arabic, phone/desktop, light/dark,
reduced-motion, live updates, evidence dialogs and the complete recorded-work
flow. The interface budget remains a gate with the allocation below.

## Loading allocation

The first integrated production build measured 97.9 KB initial JavaScript,
208.0 KB total JavaScript, 18.9 KB largest lazy chunk, 10.0 KB initial CSS,
28.2 KB total CSS and 119.4 KB fonts (gzip for scripts/styles). Its totals exceed
the previous 205 KB JavaScript and 25.5 KB CSS allocation. No library was added:
the additional code implements the requested graph controls, bilingual inspector
and asset history. Styles remain scoped to lazy views; static preview assets
and existing functionality are retained.

Allocate at most 210 KB total JavaScript and 29 KB total CSS for this expansion.
Keep the initial JavaScript, initial CSS, individual lazy chunk and font ceilings
unchanged. This is a recorded feature-capacity tradeoff, not a claim that the old
total limits passed. Do not infer a Lighthouse or network-performance score from
these size measurements.

The first overview browser scenario combines a real analysis, navigation and an
accessibility scan. Its retained Windows trace showed the scan crossing the
default deadline after UI assertions passed. Give that scenario a bounded
longer timeout; preserve its assertions. The expanded collaboration scenarios
also have explicit bounds for their multiple responsive/accessibility checks.

## Consequences

The visual connections expose existing execution evidence; they do not add a
message transport, CMMS write-back or validated prediction model. A local launch
does not authorize deployment to production.
