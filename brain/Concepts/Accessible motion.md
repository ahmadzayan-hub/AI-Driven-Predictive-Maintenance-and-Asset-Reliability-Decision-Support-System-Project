---
type: concept
aliases: []
tags: [interface]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [frontend/src/features/runs/collaboration.css, frontend/src/features/runs/AgentCollaboration.tsx, frontend/src/app/useMotion.ts, docs/design/AGENT_COLLABORATION_MOTION.md]
---

# Accessible motion

Accessible motion makes observed workflow changes noticeable while preserving control, legibility and language semantics.

## Interaction rules

- The owner chose restrained highlights, clear status words and expandable details.
- The collaboration view uses a brief highlight for an observed stage update, not perpetual activity.
- System and in-app reduced motion suppress animation. Hidden, interrupted and paused views remain still.
- Pause live view is distinct from pausing execution.
- Arabic layout, numeric ratio direction, keyboard operation and evidence-dialog focus are tested alongside English.
- Native controls and automated checks support accessibility; they do not replace manual assisted-use acceptance.

## Related

- [[Agent collaboration]] applies these rules to handoffs.
- [[Design system]] supplies tokens and typography.
- [[User]] records the owner's preference.
- [[Evidence and claims]] keeps visual emphasis separate from proof.
- [[Home]] indexes the interface knowledge.
