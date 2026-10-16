---
type: operation
aliases: [Review loop, Review super agent, Reviewer subagents]
tags: [operating, quality]
status: active
updated: 2026-10-16
review_every_days: 30
sources: [docs/AGENT_TEAM.md, .claude/skills/review-loop/SKILL.md, .claude/skills/dashboards/SKILL.md, scripts/review_gate.py, scripts/figures_check.py, scripts/analyse.py, scripts/consult.py, docs/adr/0026-uneven-periods-are-read-per-record.md]
---

# Agent team

The agent team checks this project's work and builds its outputs. Specialist subagents each do one job on the cheapest model that does it well, and a review loop runs them until a deliverable is validated, or says why it cannot be.

## Facts

- **Tiers:** deterministic scripts cost nothing. Free local models (Qwen3, gpt-oss) run through `scripts/consult.py`. Haiku reviewers do the mechanical checks, Sonnet reviewers the expert judgement, and the main session runs the loop. The tiers and the roster are in `docs/AGENT_TEAM.md`.
- **Roster:** five read-only reviewers (figures, brief, analytics, security and privacy, accessibility and Arabic), `dashboard-analyst` and `motion-designer`.
- **The loop:** a skill run by the main session, because a subagent cannot start another subagent. 100% means every gate passes, or is accepted in writing by a named person. It stops after five rounds or after two with no gain.
- **First run, 16 October 2026, on the [[Team 3 Capstone]]:**
    - The score went 50.0% → 56.2% → 62.5% → 62.5%.
    - Every gate the session could act on passed. The rest need the team: the `.pbix`, their own items, and two wording changes in their shared report.
    - The analytics reviewer found that two headline claims did not hold. A script recomputed both from the data before they went to the team.
- **What the first run changed in the tools:**
    - The figures checker now reads glued table cells and checks worked arithmetic.
    - The pipeline now reads uneven periods per record (ADR 0026), after a dashboard showed a 39% "fall" that was a fall in records.
- **Dashboards:** the `dashboards` skill builds a Claude Dashboard where the artifact type exists, and an offline page elsewhere. In both, every figure is marked with its source.
- **Local models:** they are untested live here, because this environment cannot download them.

## Related

- [[Home]]
- [[Soul]]: evidence before claims, and limits stated openly, are what the loop enforces.
- [[Weighted KPIs]]: the note the first review corrected.
- [[Governed pipeline]]: `scripts/analyse.py` runs it for dashboards at no cost.
- [[Session lifecycle]]: the loop runs inside a session, before anything is handed over.
