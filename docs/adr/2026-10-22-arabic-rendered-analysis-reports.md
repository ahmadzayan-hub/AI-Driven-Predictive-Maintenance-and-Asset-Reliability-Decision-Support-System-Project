# Arabic analysis content and rendered house-style reports

Date: 2026-10-22

Status: accepted for implementation by the owner.

## Context

The owner requested Arabic analysis and recommendations inside the platform,
including table contents and charts, and rendered writing in the house style.
Switching the interface language did not translate an existing English run;
report Markdown was displayed in a preformatted block. Arabic calculation
tables also retained English descriptions from the audit record.

## Decision

- Expose report language separately at analysis creation, initially following
  the interface language. Keep it fixed for that run, as in ADR 0022. Explain
  a report/interface language mismatch. Previously approved artifacts and their
  hashes are never translated or rewritten in place.
- Render the generated Markdown dialect as semantic headings, paragraphs,
  lists, quotations and tables in section, comprehensive and approval previews.
  Keep source content intact; HTML, images and links remain inert text. Bound
  parsing work and preserve unsupported/oversized content as readable text.
  Add no parser dependency. Tables scroll locally, expose captions and column
  headers, and isolate numeric cells for right-to-left reading.
- Provide deterministic Arabic display descriptions for built-in calculations
  and report checks. Keep the original calculation names, methods, identifiers,
  values and English claim records unchanged for validation. Unknown/custom
  metadata is disclosed as original text rather than guessed. Technical evidence
  identifiers, user filenames and user-supplied column/category names remain
  traceable source text; they are not silently translated.
- New Arabic demo runs use an Arabic-labelled version of the bundled fictional
  sales sample, including columns, regions and categories. Every date and numeric
  cell matches the English sample. Recognize Arabic date-column names in the
  existing unmapped-data heuristic. Existing stored datasets and customer inputs
  are unchanged. The Arabic demo is a new analysis with its own approval gate.
- Scope the house style to analysis output: red title bars, navy leading edges,
  readable tables, light/dark palettes and logical RTL spacing. Generate its
  CSS variables from the existing house-style tokens.json. Use its IBM Plex
  family with system fallbacks; no font files are newly bundled. Carry no
  authority logo, name, endorsement or identity.

## Loading allocation

The first integrated build measured 210.4 KB total JavaScript and 29.6 KB total
CSS (gzip), exceeding the prior 210/29 KB totals. The bounded semantic renderer,
bilingual report-language control and generated scoped styles add this capacity
without a library. Allocate 212 KB total scripts and 30.5 KB total CSS. Keep
the first-load, largest lazy chunk and font limits unchanged. This records the
feature tradeoff; it does not claim the old allocation passed or establish a
network-performance score.

## Validation

Check Arabic sample numeric/forecast/scenario parity; Arabic report display
coverage and unchanged calculation evidence; renderer preservation and inert
untrusted markup; explicit opposite-interface report-language selection; real
Arabic pipeline headings, tables, charts, approval preview and English-language
immutability. Check the rendered output on narrow screens and in both themes,
then run the repository verifier. Actual results live in README.md#testing.

## Consequences

The language selector affects new reports. An old English report needs a new
analysis to produce Arabic content, not a relabelled English artifact. Original
metadata from external plugins or customer data can still contain another
language. No production deployment or publication approval is implied by viewing
the rendered report.
