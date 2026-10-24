# Reviewed MBA analytics reference for Miyaar

Original source-grounded summaries for analytics and decision-support reasoning, with explicit partial coverage. Start at [the knowledge map](00_START_HERE.md), [method selection](03_METHOD_SELECTION.md) or [independent comparison](08_INDEPENDENT_COMPARISON.md). See the [bibliography](SOURCE_INDEX.md) and [coverage](COVERAGE.md).

هذه مراجع معرفية موثقة، وليست دليلًا على تشغيل وكيل أو نموذج أو تنفيذ تحليل المشروع. افصل بين الحسابات الفعلية، واستدلال النموذج، والمراجعة المستقلة، واعتماد الإنسان. التغطية الدلالية جزئية، ولا تتضمن الحزمة سجلات البيانات أو المصادر الأصلية.

## Retrieval and execution boundary

This collection uses the existing Markdown loader and deterministic keyword scorer in `server/knowledge.py`. Default source lookup includes the repository's reviewed `knowledge/` collections alongside operator-managed private collections. An explicit root or `AGENTIC_OS_KNOWLEDGE_DIR` remains an exclusive override. Public bundled collection IDs take precedence over conflicting private IDs; unique private collections keep their existing access rules.

The collection is public reference text with `model_context_allowed: false`. Ordinary authorized source lookup can quote it; model-bound lookup must still exclude it. Publication does not authorize forwarding user data or source documents to any model. The curated brain is linked separately and is not automatically indexed.

Adding a reference does not mean a specialist invoked it, a model ran, or an analysis was validated. Actual use requires run evidence and citations. No production activation or deployment is part of this change.

## Rights and privacy

Only original summaries, methodological guidance and safe schema examples are included. Underlying books, course slides, images, datasets and private audit reports remain outside this collection. Authors/publishers retain rights in their sources; the bibliography is attribution, not a republication license. The small source-error descriptions identify checked inconsistencies without republishing the source pages or tables.
