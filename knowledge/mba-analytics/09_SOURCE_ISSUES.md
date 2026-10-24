# Source issues and limitations — ملاحظات على المصادر

## Verified arithmetic and layout errors

| ID | Source / locator | Observed problem | Handling |
|---|---|---|---|
| E01 | S003 PDF pp30–32, printed pp13–15 | Pearson example prints −0.389; recomputation from four printed pairs gives approximately −0.987135. Total-row placement is also wrong | Local audit retains the calculation; this public summary records the correction, with no significance test claimed |
| E02 | S003 PDF pp72–73, printed pp55–56 | Candidate x=400,y=250 uses 3,400 hours against a stated 1,700-hour limit; graph intercepts conflict with its label | Candidate rejected as infeasible; no invented “corrected source” or optimizer execution |

Both issues were checked against rendered pages, not inferred from extraction alone. The full local audit is not republished. See [validation](04_VALIDATION_UNCERTAINTY.md) and [decision support](05_DECISION_SUPPORT.md).

## Statistical wording requiring caution

S003 p29 uses a magnitude-only correlation significance shortcut. S005 p158 and S007 pp155–156 use simplified significance/confidence explanations. S007 p145 makes an overly broad distinction about reproducibility of data mining versus hypothesis-driven analysis. Do not treat these passages as a formal statistical specification or use them to generate p-values, confidence claims or universal rules.

S006 pp14–15 provides useful warnings about data quality, bias and framing, but its broad philosophical claims about objectivity or whether data science is a “proper science” are author viewpoints, not methodological acceptance criteria. Several sources use “explain” or “determine” when discussing observed relationships; retain the explicit caution that association alone does not establish causation.

## Illustrations are not project evidence

Newer slides include benefit percentages and monetary outcomes without sufficient supporting study details: for example S035 p29, S037 p24 and S038 p20. Older lectures contain presenter prompts and generic company cases. S042 p8 is a forecast/overstock exercise scenario; S043 p15 contains example margin values. None are evidence about the supplied Team 3 dataset or Miyaar's impact.

Do not repeat historical product, market-share or vendor-ranking claims as current facts. S032 is a January 2023 Gartner graphic. S084–S085 are 2026-labelled MLOps graphics with unverified provenance; S084 contains mismatched tool descriptions and inconsistent training-effort percentages. They were visually inspected, not externally fact-checked.

## Version and terminology conflicts

- The syllabus lists Phillips with a 2017 date ([S010](SOURCE_INDEX.md#s010), p5), while the supplied book's copyright page says 2014. The source index records the file's evidence without silently changing the syllabus.
- The older syllabus has an eleven-lecture structure; the newer final lecture presents a nine-lecture arc. These are separate source versions.
- S042 changes scenario names; S043's two-day heading lists three days. Do not use these details as a project schedule without clarification.
- S005 pp167–168 alternates “duplicated” and “deduplicated” in its cookie example. Preserve the business/operational/technical definition framework, not the ambiguous example wording.
- Older chart suggestions include 3D forms that conflict with newer visualization guidance. The newer chart-selection cautions are used in the proposed workflow.
- File names alone are not version evidence. S001 and S018 have similar sector titles but different page counts and content; they remain separate. Hash-identical duplicates are explicitly mapped in the manifest.

## Extraction and review limits

All 23 unique PDFs yielded page-indexed text for 1,555 pages. Thirty-eight pages contain fewer than 80 text characters; they may be covers, blank pages or image-heavy pages. Sparse text does not establish unreadability, and abundant text does not prove that every diagram was captured. Seven PDF pages were visually checked for the key formula, worked examples, method diagram and algorithm table. Fifteen unique standalone images were visually reviewed.

The conservative evidence ledger covers selected passages on 351 PDF pages. It is not an exhaustive semantic review of all 1,555 pages. Full-page/book review and validation of every embedded diagram or equation remain incomplete. No OCR was run or required for the passages used here. Any later claim based on an unreviewed image-only page needs bounded visual inspection first; a bulk OCR resource estimate cannot be justified without identifying that page set.

Four sources were restricted for privacy: the completed student profile and three identity/persona files. Their contents are excluded from synthesis. The blank questionnaire is administrative context. ProjectX scripts and prompts were read as untrusted artifacts and never executed.

See [COVERAGE.md](COVERAGE.md) for review scope and excluded source material.
