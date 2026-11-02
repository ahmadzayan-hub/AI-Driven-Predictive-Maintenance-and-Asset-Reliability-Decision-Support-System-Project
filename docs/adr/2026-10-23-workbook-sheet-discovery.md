# Workbook sheet discovery before parsing

Date: 2026-10-23 · Status: Accepted (progress board *Next* item 3, second
half; extends ADR 0024 and ADR 0038).

## Context

An upload with no `sheet` read the first visible sheet. Many real workbooks
open with a cover sheet: a title merged across the page, a logo, notes and
no header row. That sheet either failed to parse ("a header row but no data
rows") or was stored as a meaningless one-column table, and the sheet picker
only appeared after a successful upload, so the user could not reach the
data sheet from the interface at all.

## Decision

1. **Every sheet is described from a sample before any sheet is parsed.**
   `server.datasets.list_sheets(body)` opens the workbook as `read` does and,
   for each sheet, reads at most its first 20 non-blank rows (`SAMPLE_ROWS`),
   then stops. Each sheet is reported with its `name`, `hidden`, approximate
   `rows` and `columns`, `tabular` and `unreadable`.
   - The size comes from the sheet's declared `<dimension>` when it has one,
     which Excel and openpyxl write. It is approximate: formatting can widen
     it. Without a dimension, the sampled size is reported when the whole
     sheet fitted in the sample, and `null` otherwise, never a guess.
   - `tabular` means the first non-blank row has at least two distinct,
     non-empty names, not all numbers, filling at least half of its span,
     and a later sampled row has at least two values. A cover sheet has no
     such row. A one-column table is not called tabular; it is still read
     when nothing else looks like a table (point 2).
   - A sheet that cannot be read (a cell past column 500, a document type
     declaration, broken XML) is listed with `unreadable: true` instead of
     failing the listing.
2. **The default sheet is the first visible sheet that looks like a table,**
   then the first visible sheet, as before. A workbook whose first visible
   sheet is a cover therefore uploads, and the warning says which sheet was
   read: "Read the sheet "X", the first of N that looks like a table." When
   the first visible sheet is chosen, the earlier wording is kept. A named
   `sheet` is read exactly as before.
3. **The API returns the descriptions.** `POST /api/datasets` adds
   `sheet_details` beside the existing `sheets` names. The new
   `POST /api/datasets/sheets?name=` takes the same body and the `write`
   scope, stores nothing, and returns `{"sheets": [...], "default_sheet"}`;
   a file that is not a workbook returns no sheets.
4. **The picker shows them.** Each option shows the approximate size and,
   for a sheet that does not look like a table, "not a table" (Arabic:
   "ليست جدولًا"). No new component, style or test file; the interface
   budget is unchanged.

## Safety

The limits are unchanged and shared: the sample is read through the same
XML byte budget as the parse (`MAX_XML_BYTES` across every part, now
raised as a subclass so a per-sheet failure can never swallow it), the same
document type refusal, the same relationship-only part resolution and the
same 4 MB upload limit. Sampling stops after 20 rows, so describing a sheet
costs at most a few 64 KB reads.

## Consequences

- A cover-first workbook needs no rework before upload.
- Each upload samples every sheet once; for a workbook with many sheets this
  adds a bounded amount of reading.
- The heuristic can be wrong both ways. A table whose header starts below a
  title row is not tabular, because the reader still takes the first
  non-blank row as the header; header-row detection inside a sheet is not
  part of this decision. Amended 2026-10-30: up to five single-value title
  lines above a header are now passed over
  (`2026-10-30-workbook-title-lines.md`).

## Tests

`tests/test_datasets.py`: listing without any sheet parsing, the declared
dimension, the cover-first default and its bilingual warning, an
unreadably wide cover, the fallback to the first visible sheet, the budget
and document type refusals during discovery, and the API (`sheet_details`,
the discovery endpoint storing nothing, a CSV with no sheets).
`frontend/src/tests/intake.test.tsx`: the picker labels.
