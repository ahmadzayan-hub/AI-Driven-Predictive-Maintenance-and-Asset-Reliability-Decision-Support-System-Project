# Separator-insensitive loose keys and typo candidates

Date: 2026-11-06 · Status: Accepted · Owner request: "Continue next developments"; the gap analysis listed fuzzy join keys (typos, other separators)

## Context

Asset and station IDs are written differently by different systems: `ST-01`, `st_01`,
`ST 01`. The loose join of 30 October ignored letter case and runs of spaces only, so
those still failed to match. Typing slips (`PMP-03` for `PUMP-03`) failed silently,
showing only as a lower match rate.

## Decision

1. **A loose key also ignores separators** (spaces, `-`, `_`, `.`, `/`, `\`), so the
   three spellings above are one key. Leading zeros stay: `ST-01` is not `ST1`.
   A collision this creates in the joined dataset is refused by the existing repeated-key
   check, so a loose join can never count a row twice. An exact join counts these rows as
   near matches, as before.
2. **Typo candidates are named, never merged.** For a one-column text key, an unmatched
   key that is one letter changed, added or dropped from exactly one key of the joined
   dataset (both compared loosely, both at least 4 characters) is counted. The join
   record carries `typo_keys`, `typo_rows` and up to five examples with the joined
   dataset's own spelling. The report adds a cited limitation in English and Arabic
   ("… were not merged; check whether they are typing slips"). A key with two candidates
   is ambiguous and named as neither; short codes such as `P1` and `P3` are never
   treated as typos.
3. The join builder's label and near-match line say "case, spaces and separators" in both
   languages. No new interface element: the candidates reach the reader through the report.

## Consequences

- Tests: key spellings and leading zeros; a one-letter slip named with its rows and not
  merged; short and ambiguous keys not guessed; separators matched under loose and counted
  as near matches under exact; a governed run whose report names the slip and passes every
  validator check. Two earlier tests changed with the definition.
- A loose join made before 6 November and re-run today can match more rows. Its report
  says how many matched only because of the loose comparison.
- Not done: composite keys and numeric keys get no typo candidates; candidates are not
  offered as one-press fixes in the join builder (the script budget has 0.4 KB left).
