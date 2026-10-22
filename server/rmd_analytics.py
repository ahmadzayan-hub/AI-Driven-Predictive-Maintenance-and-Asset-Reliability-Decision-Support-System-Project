"""Deterministic, record-grain-aware evidence analytics.

This module neither reads documents nor calls a model. Callers supply an
authorised snapshot with reviewed column roles. It returns calculations and
investigation registers; the latter must not be copied into model prompts.
Exact identifier relationships describe source records, never canonical
incidents. A candidate link always requires a separate persisted decision.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import re


CALCULATION_VERSION = "rmd-evidence/1"
GRAINS = ("mms_work_order", "occ_event", "sr_reconciliation", "summary", "other")
DETAIL_GRAINS = GRAINS[:3]
MAX_RECORDS = 100_000
MAX_PROPOSED_LINKS = 500
PLACEHOLDERS = {"NA", "N/A", "EMPTY", "TBD"}
RECORDED_STATES = {"recorded", "measured_zero"}
DECLARED_STATES = RECORDED_STATES | {
    "unknown", "not_applicable", "not_measured", "blank", "unresolved_placeholder"
}
WORDS = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)


def _bi(en, ar):
    return {"en": en, "ar": ar}


def _stable(*values):
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _display(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple, set)):
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        if value.is_integer():
            return str(int(value))
    return str(value).strip()


def _field_state(record, field):
    """Unresolved placeholder text is retained, not redefined globally.

    A reviewed mapper can provide field_states (or value_states) for a
    particular field. Without that decision NA does not mean not-applicable.
    """
    value = record["fields"].get(field)
    states = record.get("field_states") or record.get("value_states") or {}
    declared = states.get(field) if isinstance(states, dict) else None
    declared = declared.get("state") if isinstance(declared, dict) else declared
    if declared in DECLARED_STATES - RECORDED_STATES:
        return declared
    if value is None:
        return "unknown"
    # A canonical outstanding flag may be Boolean. A Boolean SR/date/location
    # is not a valid identifier or measurement. Explicit reviewed missingness
    # above always takes precedence, including for Boolean status flags.
    if isinstance(value, bool):
        return "recorded" if field == "outstanding_status" else "unknown"
    if isinstance(value, (list, dict, tuple, set)):
        return "unknown"
    text = _display(value)
    if not text:
        return "blank"
    if declared == "recorded":
        return "recorded"
    if declared == "measured_zero" and text == "0":
        return "measured_zero"
    if text.upper() in PLACEHOLDERS:
        return "unresolved_placeholder"
    if isinstance(value, (int, float)) and value == 0:
        return "measured_zero"
    return "recorded"


def _value(record, field):
    return (_display(record["fields"].get(field))
            if _field_state(record, field) in RECORDED_STATES else "")


def _date(value):
    """Only explicit ISO dates/timestamps; never guess a day/month order."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    value = _display(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T[^\s]+)?", value):
        return None
    try:
        return (datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                if "T" in value else date.fromisoformat(value))
    except ValueError:
        return None


def _record_date(record, field="event_date"):
    return _date(_value(record, field))


def _loc(record):
    return {"record_id": record["id"], "source_id": record.get("source_id"),
            "source_sha": record.get("source_sha"), "sheet": record.get("sheet"),
            "source_row": record.get("source_row"), "grain": record["grain"]}


def _prepare(records):
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError("records must be a bounded list")
    prepared, seen = [], set()
    for item in records:
        if not isinstance(item, dict) or not isinstance(item.get("fields", {}), dict):
            raise ValueError("each record must hold a fields object")
        record = dict(item)
        record["fields"] = dict(item.get("fields", {}))
        grain = record.get("grain", "other")
        if grain not in GRAINS:
            raise ValueError("unsupported record grain")
        record["grain"] = grain
        record_id = _display(record.get("id"))
        if not record_id:
            if not (record.get("source_id") and record.get("sheet")
                    and record.get("source_row") is not None):
                raise ValueError("a record needs a stable id or source locator")
            record_id = "record-" + _stable(record.get("source_id"),
                                            record.get("source_sha"),
                                            record.get("sheet"),
                                            record.get("source_row"), grain)
        if record_id in seen:
            raise ValueError("duplicate record id")
        seen.add(record_id)
        record["id"] = record_id
        prepared.append(record)
    return sorted(prepared, key=lambda r: r["id"])


def _source_versions(values):
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError("source_versions must be a list")
    allowed = {"id", "source_id", "sha256", "source_sha", "version", "filename", "kind",
               "mapping_revision", "extraction_version", "extractor_version", "extraction_status"}
    provenance_fields = {
        "tool", "version", "python_version", "xml_parser_version", "original_preserved_by",
        "isolated_profile", "macros_disabled", "external_link_updates_disabled",
        "application_credentials_forwarded", "network_isolation",
        "timeout_seconds_per_conversion", "docx_sha256", "pdf_sha256",
    }

    def scalar(value):
        return (value is None or isinstance(value, (str, int, bool))
                or isinstance(value, float) and math.isfinite(value))

    cleaned = []
    for item in values:
        if not isinstance(item, dict):
            continue
        version = {k: v for k, v in item.items() if k in allowed and scalar(v)}
        extraction = item.get("extraction")
        if isinstance(extraction, dict):
            # Only extractor provenance belongs in the safe version summary;
            # document text, cell data and binary artifacts stay in the private
            # persisted source snapshot, never this reusable metadata surface.
            metadata = {k: v for k, v in extraction.items() if k in provenance_fields and scalar(v)}
            conversion = extraction.get("conversion")
            if isinstance(conversion, dict):
                metadata["conversion"] = {k: v for k, v in conversion.items()
                                          if k in provenance_fields and scalar(v)}
            version["extraction"] = metadata
        cleaned.append(version)
    return sorted(cleaned, key=lambda x: json.dumps(x, sort_keys=True))


