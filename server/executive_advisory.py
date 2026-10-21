"""Executive recommendations from scoped aggregates, never source-file certification.

The supplied course pack is a separate verification responsibility: a dataset
name and a successful pipeline are not evidence that its workbook reconciles.
"""

import math


def advisory(table, selected, measures, priorities, models, language, add_evidence):
    def tr(en, ar):
        return ar if language == "ar" else en

    by_key = {item["key"]: item for item in measures}
    domains = []
    definitions = (
        ("condition", "Condition", "الحالة", None,
         "Confirm condition scale and reading time before setting intervention thresholds.",
         "تحقق من مقياس الحالة وتوقيت القراءة قبل تحديد حدود التدخل."),
        ("failures", "Failures", "الأعطال", "failures_per_record",
         "Use observed failures to focus reliability investigation; this is not a future failure probability.",
         "استخدم الأعطال المرصودة لتوجيه فحص الموثوقية؛ هذه ليست احتمالية عطل مستقبلي."),
        ("work_orders", "Work orders", "أوامر العمل", "overdue_rate",
         "Validate overdue work and recurring repairs with the maintenance planner before changing the schedule.",
         "راجع الأعمال المتأخرة والإصلاحات المتكررة مع مخطط الصيانة قبل تعديل الجدول."),
        ("downtime", "Downtime", "التوقف", "downtime_per_record",
         "Investigate high-downtime groups against planned exposure and operating context.",
         "افحص مجموعات التوقف المرتفع مقارنة بساعات التشغيل المخططة والسياق التشغيلي."),
        ("economic", "Economic impact", "الأثر الاقتصادي", "loss_per_record",
         "Validate the recorded production-loss valuation and maintenance spend before proposing an investment.",
         "تحقق من أساس تقييم خسائر الإنتاج المسجلة والإنفاق على الصيانة قبل اقتراح استثمار."),
    )
    for key, en, ar, metric_key, implication, implication_ar in definitions:
        metric = by_key.get(metric_key)
        if key == "work_orders" and metric is None:
            metric = by_key.get("overdue_share")
        value, records, refs = None, 0, []
        status = "unavailable"
        label = metric["title"] if metric else tr(en, ar)
        scale = metric["scale"] if metric else "score" if key == "condition" else "count"
        reason = tr("Required measurements are unavailable.", "القياسات المطلوبة غير متاحة.")
        if metric:
            value, records = (metric["numerator"] if metric["records"] else None), metric["records"]
            label = {"failures": tr("Recorded failures", "الأعطال المسجلة"),
                     "work_orders": tr("Recorded overdue work orders", "أوامر العمل المتأخرة المسجلة"),
                     "downtime": tr("Recorded downtime", "التوقف المسجل"),
                     "economic": tr("Recorded production loss", "خسائر الإنتاج المسجلة")}[key]
            if key == "work_orders":
                scale = "count"
            status = "unassessed" if value is not None else "unavailable"
            reason = tr("Observed total; no approved performance threshold for this total. Coverage follows the cited KPI population.",
                        "إجمالي مرصود؛ لا يوجد حد أداء معتمد لهذا الإجمالي. تتبع التغطية مجتمع المؤشر المشار إليه.")
            identifier = "executive.total." + key
            add_evidence(identifier, "calculation", label, value,
                         f"numerator of {metric['key']}: {metric['formula']}; {metric['population']}; selected query filters; measured={records}; unmeasured={metric['records_unmeasured']}")
            refs = [identifier, "executive.kpi." + metric["key"]]
        elif key == "condition" and "Condition_Score" in table.columns:
            index = table.columns.index("Condition_Score")
            readings = []
            for row in selected:
                try:
                    number = float(str(row[index]).strip().replace(",", ""))
                except (ValueError, TypeError):
                    continue
                if math.isfinite(number):
                    readings.append(number)
            records = len(readings)
            # Dividing before summation avoids overflowing otherwise valid means.
            value = math.fsum(number / records for number in readings) if records else None
            status = "unassessed" if value is not None else "unavailable"
            label = tr("Mean recorded condition score", "متوسط درجة الحالة المسجلة")
            reason = tr("Source scale, direction and intervention thresholds need dictionary confirmation.",
                        "يلزم تأكيد المقياس واتجاهه وحدود التدخل من قاموس البيانات.")
            identifier = "executive.condition.mean"
            add_evidence(identifier, "calculation", label, value,
                         f"mean(finite Condition_Score); selected query filters; measured={records}; unmeasured={len(selected) - records}")
            refs = [identifier]
        domains.append({"id": key, "title": tr(en, ar), "measure": label,
                        "value": value, "scale": scale, "status": status,
                        "reason": reason, "records": records,
                        "unmeasured": metric["records_unmeasured"] if metric else len(selected) - records,
                        "implication": tr(implication, implication_ar), "evidence_refs": refs})

    decisions = []
    for item in priorities:
        key = item["id"]
        owner = (tr("Data steward", "مسؤول البيانات") if key == "measurement_gaps" else
                 tr("Finance and maintenance leads", "مسؤولا المالية والصيانة") if "cost" in key else
                 tr("Maintenance planner", "مخطط الصيانة") if key == "overdue_share" else
                 tr("Reliability engineer", "مهندس الموثوقية"))
        decisions.append({"id": key, "title": item["title"], "action": item["detail"],
                          "owner": owner, "gate": tr("Before approving a maintenance intervention", "قبل اعتماد تدخل صيانة"),
                          "evidence_refs": item["evidence_refs"]})

    assessed_bad = sum(m["assessment"]["status"] == "bad" for m in measures)
    if not selected:
        recommendation = tr("No decision recommendation: select a scope with measured records.",
                            "لا توجد توصية لاتخاذ قرار: اختر نطاقاً يتضمن سجلات مقاسة.")
    elif assessed_bad:
        recommendation = tr(
            f"Commission a focused reliability review: {assessed_bad} measures are below the configured acceptance bands. Validate causes and intervention costs before authorizing changes.",
            f"كلّف الفريق بمراجعة مركزة للموثوقية: {assessed_bad} مؤشرات دون حدود القبول المحددة. تحقق من الأسباب وتكاليف التدخل قبل اعتماد التغييرات.")
    else:
        recommendation = tr(
            "Endorse a scoped maintenance and reliability review. Use observed exposure to prioritize investigation; agree performance targets and intervention economics before authorizing changes.",
            "اعتمد مراجعة محددة النطاق للصيانة والموثوقية. استخدم الأثر المرصود لترتيب أولويات الفحص، واتفق على أهداف الأداء وجدوى التدخل قبل اعتماد التغييرات.")

    return {
        "title": tr("AI-Driven Predictive Maintenance and Asset Reliability Decision-Support System",
                    "نظام الصيانة التنبؤية المدعوم بالذكاء الاصطناعي ودعم قرارات موثوقية الأصول"),
        "subtitle": tr("Condition, failures, work orders, downtime and economic impact",
                       "الحالة والأعطال وأوامر العمل والتوقف والأثر الاقتصادي"),
        "role": tr("Executive Analytics Advisory Group", "المجموعة الاستشارية للتحليلات التنفيذية"),
        "recommendation": recommendation,
        "domains": domains, "decisions": decisions,
        "prediction": tr(
            "Review the recorded model evaluations below. Retrospective discrimination is not evidence of future failure prediction; require stable asset identity, pre-decision inputs, a dated horizon and forward validation before operational use."
            if models else "No model evaluation is available. Predictive maintenance remains a proposed capability; observed condition, failures and costs support investigation only.",
            "راجع تقييمات النماذج المسجلة أدناه. التمييز بأثر رجعي لا يثبت التنبؤ بالأعطال المستقبلية؛ يلزم التحقق من هوية الأصل ومدخلات سابقة للقرار وأفق زمني محدد واختبار زمني لاحق قبل الاستخدام التشغيلي."
            if models else "لا يتوفر تقييم نموذج. تظل الصيانة التنبؤية قدرة مقترحة؛ وتدعم الحالة والأعطال والتكاليف المرصودة أعمال الفحص فقط."),
        "sources": [
            {"id": key, "title": tr(en, ar), "status": "unassessed", "detail": tr(detail, detail_ar)}
            for key, en, ar, detail, detail_ar in (
                ("csv", "Assigned CSV / approved master", "ملف CSV المخصص / البيانات الرئيسية المعتمدة",
                 "The current run supplies a cleaned analytical copy. Its identity against the approved master and its transformation log still require verification.",
                 "يوفر التشغيل الحالي نسخة تحليلية منظفة. لا تزال مطابقتها للبيانات الرئيسية المعتمدة وسجل تحويلاتها تتطلب التحقق."),
                ("workbook", "Supporting analytics workbook", "مصنف التحليلات الداعم",
                 "Reconcile supplied results with independent calculations, populations and units; reconciliation is not recorded in this snapshot.",
                 "طابق النتائج المقدمة مع حسابات مستقلة ومجتمعات القياس والوحدات؛ لم تُسجل المطابقة في هذه اللقطة."),
                ("dictionary", "Data dictionary", "قاموس البيانات",
                 "Confirm variable meanings, units, record grain, missing-value rules and timing; source-specific sign-off is not recorded here.",
                 "أكد معاني المتغيرات والوحدات ومستوى السجل وقواعد القيم المفقودة والتوقيت؛ لم يُسجل اعتماد خاص بالمصدر هنا."),
                ("reference", "Published project reference", "المرجع المنشور للمشروع",
                 "Scenario, variable definitions and dashboard inspiration only. No publication results are adopted as new findings or verified by this report.",
                 "لفهم السيناريو وتعريفات المتغيرات والاسترشاد بتصميم اللوحات فقط. لا تُعتمد نتائج المنشور كاستنتاجات جديدة ولا يتحقق هذا التقرير منها."),
            )
        ],
        "new_findings": tr("New calculations in this briefing use the selected cleaned records and named formulas. Stored analysis findings and model cards retain their whole-run scope. Neither constitutes reconciliation with the supplied workbook or reference publication.",
                           "تستخدم الحسابات الجديدة في هذا الموجز السجلات المنظفة المحددة والصيغ المسماة. تحتفظ نتائج التحليل وبطاقات النماذج المخزنة بنطاق التشغيل الكامل. ولا يعني أي منهما المطابقة مع المصنف الداعم أو المرجع المنشور."),
        "preservation": tr("Preserve the approved master dataset. Transform only a documented analytical copy or Power Query workflow, recording source version, step, rationale and affected records. This briefing reads aggregates and does not rewrite source values.",
                           "احفظ البيانات الرئيسية المعتمدة. نفّذ التحويلات في نسخة تحليلية موثقة أو سير عمل Power Query فقط، مع تسجيل إصدار المصدر والخطوة والمبرر والسجلات المتأثرة. يقرأ هذا الموجز المجاميع ولا يعيد كتابة قيم المصدر."),
        "escalation": tr("For a material business-rule issue, record the rule, conflicting evidence, affected measures and decision impact; consult the instructors before changing the scenario or source values. Keep the original values and withhold the affected conclusion until resolved.",
                         "عند وجود مشكلة جوهرية في قواعد العمل، وثّق القاعدة والأدلة المتعارضة والمؤشرات المتأثرة وأثرها على القرار؛ واستشر المدرسين قبل تغيير السيناريو أو قيم المصدر. احتفظ بالقيم الأصلية وعلّق الاستنتاج المتأثر حتى الحل."),
    }
