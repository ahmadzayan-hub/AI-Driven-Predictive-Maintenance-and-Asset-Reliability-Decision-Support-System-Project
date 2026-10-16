# .claude: how Claude Code works in this repository

Everything here is shared with the team through Git, except the paths `.gitignore` excludes: `settings.local.json`, `state/` and `agent-memory-local/`. The operating rules are in `docs/PLAYBOOK.md`.

| Path | What it holds |
| --- | --- |
| `settings.json` | The three project hooks below. Personal settings go in `settings.local.json`, which Git ignores. |
| `hooks/session_start.py` | Records where a session began, and briefs Claude: current focus, last log entry, brain health, whether maintenance is due. |
| `hooks/stop_gate.py` | Blocks a finish once when the session committed work but has no `session-logs.md` entry. |
| `hooks/session_end.py` | Appends a factual automatic log entry if the session-end skill never ran. |
| `skills/session-start/` | Orient: read the memory files, check the repository, state the plan. |
| `skills/session-end/` | Log the session, update progress, memory and the brain, then commit. |
| `skills/brain-maintenance/` | Daily: refresh stale values, merge duplicates, repair and add wikilinks. |
| `commands/` | Slash commands. Empty for now; see below. |
| `agents/` | Project subagents. Empty for now; see below. |
| `plugins/` | How to add project plugins. Documentation only. |
| `state/` | Hook runtime state, one JSON file per session. Git ignores it. |

Hooks run only after you trust this folder in Claude Code, and they need `python3` on the path. Each one fails open: an error prints a warning and never stops your session. `/hooks` lists what is active, and `"disableAllHooks": true` in your `settings.local.json` turns them off for you alone.

## Adding a command

Claude Code has merged commands into skills. Prefer `skills/<name>/SKILL.md`, which is also invocable as `/<name>`. A one-file prompt can still go in `commands/<name>.md`:

```markdown
---
description: One line shown in the / menu
argument-hint: <dataset name>
---

Analyse the dataset named $ARGUMENTS with the governed pipeline, then …
```

Every `.md` file in `commands/` becomes a command, so keep notes like this one out of that folder. Do not reuse built-in names such as `/status`, `/help` or `/review`.

Planned, with the analytics roadmap in `project-progress.md`: `/analyse <dataset>` once the dataset API exists, and `/dashboard <run>` once dashboard pages exist. They are not here yet, because a command for a missing feature would be a stub.

## Adding a subagent

One file, `agents/<name>.md`:

```markdown
---
name: data-quality-reviewer
description: Reviews a dataset profile and the cleaning stage's output for problems a person should decide on.
tools: Read, Grep, Glob, Bash
model: inherit
---

You review data quality for Agentic OS. …
```

`name` and `description` are required. Files without a `name`, or whose `---` is not the first line, are skipped silently. Candidates for the roadmap are a data-quality reviewer, a dashboard designer and a model evaluator that checks every model against its baseline. Each is added with the feature it serves.
