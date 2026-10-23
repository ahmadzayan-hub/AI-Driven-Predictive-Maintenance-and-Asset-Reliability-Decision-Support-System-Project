"""Live authorized reference answers and an allowlisted aggregate narrator.

Answers are ephemeral: no private excerpts enter ordinary chat, saved memory,
runtime tool results or model context.
"""

import re

from server import model_privacy
from server.rmd_service import bi, fail, text

GRAIN_NAMES = {
    "mms_work_order": ("MMS work-order records", "سجلات أوامر عمل MMS"),
    "occ_event": ("OCC event records", "سجلات أحداث OCC"),
    "sr_reconciliation": ("SR reconciliation records", "سجلات مطابقة SR"),
    "summary": ("summary rows", "صفوف الملخص"),
    "other": ("other source rows", "صفوف مصادر أخرى"),
}


def aggregate_facts(analysis, language="en"):
    """No free-text labels, filenames, identifiers, source rows or clauses."""
    arabic = language == "ar"
    facts = []
    for grain, labels in GRAIN_NAMES.items():
        count = analysis.get("counts_by_grain", {}).get(grain)
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            facts.append(f"{labels[arabic]}: {count}.")
    facts.append("هذه أعداد سجلات في نطاق اللقطة المحدد، وليست أعداد حوادث فريدة أو معدلات أعطال."
                 if arabic else
                 "These are record counts in the selected snapshot scope, not unique incidents or failure rates.")
    return facts


def explain(assistant, service, principal, pack_id, payload):
    service._pack(principal, pack_id)
    if set(payload) - {"question", "analysis_id", "language"}:
        fail("invalid_question", "Unsupported assistant context.")
    question = text(payload.get("question"), "question", 2000)
    language = "ar" if payload.get("language") == "ar" else "en"
    arabic = language == "ar"
    analysis_id = payload.get("analysis_id")
    analysis = service.get_analysis(principal, pack_id, analysis_id) if analysis_id else None
    procedure = bool(re.search(r"procedure|require|clause|manual|policy|إجراء|يتطلب|يشترط|دليل|وثيقة|بند", question, re.I))
    if procedure or analysis is None:
        hits = service.search_knowledge(principal, pack_id, question[:500], limit=3)["hits"]
        if not hits and procedure:
            hits = service.search_knowledge(principal, pack_id, "must shall يجب يتعين", limit=3)["hits"]
        citations = [{"source_id": hit["source_id"], "clause_id": hit["clause_id"],
                      "source_name": hit["source_name"], "locator": hit["locator"],
                      "revision": hit.get("document_revision"), "sha256": hit["source_sha256"]}
                     for hit in hits]
        answer = "\n\n".join(hit["text"][:1600] for hit in hits) if hits else (
            "لم أجد بنداً مطابقاً في المصادر المصرح بها. افتح المعرفة وابحث باسم الوثيقة أو مصطلح من النص."
            if arabic else
            "No matching clause was found in your authorized sources. Open Knowledge and search by document or source wording.")
        limitations = [(
            "النص مقتبس من النسخة المقدمة؛ قابلية التطبيق الحالية وحالة الاعتماد والتغطية البصرية تحتاج مراجعة."
            if arabic else
            "Quoted from the supplied copy. Current applicability, approval status and visual extraction coverage require review.")]
        service._pack(principal, pack_id)
        return {"text": answer, "source": "deterministic", "citations": citations,
                "limitations": limitations, "ephemeral": True}

    facts = aggregate_facts(analysis, language)
    lines = list(facts)
    lower = question.casefold()
    wanted = ("location" if any(word in lower for word in ("junction", "location", "تقاطع", "موقع"))
              else "category" if any(word in lower for word in ("category", "فئة", "تصنيف")) else None)
    if wanted:
        chart = next((c for c in analysis.get("charts", []) if wanted in c["id"]), None)
        if chart and chart.get("table"):
            row = chart["table"][0]
            lines += [f"{bi(chart['title'], language)}: {row['label']} — {row['value']}."]
    elif any(word in lower for word in ("missing", "match", "sr", "مطابقة", "مفقود")):
        lines += [(
            "نتيجة المطابقة تخص مصدر المقارنة المحدد فقط. التسميات الأصلية محفوظة ولا تعني أن SR غير موجود في كل الأنظمة."
            if arabic else
            "A match result concerns only the selected comparison source. Original labels do not establish that an SR is absent from every system.")]
        for outcome in (analysis.get("reconciliation") or {}).get("calculated_outcomes", []):
            lines.append(f"{outcome['code']}: {outcome['count']}.")
            if outcome["code"] == "not_in_uploaded_mms" and outcome["record_ids"]:
                selected = service.records(principal, pack_id, analysis_id, {
                    "record_ids": outcome["record_ids"], "limit": 40})["records"]
                lines += [str(record["fields"].get("sr_id")) + " — " + str(record["sheet"]) +
                          ":" + str(record["source_row"]) for record in selected]
                if len(outcome["record_ids"]) > len(selected):
                    lines.append("افتح الأدلة للاطلاع على بقية السجلات." if arabic else
                                 "Open evidence to inspect the remaining records.")
    elif any(word in lower for word in ("repeat", "recurr", "تكرر", "متكرر")):
        lines += [f"{item['symptom_label']} — {item['location']}: {item['count']}."
                  for item in analysis.get("recurrence", [])[:3]]
        lines += [("هذه أنماط نصية متكررة مقترحة، وليست أسبابًا جذرية متحققة."
                   if arabic else "These are candidate repeated text patterns, not verified root causes.")]
    else:
        lines += [bi(p["finding"], language) for p in analysis.get("priorities", [])[:3]]

    # Only explicit operator policy permits aggregate model use. The question,
    # investigation labels and private source text never enter this prompt.
    narration = None
    if str(service.env.get("AGENTIC_OS_RMD_MODEL_AGGREGATES", "")).lower() in ("1", "true"):
        if not model_privacy.blocks_model(texts=facts):
            try:
                result = assistant.gateway.narrate(
                    "تلخيص أعداد السجلات الموثقة" if arabic else "Summarize verified record counts",
                    facts, language=language, task="chat")
                # Numeric overlap cannot validate causal/engineering wording.
                # Only already approved complete fact templates may be shown.
                allowed = set(facts) | {" ".join(facts), "\n".join(facts)}
                if result.get("source") == "model" and result.get("text", "").strip() in allowed:
                    narration = result["text"]
            except Exception:
                pass
    service._pack(principal, pack_id)
    citations = [{"source_id": s.get("source_id") or s.get("id"),
                  "locator": {"analysis_id": analysis_id, "calculation_version": analysis["calculation_version"]},
                  "sha256": s.get("sha256") or s.get("source_sha")}
                 for s in analysis.get("source_versions", []) if s.get("source_id") or s.get("id")]
    return {"text": "\n".join(([narration] if narration else []) + lines),
            "source": "model" if narration else "deterministic", "citations": citations,
            "limitations": analysis.get("limitations", []), "ephemeral": True,
            "analysis_id": analysis_id, "fingerprint": analysis["fingerprint"]}
