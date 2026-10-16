---
type: project
aliases: [Agentic OS project]
tags: [project]
status: active
updated: 2026-10-16
review_every_days: 14
sources: [README.md, docs/ROADMAP.md, docs/VERCEL_DEPLOYMENT.md, project-progress.md, docs/adr/0023-the-analytics-workspace-interface.md]
---

# Agentic OS

The product in this repository, described in [[Identity]]: a governed business-analytics assistant with a web workspace and a command-line interface.

## Where it lives

- **Repository:** `ahmadzayan-hub/agentic-os-final-project`, public. The old name `ahmadzayan-hub/11` redirects.
- **Default and working branch:** `claude/agentic-os-final-project-53j6ql`. `main` is behind it, and it stays the default until after submission.
- **Production:** a Vercel deployment behind Vercel Authentication. It is verified for a signed-in owner only, and auth and the database are unverified there.

## What it does today

- Chat in English or Arabic that maps a sentence to a typed action.
- Analyses of one CSV dataset (up to 2 MB) through the [[Governed pipeline]], sequenced by the [[Hermes orchestrator]].
- Reports with claims linked to calculations, published through the [[Approval gate]].
- Optional narration through the [[Model gateway]]; extension through [[Custom stages]] and [[Agent runtimes and MCP]].
- The bundled [[Sample sales data]] works without an upload.
- An Overview of key figures, the latest findings and the approval queue, and a Datasets view that analyses a stored dataset again by reference. Both follow the [[Design system]].

## Verified state on 2026-10-16

- 646 Python tests passed against PostgreSQL, with 16 optional-library skips. That includes 30 tests for the brain checker and the session hooks.
- After the interface work (`dea3b38`): 52 frontend unit tests passed, and 57 of 60 end-to-end checks ran and passed, with 3 skipped by design because each covers one viewport.
- CI run 43 was green on commit `7091b76`, before the operating-system commit.

These counts go stale fast; `README.md` is the one place where they are maintained.

## Direction

The next stage is the [[Analytics OS roadmap]]: several datasets, dynamic inputs, a dashboard and live data. Decisions so far are in the [[Decision log]].

## Related

- [[User]], who owns it.
- [[Team collaboration]], for how teammates contribute.
- [[Session lifecycle]], for how work on it is run.
