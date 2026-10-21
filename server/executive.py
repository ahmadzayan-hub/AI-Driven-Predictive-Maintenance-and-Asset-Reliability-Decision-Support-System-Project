"""A read-only executive briefing over a run's existing, auditable evidence.

No language model, dataset mutation, fitted model, or approval is invoked here.
Filtered observations and whole-run evaluation evidence stay separate (ADR 0058).
"""

import copy
import hashlib
import json
import math

from server import query
from server.maintenance import contract, kpis, performance
from server.runs import model_cards

MAX_FILTER_CHARS = 16_000
MAX_PRIORITIES = MAX_QUESTIONS = 6
MAX_FINDINGS = MAX_MODELS = 12
MAX_EVIDENCE = 120
MAX_DRILLDOWNS = 8
MAX_TEXT = 1000
# These stages can contain cleaned rows; their output is not executive evidence.
ROW_STAGES = {"collector", "profiler", "cleaner", "merge", "preparer"}
STAGE_ORDER = ("maintenance_governance", "rail_asset_manager", "maintenance_risk",
               "validator", "quality", "diagnostic", "prescriptive", "anomaly",
               "descriptive", "sensitivity")


def _say(language, en, ar):
    return ar if language == "ar" else en


def _text(value):
    return str(value or "")[:MAX_TEXT]


def _problem(en, ar):
    return query.QueryError([query.Problem("filters", None, en, ar)])


def parse_filters(encoded):
    """Check the GET transport shape, then let query.filtered check semantics."""
    if not isinstance(encoded, str) or len(encoded) > MAX_FILTER_CHARS:
        raise _problem("The encoded filters exceed the 16,000-character limit.",
                       "تتجاوز المرشحات المشفرة الحد الأقصى البالغ 16000 حرف.")
    try:
        filters = json.loads(encoded)
    except (ValueError, TypeError):
        raise _problem("Filters must be a JSON array of filter objects.",
                       "يجب أن تكون المرشحات مصفوفة JSON من كائنات الترشيح.") from None
    if not isinstance(filters, list) or any(not isinstance(f, dict) for f in filters):
        raise _problem("Filters must be a JSON array of filter objects.",
                       "يجب أن تكون المرشحات مصفوفة JSON من كائنات الترشيح.")
    # Retain the query language, not arbitrary nested data or extra payloads.
    for item in filters:
        values = item.get("values", [])
        if (not isinstance(item.get("column"), str)
                or not isinstance(item.get("op"), str)
                or not isinstance(values, list)
                or any(isinstance(v, (dict, list)) for v in values)
                or isinstance(item.get("value"), (dict, list))
                or any(isinstance(v, float) and not math.isfinite(v)
                       for v in values + [item.get("value")])):
            raise _problem("Each filter needs a column, operator and scalar values.",
                           "يحتاج كل مرشح إلى عمود وعامل وقيم مفردة.")
    return [{k: copy.deepcopy(v) for k, v in item.items()
             if k in {"column", "op", "value", "values"}} for item in filters]


