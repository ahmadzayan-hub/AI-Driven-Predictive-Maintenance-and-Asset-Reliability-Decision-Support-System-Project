# The sheet picker after a failed workbook upload

Date: 2026-10-30 · Status: Accepted (progress board *Next* item 3, the last
open part; builds on `2026-10-23-workbook-sheet-discovery.md` and
`2026-10-30-workbook-title-lines.md`).

## Context

The sheet picker appeared only after a successful upload, because it read the
sheet list from the upload's answer. When a workbook's default sheet could not
be read (no sheet looked like a table, or the one chosen held no data), the
upload failed and there was no list to show. The user saw the error and had no
way, inside the interface, to point the reader at another sheet. The server has
offered `POST /api/datasets/sheets` since 23 October, which describes every
sheet and stores nothing, but nothing in the interface called it.

## Decision

1. **After a failed upload of a workbook, the interface asks for its sheets.**
   `sheetsAfterFailure(file, language)` in
   `frontend/src/features/datasets/WorkbookSheetPicker.tsx` calls
   `api.listSheets`, which posts the same file to `/api/datasets/sheets`. Both
   upload screens use it: Datasets and Runs.
2. **The picker shows them, beside the error.** When the workbook has two or
   more sheets, the existing picker appears with each sheet's approximate size
   and the "not a table" note, in English and Arabic as before. Choosing a sheet
   uploads the same file again with that sheet, exactly as the picker already
   did after a successful upload. The error message stays on screen.
3. **Only for workbooks.** The call is made only when the file name ends in an
   Excel extension (`.xls…`), so a failed CSV or JSON upload sends nothing more.
   A listing that fails is ignored; the upload error already says what went
   wrong.
4. **No new string, component or style.** The picker, its labels and its help
   text are reused.

## Budget

The total script ceiling rises from 257 to **257.1 KB** (total only; first
load, largest chunk and styles unchanged). The change measured 257,076 bytes
against 257,000. Trimming was tried first, as the owner requires:
- no translation key is unused (the 56 keys not found literally are all built
  at run time, such as `state.${...}` and `grain.${...}`);
- the exported functions that nothing imports are already removed by the
  bundler, so deleting them saves nothing;
- sharing the upload request between the two endpoints and sharing the
  "file too large" message between the two screens did not reduce the
  compressed total (the second made it 6 bytes larger and was reverted).

First load is 99.6 of 100 KB; the new client call sits in the shared API
module.

## Consequences

- A workbook whose sheets are all covers, notes or titled tables beyond what
  the reader detects can still be uploaded, by choosing its sheet.
- A failed workbook upload sends the file a second time, to list its sheets.
  The file is at most 4 MB and the listing stores nothing.
- Board item 3 has no open interface part left; exercising a live source on a
  host with direct egress remains.

## Tests

`frontend/src/tests/intake.test.tsx`: a failed workbook upload lists the
sheets, shows the picker beside the error and retries with the chosen sheet;
a failed CSV upload does not ask for sheets. `frontend/src/tests/views.test.tsx`:
the same on the Datasets screen. `tests/test_verify.py`: the new ceiling, exact
to the byte.
