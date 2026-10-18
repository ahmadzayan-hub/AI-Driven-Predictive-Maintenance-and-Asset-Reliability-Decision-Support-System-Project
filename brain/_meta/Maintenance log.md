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

