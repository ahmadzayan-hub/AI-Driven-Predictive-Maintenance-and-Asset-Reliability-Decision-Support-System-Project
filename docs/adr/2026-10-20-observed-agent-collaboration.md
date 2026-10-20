# Present observed agent collaboration with restrained motion

Date: 2026-10-20

Status: Accepted

## Context

The owner requested animations and a combined presentation of agent
communication and interactions, then selected professional, restrained motion
with live handoffs, clear statuses and expandable details. The governed run
workspace has stage snapshots and bounded browser observations, but no durable
message transcript or complete event stream.

## Decision

Add a lazy-loaded collaboration panel inside Runs using the existing pipeline
groups, run store, evidence dialog, bilingual strings and design tokens.
Show workflow order and observed results, explicitly describe the limits of
the activity history, and never invent message content or unseen transitions.

Use a single short connection highlight per observed stage update. Provide a
pause-view control independent of the analysis pause action; respect system
and app reduced motion, document visibility and interrupted connections.
Reset held state on run changes. Keep evidence current and human approval
in the existing governed controls.
Isolate numeric ratios left-to-right in both the new panel and existing timeline
so Arabic direction cannot reverse the finished/completed and total counts.

Use native CSS and SVG with no dependency or backend change. The first-load
JavaScript, first-load CSS, individual JavaScript chunk and font budgets remain
unchanged. The aggregate CSS allowance becomes 23 KB gzipped, from 22 KB,
to accommodate the lazy collaboration diagram and responsive inspector.
The aggregate JavaScript allowance remains 185 KB. Measure these limits with
the existing verifier; actual results live only in README Testing.

## Consequences

People can inspect stage results, order, evidence and recent activity together.
They can pause visual updates without cancelling analysis. Observations can
omit intermediate states and are not recoverable after a reload; the interface
says so. Actual agent communications require a future server event contract.

Component tests cover snapshot holding, current evidence, run isolation,
custom stages, escaping, Arabic decisions and hidden/interrupted views.
Browser tests cover live updates, keyboard operation, both reduced-motion
settings, small-screen RTL, themes and accessibility. The real pipeline approval
scenario also exercises the new panel.

The [design study](../design/AGENT_COLLABORATION_MOTION.md) records the research,
interaction model and future event requirements.
