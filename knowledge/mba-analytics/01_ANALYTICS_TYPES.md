# Analytics types and the question being answered — أنواع التحليلات

## Source-backed taxonomy

The introductory and strategy lectures distinguish four analytics types. Some older slides discuss only descriptive, predictive and prescriptive methods; diagnostic analysis appears explicitly in the broader four-type treatment. This is variation in presentation, not evidence that diagnosis is unnecessary. [S012](SOURCE_INDEX.md#s012), PDF p5; [S015](SOURCE_INDEX.md#s015), pp4–7; [S037](SOURCE_INDEX.md#s037), pp12–15.

| Type | Question | Source-supported purpose | Limit of the answer |
|---|---|---|---|
| Descriptive — وصفي | What happened? | Summarize historical observations and performance | A summary does not explain the cause |
| Diagnostic — تشخيصي | Why might it have happened? | Examine patterns and relationships behind a change | An observed relationship alone does not establish causation |
| Predictive — تنبؤي | What may happen next, or which outcome is likely? | Use historical patterns and models to estimate outcomes | Reliability depends on validation and the relevance of the data |
| Prescriptive — توجيهي | What action should be considered? | Evaluate actions against goals and constraints | A recommendation depends on its assumptions and feasibility |

The limitations above combine the taxonomy with the books' warnings about spurious relationships, overfitting and future uncertainty. [S003](SOURCE_INDEX.md#s003), pp29–40; [S006](SOURCE_INDEX.md#s006), pp14–15. They are not promises of accuracy for a particular project.

## Reporting, analysis and decision support

The managerial book distinguishes retrieving and presenting a report from using analytical methods to interpret information. Its method-selection dialogue starts by asking which of those deliveries is needed. It then asks whether the inquiry is hypothesis driven or data driven and whether there is a target variable or an exploratory structure to discover. [S007](SOURCE_INDEX.md#s007), pp141–149.

The course describes decision-support systems as computer assistance for complex decisions and emphasizes their connection to business goals, usable information and human expertise. [S019](SOURCE_INDEX.md#s019), pp3–7,16; [S036](SOURCE_INDEX.md#s036), p12. The final lecture places BI reporting alongside agentic exploration rather than treating one as proof that the other is correct. [S043](SOURCE_INDEX.md#s043), p5.

## Proposed Miyaar application

For an asset-reliability project, begin with a written decision question. Examples below are proposals, not observed results or confirmed fields in the Team 3 dataset:

- Descriptive: count documented failures by asset group and observation period, with a confirmed denominator.
- Diagnostic: compare downtime across operating conditions and investigate plausible explanations, retaining confounding and data-quality caveats.
- Predictive: estimate a defined future failure outcome only if event timing, labels, predictor availability and a credible evaluation set exist.
- Prescriptive: compare maintenance actions only when costs, safety constraints, resources and consequences are specified. A risk ranking alone is not an optimized maintenance schedule.

The sophistication of the method is not a completion criterion. A well-supported descriptive result is preferable to a predictive claim that cannot be evaluated. Record explicitly when the dataset does not support the desired predictive or prescriptive question.

## Learning methods are a separate classification

The AI lectures distinguish supervised learning with labels, unsupervised discovery such as clustering, and reinforcement learning. The more practical lecture asks the analyst to choose by the goal and available data. These categories describe learning setups; they are not synonyms for the four business-analytics types. [S014](SOURCE_INDEX.md#s014), p5; [S040](SOURCE_INDEX.md#s040), p13.

Course diagrams and cheat sheets provide introductory maps. Their sample-size thresholds and simple branching rules should not be converted into universal acceptance criteria. [S023](SOURCE_INDEX.md#s023), p1; [S024](SOURCE_INDEX.md#s024), whole image.