def _list_filter(filters, *names):
    for name in names:
        if name in filters:
            value = filters[name]
            if value is None:
                return None
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ValueError(name + " must be a list of strings")
            return set(value)
    return None


def _select(records, filters):
    period = filters.get("period") or {}
    if not isinstance(period, dict):
        raise ValueError("period must be an object")
    start_raw = filters.get("date_from") or filters.get("from") or period.get("from")
    end_raw = filters.get("date_to") or filters.get("to") or period.get("to")
    start, end = _date(start_raw), _date(end_raw)
    if (start_raw and start is None) or (end_raw and end is None):
        raise ValueError("period boundaries must be ISO dates")
    if start and end and start > end:
        raise ValueError("period start is after its end")
    sources = _list_filter(filters, "source_ids", "sources")
    grains = _list_filter(filters, "grains", "roles")
    if grains and not grains.issubset(GRAINS):
        raise ValueError("unsupported grain filter")
    selected, exclusions = [], Counter()
    for record in records:
        if sources is not None and record.get("source_id") not in sources:
            exclusions["source_filter"] += 1
            continue
        if grains is not None and record["grain"] not in grains:
            exclusions["grain_filter"] += 1
            continue
        mismatch = False
        for name, field in (("location", "location"), ("category", "category"),
                            ("status", "wo_status")):
            wanted = filters.get(name)
            if wanted is not None and _display(wanted) != _value(record, field):
                exclusions[name + "_filter"] += 1
                mismatch = True
                break
        if mismatch:
            continue
        if start or end:
            observed = _record_date(record)
            if observed is None:
                exclusions["unavailable_event_date"] += 1
                continue
            if (start and observed < start) or (end and observed > end):
                exclusions["outside_period"] += 1
                continue
        selected.append(record)
    return selected, dict(sorted(exclusions.items())), {
        "from": start.isoformat() if start else None,
        "to": end.isoformat() if end else None,
        "basis": "validated_recorded_event_date" if start or end else "all_uploaded_recorded_dates",
    }


def _group_counts(records, field):
    grouped = defaultdict(list)
    for record in records:
        grouped[(_display(record["fields"].get(field)), _field_state(record, field))].append(record["id"])
    return [{"label": label, "state": state, "count": len(ids), "record_ids": ids}
            for (label, state), ids in sorted(grouped.items(), key=lambda x: (-len(x[1]), x[0]))]


def _completeness(groups):
    result = []
    fields = {
        "mms_work_order": ("sr_id", "wo_id", "wo_status", "event_date", "location", "rca_evidence"),
        "occ_event": ("event_date", "location", "category", "sr_id"),
        "sr_reconciliation": ("sr_id", "comparison_source", "event_date", "location"),
    }
    for grain, names in fields.items():
        for field in names:
            population = groups[grain]
            states = Counter(_field_state(r, field) for r in population)
            missing_ids = [r["id"] for r in population
                           if _field_state(r, field) not in RECORDED_STATES | {"not_applicable"}]
            result.append({
                "grain": grain, "field": field, "total_records": len(population),
                "applicable_records": len(population) - states["not_applicable"],
                "recorded": states["recorded"] + states["measured_zero"],
                "missing": states["blank"], "unknown": states["unknown"],
                "not_applicable": states["not_applicable"], "not_measured": states["not_measured"],
                "unresolved_placeholders": states["unresolved_placeholder"],
                "states": dict(sorted(states.items())), "record_ids_missing": missing_ids,
                "interpretation": "recorded field presence, not evidence validation or compliance",
            })
    return result


def _reconciliation(selected, all_records, filters):
    comparison_sources = _list_filter(filters, "comparison_source_ids")
    reference = [r for r in all_records if r["grain"] == "mms_work_order"
                 and (comparison_sources is None or r.get("source_id") in comparison_sources)]
    by_sr = defaultdict(list)
    for record in reference:
        if _value(record, "sr_id"):
            by_sr[_value(record, "sr_id")].append(record["id"])
    reconciliation = [r for r in selected if r["grain"] == "sr_reconciliation"]
    results = []
    outcomes = defaultdict(list)
    for record in reconciliation:
        sr = _value(record, "sr_id")
        matched = list(by_sr.get(sr, [])) if sr else []
        if not sr:
            outcome = "identifier_unavailable"
        elif not reference:
            outcome = "comparison_unavailable"
        elif matched:
            outcome = "matched_in_uploaded_mms"
        else:
            outcome = "not_in_uploaded_mms"
        outcomes[outcome].append(record["id"])
        results.append({"record_id": record["id"], "source_label": record["fields"].get("source_reconciliation_label"),
                        "source_label_comparison_source": _value(record, "comparison_source") or None,
                        "calculated_match": outcome, "matched_record_ids": matched})
    return {
        "source_labels": _group_counts(reconciliation, "source_reconciliation_label"),
        "calculated_outcomes": [{"code": code, "count": len(ids), "record_ids": ids}
                                for code, ids in sorted(outcomes.items())],
        "records": results,
        "comparison_scope": {"grain": "mms_work_order", "records": len(reference),
                             "source_ids": sorted({_display(r.get("source_id")) for r in reference}),
                             "date_filter_applied": False, "display_filters_applied": False,
                             "basis": "exact recorded SR identifiers in the uploaded reference snapshot"},
        "interpretation": _bi(
            "Source labels retain their original meaning. A match here compares only the uploaded MMS snapshot; an unstated original comparison source remains unknown.",
            "تُحفظ تسميات المصدر بمعناها الأصلي. المطابقة هنا تخص نسخة MMS المرفوعة فقط؛ ويظل مصدر المقارنة الأصلي غير معلوم إذا لم يُسجّل."),
    }


