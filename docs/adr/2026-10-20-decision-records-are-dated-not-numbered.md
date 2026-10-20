# Decision records are dated, not numbered

- Status: accepted
- Date: 2026-10-20
- Closes the sequential counter at ADR 0060. Does not rename the 60 records
  that exist.

## Problem

Eight number collisions in three days, four of them on 19 October alone:

| Number | Claimed by | And by |
| --- | --- | --- |
| 0045 | rail-asset screening contract | a second record, renumbered 0052 |
| 0046 | opt-in maintenance profile | the Supabase record, renumbered 0053 |
| 0054 | Miyaar workspace (PR #15) | the causal lint, renumbered 0056 |
| 0055 | local model and Whisper (PR #15) | knowledge collections, renumbered 0057 |
| 0059 | executive business exports | the standards lint, renumbered 0060 |

Every one happened the same way. Two sessions each read `docs/adr/`, each
correctly worked out the next free number, and both were right: nothing had
been pushed yet. The second to push renumbered, and renumbering is not free -
it touches the file name, the heading, and every reference in code, tests, the
board and other records. On 19 October one renumbering updated ten references
across eight files.

**A sequential counter is shared mutable state that no session can see.** Two
sessions cannot both pick the next number correctly, and nothing in the
repository told either of them that the other existed. The session-end gate
caught four of these before a push, which is why nothing was lost - but a gate
that keeps catching the same thing is describing a design fault, not fixing it.

## Decision

**A new decision record is named `YYYY-MM-DD-slug.md`.** The sequential counter
is closed at 0060.

Two sessions collide only by choosing the same slug for different decisions on
the same day. Slugs describe the decision, so that is already unlikely; and
when it happens Git conflicts on the path, which is a visible conflict a person
resolves, not two records silently claiming one number.

**The 60 existing records keep their numbers.** They are referenced from
`config.json`, `server/`, `tests/`, `README.md`, `project-progress.md`,
`Memory.md`, the brain's decision log and each other. Renaming them would be a
large mechanical change with nothing to gain, and a record states what was true
when it was written - the same reason the dated verification records of 17 and
18 October were left alone.

So `docs/adr/` holds both forms, and that is intended: a number means "written
before 20 October 2026", a date means "written after".

**Three tests in `tests/test_docs.py` enforce it**, each proven to fail when
violated:

- `test_no_two_records_share_a_number` - no two records share a number.
- `test_a_new_record_is_dated_rather_than_numbered` - a sequential number above
  0060 fails, with the message "the sequential counter is closed at 0060; name
  a new record YYYY-MM-DD-slug.md so two sessions cannot collide".
- `test_every_record_opens_with_its_own_name` - a numbered record's heading
  carries its number, so a half-finished renumbering cannot pass.

## What was considered and rejected

- **Keep numbering and rely on the gate.** It has worked four times out of
  four, but it works by making the second session redo its naming. The cost
  falls on whoever pushes second, every time.
- **Reserve a number by pushing an empty record first.** It makes the counter
  visible, at the price of a push before the work and a stub if the work is
  abandoned.
- **Rename all 60 to dates.** Consistent, and not worth breaking every
  reference in the repository for.
- **A monotonic id from a timestamp or a hash.** Collision-free and unreadable;
  a decision record is read by people.

## Consequences

- `docs/PLAYBOOK.md` and `AGENTS.md` now state the dated form, so a session
  following either does not reach for a number.
- Referring to a record is by its name rather than "ADR NNNN"; the older
  records keep their familiar numbers in prose.
- A date in the file name is not the decision's authority - `Status:` and the
  body are. Two records on one day are ordered by their content, not their
  names.
