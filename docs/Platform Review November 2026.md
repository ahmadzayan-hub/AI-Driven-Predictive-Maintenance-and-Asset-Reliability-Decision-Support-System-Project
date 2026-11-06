# Platform review, 6 November 2026

The owner's brief, "Review, repair, test and improve this repository into an interactive
AI-driven predictive maintenance decision-support assistant", in phases. This record
separates what was verified from what was not. Nothing here claims production readiness.

## Phase 1: pull requests and merge reconciliation

Live state, fetched 6 November 2026, about 17:30 UTC:

| PR | Base | Head | State | Finding |
| --- | --- | --- | --- | --- |
| #96 | `main` (`654c500`) | `claude/tender-clarke-m4uwgq` | open, ready | This branch: 23 feature commits, the three drafts merged in, and the fixes below |
| #93 | `main` | `feature/isolated-large-data-video-worker-assessment` (`b795f5d`) | draft | Experimental large-data modules (`server/experimental_*.py`), not wired to any API route (their header says so; no route imports them). `server/datasets.py` change refuses PDF, images and Parquet early, including renamed `.csv`. Component tests only: they do not prove an authenticated 300 MB application upload |
| #94 | #93's branch | `test/pr93-verified-acceptance-20261106` (`50252ec`) | draft | Diverged from #93 (3 commits only in #94, 6 only in #93). Added four action pins without the release comment `tests/test_sbom.py` requires, and a second copy of the 300 MB benchmark |
| #95 | `main` | `feature/external-tool-evaluation-20261106` (`1a59a59`) | draft | Its safety tests were pytest functions: `python -m unittest discover` (what CI runs) ran 0 of them. The gate accepted self-declared booleans (`revision_pinned`, `external_egress`) as proof |