def _relationships(records):
    sr_nodes, wo_nodes, edges = {}, {}, []
    for record in records:
        if record["grain"] not in DETAIL_GRAINS:
            continue
        sr, wo = _value(record, "sr_id"), _value(record, "wo_id")
        for namespace, identifier, nodes in (("sr", sr, sr_nodes), ("wo", wo, wo_nodes)):
            if not identifier:
                continue
            node_id = namespace + "-" + _stable(identifier)
            node = nodes.setdefault(identifier, {"id": node_id, "identifier": identifier, "record_ids": []})
            node["record_ids"].append(record["id"])
            edges.append({"record_id": record["id"], "entity_id": node_id,
                          "relation": "records_identifier", "basis": "exact_source_identifier"})
    sr_to_wo = defaultdict(set)
    for record in records:
        if record["grain"] in DETAIL_GRAINS:
            sr, wo = _value(record, "sr_id"), _value(record, "wo_id")
            if sr and wo:
                sr_to_wo[sr].add(wo)
    return {"sr_nodes": sorted(sr_nodes.values(), key=lambda n: n["identifier"]),
            "wo_nodes": sorted(wo_nodes.values(), key=lambda n: n["identifier"]),
            "edges": edges,
            "sr_to_work_orders": [{"sr_id": sr, "wo_ids": sorted(wos)}
                                  for sr, wos in sorted(sr_to_wo.items())],
            "canonical_incident_count": None,
            "canonical_incident_basis": "No reviewed canonical incidents are supplied to this calculation.",
            "interpretation": "Identifier equality links records; it does not prove unique incident identity."}


def _conflicts(records):
    by_sr = defaultdict(list)
    for record in records:
        if record["grain"] in DETAIL_GRAINS and _value(record, "sr_id"):
            by_sr[_value(record, "sr_id")].append(record)
    conflicts = []
    for sr, group in sorted(by_sr.items()):
        for kind, field in (("date", "event_date"), ("location", "location")):
            values = defaultdict(list)
            for record in group:
                observed = _record_date(record) if kind == "date" else _value(record, field)
                if observed:
                    values[str(observed)].append(record["id"])
            if len(values) > 1:
                conflicts.append({"id": "conflict-" + _stable(kind, sr, sorted(values)),
                                  "kind": kind, "sr_id": sr, "record_ids": sorted({i for ids in values.values() for i in ids}),
                                  "values": [{"value": value, "record_ids": ids} for value, ids in sorted(values.items())],
                                  "status": "unresolved",
                                  "interpretation": _bi(
                                      "Records share an SR identifier but report different values. Multiple work orders or reporting versions may explain this; do not choose a value or merge incidents automatically.",
                                      "تشترك السجلات في معرف SR وتختلف قيمها. قد تفسر ذلك أوامر عمل متعددة أو نسخ تقارير مختلفة؛ ولا يجوز اختيار قيمة أو دمج الوقائع تلقائيًا.")})
    return conflicts


def _proposed_links(records, reconciliation, selected_ids):
    by_id = {r["id"]: r for r in records}
    links, seen = [], set()
    truncated = False

    def append(left, right, method, evidence):
        nonlocal truncated
        key = tuple(sorted((left, right)))
        if key in seen:
            return
        if len(links) >= MAX_PROPOSED_LINKS:
            truncated = True
            return
        seen.add(key)
        links.append({"id": "link-" + _stable(key, method),
                      "left_record_id": left, "right_record_id": right,
                      "method": method, "relation": "candidate_same_event", "state": "proposed",
                      "evidence": evidence,
                      "reason": _bi("Review the supporting records before confirming a relationship; this proposal does not merge incidents.",
                                    "راجع السجلات الداعمة قبل تأكيد العلاقة؛ لا يدمج هذا المقترح الوقائع.")})

    for result in reconciliation["records"]:
        for target in result["matched_record_ids"]:
            append(result["record_id"], target, "exact_identifier",
                   {"sr_id": _value(by_id[result["record_id"]], "sr_id"),
                    "basis": "exact identifier equality, not incident identity"})
    index = defaultdict(list)
    reference_sources = set(reconciliation["comparison_scope"]["source_ids"])
    for record in records:
        if (record["grain"] != "mms_work_order"
                or _display(record.get("source_id")) not in reference_sources):
            continue
        observed, location = _record_date(record), _value(record, "location")
        if observed and location:
            index[(observed, " ".join(location.casefold().split()))].append(record)
    for record in records:
        if (record["grain"] not in {"occ_event", "sr_reconciliation"}
                or record["id"] not in selected_ids):
            continue
        observed, location = _record_date(record), _value(record, "location")
        if not observed or not location:
            continue
        for delta in (-1, 0, 1):
            bucket = index.get((observed + timedelta(days=delta), " ".join(location.casefold().split())), [])
            for other in bucket:
                if len(links) >= MAX_PROPOSED_LINKS:
                    truncated = True
                    break
                left_sr, right_sr = _value(record, "sr_id"), _value(other, "sr_id")
                if left_sr and right_sr and left_sr != right_sr:
                    continue  # Never let a heuristic overrule contradictory exact IDs.
                left_terms = set(WORDS.findall(_value(record, "symptom").casefold()))
                right_terms = set(WORDS.findall(_value(other, "symptom").casefold()))
                overlap = sorted(left_terms & right_terms)
                if delta and len(overlap) < 2:
                    continue
                append(record["id"], other["id"], "date_location",
                       {"recorded_dates": [observed.isoformat(), _record_date(other).isoformat()],
                        "date_difference_days": abs(delta), "location": location,
                        "shared_symptom_terms": overlap[:10], "heuristic": True})
            if truncated:
                break
        if truncated:
            break
    return links, truncated


