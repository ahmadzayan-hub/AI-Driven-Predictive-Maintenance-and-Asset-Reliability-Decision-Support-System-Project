# Derived columns: arithmetic over the measures, saved with the mapping

Date: 2026-10-27 · Status: Accepted (the "derived columns" half of the
dynamic-inputs gap in the 16 October code audit, `project-progress.md`;
the slice after `2026-10-27-week-grain.md`). Amends ADR 0025.

## Context

A run analysed one mapped column. The figure a manager wants is often a
ratio or a difference of two columns an export carries: cost per hour,
downtime less planned downtime, revenue in thousands. Owners computed it
in a spreadsheet and uploaded again, which broke the content-addressed
dataset, its mapping and its runs, and put an unrecorded step between
the data and the report.

## Decision

1. **A mapping may declare up to five derived columns**, each a name and
   a formula. The formula is arithmetic only: `+ - * /`, brackets, unary
   minus, numbers, and the names of mapped measures or of earlier derived
   columns (a name with spaces goes in backticks). No functions, no text,
   no conditionals, no code: the parser is a small recursive descent in
   `server/mapping.py`, and nothing is evaluated by the interpreter.
2. **Checked when saved, in both languages.** A name must be an
   identifier of at most 40 characters that is not already a column; a
   formula must read; every name it reads must be a measure of the dataset
   or an earlier derived column; at most five. A derived column may be the
   measure the analysis is about.
3. **Computed after cleaning, from numbers.** The collector lists the
   derived names as columns of the table; the profiler counts them among
   the measures; the cleaner, once the measures are numbers, computes each
   formula row by row in order. A cell stays empty (None) where a value it
   reads is missing or a division divides by zero, as a measure that could
   not be read is empty. The cleaner records the formulas as a calculation
   and a claim that names them and counts the empty cells.
4. **Joined and stacked tables follow the mapping they are read with**:
   `clean_table` computes the derived columns of the mapping it is given,
   so a stacked export read with the main mapping has the same columns as
   the main table and stacks.
5. **The analysis table names them** (`roles[column] = "derived"`), from
   the names the cleaner recorded, so queries and downloads carry them.
6. **The mapping panel** has a *Derived columns* section: name, formula,
   remove, add; a refusal links to its row; a derived name appears among
   the measures to analyse. Strings in English and Arabic in the Datasets
   chunk, not the first load.

7. **Budget.** Measured after the change: first-load script 99.7 of 100
   KB, total script 255.1 KB, total style 34.1 of 35 KB. The strings live
   in the Datasets chunk and the section's handlers were factored once;
   the rest is the section itself. The total script ceiling moves to
   256 KB (`scripts/verify.py`, `tests/test_verify.py`); first-load
   ceilings do not move.

## Consequences

- `tests/test_mapping.py`: `DerivedColumnTests` (precedence, brackets,
  unary minus, backtick names, empty cells on missing values and zero
  divisors, the reasons a formula or a declaration is refused in both
  languages, a derived measure saved) and an API case on SQLite and
  PostgreSQL (the run computes the column, analyses it as the measure,
  records the claim; a refusal in Arabic names the row).
  `tests/test_joins.py`: a stacked table gets the main mapping's derived
  columns. `frontend/src/tests/mapping.test.tsx`: adding a derived column,
  choosing it as the measure, the body sent, a refusal linked to its row.
- Mappings saved before this decision have no `derived` key and read as
  having none.
- Not done: functions (round, abs, log), conditionals, text columns, and
  derived dimensions. Each needs its own decision and its own refusal
  wording.