class ExecutiveDashboardAgent:
    """Deterministic decision support. Existing permissions remain the API's job."""

    def brief(self, table, run, tasks=(), filters=None, language="en", policy=None):
        selected_policy = performance.policy() if policy is None else policy
        filters = copy.deepcopy(filters or [])
        selected, _ = query.filtered(table, filters)
        supported, _ = kpis.computable(table.columns)
        needed = {column for measure in supported for column in measure.source_columns}
        positions = [(i, column) for i, column in enumerate(table.columns) if column in needed]
        # Wide tables do not need a second dictionary copy of every source cell.
        records = [{column: row[i] for i, column in positions} for row in selected]
        computed = kpis.compute_all(table.columns, records)
        measures = []
        for result in computed["results"]:
            if any(value is not None and not math.isfinite(value) for value in
                   (result["value"], result["numerator"], result["denominator"])):
                raise query.QueryError([query.Problem("measure", result["key"],
                    "A KPI aggregate exceeds the supported numeric range.",
                    "يتجاوز مجموع أحد المؤشرات النطاق العددي المدعوم.")])
            item = dict(result)
            item["title"] = result["title_ar"] if language == "ar" else result["title"]
            item.pop("title_ar", None)
            # `population` stays the code the export matches on; the label is shown.
            item["population_label"] = result["population_ar"] if language == "ar" else result["population"]
            item.pop("population_ar", None)
            item["assessment"] = performance.assessment(item, selected_policy["rules"], language)
            measures.append(item)
        evidence, priorities, questions, drilldowns = [], [], [], []
        limitations, findings, models = [], [], []
        evidence_ids = set()

        def add_evidence(identifier, kind, label, value, method, scope="filtered"):
            if identifier in evidence_ids:
                return True
            if len(evidence) >= MAX_EVIDENCE:
                return False
            evidence.append({"id": identifier, "kind": kind, "label": _text(label),
                             "value": value, "method": _text(method), "scope": scope})
            evidence_ids.add(identifier)
            return True

        def priority(identifier, title, detail, refs, drilldown=None):
            if len(priorities) < MAX_PRIORITIES:
                priorities.append({"id": identifier, "title": _text(title), "detail": _text(detail),
                                   "evidence_refs": refs, "drilldown_id": drilldown})

        def question(identifier, en, ar, refs):
            if len(questions) < MAX_QUESTIONS:
                questions.append({"id": identifier, "text": _say(language, en, ar),
                                  "evidence_refs": refs})

        def drill(identifier, label, extra=()):
            full = filters + list(extra)
            if (len(full) > query.MAX_FILTERS or len(drilldowns) >= MAX_DRILLDOWNS
                    or len(json.dumps(full, ensure_ascii=False)) > MAX_FILTER_CHARS):
                return None
            drilldowns.append({"id": identifier, "label": label, "filters": full})
            return identifier

        add_evidence("executive.scope.records", "scope",
                     _say(language, "Records in the selected scope", "السجلات ضمن النطاق المحدد"),
                     len(selected), _say(language, "Count of cleaned records passing the existing query filters.",
                                         "عدد السجلات المنظفة التي تستوفي مرشحات الاستعلام الحالية."))
        add_evidence("executive.scope.total", "scope",
                     _say(language, "Records in the whole run", "السجلات في التشغيل الكامل"),
                     len(table.rows), _say(language, "Count of the run's cleaned records before filters.",
                                          "عدد سجلات التشغيل المنظفة قبل تطبيق المرشحات."), "whole_run")
        all_rows = drill("scope", _say(language, "Inspect scoped records", "فحص سجلات النطاق"))
        by_key = {m["key"]: m for m in measures}
        for measure in measures:
            add_evidence("executive.kpi." + measure["key"], "kpi", measure["title"],
                         measure["value"],
                         f"{measure['formula']}; {measure['population']}; "
                         f"measured={measure['records']}; unmeasured={measure['records_unmeasured']}; "
                         f"excluded={measure['records_excluded']}")

        if selected and any(m["value"] is None for m in measures):
            limitations.append(_say(language, "Some KPI values are undefined because their measured population or denominator is empty; they are not zero performance.",
                                    "بعض قيم المؤشرات غير محددة لغياب مجموعة مقاسة أو مقام صالح؛ ولا تعني أداءً صفرياً."))
        gaps = [m for m in measures if m["records_unmeasured"]]
        if gaps and selected:
            names = ", ".join(m["title"] for m in gaps)
            limitations.append(_say(language, "Some KPI populations contain unmeasured records; they are disclosed, not counted as zeros.",
                                    "تحتوي بعض مجموعات المؤشرات على سجلات غير مقاسة؛ يُفصح عنها ولا تُحتسب أصفاراً."))
            priority("measurement_gaps", _say(language, "Resolve missing measurements", "استكمال القياسات المفقودة"),
                     _say(language, f"Review the excluded measurements before using these measures: {names}.",
                          f"راجع القياسات المستبعدة قبل استخدام المؤشرات التالية: {names}."),
                     ["executive.kpi." + m["key"] for m in gaps], all_rows)

        for key, en, ar in (
            ("overdue_share", "Review overdue work", "مراجعة الأعمال المتأخرة"),
            ("repeat_repair", "Review repeat corrective repairs", "مراجعة الإصلاحات التصحيحية المتكررة"),
        ):
            measure = by_key.get(key)
            if selected and measure and measure["value"] is not None and measure["value"] > 0:
                priority(key, _say(language, en, ar),
                         _say(language, "The selected records contain observed work requiring review. The figure is a population ratio, not a future failure probability.",
                              "تتضمن السجلات المحددة أعمالاً مرصودة تستلزم المراجعة. الرقم نسبة في مجموعة السجلات وليس احتمال عطل مستقبلي."),
                         ["executive.kpi." + key], all_rows)

        # Rank observed groups with the same bounded aggregate engine used by dashboards.
        dimension = next((c for c in ("Site", "Asset_Class") if c in table.columns
                          and c not in table.numeric), None)
        if dimension is None:
            dimension = next((c for c, role in table.roles.items()
                              if role == "breakdown" and c not in table.numeric), None)
        if selected and dimension:
            for column, en, ar in (("Downtime_Hours", "Review the largest observed downtime group", "مراجعة المجموعة الأعلى في التوقف المرصود"),
                                   ("Maintenance_Cost_USD", "Review the largest observed maintenance-cost group", "مراجعة المجموعة الأعلى في تكلفة الصيانة المرصودة")):
                if column not in table.numeric:
                    continue
                answer = query.aggregate(table, {"group_by": [dimension], "filters": filters,
                    "measures": [{"agg": "sum", "column": column}],
                    "sort": {"by": "sum:" + column, "desc": True}, "limit": 1})
                top = answer["groups"][0] if answer["groups"] else None
                if not top or top["values"][0] is None or top["values"][0] <= 0:
                    continue
                value, group = top["values"][0], top["keys"][0]
                if not math.isfinite(value):
                    raise query.QueryError([query.Problem("measure", column,
                        "A grouped aggregate exceeds the supported numeric range.",
                        "يتجاوز مجموع إحدى المجموعات النطاق العددي المدعوم.")])
                identifier = "executive.group." + column.lower()
                add_evidence(identifier, "calculation", f"{dimension}: {group}", value,
                             f"sum({column}) grouped by {dimension}; selected query filters")
                extra = [{"column": dimension, "op": "in", "values": [group]}]
                full = filters + extra
                link = None
                if (len(full) <= query.MAX_FILTERS
                        and len(json.dumps(full, ensure_ascii=False)) <= MAX_FILTER_CHARS):
                    matched, _ = query.filtered(table, full)
                    # Text filtering normalises null and blank values. Do not offer
                    # a group drilldown if that normalisation would widen its rows.
                    if len(matched) == top["records"]:
                        link = drill(column.lower(), _say(language, "Inspect this group", "فحص هذه المجموعة"), extra)
                priority(column.lower(), _say(language, en, ar),
                         _say(language, f"{dimension}: {group} has the largest observed total ({value:g} in {column}). Inspect its records before choosing an intervention.",
                              f"تسجل المجموعة {dimension}: {group} أعلى إجمالي مرصود ({value:g} في {column}). افحص سجلاتها قبل اختيار أي تدخل."),
                         [identifier], link)

        # Read only non-row stage results. Findings are historical whole-run evidence.
        stages = []
        for task in tasks:
            role = task.get("role", "")
            if role in ROW_STAGES or task.get("state") != "succeeded":
                continue
            try:
                result = json.loads(task["result_json"]) if task.get("result_json") else task.get("result", {})
            except (ValueError, TypeError):
                continue
            if isinstance(result, dict):
                stages.append((task, result))
        order = {role: i for i, role in enumerate(STAGE_ORDER)}
        stages.sort(key=lambda item: order.get(item[0].get("role"), len(order)))
        calculations = {}
        for task, result in stages:
            for calc in result.get("calculations", []):
                value = calc.get("value")
                if (isinstance(calc.get("id"), str) and
                        (value is None or (isinstance(value, (int, float)) and
                         not isinstance(value, bool) and math.isfinite(value)))):
                    calculations[calc["id"]] = calc
            for card in model_cards(result):
                if len(models) < MAX_MODELS:
                    models.append({**copy.deepcopy(card), "role": task["role"],
                                   "title": task.get("title", task["role"]), "scope": "whole_run"})
        omitted = untranslated = False
        for task, result in stages:
            for claim in result.get("claims", []):
                refs = claim.get("evidence", [])
                if (claim.get("status") != "verified" or claim.get("type") == "forecast"
                        or not refs or len(refs) > 12 or any(ref not in calculations for ref in refs)):
                    continue
                if len(findings) >= MAX_FINDINGS or len(evidence) + len(set(refs) - evidence_ids) > MAX_EVIDENCE:
                    omitted = True
                    continue
                for ref in refs:
                    calc = calculations[ref]
                    add_evidence(ref, "calculation", calc.get("name"), calc.get("value"), calc.get("method"), "whole_run")
                text = (claim.get("text_ar") if language == "ar" else claim.get("text"))
                if not text:
                    untranslated = True
                    # Do not relabel an English source finding as an Arabic translation.
                    continue
                findings.append({"id": claim.get("id"), "text": _text(text),
                                 "stage": task["role"], "kind": claim.get("type"),
                                 "evidence_refs": refs, "scope": "whole_run"})
        if omitted:
            limitations.append(_say(language, "This bounded briefing does not reproduce every run finding; inspect the full run for the complete record.",
                                    "لا يعرض هذا الملخص المحدود جميع نتائج التشغيل؛ افحص التشغيل الكامل للاطلاع على السجل الكامل."))
        if filters and (findings or models):
            limitations.append(_say(language, "Existing findings and model evaluations describe the whole run and were not recomputed for these filters.",
                                    "تصف النتائج وتقييمات النماذج الموجودة التشغيل الكامل ولم تُعَد حساباتها لهذه المرشحات."))
        if untranslated:
            limitations.append(_say(language, "Some stored findings have no text in the requested language; inspect the original run for those findings.",
                                    "لا يتوفر نص لبعض النتائج المخزنة باللغة المطلوبة؛ افحص التشغيل الأصلي للاطلاع عليها."))
        failed_checks = sum(1 for _, result in stages for check in result.get("quality_checks", [])
                            if check.get("passed") is False)
        failed_stages = sum(1 for task in tasks if task.get("state") == "failed")
        if failed_checks or failed_stages:
            add_evidence("executive.validation.failed_checks", "calculation",
                         _say(language, "Original run checks not passed", "فحوص التشغيل الأصلي غير المجتازة"),
                         failed_checks, "count stored quality checks where passed=false", "whole_run")
            limitations.append(_say(language, "Some original run checks or stages did not pass; inspect the full validation record before acting.",
                                    "لم تجتز بعض فحوص التشغيل الأصلي أو مراحله التحقق؛ افحص سجل التحقق الكامل قبل اتخاذ أي إجراء."))
        if any(card.get("split", {}).get("kind") == "every_fifth" for card in models):
            limitations.append(_say(language, "An existing model uses every-fifth-record holdout; that split does not establish future-period predictive performance.",
                                    "يستخدم أحد النماذج الموجودة حجب كل خامس سجل للاختبار؛ وهذا التقسيم لا يثبت الأداء التنبؤي للفترات المستقبلية."))
        unavailable = computed["unavailable"]
        if unavailable:
            limitations.append(_say(language, "Some controlled maintenance KPIs are unavailable because required columns are absent.",
                                    "بعض مؤشرات الصيانة المنضبطة غير متاحة لغياب الأعمدة المطلوبة."))
            question("missing_columns", "Which source can supply the fields needed by the unavailable KPIs?",
                     "ما المصدر الذي يمكنه توفير الحقول اللازمة للمؤشرات غير المتاحة؟", ["executive.scope.records"])
        if not models:
            limitations.append(_say(language, "No model evaluation cards are available for this run; no predictive performance is claimed.",
                                    "لا تتوفر بطاقات تقييم نماذج لهذا التشغيل؛ ولا يُدّعى أي أداء تنبؤي."))
            question("model_evidence", "Does a maintenance-profile run with suitable dated records support the intended decision?",
                     "هل يدعم تشغيل بملف الصيانة وسجلات مؤرخة مناسبة القرار المقصود؟", ["executive.scope.total"])
        elif any(c.get("fitted") is False or c.get("details", {}).get("verdict") in {"weak", "not_supported"}
                 or c.get("beats_baseline") is False for c in models):
            limitations.append(_say(language, "Some models are weak or unsupported; inspect their original baselines and limitations before use.",
                                    "بعض النماذج ضعيفة أو غير مدعومة؛ افحص خطوطها المرجعية وحدودها الأصلية قبل استخدامها."))
            question("model_validation", "Which decision remains justified by observed evidence while model support is limited?",
                     "ما القرار الذي تبرره الأدلة المرصودة عندما يكون دعم النموذج محدوداً؟", ["executive.scope.total"])
        fields, _ = contract.resolve(table.columns)
        if any(f.timing == contract.UNKNOWN for f in fields.values()):
            question("feature_timing", "When were condition or sensor readings recorded relative to the decision?",
                     "متى سُجلت قراءات الحالة أو المستشعرات مقارنة بوقت اتخاذ القرار؟", ["executive.scope.total"])
        question("human_review", "Which approved site or manufacturer procedure governs the engineering review?",
                 "ما إجراء الموقع أو الشركة المصنعة المعتمد الذي يحكم المراجعة الهندسية؟", ["executive.scope.records"])
        if run.get("state") in {"failed", "cancelled"}:
            limitations.append(_say(language, "The run did not complete successfully; this is a partial evidence briefing.",
                                    "لم يكتمل التشغيل بنجاح؛ وهذا ملخص للأدلة الجزئية."))
        limitations.append(_say(language, "Observed maintenance records do not establish future asset failure, remaining useful life, physical asset identity, or causal savings. Actions require qualified human review.",
                                "لا تثبت سجلات الصيانة المرصودة الأعطال المستقبلية أو العمر المتبقي أو هوية الأصل الفعلية أو الوفورات السببية. تتطلب الإجراءات مراجعة بشرية مؤهلة."))
        status = "empty" if not selected else "limited" if len(limitations) > 1 else "ready"
        headline = (_say(language, "No cleaned records match the selected scope.", "لا توجد سجلات منظفة تطابق النطاق المحدد.")
                    if not selected else _say(language,
                        f"{len(selected)} records in scope; {len(measures)} controlled measures available for review.",
                        f"يتضمن النطاق {len(selected)} سجلاً؛ ويتاح {len(measures)} مؤشراً منضبطاً للمراجعة."))
        brief = {"run": {"id": run["id"], "dataset_name": run.get("dataset_name", ""),
                        "state": run.get("state"), "updated_at": run.get("updated_at")},
                "language": language, "source": "engine", "scope": {"records": len(selected),
                "total_records": len(table.rows), "filters": filters}, "headline": headline,
                "readiness": {"status": status, "limitations": limitations},
                "kpis": {"measures": measures, "unavailable": unavailable},
                "priorities": priorities, "questions": questions, "findings": findings,
                "models": models, "evidence": evidence, "drilldowns": drilldowns,
                "kpi_policy": copy.deepcopy(selected_policy)}
        # Task results may change without advancing the run row's timestamp.
        # Bind downloads to every fact in the prepared response, including its
        # language, filters, metadata and evidence, without trusting client data.
        canonical = json.dumps(brief, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, allow_nan=False).encode("utf-8")
        brief["snapshot_id"] = hashlib.sha256(canonical).hexdigest()
        return brief
