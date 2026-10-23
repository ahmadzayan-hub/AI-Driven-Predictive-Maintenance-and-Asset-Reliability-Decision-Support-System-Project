---
type: concept
aliases: [Brain, Knowledge vault]
tags: [operating, meta, operations]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [scripts/brain_check.py, .claude/skills/brain-maintenance/SKILL.md, docs/design/KNOWLEDGE_GRAPH.md]
---

# Second brain

This vault: the project's knowledge as small markdown notes joined by `[[wikilinks]]`. Open the `brain/` folder in Obsidian, or read it on GitHub.

## How it is organised

- **The core three:** [[User]], [[Identity]] and [[Soul]]. Every other note connects back to at least one of them.
- **Projects, concepts, data and operating notes,** all reachable from [[Home]].
- **Rules for notes** live in [[Note schema]], and **the record of upkeep** in [[Maintenance log]].

## Exploring the graph

Use `-path:_templates` in the global graph filter so the note template does not appear as a project concept. The source-grounded expansion adds focused agents, data, security, interface and operations topics. The guide in `docs/design/KNOWLEDGE_GRAPH.md` explains category colors, local graph depth and the distinction between a knowledge relationship and a live agent handoff.

## How it stays true

- `scripts/brain_check.py` finds broken links, stale notes, duplicate candidates, unlinked mentions, orphans and weakly linked notes. It never edits anything.
- The brain-maintenance skill runs once a day. The SessionStart hook says when it is due. The skill checks stale values against their sources, merges duplicates, links unlinked mentions and records what it changed.
- The session-end skill updates the notes a session touched. See [[Session lifecycle]].

## What it is not

It is not the runtime `vault/`, which holds published reports as user data behind the [[Approval gate]]. Brain notes are reviewed project content in Git. They hold no secrets and no personal data about others, and private notes belong in `brain/private/`, which Git ignores.

## Related
- [[Knowledge retrieval]]: is a separate reference service, not automatic access to these notes.
