---
type: log
aliases: [Brain maintenance log]
tags: [meta]
status: active
updated: 2026-10-17
review_every_days: 7
sources: [scripts/brain_check.py]
---

# Maintenance log

What each round of brain maintenance changed, newest last. The SessionStart hook reads the latest date here to decide whether maintenance is due today. The rules are in [[Note schema]] and the method in [[Second brain]].

## 2026-10-16

- Created the brain: [[Home]], the core three ([[User]], [[Identity]], [[Soul]]), plus project, concept, data, decision and operating notes.
- Ran `scripts/brain_check.py --strict` and resolved every finding before the first commit.

## 2026-10-17

- The check found no broken links, stale notes, duplicates or orphans.
- Refreshed facts that today's work changed:
    - [[Agentic OS]]: the test count, 851 at the verify run and 856 now, from the unittest run with PostgreSQL.
    - [[Team 3 Capstone]]: the report is now 23 pages, both deliverables are restyled, and the round-6 gates are unchanged. Sources: `session-logs.md`, the gate output.
    - [[User]]: the house style and typeface choice, and the wish to have agents measured. Sources: `Memory.md`, `session-logs.md`.
- Added [[House style]] (agent outputs, kept apart from the app's [[Design system]]). It is linked from [[Home]], [[User]], [[Team 3 Capstone]], [[Design system]] and [[Agent team]], and it links to [[Agent evaluation]].
- Linked one unlinked mention (House style, in [[Agent team]]).

- Checked the brain structure against `scripts/brain_check.py --json`: no broken links, missing fields, stale notes or duplicate candidates were reported.
- Added ADR 0029 to [[Decision log]], sourced from the implementation decision record. UI verification status is kept in the design validation record rather than copied from historical test counts.

## 2026-10-18

- `scripts/brain_check.py --json` reported a structurally clean brain: 27 notes, 278 links, and nothing under broken links, missing fields, bad dates, missing sources, stale, orphans, duplicates, unlinked mentions or weakly linked. No structural work was needed, so none was invented.
- Refreshed facts that today's remediation changed, each against the code it describes:
    - [[Weighted KPIs]]: added the third lesson — a gap is not a zero. Summing `value or 0` reported 5 hours of downtime per record from one reading of 10 across two records; a record now counts only when every column the arithmetic reads holds a finite number, and the excluded count travels with the figure. Sources: `server/maintenance/kpis.py`, ADR 0042.
    - [[Custom stages]]: added "written is not registered" — the maintenance governance and risk stages had their records and tests but were absent from `config.json`, so no run could select them until ADR 0041. Also corrected a stale sentence that still called the four modelling methods planned; they shipped on the `models` profile under ADR 0033. Sources: `config.json`, `server/stages.py`, ADRs 0033, 0039, 0040, 0041.
    - [[Decision log]]: added decisions 0041 and 0042.
- Added no notes and merged none: the two changes belong in concepts that already exist, and neither ADR introduces a concept the brain was missing.
- `scripts/brain_check.py --strict` exits 0 after the edits.

## 2026-10-19

- `scripts/brain_check.py --json` reported a structurally clean brain: 27 notes, 299 links, and nothing under broken links, missing fields, bad dates, missing sources, stale, orphans, duplicates, unlinked mentions or weakly linked. Nothing structural was needed, so none was invented. The round was due only because the log had no section dated today.
- Checked the brain's numeric claims against their sources rather than trusting the link check, which cannot see a wrong number. [[Decision log]] already runs through ADR 0053, backfilled earlier today by the other working copy, and no note quotes a test count — those live in `README.md` by convention, and the dated "Verified state" sections in [[Agentic OS]] are records of their own dates and were left alone.
- Refreshed [[Session lifecycle]]: step 3 of the loop now says to fetch before writing. A session that writes first can silently revert work that landed while it was thinking — which is how pull request #14's security fix nearly went, and how this session's own fix came to duplicate `a036cf9`. Sources: `docs/GITHUB_SYNC.md`, this session's log entry.
- Added no notes and merged none. The one lesson of the day belongs in a note that already exists, and nothing today introduced a concept the brain was missing.
- Corrected a record outside the brain, under the rule that the code wins: `Memory.md`'s environment line still said full Python verification fails on locked SQLite files and CRLF mismatches. It no longer does — 1188 tests, 142 skipped, 0 errors, 0 failures — so the line now states the green result, names the commits that closed it, and keeps only the two load-dependent flakes that are real.
- `scripts/brain_check.py --strict` exits 0 after the edits.

## 2026-10-20

- `scripts/brain_check.py --json` reported a structurally clean brain: 27 notes, 323 links, and nothing under broken links, missing fields, bad dates, missing sources, stale, orphans, duplicates, unlinked mentions or weakly linked. Nothing structural was invented.
- Refreshed [[Decision log]] with the two records this session decided, both named for the day rather than with the next number: the clip-source check, and the closing of the sequential counter at 0060. The log already carried 0058, 0059, 0060 and another session's dated record, which is the convention working in both directions on its first day.
- Checked, and left alone: [[Session lifecycle]] was refreshed yesterday with "fetch before you write" and already describes the loop the dated-record rule belongs to; the rule itself lives in `docs/PLAYBOOK.md` and `AGENTS.md`, where a session reads it, rather than being copied into a note.
- Added no notes and merged none. Neither of today's decisions introduces a concept the brain was missing: one is a naming convention, the other tightens a gate a note already describes.
- `scripts/brain_check.py --strict` exits 0 after the edits.
