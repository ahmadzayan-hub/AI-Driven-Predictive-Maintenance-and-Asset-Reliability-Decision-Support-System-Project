# RMD V2 MBA 9227 project knowledge

Public departmental copy of the owner's MBA 9227 handover (course "AI for Business Strategy and Decision Making", AASTMT). Split by section; each section carries a `kb:` directive giving its domain, evidence status and limits, which retrieval returns with every quote.

**Academic cases only.** The G02 e-commerce parcel case, its P75 benchmarks and its warning rule are course material. None of it is an RMD operational rule, threshold or KPI. Domains starting `mba.9227.` are academic; `rmd.proposed` and `rmd.product` are proposals and dated requirements, not current functionality.

**Correction history is kept.** Superseded values (for example the provisional P75 values 8, 12 and 10) stay in the pack with `status=superseded`. A normal question never returns them; a question about corrections, provisional or outdated values does.

**What is withheld.** The owner profile and identifiers (section 02) are in the git-ignored private copy only. The public copy holds the working name, not the legal name, and no links into private file libraries. `scripts/build_knowledge_packs.py` fails the build if any such string survives.

**Model use.** `model_context_allowed` is false. Reading these passages in the knowledge view or in Ask Miyaar quotes is allowed; forwarding them to a model needs the owner's explicit decision.

Rebuild: `python scripts/build_knowledge_packs.py --mba <file> --analytics <file>`. Acceptance results: [RMD_KNOWLEDGE_ACCEPTANCE.md](../../docs/RMD_KNOWLEDGE_ACCEPTANCE.md). Decision: [ADR 2026-11-04](../../docs/adr/2026-11-04-evidence-aware-knowledge.md).

هذه نسخة عامة من ملف معرفة مقرر 9227. حالات المقرر أكاديمية فقط وليست قواعد تشغيلية في RMD. القيم المستبدلة محفوظة بحالة «superseded» ولا تظهر في الإجابات الحالية.
