# Synthetic stress datasets and the gaps they found

Date: 2026-11-05 · Status: Accepted · Owner request: "generate synthetic data sets to test beyond your capabilities and test all features and identify gaps"

## Context

The platform had been tested on a few synthetic files and one real survey. The owner
asked for datasets that push past what it was built for, every feature exercised, and
the gaps named.

## Decision

1. **A repeatable harness.** `scripts/stress_datasets.py` builds 23 seeded datasets
   (condition surveys on three scales and in words, maintenance up to 50,000 rows and
   with planted defects, Arabic headers and values, mixed date formats, formatted and
   decimal-comma numbers, formula and prompt injection, 300 columns, 5,000 distinct tags,
   all-text, one row, repeated headers, not-applicable markers, outliers, sensor
   timestamps, costs, contracts, a workbook with a cover sheet) and a feature sweep
   (KPIs against the register, query and records, exports in three formats and two
   languages, reviews, saved views, layout history and conflicts, Ask Miyaar in English
   and Arabic, knowledge search, approval and publication, pause, resume and cancel,
   video, dataset deletion). Each check states what a careful analyst expects.
   Results: `docs/STRESS_TEST_RESULTS.md`.
2. **Fixes** for the nine defects listed there, the most serious being clean files
   rejected because claims quoted uncited figures, and a decimal comma read as a
   number a hundred times too large.
3. **Claims may declare labels.** A period or group quoted in a claim's text is listed
   in `labels`, and the figures check reads past it. Without this, "2025" or "2069"
   in a sentence counted as an uncited figure.
4. **A test that passed for the wrong reason is corrected**, not kept: the planted
   defects are findings for a reviewer, and the run reaches the approval gate.

## Consequences

- Final run: 24 datasets, 87 of 91 checks pass. Four gaps stay open and are recorded
  in `docs/KNOWN_LIMITATIONS.md`.
- Unmapped files now read currency, percent and Arabic digits as numbers, and refuse
  comma-decimal values instead of misreading them.
- The harness is not part of verify (it takes about a minute); run it before a release.

## Addendum, the four open gaps (same day)

5. **Direction is declared, not guessed.** `mapping.better = {measure: "higher" | "lower"}`,
   validated against the measures, shown in the mapping panel beside the allowed range,
   and passed to the layout planner so a 1-is-best grade ranks its highest values as the
   weakest.
6. **Decimal mark is declared, and suggested.** `mapping.decimal = "comma"` makes every
   mapped read of the file use `parse_number(value, "comma")`. `suggest` proposes it only
   when a column reads that way and at least one value is unambiguous (not three digits
   after the comma). The CSV separator check now prefers the separator that splits the
   header the same way as the rows, which fixed a semicolon file split on its commas.
7. **Ask Miyaar groups digits** with `,.12g`: same precision, readable thousands.
8. **Knowledge without a model.** When no model is configured and a question has a strong
   public match (two or more subject words, at least half of them, and one named term: a code
   such as P75 or G02, an identifier such as Failure_Probability, or a word written in capitals),
   the rules route it to the cited knowledge search; the reader's own access still decides what
   is quoted. Conversation words never count, and a general question ("What is preventive
   maintenance?") still gets the honest no-model reply.

Final run: 24 datasets, 95 of 95 checks pass.