def _chart(records, field, grain, calc_id):
    population = [r for r in records if r["grain"] == grain]
    grouped, missing = defaultdict(list), []
    for record in population:
        value = _record_date(record) if field == "event_date" else _value(record, field)
        if not value:
            missing.append(record["id"])
        else:
            label = value.strftime("%Y-%m") if field == "event_date" else value
            grouped[label].append(record["id"])
    observed_count = sum(len(ids) for ids in grouped.values())
    items = sorted(grouped.items()) if field == "event_date" else sorted(grouped.items(), key=lambda i: (-len(i[1]), i[0]))
    cumulative = 0
    table = []
    for label, ids in items:
        cumulative += len(ids)
        table.append({"label": label, "value": len(ids), "record_ids": ids,
                      "numerator": len(ids), "denominator": observed_count,
                      "share": len(ids) / observed_count if observed_count else None,
                      "cumulative_share": cumulative / observed_count if observed_count else None})
    titles = {"location": _bi("Recorded issues by location", "الوقائع المسجلة حسب الموقع"),
              "category": _bi("Recorded issues by source category", "الوقائع المسجلة حسب فئة المصدر"),
              "event_date": _bi("Observed monthly event history", "التاريخ الشهري للوقائع المرصودة")}
    return {"id": "recorded-" + field, "title": titles[field],
            "question": _bi("How are the selected source records distributed?", "كيف تتوزع سجلات المصدر المحددة؟"),
            "kind": "line" if field == "event_date" else "bar", "grain": grain,
            "unit": "records", "table": table, "denominator": observed_count,
            "population_records": len(population), "missing_records": len(missing),
            "missing_record_ids": missing, "calculation_id": calc_id,
            "interpretation": "Counts of this record grain only. Missing months are not measured zero events."}


def _recurrence(records, grain):
    groups = defaultdict(list)
    for record in records:
        if record["grain"] != grain:
            continue
        symptom, location = _value(record, "symptom"), _value(record, "location")
        if symptom and location:
            groups[(symptom, location)].append(record["id"])
    return [{"id": "recurrence-" + _stable(grain, symptom, location),
             "grain": grain, "symptom_label": symptom, "location": location,
             "count": len(ids), "record_ids": ids, "state": "candidate",
             "interpretation": _bi("Repeated recorded wording and location; not a verified repeat failure or root cause.",
                                   "تكرار صياغة العَرَض والموقع في السجلات؛ وليس إثباتًا لعطل متكرر أو سبب جذري.")}
            for (symptom, location), ids in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0]))
            if len(ids) > 1]


def _overdue(records, as_of):
    result, counters = [], Counter()
    for record in records:
        if record["grain"] not in DETAIL_GRAINS:
            continue
        event, due = _record_date(record), _record_date(record, "due_date")
        value = record["fields"].get("outstanding_status")
        known_status = None
        if _field_state(record, "outstanding_status") in RECORDED_STATES:
            known_status = value if isinstance(value, bool) else {
                "true": True, "false": False, "outstanding": True, "not_outstanding": False,
            }.get(_display(value).casefold())
        assessed = due is not None and known_status is not None
        overdue = (known_status and due < as_of) if assessed else None
        counters["overdue" if overdue else "not_overdue" if assessed else "unassessable"] += 1
        result.append({"record_id": record["id"],
                       "age_since_event_days": (as_of - event).days if event and event <= as_of else None,
                       "overdue": overdue, "due_date": due.isoformat() if due else None,
                       "outstanding_status": known_status,
                       "due_date_basis": _value(record, "due_date_basis") or ("recorded due_date field" if due else None),
                       "reason": None if assessed else "A validated recorded due date and explicit outstanding status are both required."})
    return {"as_of": as_of.isoformat(), "records": result,
            "overdue": counters["overdue"], "not_overdue": counters["not_overdue"],
            "unassessable": counters["unassessable"],
            "interpretation": "Event age is independent of overdue work. No procedural deadline is supplied or inferred."}


