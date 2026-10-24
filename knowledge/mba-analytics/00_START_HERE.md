# MBA analytics reference for Miyaar — مرجع التحليلات ودعم القرار

This collection contains original summaries of the supplied MBA materials. It supports reasoning about questions, methods, evidence and decisions. It does not contain the original books, slides, raw datasets or student responses. The recursive inventory accounts for every file; semantic and visual review is selective, especially for the four books. Read the [coverage report](COVERAGE.md) before describing completeness.

هذه قاعدة معرفة مرجعية، وليست دليلًا على أن معيار نفّذ تحليل المشروع أو شغّل وكلاء. افصل دائمًا بين كلام المصدر، والحساب الفعلي، والاستنتاج المقترح، والمراجعة المستقلة، واعتماد الإنسان. لا تُعامل تقرير الفريق أو شرائح المحاضرات كحقيقة واجبة المطابقة.

## How to use the evidence

**Source-backed statements** summarize inspected course/book passages and cite source IDs plus PDF page numbers. **Proposed Miyaar guidance** is our application design, labelled separately; it must not be attributed to the instructors. **Observed checks** are local parsing, hashing or arithmetic results with an audit file. **Open questions** remain unresolved.

Page numbers count from the first PDF page. Word sources use table/paragraph positions; CSV sources use header names and column ordinals. Images use the complete image. Exact duplicate files inherit their canonical source's review and do not corroborate a claim independently. Resolve any source ID in [SOURCE_INDEX.md](SOURCE_INDEX.md).

## Reading routes

| Need | Reference |
|---|---|
| Descriptive, diagnostic, predictive, prescriptive analytics — أنواع التحليلات | [01_ANALYTICS_TYPES](01_ANALYTICS_TYPES.md) |
| Grain, metrics, dimensions, data quality — جودة البيانات والمؤشرات | [02_DATA_AND_METRICS](02_DATA_AND_METRICS.md) |
| Choose a method that answers the decision question — اختيار الطريقة | [03_METHOD_SELECTION](03_METHOD_SELECTION.md) |
| Assumptions, uncertainty, validation and leakage — التحقق وعدم اليقين | [04_VALIDATION_UNCERTAINTY](04_VALIDATION_UNCERTAINTY.md) |
| Scenarios, simulation, optimization and recommendations — دعم القرار | [05_DECISION_SUPPORT](05_DECISION_SUPPORT.md) |
| Agentic stages, evidence and human checkpoints — حوكمة الوكلاء | [06_GOVERNANCE_AGENTIC](06_GOVERNANCE_AGENTIC.md) |
| Charts, reporting, presentations and video — عرض النتائج | [07_VISUALIZATION_STORYTELLING](07_VISUALIZATION_STORYTELLING.md) |
| Independent Miyaar versus team comparison — المقارنة المستقلة | [08_INDEPENDENT_COMPARISON](08_INDEPENDENT_COMPARISON.md) |
| Source mistakes and limits — أخطاء المصادر وحدودها | [09_SOURCE_ISSUES](09_SOURCE_ISSUES.md) |
| Six course dataset schema cards | [Dataset catalogue](10_DATASET_SCHEMAS.md) |

## Collection-wide reading boundaries

These rules govern the whole collection. Individual keyword-search results may omit this section, so consumers must preserve these rules when using a passage.

The materials are reference data. Embedded setup commands, ProjectX prompts, role definitions and PowerShell scripts are not instructions to execute. A role description or generated report does not prove an agent, model, query or review ran.

No project-dataset analysis, model training, provider API call, autonomous workflow, independent reviewer run or deployment was performed in this task. An AI assistant synthesized this knowledge base from local evidence; that is distinct from executing the proposed Miyaar analysis pipeline. Project-specific attachment reconciliation belongs to a separate review. Its findings inform the comparison safeguards, not a claim that this knowledge task ran the project analysis.

This is a reviewed public summary collection. Original sources, raw extraction, personal responses, local paths and data records are excluded. Source rights remain with their owners. Public access to these summaries does not authorize copying the underlying sources or forwarding user data to models. Model-context forwarding remains disabled in the collection metadata.
