# OpenDocument spreadsheets (.ods)

Date: 2026-10-30 · Status: Accepted (gap analysis, *Ingestion* row; extends
ADR 0024 and the workbook decisions of 23 and 30 October).

## Context

The dataset reader took CSV, TSV, Excel (`.xlsx`), JSON and JSON Lines. An
OpenDocument spreadsheet, LibreOffice's default format and common in public
bodies, was refused as "not a format the workspace reads", so the user had to
convert it first. The gap analysis listed OpenDocument as missing.

## Decision

1. **`.ods` is read as a workbook.** `server/datasets.py` reads the file's
   `content.xml`, where every sheet lives, into the same canonical table as an
   Excel workbook. The stored format is `ods`.
   - Typed cells are written as a workbook's are: numbers, percentages and
     currency as their value; dates as `2025-01-15`, or with their clock time
     as `2025-02-01 09:30:00`; times as `18:30:00`; booleans as `TRUE` and
     `FALSE`. Text cells keep their paragraphs (joined by a line break), runs
     of spaces and tabs.
   - Cell comments (`office:annotation`) are not part of the value.
2. **LibreOffice's unused grid is never expanded.** It writes the rest of a
   sheet as repeated empty cells and rows (16,384 columns, a million rows).
   An empty repeat only moves the position. A value repeated across cells is
   copied; a value past column 500 is refused, as in a workbook; a repeated
   row is copied only until the row limit is exceeded, so the table refuses it
   with the usual message.
3. **Sheets behave as in a workbook.** The same choice (the named sheet, then
   the first that looks like a table), the same warnings, title lines left out,
   and `POST /api/datasets/sheets` lists an `.ods` file's sheets, so the
   picker after a failed upload works for it too. Hidden sheets are not
   detected: OpenDocument hides a sheet through its style, which is not read.
4. **Detection.** By the `.ods` name, or, without a known name, by the
   OpenDocument type the archive names in its first entry. Live sources accept
   `ods` as a format.
5. **The interface.** The file picker accepts `.ods`, and the dataset list
   shows the format as `ODS`. The upload help text is unchanged (see
   Consequences).

## Safety

The same limits and defences as a workbook: the 4 MB upload limit, the
200 MB XML budget across the part, the document type refusal (no entity
expansion), the 500-column and 50,000-row limits. Only `content.xml` is read.

## Consequences

- An `.ods` export uploads without converting it first.
- The interface's upload help still lists "CSV, TSV, Excel (.xlsx), JSON or
  JSON Lines". Adding OpenDocument to that sentence in both languages would put
  the script total over its 257.1 KB ceiling; the server's own refusal message
  names `.ods`. To be updated when string space is freed.
- Old binary `.xls` and Parquet remain unread.

## Tests

`tests/test_datasets.py`, `OdsTests`: typed values in both languages' text;
the unused grid not expanded; repeated values and gaps; paragraphs, spaces and
notes; the column and row limits; sheet listing, default choice, title lines,
named and missing sheets; detection by name and by bytes; a document type,
broken XML and a missing `content.xml` refused. `DatasetApiTestCase`: an
`.ods` file listed and stored as `ods`, on SQLite and PostgreSQL.
`tests/ods_builder.py` writes the files as LibreOffice does.
