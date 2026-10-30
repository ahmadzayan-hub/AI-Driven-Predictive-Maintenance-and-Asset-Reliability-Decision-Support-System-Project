# codebase-memory-mcp as a code-navigation aid: options for the owner's decision

Date: 2026-10-30 · Status: **Proposed, awaiting the owner's decision.** Nothing
is installed, configured or committed for it. This record exists because the
tool would change how every coding agent works in this repository, and that is
a team-wide decision, not a session's.

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

## What the owner must decide

1. Option A, B, C or D.
2. If A, who runs the trial, and whether its results are recorded in this
   record.

## Sources

- <https://github.com/DeusData/codebase-memory-mcp> (README, LICENSE)
- <https://www.npmjs.com/package/codebase-memory-mcp> and
  <https://pypi.org/project/codebase-memory-mcp/> (version 0.12.1)
- <https://github.com/NanoNets/Graft>, <https://github.com/calesthio/OpenMontage>,
  <https://github.com/msitarzewski/agency-agents> (LICENSE files)