def _readiness():
    inputs = {
        "mtbf": ("MTBF", "متوسط الزمن بين الأعطال", [
            ("Operating exposure for the complete covered asset population, including units without failures", "التعرض التشغيلي لكامل الأصول المشمولة، بما فيها الأصول دون أعطال"),
            ("Validated failure events, stable asset identity and reporting coverage", "وقائع أعطال متحقق منها وهوية أصول مستقرة وتغطية التقارير")]),
        "mttr": ("MTTR", "متوسط زمن الاستعادة", [
            ("Validated failure/restoration intervals and the agreed restoration or active-repair definition", "فترات أعطال واستعادة متحقق منها وتعريف متفق عليه للاستعادة أو الإصلاح الفعلي"),
            ("Applicable failure population and missing-interval coverage", "مجتمع الأعطال المنطبق وتغطية الفترات المفقودة")]),
        "availability": ("Availability", "الإتاحة", [
            ("An approved availability definition and planned/required exposure", "تعريف إتاحة معتمد والتعرض المخطط أو المطلوب"),
            ("Validated downtime intervals, overlap treatment and population coverage", "فترات توقف متحقق منها ومعالجة التداخل وتغطية المجتمع")]),
        "failure_probability": ("Failure probability", "احتمال العطل", [
            ("A validated target and prediction horizon with time-available features", "هدف متحقق منه وأفق تنبؤ وخصائص متاحة وقت القرار"),
            ("Exposure, censoring, stable asset histories and independent outcome labels", "التعرض والمشاهدات المراقبة وتواريخ أصول مستقرة وتسميات نتائج مستقلة")]),
        "remaining_useful_life": ("Remaining useful life", "العمر النافع المتبقي", [
            ("Validated asset configuration and longitudinal degradation/failure histories", "تكوين أصول متحقق منه وسجل زمني للتدهور والأعطال"),
            ("Operating exposure, censoring and a defined end-of-life criterion", "التعرض التشغيلي والمشاهدات المراقبة ومعيار محدد لنهاية العمر")]),
        "aed_loss": ("AED loss", "الخسارة بالدرهم", [
            ("Approved cost assumptions, currency and attribution rules", "افتراضات تكلفة وعملة وقواعد إسناد معتمدة"),
            ("Validated service-impact quantities and units without overlapping double counts", "كميات أثر خدمة ووحدات متحقق منها دون عد مزدوج للتداخل")]),
    }
    validation = [
        _bi("Require time-respecting validation and suitable asset/group separation.", "يلزم تحقق يحترم الزمن وفصل ملائم للأصول أو المجموعات."),
        _bi("Check leakage, suitable baselines, sample sizes and uncertainty; keep weak models visibly weak.", "افحص تسرب المعلومات وخطوط الأساس وحجم العينة وعدم اليقين؛ وأبقِ ضعف النموذج ظاهرًا."),
        _bi("Predictions do not authorise maintenance or safety decisions.", "التنبؤات لا تمنح صلاحية اتخاذ قرارات الصيانة أو السلامة."),
    ]
    return [{"id": key, "label": _bi(en, ar), "available": False, "state": "unavailable",
             "missing_inputs": [_bi(a, b) for a, b in required],
             "reason": _bi("This record extract alone does not establish the required measurement contract and validated inputs.",
                           "هذا المستخرج وحده لا يثبت عقد القياس والمدخلات المتحقق منها المطلوبة."),
             "needed_validation": validation} for key, (en, ar, required) in inputs.items()]


def _priority(key, finding, ids, calculation_ids, implication, uncertainty, action, owner, closure):
    return {"id": "priority-" + key, "finding": finding,
            "evidence": {"record_ids": sorted(set(ids)), "calculation_ids": calculation_ids},
            "management_implication": implication, "uncertainty": uncertainty,
            "proposed_action": action, "owner_role": owner, "owner_is_suggested": True,
            "due_date": None, "due_date_basis": _bi("Suggested follow-up; management must confirm an applicable owner and deadline. No default SR/ORP deadline is inferred.",
                                                    "متابعة مقترحة؛ على الإدارة اعتماد المسؤول والموعد المنطبقين. لا يُفترض موعد افتراضي لـ SR/ORP."),
            "closure_evidence": closure, "status": "proposed"}


