# Title lines above a workbook's header

Date: 2026-10-30 · Status: Accepted (progress board *Next* item 3; amends
`2026-10-23-workbook-sheet-discovery.md`, which left header detection inside
a sheet out of scope).

## Context

Reports exported from maintenance and finance systems often open with a few
lines before the table: the report's name, a "generated on" date, the site.
The workbook reader took the first non-blank row as the header. For such a
sheet that gave a dataset whose only column name was the report title, with
the real header read as the first data row. The sheet listing also called the
sheet "not a table", so a workbook with a cover sheet followed by a titled
table defaulted to the wrong sheet or refused the upload.

## Decision

1. **Title lines are passed over only in a narrow case.** In
   `server/datasets.py`, `_header_start(rows)` returns how many title lines
   sit above the header among the non-blank rows:
   - 0 when the first non-blank row already looks like a header (the rule in
     `_looks_tabular`, unchanged). Every table that read correctly before reads
     the same way now.
   - Otherwise, up to `MAX_TITLE_ROWS` (5) lines are passed over, each holding
     at most one value, and only when the row after them looks like a header
     with data below it.
   - Anything else is 0: a line with two values is never skipped (it may be a
     header or data), six or more single-value lines are not a title block,
     and a one-column table is unchanged.
2. **Nothing is dropped silently.** When lines are passed over, the upload
   carries a warning in both languages: "Left out 2 title lines above the
   header row." / "استُبعدت أسطر العنوان فوق صف عناوين الأعمدة، وعددها 2."
3. **The listing agrees with the reader.** `list_sheets` judges `tabular` on
   the rows from the detected header, so a titled table counts as a table and
   can be the default sheet after a cover.
4. **Scope: workbooks only.** CSV, TSV and JSON reading is unchanged.

## Safety

No limit changes. Detection works on the rows already read, within the same
XML byte budget, the same 20-row sample for the listing and the same row and
column limits. The title lines are left out of the dataset, not stored
elsewhere, and their text does not appear in the warning.

## Consequences

- A titled export uploads without editing in Excel.
- The listing now skips blank rows before judging a sheet, as the reader
  already did. A sheet that opens with an empty, formatted row therefore
  counts as a table where it did not before, and can become the default
  sheet. That brings the listing into line with what the reader stores.
- The rule can still miss: a title block of more than five lines, or title
  lines that hold two values each (a label and a date in separate cells),
  are read as before. The sheet picker remains the way out.
- Still open from board item 3: the picker does not call
  `/api/datasets/sheets` when no sheet looks tabular.

## Tests

`tests/test_datasets.py`, `XlsxTests`: two title lines and a blank line left
out with the warning in both languages, and the sheet listed as a table; the
singular wording; a titled table after a cover chosen as the default sheet;
and the limits (a two-value line kept, six lines not passed over, a
one-column table unchanged).
