# Keeping GitHub and the local folder in step

How the working copy at
`C:\Users\ahmad\OneDrive\Desktop\agentic-os-final-project-claude-agentic-os-final-project-53j6ql`
relates to
[`ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project`](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project),
and the routine for pushing local progress to it.

## Current merge status - 19 October 2026

The executive dashboard and evidence agent merged into `main` at `1b08b59`,
with parents `13171ce` and `a1c4af8`. The merge tree exactly matches its verified
feature tree. The source commits are `dccb156` and `f1c894d`; ADR 0058 and the
[Arabic/English handoff](design/EXECUTIVE_DASHBOARD_HANDOFF.md) record the
behavior and capability boundaries. Main's incoming Arabic causal lint and
Markdown knowledge collection work (ADRs 0056/0057) is preserved.

Both the active `miyaar` workspace and the Desktop checkout above select
`main` and were synchronized without discarding changes. The Desktop was
fast-forwarded from `6a03bba`, its frontend rebuilt under the supported Node
runtime, and its local server restarted on `http://localhost:8000`. A read-only
Arabic executive API smoke passed on an existing authorized run. The isolated
fictional preview remains separate from the Desktop database. Local operation
is not a production deployment or hosted Claude Artifact activation.

[PR #15](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/pull/15)
previously merged the Miyaar/local-AI implementation at `893986d`. Historical
feature refs are retained snapshots; they do not imply additional unmerged
work. This executive session created no pull request.

Use `origin`, the home repository linked above. `canonical` in the Desktop
checkout is an older remote, not a push target. Ignored private, course and
runtime files stay private. Verification results and counts belong in
[README - Testing](../README.md#testing).

## Safely update the Desktop checkout

Run these commands from that checkout's root. Continue only when the first
status command shows a clean tree. This downloads the latest refs and
fast-forwards local `main` without rewriting its history.

```bash
git status --short
git fetch origin refs/heads/main:refs/remotes/origin/main
git switch main
git merge --ff-only origin/main
git status --short --branch
```

If a branch has gained local work and a fast-forward is refused, stop and
inspect that divergence; preserve it with an ordinary merge. Do not discard
local changes, force-push, rewrite history or delete branches. For future
development, fetch and integrate before editing, verify the changes, and
follow the session-end merge procedure in [AGENTS.md](../AGENTS.md).

## Historical comparison — before PR #15

The rest of this document preserves the earlier 19 October comparison,
made after `git fetch origin --prune` when `origin/main` was `f744fd6`.
Its refs, differences and open-item observations describe that earlier
snapshot, not the current merge status. The old reset recipe has been
replaced by the fast-forward procedure above.

### The headline at that time

**The direction is the reverse of what it looks like.** The local folder has
nothing GitHub is missing. GitHub's `main` is one pull request ahead of the
local working copy. Nothing needs uploading; something needs pulling.

| Ref | Commit | Date | Subject |
| --- | --- | --- | --- |
| local `HEAD` = `claude/agentic-os-final-project-53j6ql` | `f4155e8` | 18 Oct 2026 22:53 +04 | Record what CI actually proves, and correct a claim I made |
| `origin/claude/agentic-os-final-project-53j6ql` | `f4155e8` | — | identical to local `HEAD` |
| `origin/main` (GitHub default branch) | `f744fd6` | 18 Oct 2026 23:56 +04 | Secure Supabase data-plane migration and Auth integration preparation (#14) |
| local `main` | `a71e030` | 18 Oct 2026 18:33 +04 | checkpoint: pending work before replay onto the canonical branch — **stale, see below** |

Measured, not assumed:

```
git rev-list --count origin/main..HEAD   ->  0    # local has nothing GitHub lacks
git rev-list --count HEAD..origin/main   ->  19   # GitHub main is ahead
git status --porcelain --untracked-files=all  ->  (empty)   # clean tree, nothing unstaged
```

The 19 commits are the merge commits that carried this branch into `main`
plus the pull requests merged there (#1, #2, #3, #4, #6, #9, #11, #12, #14).
Only one of them, #14, changes the tree relative to the local copy.

### What differed at that time

`git diff --name-status HEAD origin/main` — 8 files, all from PR #14,
316 insertions and 10 deletions:

| Status | Path | What it is |
| --- | --- | --- |
| added | `database/migrations/20261018_asset_reliability_ai_initial.sql` | the initial Supabase schema migration |
| added | `docs/SUPABASE_SECURE_CONNECTION.md` | how the secure connection is set up |
| added | `docs/adr/0046-dedicated-supabase-schema-and-auth-bootstrap.md` | the decision record |
| added | `tests/test_supabase_schema_snapshot.py` | checks the migration against `server.storage` |
| modified | `server/auth.py` | `public_auth_config` now advertises `["password"]` only; the magic-link callback is not implemented, so it is no longer offered |
| modified | `tests/test_auth.py` | asserts `magic_link` is absent from the advertised flows |
| modified | `frontend/src/features/auth/SignIn.tsx` | an `sb_publishable_*` key goes in the `apikey` header only, never as an `Authorization: Bearer` credential; the magic-link button renders only when the flow is advertised |
| modified | `frontend/src/tests/signin.test.tsx` | covers the modern-key header and the hidden button |

Decision records: 52 locally, 53 on `origin/main`.

### What the local folder held that GitHub did not

Nothing tracked. The tree is clean, with no modified and no untracked files.

Everything else in the folder is git-ignored on purpose and must stay that
way — `private/`, `inputs/`, `vault/`, `backups/`, `data/`, the course files
matched by `Group_9226_*` and `Team3_*`, `roles/`, the private review's
scripts and captured output, `.claude/settings.local.json`, `.claude/state/`,
`brain/.obsidian/`, `node_modules/` and `frontend/dist/`. The repository is
public; course files, registration numbers and other people's personal data
never go in it.

At this earlier snapshot, local `main` at `a71e030` was one commit ahead of
and 142 behind `origin/main`, with pre-reconciliation history from ADR
0039/0047. Its ADR 0041/0042 content was already on `origin/main` through the
working branch. That old divergence has since been reconciled: the latest
pre-merge Desktop audit found local `main` at `9a4199b`, so only the safe fast-forward
procedure above applies now.

### Open items the earlier comparison turned up

Each one is real and checkable, listed heaviest first. Items 2, 3 and 4
were **closed on 19 October**, in the session that found them, and each
carries a note saying what was done. Item 1 is the owner's alone, and
item 5 follows from it.

1. **Five remote branches still publish the private course files.** The
   current `origin/main` tree is clean — 0 sensitive paths. But
   `origin/chore/team3-contribution-folders`,
   `origin/feature/asset-reliability-identity-agent-evidence`,
   `origin/feature/saas-maintenance-decision-profile`,
   `origin/feature/voice-companion-executive-command-centre` and
   `origin/governance/team3-codeowners` each still carry 20 of them,
   including the 5,000-row course dataset, the file holding five
   registration numbers, the private assessment and its probe output.
   Ignoring the paths, as ADR 0047 says, stops the next upload; it does not
   contain what is already public. Only the owner can act on this, on
   GitHub, and deciding what to do with those branches is the owner's call —
   this document does not delete them.

2. **PR #14 is not recorded anywhere in the working memory.** No entry in
   `session-logs.md`, nothing on the board in `project-progress.md`, no line
   in `README.md`, `Memory.md`, `docs/KNOWN_LIMITATIONS.md` or the brain's
   decision log. The code shipped and the record did not follow it.

   **Closed 19 October.** Recorded in `session-logs.md` and
   `project-progress.md`, and the brain's decision log was backfilled with
   every record from 0044 to 0053 — it had drifted nine behind.

3. **Two decision records share the number 0046** on `origin/main`:
   `0046-opt-in-maintenance-profile.md` and
   `0046-dedicated-supabase-schema-and-auth-bootstrap.md`. One needs
   renumbering, with every reference to it updated in the same commit.

   **Closed 19 October.** The Supabase record is now **0053**, moved with
   `git mv` and carrying a note that only the number changed. The
   "ADR 0046" reference at `tests/test_stages.py:551` points at the
   maintenance-profile record, which keeps its number, so it needed no
   edit.

4. **The `README.md` verification record was behind the tree.** Its dated
   measurements needed a fresh verification run after PR #14.

   **Closed 19 October.** The record was refreshed. Two defects turned up:
   stores left open inside `TemporaryDirectory` made Windows report cleanup
   errors after passing test bodies, and `scripts/verify.py` could die on
   its own output on a cp1252 console. Current results and counts are kept
   only in [README — Testing](../README.md#testing).

5. **The stale remote feature branches are missing everything merged after
   them** — between 100 and 136 files differ from `origin/main` on each.
   They are snapshots of already-merged pull requests, not live work. Only
   `origin/infra/supabase-secure-init-20261018` matches `origin/main`
   exactly, because it is PR #14's own source branch.

### Historical verification boundary

The original comparison measured Git refs and file trees. Its later local
verification encountered a child-interpreter startup failure under suite
load; Playwright and PostgreSQL were not run in that comparison. This is a
historical observation, not a statement about the newly merged release.
Use [README — Testing](../README.md#testing) for the current measured results
and remaining acceptance limits.
