---
type: concept
aliases: []
tags: [agents]
status: active
updated: 2026-10-22
review_every_days: 30
sources: [frontend/src/features/runs/AgentCollaboration.tsx, docs/design/AGENT_COLLABORATION_MOTION.md, docs/design/REACT_AGENT_CONNECTIONS_STUDY.md, docs/adr/2026-10-21-connected-agent-workspace.md]
---

# Agent collaboration

Agent collaboration is the interface for inspecting observed specialist handoffs through the [[Hermes orchestrator]], rather than a simulated conversation.

## What is implemented

- Workflow groups expose stage order, states, summaries, checks and claims from the current run.
- The connected workspace places Hermes among the workflow groups, with bounded zoom, fit, previous/next-stage selection and a responsive inspector. Phones use a vertical sequence. Directional highlights follow observed state transitions; they do not replay a snapshot as new activity.
- Recent browser observations can omit intermediate transitions; they are not a durable transcript of messages or model thoughts.
- Pause live view holds only this panel. Analysis can continue, and opening current evidence uses the newest task.
- Actual message inspection would require a tenant-scoped event contract and redacted payloads that the current stage API does not provide.

## React connection-view study

The 21 October study recommends React with SVG/CSS for the compact workflow, with React Flow reserved for an optional graph explorer. Its isolated size experiment is recorded in `docs/design/REACT_AGENT_CONNECTIONS_STUDY.md`. The explorer and durable message history remain proposals; no graph dependency was added to the production app. [[Design system]] and [[Accessible motion]] govern any implementation.

## Related

- [[Run lifecycle]] explains which transitions are durable.
- [[Evidence and claims]] explains what a stage's result can substantiate.
- [[Accessible motion]] describes the visual controls.
- [[Home]] connects the rest of the platform.
