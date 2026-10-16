---
type: log
aliases: [Brain maintenance log]
tags: [meta]
status: active
updated: 2026-10-16
review_every_days: 7
sources: [scripts/brain_check.py]
---

# Maintenance log

What each round of brain maintenance changed, newest last. The SessionStart hook reads the latest date here to decide whether maintenance is due today. The rules are in [[Note schema]] and the method in [[Second brain]].

## 2026-10-16

- Created the brain: [[Home]], the core three ([[User]], [[Identity]], [[Soul]]), plus project, concept, data, decision and operating notes.
- Ran `scripts/brain_check.py --strict` and resolved every finding before the first commit.
