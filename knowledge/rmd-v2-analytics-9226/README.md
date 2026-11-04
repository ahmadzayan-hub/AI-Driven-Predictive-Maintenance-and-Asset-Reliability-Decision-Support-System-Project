# RMD V2 data analytics project knowledge

Public departmental copy of the owner's Group 9226 analytics handover. Each section carries a `kb:` directive (domain, evidence status, synthetic flag, limits).

**Synthetic and educational.** The 5,000 row, 60 column dataset is generated for teaching. Its scores, including `Failure_Probability`, are not validated predictions of future failure, and nothing here is actual RTA or RMD operational performance. Every passage drawn from it carries `synthetic=true` and the limits `synthetic_educational_data`, `not_validated_prediction`, `not_operational_rmd`.

**History is not verification.** Project status from earlier conversations (section 10) is labelled `HISTORICAL` with the limit `historical_not_current_verification`. Repository, CI and deployment state must be checked afresh.

**Data-quality limits stay attached.** Unstable asset identities, duplicate Asset_ID and date pairs, and rows where operating plus downtime exceeds planned hours are in the findings sections and are returned with the figures that depend on them.

**Figures.** Aggregates are reconciled to the source workbook by `tests/test_rmd_knowledge_reconciliation.py` (skipped unless the file with the documented SHA-256 is present). Live numerical answers must come from the deterministic KPI engine, not from these quoted figures.

**Model use.** `model_context_allowed` is false.

Rebuild: `python scripts/build_knowledge_packs.py --mba <file> --analytics <file>`. Acceptance results: [RMD_KNOWLEDGE_ACCEPTANCE.md](../../docs/RMD_KNOWLEDGE_ACCEPTANCE.md).

هذه نسخة عامة من ملف معرفة مشروع تحليلات البيانات (المجموعة 9226). البيانات اصطناعية وتعليمية، ودرجاتها ليست تنبؤات مُتحقَّقاً منها بالأعطال، والحالة التاريخية ليست تحققاً حالياً.
