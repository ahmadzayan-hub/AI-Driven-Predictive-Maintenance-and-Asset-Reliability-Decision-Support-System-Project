# A clip's number must be in its source, not merely cite one

- Status: accepted
- Date: 2026-10-20
- Extends the motion skill (`.claude/skills/motion/`) and the figures discipline
  of `scripts/figures_check.py`.

## Problem

The owner pointed out that `motion-designer` has a real role in the
deliverables - a presentation's animated opener, a dashboard teaser, a capstone
briefing clip - and that the question is not whether it belongs but whether it
earns its place. I had recorded the opposite in ADR 0060's consequences, which
was wrong: the agent's own description names those roles and `docs/PLAYBOOK.md`
has a runbook for it. What it lacked was use, not a purpose.

Looking for where it could add value found a hole in its only gate.
`render.mjs --check` required a figure's `source` to be a non-empty string and
nothing more. So a clip could carry

```json
{"label": "Availability", "value": 42.0, "source": "the workbook"}
```

with an invented number, pass the check, and the tool would print
**"7 figures, each with a source"** - a sentence that sounds like verification
and is not. Everywhere else in this project a figure traces to a calculation:
`figures_check.py` reads the register and checks the arithmetic, the dashboard
marks every number to its dataset, and the governed pipeline refuses a claim
with no calculation behind it. The clip, which is the artefact an audience sees
first and scrutinises least, had the weakest check of any of them.

## Decision

`checkSources(spec, read)` reads the file a `source` names and requires the
clip's number to be in it.

- A source that **names a file** (`.csv`, `.json`, `.md`, `.txt`, `.tsv`) is a
  claim the tool can test, so it tests it. The value must appear in that file,
  at the precision the clip shows it: a clip saying `96.8` is satisfied by
  `96.779802` in the register, because that is the same number rounded, and is
  not satisfied by `42`.
- A source that names a **file that is not there** is now refused. Before, a
  typo in a path passed silently.
- A source that names a **place in prose** ("the workbook, Executive KPIs") is
  a claim only a person can check, so the tool does not pretend to: it says so.

The summary line now says what it verified rather than what it required -
either "`N of M checked against the file their source names`" or "`no source
names a file, so no figure was checked against one`". A tool that overstates
its own check is worse than one with no check, because it transfers confidence
it has not earned.

`validate` stays pure and file-free; the reading is a separate function the
command wires to the filesystem, so the spec rules remain testable without a
disk.

## What this is worth, measured

`tests/test_motion.py`, 11 tests, all passing. Three are new and each was seen
to fail before the change:

- a figure whose value is absent from the file its source names is refused,
  while the true figure beside it passes;
- a source naming a file that is not there is refused;
- the summary says "no source names a file" when none does.

The two shipped examples still pass. Their sources name places in prose, so
they are now honestly reported as unchecked rather than as sourced - which is
the first thing this change revealed about the material already in the
repository.

## Consequences

- `motion-designer` can be pointed at the verified KPI register and the clip
  cannot contain a number the register does not hold. That is the value it was
  missing: not a new capability, but the same guarantee the report and the
  dashboard already give.
- A spec written against prose sources is unchanged and still renders; it is
  simply not claimed to be verified.
- The check reads whatever the file holds as text and looks for the number, so
  it cannot tell a coincidence from a citation. Finding `42` somewhere in a
  register does not prove the figure means what the clip says it means; a
  reviewer still reads the clip.
- ADR 0060's line suggesting `motion-designer` should justify its place or be
  retired is superseded by this record.
