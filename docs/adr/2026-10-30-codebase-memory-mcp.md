# codebase-memory-mcp as a code-navigation aid

Date: 2026-10-30 · Status: **Accepted, option A** (the owner, 2026-10-30). Each
developer may install it on their own machine as an MCP server only, after a
measured trial. Nothing is added to the tracked agent configuration. The one
tracked change is a `.gitignore` guard for the tool's optional graph snapshot.
The trial has not yet run; its owner is not yet named.

This record exists because the tool would change how every coding agent works
in this repository, and that is a team-wide decision, not a session's.

## Context

The owner asked whether four tools shown in a social-media reel add value to
this project. Each was checked against its own repository on 2026-10-30, not
against the reel. Three were rejected:

- **Graft, now Trail** (`NanoNets/Graft`, npm `@trailhq/trail-code`, MIT).
  `trail init` reads Claude Code transcripts and the review comments of the
  last 50 merged pull requests, and writes "learnings" into a `.trail/` folder
  that is meant to be committed. This repository is public, so that risks
  private session content reaching Git. Anonymous telemetry is on by default.
- **OpenMontage** (`calesthio/OpenMontage`, AGPLv3). The licence is the
  blocker: code taken into a hosted product could oblige publishing the
  platform's source. The project's motion skill already makes clips from
  verified figures without a video model.
- **The Agency** (`msitarzewski/agency-agents`, MIT). 232 prompt personas with
  no measured recall. This project's reviewer agents are scored against
  labelled benchmarks with recall floors (`evals/floors.json`); unmeasured
  agents would weaken that loop.

The fourth, **codebase-memory-mcp** (`DeusData/codebase-memory-mcp`), is the
subject of this record.

## What the tool is (verified from its repository and package registries)

- An MCP server, written in C, that parses a repository into a local graph of
  files, functions, classes and call edges, and answers structural questions
  ("who calls this", "what does this change affect") through MCP tools.
- Licence: MIT. Version 0.12.1 on both npm and PyPI on 2026-10-30.
- Indexing and queries run on the local machine with no API key and no hosted
  service. Its README states that the binary makes no network request of its
  own accord and does not phone home. That is the vendor's statement; it has
  not been tested here.
- Releases carry a `checksums.txt` of SHA-256 hashes, and the repository shows
  an SLSA level 3 badge.
- Its optional browser companion, CBM Lens, downloads a model from Hugging Face
  only if the user enables local chat.
- Its `install` command does more than register the server: it writes client
  configuration, skills, "Scout/Verify/Auditor" agent profiles and context
  hooks for every coding agent it detects.

This repository holds 516 tracked Python, TypeScript and JavaScript files, and
about 115,000 lines of Python and TypeScript (counted 2026-10-30). The vendor's
token-saving figures come from its own benchmark and have not been measured on
this repository.

## The constraint found in this environment

The npm and PyPI packages are thin wrappers (the wheel is 16 KB) that fetch the
native binary from GitHub releases. In the cloud sessions used for this
project, the network proxy refuses GitHub release downloads (HTTP 403), so the
tool cannot be installed there by any of its routes. It can be installed on a
developer's own machine.

## Options

**A. Each developer installs it locally, the MCP server only (recommended).**
Download the release, check it against `checksums.txt`, and register only the
MCP server in the developer's own, untracked Claude Code configuration. Do not
run `install`, so no agent profiles, skills or hooks are written.
- For: no change to tracked files; the project's own agent team is unchanged;
  anyone can stop using it by removing one entry.
- Against: each developer sets it up by hand; cloud sessions cannot use it.

**B. Add it to the tracked `.mcp.json`.**
- Against: every contributor's Claude Code would try to start a binary most of
  them do not have, and cloud sessions would show a failing server. Not
  recommended while the binary cannot be fetched there.

**C. Run its `install` command.**
- Against: it writes its own agent profiles and hooks beside the project's
  measured reviewers (`.claude/agents/`) and hooks (`.claude/hooks/`), which
  would change agent behaviour outside the review loop. Not recommended.

**D. Do not adopt it.**
- For: nothing to review or maintain. Agents keep using the built-in search
  tools, which work today.
- Against: gives up a possible saving on large structural questions.

## Recommendation

Option A, with a short measured trial before anything wider:

1. One developer installs it locally as in A.
2. On this repository, ask the same three structural questions with and without
   it (for example: what calls `save_dashboard_view`; what a change to
   `server/storage.py` affects; where a run's stage report is assembled), and
   record tokens used, time and whether each answer was correct.
3. Point the index at tracked source only. Before use, confirm how the tool
   selects files, and that it leaves out `private/`, the runtime `vault/` and
   any dataset files. Index files never go into Git.
4. Adopt more widely only if the trial shows a clear saving with correct
   answers. A wider adoption would amend this record.

## Decision

Option A, chosen by the owner on 2026-10-30. Still open: who runs the trial.
Its results are to be added to this record.

## Setup on a developer's machine (macOS or Linux)

These steps follow the tool's own manual-install and manual-configuration
sections and skip its `install` command on purpose.

1. Download the archive for your platform and `checksums.txt` from the latest
   release at <https://github.com/DeusData/codebase-memory-mcp/releases>
   (for example `codebase-memory-mcp-darwin-arm64.tar.gz` on Apple Silicon).
2. Verify it: `shasum -a 256 -c checksums.txt --ignore-missing` on macOS, or
   `sha256sum -c checksums.txt --ignore-missing` on Linux. Stop if it fails.
3. Extract the executable to a folder of your own, outside this repository,
   for example `~/bin/codebase-memory-mcp`. Do not run its `install` or
   `install.sh`.
4. Register the server for your user only, so no tracked file changes:
   `claude mcp add --scope user codebase-memory-mcp "$HOME/bin/codebase-memory-mcp"`.
   This writes to `~/.claude.json`, outside the repository. Do not add it to
   the tracked `.mcp.json`.
5. Restart Claude Code and check `/mcp`. The tool's README says it should list
   `codebase-memory-mcp` with 17 tools.
6. Before relying on it, ask it to index this repository and read its coverage
   report. Its ignore rules follow `.gitignore`, which already excludes
   `private/`, `brain/private/`, `vault/` and the local database
   (`data/agentic.db*`). Confirm that none of them appears in the index.
7. Leave `persistence` at its default (`false`). If a `.codebase-memory/`
   folder appears anyway, `.gitignore` keeps it out of Git.

To stop using it: `claude mcp remove --scope user codebase-memory-mcp`, then
delete the executable and its cache folder.

## The trial

Ask the same three questions with and without the tool, in fresh sessions on
the same commit:

1. What calls `SqlStore.save_dashboard_view` (`server/storage.py`)?
2. What would a change to `SqlStore.save_dashboard_view` affect?
3. Where is a run's stage report assembled?

Record, for each: tokens used, time taken and whether the answer was correct
against the code. Adopt it more widely only on a clear saving with correct
answers, and amend this record either way.

## Sources

- <https://github.com/DeusData/codebase-memory-mcp> (README, LICENSE)
- <https://www.npmjs.com/package/codebase-memory-mcp> and
  <https://pypi.org/project/codebase-memory-mcp/> (version 0.12.1)
- <https://github.com/NanoNets/Graft>, <https://github.com/calesthio/OpenMontage>,
  <https://github.com/msitarzewski/agency-agents> (LICENSE files)