Repairs made on this branch (all in #96):

1. `51302dd`: release comments on the four pins, copied from the same commits elsewhere in
   the workflows (`checkout` v5.1.0, `setup-python` v7.1.0). The check is not weakened.
2. `89a27a3`: #95's tests are unittest cases now (5 run, 0 before). The gate demands evidence:
   a 40-hex commit for a pinned revision, a 64-hex sandbox-run digest for isolation and
   blocked egress, a reviewer and date for a passed review. All three listed candidates stay
   BLOCKED (tested). The 300 MB benchmark lives only in `pr93-isolated-acceptance.yml`, started
   by hand; the duplicate job in `ci.yml`, skipped on every PR, is removed.
3. `b3f4700`: the four model validity corrections (Phase 4).

Exact-head tests, `python scripts/verify.py` on `b3f4700`: 8 of 8 steps passed; Python 2,766
tests, 303 skipped (PostgreSQL-only and optional-runtime tests skip without those services;
the deletion and named-view PostgreSQL cases were run separately and pass); frontend 613
passed; script total 287.5 of 292 KB. Not run here: the full end-to-end suite (26 of 26 of
the affected specs passed earlier on this branch), the 300 MB benchmark, the Android build.
CI on GitHub for the latest head had not finished when this was written.

Merge order and gates: #96 carries #93, #94 and #95 as merge commits, so merging #96 merges
all four; #93 to #95 would then show their commits in `main`. The merge is **held**:

- Merging to `main` starts a Vercel production build (every production deployment so far came
  from a `main` commit). Production currently fails closed (`DATABASE_URL` without a sign-in
  provider). A production deployment needs the owner's explicit approval under this brief.
- Human review of #93 to #95 is not recorded; their authors marked them draft.
- The green checks do not cover the skipped 300 MB job.

Rollback: `main` is at `654c500`. If #96 is merged and must be undone, revert the merge commit
with `git revert -m 1 <merge>` (no history rewrite) and redeploy the previous production
deployment from Vercel's list.

Cost register:

| Item | Finding | Recommendation |
| --- | --- | --- |
| CI runs twice per push to a PR branch | `ci.yml` triggers on `push` to every branch and on `pull_request` | Limit `push` to `main` (owner decision: other sessions rely on push CI for branches without a PR) |
| 300 MB benchmark | About an hour of runner time; was configured twice | Now one manual workflow |
| Timeouts raised by #94 | `test` 45 to 90 min, `arabic-media` 10 to 45 min | Raises the worst-case cost of a hung job, not the normal one |
| Vercel | Hobby plan (runtime log retention is one hour); every branch push makes a preview build | GitHub Actions and Vercel billing could not be read from this session |

## Phase 2: separating Miyaar from RMD and RTA

Inventory (read-only; nothing removed yet):

| Area | RMD-specific | RTA-specific |
| --- | --- | --- |
| API | 22 routes under `/api/rmd` (`server/rmd_api.py`) | none |
| Server | `server/rmd_analytics.py`, `rmd_api.py`, `rmd_assistant.py`, `rmd_ingestion.py`, `rmd_schema.py`, `rmd_service.py`, `rmd_workflow.py` | none |
| Tables | `rmd_actions`, `rmd_analyses`, `rmd_analysis_sources`, `rmd_audit`, `rmd_counts`, `rmd_incidents`, `rmd_links`, `rmd_packs`, `rmd_requests`, `rmd_runs`, `rmd_sources` | none |
| Interface | the `rmd` tab (`frontend/src/app/WorkflowNav.tsx`, `routing.ts`, `App.tsx`, `lazyViews.tsx`), `frontend/src/features/rmd/`, strings in `i18n` | no RTA string, logo or token in `frontend/src` or `server` |
| CI | `.github/workflows/rmd-evidence.yml` | none |
| Knowledge | `knowledge/rmd-v2-mba-9227/`, `knowledge/rmd-v2-analytics-9226/` | none |
| Repository tooling | none | `.claude/skills/rta-style/` (agent-output colours and type only) and its mention in `CLAUDE.md` |

The authorization boundary. `server/rmd_workflow.py` `authorize_run` returns `None` for an
ordinary run and the evidence-pack decision for an RMD-bound run; `server/app.py` `owns_run`,
the run list, chat (`server/assistant.py`, `server/data_chat.py`), erasure (`server/erasure.py`)
and motion (`server/motion_storyboard.py`) consult `rmd_runs` directly. Deleting the RMD
module or this check would make RMD-bound runs fall back to ordinary ownership and become
visible. It must not be removed.

Safe plan, not yet executed:

1. Retire the RMD routes and tab behind one setting, default retired, with the legacy mode
   available only to an operator preparing an archive. Retired `/api/rmd/*` answers 404.
2. Keep `authorize_run` as a quarantine: when retired, every RMD-bound run is refused (404) to
   everyone through every generic path: runs, query, records, brief, exports, video, chat,
   layouts, views. Test each path with a seeded RMD-bound run.
3. Keep the `rmd_*` tables, migrations and backup and restore order untouched; mark them
   retired in the schema notes. No data is deleted or moved.
4. A reviewed, reversible archive (counts, hashes, ownership, audit trail, reports) only with
   the owner's authorization, as a separate change.
5. Production connector IDs and schedules: to be inventoried read-only once the hosted service
   is reachable with sign-in; none is changed.

Human decisions needed before step 1: whether the RMD V2 knowledge packs go (the owner's
instruction of 23 October 2026 says to preserve public MBA course materials, which they are);
whether the `rta-style` skill should be renamed to a neutral house style.

## Phase 4: model validity

All four static-review leads were reproduced and corrected; see
[the decision record](adr/2026-11-06-model-validity-corrections.md). The risk ranking now
backtests itself on the window after a cutoff one horizon back: a stated future-failure target
and horizon, refits on records up to the cutoff only, Brier score against a constant-rate
baseline, calibration bands, top-ten hits and false alerts per asset-month
([decision](adr/2026-11-06-risk-ranking-backtest.md)). Remaining: asset and site holdouts,
feature availability timestamps, and prospective shadow-ledger outcomes (the ledger exists;
no real outcomes are recorded).

## Phase 3: agent harness

Separation of duties: with `AGENTIC_OS_SEPARATE_APPROVER` on, the person who started an
analysis cannot approve its report or exports; it is off by default and the operator decides
([decision](adr/2026-11-06-separate-approver.md)). AI already holds no approval: specialist
tool grants refuse publish, approve, delete and shell. Not started: request-bound revocable
tool capabilities, stale-worker and cancellation tests, and a workspace reviewer role.

## Phases 5 and 6

Not started in this session: the end-to-end authenticated slice, and the read-only
enterprise integration proposal. They depend on Phase 2's separation and on a reachable,
signed-in hosted deployment for the authenticated journey.
