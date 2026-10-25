# Navigable business reports with a bounded executive summary

The owner requested reusable report typography and navigation improvements after
reviewing a reference PDF. The reference is a design example, not numerical or
methodological authority. Its reported missing links are independent of font
embedding; Miyaar already includes the verified, unmodified Dubai font resource.

## Decision

- Contents follow actual evidence: summary, decision questions and scope, source
  and governance coverage, definitions and measured KPIs, saved findings and model
  evidence, review proposals, limitations and evidence appendix. Numbered section
  headings match the index. Empty decorative headings are omitted; unavailable
  methods remain explicit status statements, never invented completed analyses.
- The executive summary is unnumbered; the next body section starts at 1. The
  contents begins with Lists of Tables and Figures, followed by the summary and
  actual body sections. Table captions and their index share one catalog; empty
  tables are not advertised. This renderer contains evidence tables, not figure
  objects, so the figure list explicitly states that no figures are included.
  Word page-reference fields resolve against caption/section bookmarks. HTML and
  browser PDF retain destinations, not guessed printed page references; page
  footers reflect actual pagination. Printed contents page numbers in arbitrary
  browser PDF output are not supported by the current engine.
- Executive HTML and DOCX retain a concise front-page executive summary. Bounded
  preview prose points to full scope, proposals and limitations below; facts and
  evidence tables are retained without recalculation. No fixed-height clipping or
  small-font overflow workaround is used.
- HTML uses one shared renderer for executive and RMD evidence exports, embedded
  Dubai typography, internal section destinations, a contents index without a
  self-entry, semantic headings, repeat table headers, whole-row pagination and
  print page counters. The existing font notice and hash gate remain unchanged.
- Word includes internal bookmarks, linked contents, dirty PAGEREF fields and
  update-on-open settings. It uses the Office pagination engine for page numbers;
  the generator never invents cached page references. PAGE fields supply footers.
- The existing Print / Save as PDF workflow is retained. Chromium print QA can
  produce real PDF links, embedded fonts and an outline from semantic headings.
  Native browser print dialogs vary: PDF outline retention is not guaranteed in
  every viewer. There is no native PDF export API and no new runtime dependency.
- CSV, JSON and stored Markdown remain data/text outputs; typography, bookmarks
  and printed pagination do not apply to those formats. Their source values and
  access boundaries are unchanged. Existing in-app report rendering is retained.
- The owner's subsequent interface request moves the existing export controls to
  the beginning of a prepared brief, keeps cancellation/errors beside them, and
  gives source selectors full available width, inherited Dubai typography and
  larger touch targets. Long source names wrap without changing selection or
  persistence. Existing design tokens, model-status disclosures and page
  architecture remain intact; no government affiliation is implied.
- Word package structure can be verified without Office, but native Word field
  refresh, visual pagination and Arabic layout require an Office renderer. Do not
  claim those passed from XML checks. Unsupported cached page numbers show a dash
  until the reader updates fields; section links still use real bookmarks.

## Verification and limits

Regression checks cover HTML link destinations, duplicate/self-index prevention,
Word bookmarks and page fields, escape rules, RTL/math direction, source values,
font integrity, row pagination settings, snapshot freshness and owner checks.
Browser QA checks actual anchor clicks, embedded fonts, table overflow, summary
page boundaries and generated PDF links/outlines in both languages. Local private
report samples and test logs stay outside Git. Exact executed counts are in README.
The full hosted suite and native Office rendering are separate acceptance limits.

The existing guarded local profile, data storage, Qwen settings and bundle ceilings
are unchanged. Local activation is authorized only after candidate checks and a
source/config/data rollback snapshot; remote publication is a separate decision.

## Primary format references

- [Microsoft updateFields semantics](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.updatefieldsonopen)
- [Playwright browser PDF options](https://playwright.dev/docs/api/class-page#page-pdf)
- [Existing font permission record](../../server/assets/fonts/DUBAI-FONT-NOTICE.md)