def _priorities(selected, conflicts, reconciliation, completeness, recurrence, calc_ids):
    priorities = []
    if conflicts:
        ids = [i for c in conflicts for i in c["record_ids"]]
        priorities.append(_priority(
            "conflicts", _bi(f"{len(conflicts)} date/location conflict groups require review.", f"تحتاج {len(conflicts)} مجموعات اختلاف في التاريخ أو الموقع إلى مراجعة."), ids, [calc_ids["conflict_count"]],
            _bi("Record relationships cannot safely resolve incident identity while the reported values differ.", "لا يمكن حسم هوية الوقائع بأمان ما دامت القيم المسجلة مختلفة."),
            _bi("Different work orders or reporting versions may explain an apparent conflict.", "قد تفسر أوامر عمل أو نسخ تقارير مختلفة الاختلاف الظاهر."),
            _bi("Review the original records and record a confirmed or rejected link without overwriting the sources.", "راجع السجلات الأصلية وسجّل تأكيد العلاقة أو رفضها دون تغيير المصادر."),
            _bi("Maintenance investigation lead", "مسؤول تحقيقات الصيانة"),
            _bi("Source-row review, agreed date/location interpretation and a recorded link decision.", "مراجعة صفوف المصدر وتفسير متفق عليه للتاريخ والموقع وقرار علاقة مسجل.")))
    unexplained = [r for r in reconciliation["records"]
                   if r["source_label_comparison_source"] is None
                   or r["calculated_match"] != "matched_in_uploaded_mms"]
    if unexplained:
        priorities.append(_priority(
            "reconciliation", _bi(f"{len(unexplained)} reconciliation records have an unresolved comparison basis or match.", f"لدى {len(unexplained)} سجلات تسوية أساس مقارنة أو مطابقة غير محسوم."),
            [r["record_id"] for r in unexplained], [calc_ids["unresolved_reconciliation_count"]],
            _bi("The source label and the uploaded-reference match answer different questions.", "تجيب تسمية المصدر والمطابقة مع النسخة المرفوعة عن سؤالين مختلفين."),
            _bi("The original comparison source may not have been supplied; absence from a reference is not a verified missing incident.", "قد لا يكون مصدر المقارنة الأصلي متاحًا؛ والغياب من مرجع لا يثبت واقعة مفقودة."),
            _bi("Identify the intended comparison source and review the proposed record links.", "حدّد مصدر المقارنة المقصود وراجع علاقات السجلات المقترحة."),
            _bi("Operational records custodian", "مسؤول السجلات التشغيلية"),
            _bi("Named versioned comparison source, reproducible matching criteria and reviewed links.", "مصدر مقارنة محدد النسخة ومعايير مطابقة قابلة للتكرار وعلاقات خضعت للمراجعة.")))
    gaps = [item for item in completeness if item["field"] in {"sr_id", "wo_id", "rca_evidence"}
            and item["record_ids_missing"]]
    if gaps:
        ids = sorted({i for gap in gaps for i in gap["record_ids_missing"]})
        priorities.append(_priority(
            "evidence", _bi(f"{len(ids)} source records have an identifier or recorded RCA-evidence gap.", f"توجد فجوة معرف أو دليل RCA مسجل في {len(ids)} سجل مصدر."), ids, [calc_ids["evidence_gap_count"]],
            _bi("Recorded completion status alone cannot establish verified RCA or engineering closure.", "حالة الإنجاز المسجلة وحدها لا تثبت التحقق من RCA أو الإغلاق الهندسي."),
            _bi("Evidence may exist outside this extract; field presence is not a compliance assessment.", "قد توجد الأدلة خارج هذا المستخرج؛ ووجود الحقل لا يثبت الامتثال."),
            _bi("Locate the supporting records, resolve placeholder meanings and document the review outcome.", "اعثر على السجلات الداعمة واحسم معاني القيم النائبة ووثّق نتيجة المراجعة."),
            _bi("Maintenance records and RCA coordinator", "منسق سجلات الصيانة وتحليل الأسباب الجذرية"),
            _bi("Traceable identifiers, an authorised RCA/evidence reference and documented acceptance.", "معرفات قابلة للتتبع ومرجع RCA أو دليل مصرح به وقبول موثق.")))
    if len(priorities) < 3 and recurrence:
        item = recurrence[0]
        priorities.append(_priority(
            "recurrence", _bi(f"{item['count']} records repeat one symptom/location description.", f"تكرر {item['count']} سجلات وصف عَرَض وموقع واحد."), item["record_ids"], [calc_ids["recurrence_top_count"]],
            _bi("This is an investigation lead, not evidence of a failure rate or a root cause.", "هذا مسار للتحقيق، وليس دليلًا على معدل أعطال أو سبب جذري."),
            _bi("Repeated wording, duplicate reporting or multiple work orders may explain the pattern.", "قد تفسر النمط صياغة متكررة أو تقارير مكررة أو أوامر عمل متعددة."),
            _bi("Check the distinct events and supporting engineering evidence before recommending an intervention.", "تحقق من الوقائع المميزة والأدلة الهندسية قبل اقتراح تدخل."),
            _bi("Maintenance investigation lead", "مسؤول تحقيقات الصيانة"),
            _bi("Reviewed incident links, physical asset identity and independent engineering findings.", "علاقات وقائع خضعت للمراجعة وهوية أصول فعلية ونتائج هندسية مستقلة.")))
    if selected and len(priorities) < 3:
        priorities.append(_priority(
            "readiness", _bi("Reliability and predictive measures remain unavailable from this extract alone.", "تظل مقاييس الموثوقية والتنبؤ غير متاحة من هذا المستخرج وحده."),
            [r["id"] for r in selected if r["grain"] in DETAIL_GRAINS], [calc_ids["record_count"]],
            _bi("Historical record counts cannot support maintenance intervals, failure probabilities or claimed savings.", "أعداد السجلات التاريخية لا تسند فترات صيانة أو احتمالات أعطال أو وفورات مدعاة."),
            _bi("Operating exposure, validated outcomes and approved measurement/cost definitions have not been established by this calculation.", "لم يثبت هذا الحساب التعرض التشغيلي والنتائج المتحقق منها وتعريفات القياس أو التكلفة المعتمدة."),
            _bi("Agree the measurement contract and gather the missing inputs before evaluating a model.", "اتفق على عقد القياس واجمع المدخلات الناقصة قبل تقييم نموذج."),
            _bi("Reliability engineering and data governance leads", "مسؤولو هندسة الموثوقية وحوكمة البيانات"),
            _bi("Approved definitions, exposure/interval data, target and timing review, and an independent baseline evaluation.", "تعريفات معتمدة وبيانات تعرض وفترات ومراجعة الهدف وتوقيت البيانات وتقييم مستقل لخط الأساس.")))
    return priorities[:3]


