# Old .xls workbooks, read with xlrd

Date: 2026-11-06 · Status: Accepted · Owner decision: ".xls via xlrd only"

## Context

Every format was read by the project's own standard-library code, and `.xls` (Excel
97 to 2003, a binary OLE2 file) was refused with "save it as .xlsx". Maintenance systems
still export it. A hand-written BIFF8 parser would be large and security-sensitive.

## Decision

1. `xlrd==2.0.1` is a declared, hash-pinned dependency. It is pure Python, about 100 KB,
   and since 2.0 reads `.xls` only. It reads saved cell values: formulas are their stored
   results and no macro or code in the file runs.
2. A file named `.xls`, or starting with the OLE2 signature, is read by `_read_xls` into
   the same shape the `.xlsx` reader gives: numbers and dates as text (dates through the
   same serial conversion, including the 1904 date system), true/false as `TRUE`/`FALSE`,
   error cells left empty and counted, the first sheet that looks like a table chosen,
   title lines above the header left out, and the sheet picker listing every sheet.
3. A file that is not a readable workbook is refused (422) with the existing bilingual
   "not a workbook" message. Parquet stays unsupported: pyarrow is about 40 MB of compiled
   code and strains the serverless bundle; the upload help says to export it as CSV.

## Consequences

- Tests: a real Excel 97 workbook made by LibreOffice from synthetic rows (cover sheet,
  title line, dates, decimals, true/false, an error cell) reads as an `.xlsx` would; its
  sheets list and a missing sheet is refused; a fake `.xls` is refused in both languages.
- The interface accepts `.xls` and the upload help names it in English and Arabic.
- Live sources do not fetch `.xls` yet.
