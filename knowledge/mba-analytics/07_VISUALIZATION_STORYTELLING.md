# Visualization and consistent outputs — عرض النتائج

## Source-backed chart and reporting principles

The Power BI lecture recommends matching the visual to the question: bars for comparisons, lines for trends and tables for detail. It emphasizes position/length, restrained colour, clean formatting and avoiding unnecessary 3D or confusing dual axes. It also includes filtering and peer review. [S039](SOURCE_INDEX.md#s039), pp4,10–15.

The image references organize chart choice by comparison, relationship, distribution and composition. Some older suggestions include designs that conflict with the newer lecture's cautions. Use them as idea menus rather than compulsory designs. [S020](SOURCE_INDEX.md#s020), [S021](SOURCE_INDEX.md#s021), [S033](SOURCE_INDEX.md#s033), whole images.

The staged dashboard exercise links a small KPI set to a named audience and a decision. The final lecture asks for a clear action, confidence/caveats and impact measurement. [S041](SOURCE_INDEX.md#s041), pp13–15; [S043](SOURCE_INDEX.md#s043), p17. These support concise, evidence-linked communication.

## Proposed one-analysis, consistent-output contract

The desired workflow produces a report, presentation and dashboard from one accepted analysis, with an optional motion video. A separate requirements review supplied during curation identifies PDF, PPTX and PBIX as the required course deliverables; video is a separate optional extension. That requirements finding was reported by the independent review, not re-derived from attachments in this task. All four outputs should refer to the same approved metric definitions, calculation version and claim registry.

| Output | Purpose | Required evidence consistency |
|---|---|---|
| Report | Explain question, data, methods, findings, uncertainty and decision | Each numerical/causal/predictive claim has an evidence ID and appropriate caveat |
| Presentation | Tell the decision story and compare alternatives | Key figures and scope match the report; simplification does not remove material limitations |
| Dashboard | Explore approved metrics and filters | Filter context, denominators, units, update time and totals are visible and reproducible |
| Motion video | Communicate the accepted story over time | Script, narration, animation labels and on-screen numbers refer to the same claims and version |

Do not create a separate set of calculations inside each medium. Generate them from an approved result table or claim registry and reconcile displayed values. No report, slide deck, dashboard or video for Team 3 has been produced in this knowledge task.

## Proposed visual verification

For every important chart, record the source data, transformation, units, filters and analytical purpose. Check axis direction and range, missing categories, aggregation and whether colour conveys a documented meaning. A trend line is not a forecast unless a forecast method and evaluation support it. An animation must not imply causation or certainty absent from the analysis.

For forecasts, show the horizon, evaluation context and uncertainty when justified. For scenarios, label the assumed inputs and distinguish them from observations. For rankings, show the basis and sensitivity. Keep personally identifying rows out of screenshots, tooltips, narration and public-facing artifacts.

## Refresh and reproducibility

The lecture's sub-second live dashboard target is an exercise acceptance condition, not a measured property of Miyaar. The slide's individual watcher/fetch timings do not establish end-to-end performance. Any later freshness claim must be measured from a known source change to the updated displayed result, with retry/error behavior recorded. [S041](SOURCE_INDEX.md#s041), pp5,16–19; [S043](SOURCE_INDEX.md#s043), p14.

Use a fixed analysis snapshot for the comparison with the team. If a live dashboard updates, identify the new snapshot and avoid comparing it silently with an older report or video.
