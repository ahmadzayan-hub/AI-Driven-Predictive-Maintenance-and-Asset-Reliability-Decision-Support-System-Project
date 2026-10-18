# Keeping GitHub and the local folder in step

How the working copy at
`C:\Users\ahmad\OneDrive\Desktop\agentic-os-final-project-claude-agentic-os-final-project-53j6ql`
relates to
[`ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project`](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project),
and the routine for pushing local progress to it.

Comparison made 19 October 2026, after `git fetch origin --prune`.

## The headline

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

## What exactly differs

`git diff --name-status HEAD origin/main` — 8 files, all from PR #14,
316 insertions and 10 deletions:

| Status | Path | What it is |
| --- | --- | --- |
| added | `database/migrations/20261018_asset_reliability_ai_initial.sql` | the initial Supabase schema migration |
| added | `docs/SUPABASE_SECURE_CONNECTION.md` | how the secure connection is set up |
| added | `docs/adr/0046-dedicated-supabase-schema-and-auth-bootstrap.md` | the decision record |
| added | `tests/test_supabase_schema_snapshot.py` | 3 tests checking the migration against `server.storage` |
| modified | `server/auth.py` | `public_auth_config` now advertises `["password"]` only; the magic-link callback is not implemented, so it is no longer offered |
| modified | `tests/test_auth.py` | asserts `magic_link` is absent from the advertised flows |
| modified | `frontend/src/features/auth/SignIn.tsx` | an `sb_publishable_*` key goes in the `apikey` header only, never as an `Authorization: Bearer` credential; the magic-link button renders only when the flow is advertised |
| modified | `frontend/src/tests/signin.test.tsx` | 1 test covering the modern-key header and the hidden button |

Decision records: 52 locally, 53 on `origin/main`.

## What the local folder holds that GitHub does not

Nothing tracked. The tree is clean, with no modified and no untracked files.

Everything else in the folder is git-ignored on purpose and must stay that
way — `private/`, `inputs/`, `vault/`, `backups/`, `data/`, the course files
matched by `Group_9226_*` and `Team3_*`, `roles/`, the private review's
scripts and captured output, `.claude/settings.local.json`, `.claude/state/`,
`brain/.obsidian/`, `node_modules/` and `frontend/dist/`. The repository is
public; course files, registration numbers and other people's personal data
never go in it.

Local `main` is a dead end, not work to preserve. It is 1 commit ahead of and
142 behind `origin/main`, and is not an ancestor of it — it is the
pre-reconciliation history from ADR 0039/0047. Its one unique commit
`a71e030` is the ADR 0041/0042 work, and that content is already on
`origin/main` by the route the working branch took. Nothing is lost by
discarding it.

## Bringing the local folder up to date

Run from the repository root. Each step is safe: no force-push, no history
rewriting, no branch deletion.

```bash
git fetch origin --prune

# 1. Put the working branch on top of what GitHub already has.
git switch claude/agentic-os-final-project-53j6ql
git merge --ff-only origin/main        # fast-forwards; origin/main contains HEAD

# 2. Repoint the stale local main at GitHub's main.
git switch main
git reset --hard origin/main           # discards a71e030, whose content is already on main
git switch claude/agentic-os-final-project-53j6ql
```

Then verify before trusting it:

```bash
python -m unittest discover tests
npm --prefix frontend ci
npm --prefix frontend run typecheck && npm --prefix frontend test && npm --prefix frontend run build
python scripts/brain_check.py --strict
python scripts/verify.py                # all of the above in one run, with real counts
```

## The routine for future local -> GitHub updates

This is the loop to use from here on, every session.

```bash
# 1. Start from what GitHub has, before writing anything.
git fetch origin --prune
git switch claude/agentic-os-final-project-53j6ql
git merge --ff-only origin/main

# 2. Do the work. A behaviour change needs a decision record and tests.

# 3. Prove it.
python scripts/verify.py

# 4. Record it in the working-memory files, then commit.
#    session-logs.md (one entry), project-progress.md (the board),
#    Memory.md (durable facts only), the brain notes the work touched.
git add -A
git commit            # end the message with the Co-Authored-By line

# 5. Push the working branch.
git push origin claude/agentic-os-final-project-53j6ql

# 6. End the session on main (standing permission, given 18 October).
git switch main
git merge --ff-only origin/main
git merge --no-ff claude/agentic-os-final-project-53j6ql
git push origin main
git switch claude/agentic-os-final-project-53j6ql
```

The `session-end` skill does steps 4 to 6, and a Stop hook blocks once if
commits were made and nothing was logged. Prefer the skill over running the
commands by hand.

Two rules that this comparison exists to protect:

- **Fetch before you write, not after.** PR #14 landed on GitHub an hour
  after the last local commit. Had the next session started by editing
  `server/auth.py`, it would have reverted a security fix without noticing.
- **Never force-push, rewrite history or delete a branch here.** The
  divergence above is resolved by merging and resetting a local-only
  pointer, nothing more.

## Open items this comparison turned up

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

4. **The `README.md` verification record is behind the tree.** It states
   that the suite discovers 1,177 tests, measured on 18 October. The local
   tree now discovers 1,185, and 1,188 once PR #14 is pulled in. The record
   is dated, so it is not wrong about that date — but a fresh
   `python scripts/verify.py` run should replace it.

   **Closed 19 October.** The live figures now read 1,188 Python and 143
   frontend tests; the dated records of 17 and 18 October stand as they
   are. Two defects turned up behind this one. The 93 cleanup errors were
   a real defect — stores left open inside a `TemporaryDirectory`, so
   Windows refused to unlink the file and passing tests were reported as
   errors — and are now **0**. And `scripts/verify.py` had been dying on
   its own output on a cp1252 console, killing the run after its first
   step while appearing to report on all six.

5. **The stale remote feature branches are missing everything merged after
   them** — between 100 and 136 files differ from `origin/main` on each.
   They are snapshots of already-merged pull requests, not live work. Only
   `origin/infra/supabase-secure-init-20261018` matches `origin/main`
   exactly, because it is PR #14's own source branch.

## Not checked here

The comparison above is a measurement of git refs and file trees, and made
no claim about whether either side was green. It has since been run.
Measured on 19 October 2026, after the fixes in items 2 to 4:

| Step | Result |
| --- | --- |
| Python tests | 1188 tests, **0 errors**, 1 failure, 132 skipped |
| Brain check | pass — 27 notes, 0 broken links, 0 orphans |
| Type check | pass |
| Frontend unit tests | pass — 143 of 143 |
| Production build | pass |
| Interface budget | pass, with almost no headroom |

The one remaining failure is environmental and was deliberately not
papered over: `test_backup.test_a_destroyed_database_is_rebuilt_from_a_backup`
launches `backup.py` as a subprocess, and under full-suite load on this
workspace that child interpreter dies before any of its code runs with
`_Py_HashRandomization_Init: failed to get random numbers`. No change to
`backup.py` can address that. CI on Linux is the authority for it.

The Playwright suite and PostgreSQL were **not** run here.