def analyse_records(records, *, source_versions=None, filters=None, language="en", calculated_at=None):
    """Compute one auditable snapshot without mutating or merging source rows."""
    all_records = _prepare(records)
    if filters is not None and not isinstance(filters, dict):
        raise ValueError("filters must be an object")
    filters = dict(filters or {})
    language = "ar" if str(language).lower().startswith("ar") else "en"
    timestamp = calculated_at or datetime.now(timezone.utc).isoformat()
    if not isinstance(timestamp, str):
        raise ValueError("calculated_at must be an ISO date or timestamp")
    as_of = _date(timestamp)
    if as_of is None:
        raise ValueError("calculated_at must be an ISO date or timestamp")
    if source_versions is None:
        version_pairs = sorted({(_display(r.get("source_id")), _display(r.get("source_sha")))
                                for r in all_records})
        source_versions = [{"source_id": source, "source_sha": sha} for source, sha in version_pairs]
    versions = _source_versions(source_versions)
    selected, exclusions, period = _select(all_records, filters)
    groups = {grain: [r for r in selected if r["grain"] == grain] for grain in GRAINS}
    counts = {grain: len(group) for grain, group in groups.items()}
    input_fingerprint = _stable([
        {k: r.get(k) for k in ("id", "source_id", "source_sha", "grain", "fields", "field_states", "value_states")}
        for r in all_records])
    calculation_id = "rmd-" + _stable(CALCULATION_VERSION, versions, input_fingerprint,
                                     [r["id"] for r in selected], filters)
    calc_ids = {key: calculation_id + "-" + key.replace("_", "-") for key in
                ("record_count", "reconciliation_count", "conflict_count",
                 "unresolved_reconciliation_count", "evidence_gap_count", "recurrence_top_count")}
    selected_dates = [_record_date(r) for r in selected if r["grain"] in DETAIL_GRAINS]
    valid_dates = [d for d in selected_dates if d is not None]
    coverage = {"input_records": len(all_records), "selected_records": len(selected),
                "selected_detail_records": sum(counts[g] for g in DETAIL_GRAINS),
                "summary_records": counts["summary"], "records_with_validated_dates": len(valid_dates),
                "records_without_validated_dates": len(selected_dates) - len(valid_dates),
                "observed_from": min(valid_dates).isoformat() if valid_dates else None,
                "observed_to": max(valid_dates).isoformat() if valid_dates else None,
                "reporting_coverage_verified": False, "exclusions": exclusions,
                "source_totals_by_grain": {g: sum(1 for r in all_records if r["grain"] == g) for g in GRAINS}}
    completeness = _completeness(groups)
    reconciliation = _reconciliation(selected, all_records, filters)
    conflicts = _conflicts(selected)
    # The reference may include rows excluded by a display/date filter.
    selected_ids = {r["id"] for r in selected}
    links, links_truncated = _proposed_links(all_records, reconciliation, selected_ids)
    chart_grain = filters.get("chart_grain")
    if chart_grain is not None and chart_grain not in DETAIL_GRAINS:
        raise ValueError("chart_grain must be a detailed operational record grain")
    chart_grain = chart_grain or next((g for g in ("occ_event", "sr_reconciliation", "mms_work_order") if counts[g]), "occ_event")
    charts = [_chart(selected, field, chart_grain, calculation_id + "-" + field)
              for field in ("location", "category", "event_date")]
    for chart in charts:
        field = chart["id"].removeprefix("recorded-")
        grouping = "year_month(validated event_date)" if field == "event_date" else field
        chart.update({"formula": "count(selected " + chart_grain + " source rows grouped by " + grouping + ")",
                      "population": {"grain": chart_grain, "records": counts[chart_grain],
                                     "record_ids": [r["id"] for r in groups[chart_grain]]},
                      "period": period, "coverage": coverage,
                      "exclusions": {**exclusions, "unavailable_grouping_field": chart["missing_records"]},
                      "missing_policy": "Rows lacking the grouping field are reported as excluded; month gaps are not filled with measured zeros.",
                      "source_versions": versions, "calculation_version": CALCULATION_VERSION})
    recurrence = _recurrence(selected, chart_grain)
    kpis = []
    titles = {"mms_work_order": _bi("MMS source rows", "صفوف مصدر MMS"),
              "occ_event": _bi("OCC event source rows", "صفوف مصدر وقائع OCC"),
              "sr_reconciliation": _bi("Reconciliation source rows", "صفوف مصدر التسوية"),
              "summary": _bi("Summary source rows", "صفوف مصدر الملخص"),
              "other": _bi("Other source rows", "صفوف المصادر الأخرى")}
    for grain in GRAINS:
        ids = [r["id"] for r in groups[grain]]
        kpis.append({"id": grain + "_record_count", "calculation_id": calculation_id + "-" + grain + "-count",
                     "title": titles[grain], "value": len(ids), "unit": "records", "grain": grain,
                     "question": _bi("How many selected source rows are in this record population?", "كم عدد صفوف المصدر المحددة في هذا المجتمع؟"),
                     "formula": "count(selected source rows with grain == " + grain + ")",
                     "population": {"grain": grain, "records": len(ids), "record_ids": ids},
                     "numerator": len(ids), "denominator": None, "period": period,
                     "coverage": coverage, "missing_policy": "Count source rows; do not infer unique incidents. Summary rows are a separate population.",
                     "exclusions": exclusions, "calculation_version": CALCULATION_VERSION,
                     "source_versions": versions, "evidence_record_ids": ids})
    detail_ids = [r["id"] for r in selected if r["grain"] in DETAIL_GRAINS]
    unexplained_ids = [r["record_id"] for r in reconciliation["records"]
                       if r["source_label_comparison_source"] is None
                       or r["calculated_match"] != "matched_in_uploaded_mms"]
    gap_ids = sorted({i for item in completeness if item["field"] in {"sr_id", "wo_id", "rca_evidence"}
                      for i in item["record_ids_missing"]})
    conflict_ids = sorted({i for item in conflicts for i in item["record_ids"]})
    calculation_specs = [
        ("record_count", len(detail_ids), "records", detail_ids, "count(selected detailed source rows; summary and other grains excluded)"),
        ("reconciliation_count", counts["sr_reconciliation"], "records", [r["id"] for r in groups["sr_reconciliation"]], "count(selected sr_reconciliation source rows)"),
        ("conflict_count", len(conflicts), "conflict_groups", conflict_ids, "count(unresolved SR groups with differing recorded dates or locations; one group per field)"),
        ("unresolved_reconciliation_count", len(unexplained_ids), "records", unexplained_ids, "count(selected reconciliation rows whose original comparison source is unstated OR whose uploaded MMS match is not established)"),
        ("evidence_gap_count", len(gap_ids), "records", gap_ids, "count(distinct selected record IDs with an unresolved required SR/WO/RCA-evidence field)"),
        ("recurrence_top_count", recurrence[0]["count"] if recurrence else 0, "records", recurrence[0]["record_ids"] if recurrence else [], "count(source rows in the largest repeated exact symptom/location group for the chart grain)"),
    ]
    calculations = list(kpis)
    for key, value, unit, ids, formula in calculation_specs:
        calculations.append({"id": key, "calculation_id": calc_ids[key], "value": value,
                             "unit": unit, "formula": formula,
                             "question": _bi("What recorded evidence supports this finding?", "ما الأدلة المسجلة التي تسند هذه النتيجة؟"),
                             "population": {"grain": "explicit_formula_population", "records": len(ids), "record_ids": ids},
                             "numerator": value, "denominator": None, "period": period,
                             "coverage": coverage, "missing_policy": "Unresolved values are counted only as the formula explicitly states; none become measured zero.",
                             "exclusions": exclusions, "source_versions": versions,
                             "calculation_version": CALCULATION_VERSION, "evidence_record_ids": ids})
    calculations.extend(charts)
    limitations = [
        _bi("Source-row, OCC-event, SR, work-order and canonical-incident populations are different; a source-record sum is not a unique-incident count.",
            "تختلف مجتمعات صف المصدر وواقعة OCC وSR وأمر العمل والواقعة الموحدة؛ ومجموع السجلات ليس عدد وقائع فريدة."),
        _bi("CLOSE and COMP remain recorded source codes; neither proves verified RCA or complete engineering closure.",
            "تظل CLOSE وCOMP رمزين مسجلين في المصدر؛ ولا يثبت أي منهما التحقق من RCA أو الإغلاق الهندسي الكامل."),
        _bi("Observed counts do not establish failure rates, deterioration, causal effects or complete reporting coverage.",
            "الأعداد المرصودة لا تثبت معدلات أعطال أو تدهورًا أو أثرًا سببيًا أو اكتمال تغطية التقارير."),
        _bi("Service disruption, train delay, headway and accumulated delay are different measures; no service-impact total is inferred from narratives.",
            "انقطاع الخدمة وتأخر القطارات والتقاطر والتأخير المتراكم مقاييس مختلفة؛ ولا يُستنتج مجموع أثر الخدمة من السرد."),
        _bi("Placeholder states require field-specific interpretation; unknown, not applicable, not measured and measured zero are not interchangeable.",
            "تتطلب القيم النائبة تفسيرًا لكل حقل؛ ولا تتكافأ الحالات غير المعلومة وغير المنطبقة وغير المقاسة والصفر المقاس."),
    ]
    return {"calculation_id": calculation_id, "calculation_version": CALCULATION_VERSION,
            "calculated_at": timestamp, "language": language,
            "source_versions": versions, "filters": filters, "period": period,
            "scope": {"record_ids": [r["id"] for r in selected],
                      "source_ids": sorted({_display(r.get("source_id")) for r in selected}),
                      "chart_grain": chart_grain},
            "coverage": coverage, "counts_by_grain": counts,
            "status_distributions": {grain: _group_counts(groups[grain], "wo_status") for grain in DETAIL_GRAINS},
            "completeness": completeness, "reconciliation": reconciliation,
            "relationships": _relationships(selected), "conflicts": conflicts,
            "proposed_links": links, "proposed_links_truncated": links_truncated,
            "proposal_limit": MAX_PROPOSED_LINKS,
            "charts": charts, "recurrence": recurrence,
            "age_and_due_date_review": _overdue(selected, as_of),
            "readiness": _readiness(), "kpis": kpis, "calculations": calculations,
            "evidence_index": {r["id"]: _loc(r) for r in all_records},
            "priorities": _priorities(selected, conflicts, reconciliation, completeness, recurrence, calc_ids),
            "limitations": limitations,
            "investigation_registers_require_authorisation": True}
