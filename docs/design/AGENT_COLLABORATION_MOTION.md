# Agent collaboration and motion study

Date: 2026-10-20

The owner chose professional, restrained motion: live handoffs, clear statuses
and expandable details. The implementation is in an analysis's Runs workspace,
under **Agents working together** / **الوكلاء يعملون معاً**.

## What the platform can show truthfully

Hermes sequences specialist stages. `RunDetail.tasks` supplies the actual stage
order, states, summaries, quality checks and claims. `runStore.ts` retains a
bounded session history derived by `runEvents.ts` from observed server snapshots.
The API does not return message envelopes, stage-specific timestamps or complete
historical transitions. Polling can miss intermediate states.

Accordingly, the diagram presents workflow connections through Hermes. It does
not synthesize agent dialogue, thoughts, token streams, progress percentages,
message counts or stage start times. Its activity times are the server snapshot's
`updated_at`, labelled as observations. Reloading cannot reconstruct missing
history. Failed and cancelled stages count as finished, with their outcome still
visible; finished never means successful.

## Interaction design

| Element | Behavior |
| --- | --- |
| Hermes and four workflow groups | Data, analytics, assurance and publication, derived from the existing pipeline mapping |
| Group buttons | Expand details and select a relevant stage; failure and human-review states take priority |
| Stage inspector | Previous/selected/next stage in returned order, result summary, check and claim counts |
| Current evidence | Opens the existing governed evidence dialog for the current task |
| Follow current stage | Releases manual selection and follows the most relevant returned stage |
| Observed activity | The newest twelve of up to 120 retained observations, with visible retained/displayed counts |
| Pause live view | Holds this panel's snapshot and motion; analysis and approval controls continue normally |
| Resume live view | Shows the newest available snapshot, without replaying a backlog |

The paused panel deliberately opens **current** evidence, labelled as such.
Switching runs remounts the panel, clearing its paused snapshot and selection.
The component owns no API calls, extra polling, persistence or approval mutations.
Its lazy import keeps code, bilingual copy and styles off the initial page load.

## Motion and accessibility

An observed stage change gives its workflow connection one 900 ms dashed-stroke
highlight. Loading an existing run does not replay a handoff. Actual running
state has a static highlighted connection; there are no perpetual particles,
bouncing avatars or fabricated conversations. Collapsed details reduce density.
On phones the groups form a two-column grid and stage order stacks vertically;
the wide connector graphic is hidden to avoid misleading connections.

Text labels accompany color. Native buttons and disclosure elements support
keyboard operation, and the existing run announcement remains the screen-reader
live region. Both Arabic RTL and English reuse the application's tokens and
typefaces. System reduced motion, the in-app reduced-motion setting, paused
analyses, interrupted connections, hidden documents and the pause-view control
suppress animation.

The design follows the intent of W3C's
[Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)
and [Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html).
The operating-system preference is implemented using
[prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion).
These sources guide the controls; automated accessibility checks alone do not
establish complete WCAG conformance.

## Future communication support

A real communication view would first need a tenant-scoped durable event
contract: event ID, run/stage IDs, sender/recipient, event type, timestamp,
sequence/cursor and approved redacted payload. Reconnect, deduplication,
retention and authorization would need server tests. Such events could then
drive actual message inspection and replay. They are not available or simulated
in this release.

Validation and measured bundle results belong in [README Testing](../../README.md#testing).
The behavior decision is [the dated ADR](../adr/2026-10-20-observed-agent-collaboration.md).
Actual browser captures show a synthetic failed analysis in
[desktop Arabic](../screenshots/agent-collaboration-desktop-ar.png) and
[320 px Arabic stage inspection](../screenshots/agent-collaboration-mobile-ar.png);
the synthetic failure makes attention and evidence controls visible.
