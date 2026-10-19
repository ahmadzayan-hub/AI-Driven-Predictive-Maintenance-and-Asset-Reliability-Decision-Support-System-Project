# 0059 - Executive business document exports

Date: 2026-10-19

## Context

The owner requested business files instead of `miyaar-executive-*.json`.
ADR 0058's JSON handoff preserved evidence but required a technical reader.
The product already computes an authorized, filtered executive brief; its
measure populations, limitations and whole-run evaluation scope must survive
the change in file format.

## Decision

- Replace the executive JSON download with standalone HTML by default and a
  genuine editable Word `.docx` option. Add a separately labelled
  **Print / Save as PDF** action using the browser's native print dialog.
  This is a printable report and a user-selected PDF destination, not a
  claim that the server has a PDF conversion service.
- Add an authenticated read-only executive export endpoint. It rebuilds the
  report from the authorized run and validated dashboard filters, not from
  browser-submitted claims. Require the prepared brief's stored
  `run.updated_at` and a deterministic SHA-256 revision of the complete brief;
  reject a changed snapshot with 409 and a refresh message. A task may finish
  between run-state updates, so the timestamp alone is not a sufficient guard.
  Export neither advances nor approves nor publishes a run.
- Use a common report structure for HTML and Word: run and source metadata,
  period/filter scope and record counts, executive summary, limitations,
  controlled KPI definitions and coverage, review priorities/questions,
  whole-run findings/model evidence and a calculation-reference appendix.
  Do not include source rows, credentials, speculative scores or JSON dumps.
- Keep English and Arabic RTL labels and document direction. Use readable
  business typography, black headings, deliberate table widths, repeating
  table headers, visible cell borders and print/page-break rules. Preserve
  source units, missing readings and model verdicts.
  The report opens with a compact KPI summary before its detailed audits.
  Arabic Word paragraphs use logical leading-edge (`start`) alignment with
  BiDi text; hardcoded `right` renders at the trailing edge in LibreOffice.
- Generate escaped HTML and Office Open XML with Python's standard library.
  Word is a real ZIP package with document/styles/relationships, not HTML
  renamed `.doc`. No scripts, macros, external relationships or network/file
  fetching are needed to generate either document. HTML is self-contained
  and carries a restrictive content policy.
- Use authenticated binary downloads with MIME checks, bounded requests and
  cancellation. Scope/language/run changes remove the prepared report and
  abort or discard obsolete downloads. Handle failed/stale requests and
  blocked print windows without creating a misleading file.
- Do not add a browser or Office dependency to the deployed server. Native
  print supports the user's installed fonts; final Arabic pagination still
  needs visual review. Word/HTML/PDF QA tools used locally are not runtime
  requirements for HTML or Word export.

## Verification and consequences

Renderer/API checks cover real file structures, escaped hostile content,
Arabic direction, exact measures/populations/evidence, ownership/readiness,
snapshot rejection and unchanged approvals. UI/browser checks cover format
selection, correct authenticated downloads, recoverable failures, cancellation
and print-preview behavior. Generated Arabic/English HTML/PDF and Word page
renders are inspected visually using fictional verification data.

The recipient receives a business report rather than a machine payload.
The export remains decision support, and filtering still does not retrain
models or approve maintenance. Actual results are maintained in
`README.md#testing`. This supersedes only ADR 0058's executive file format;
its evidence, scope and authority boundaries remain in force.

## References

- [MDN: Window.print](https://developer.mozilla.org/en-US/docs/Web/API/Window/print)
- [MDN: Window.open](https://developer.mozilla.org/en-US/docs/Web/API/Window/open)
- [Microsoft: Word right-to-left text](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.righttolefttext?view=openxml-3.0.1)
- [Microsoft: paragraph BiDi layout](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.bidi?view=openxml-3.0.1)
