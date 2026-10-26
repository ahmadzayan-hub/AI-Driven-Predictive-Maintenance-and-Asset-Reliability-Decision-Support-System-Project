"""Owner-scoped, snapshot-bound aggregate chat. No model, code or SQL execution."""
import copy
import hashlib
import json
import math
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from server import query
from server.executive import currency_of
from server.maintenance import contract, kpis
from server.runs import TableNotReady

Metric = Literal["maintenance_cost", "production_loss", "failure_count", "availability",
                 "utilisation", "mtbf", "mttr", "overdue_rate", "first_time_fix",
                 "sla_attainment", "loss_per_record", "loss_to_maintenance_ratio",
                 "loss_per_downtime_hour", "cost_per_operating_hour", "asset_age_summary"]


class DataQueryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metrics: list[Metric] = Field(min_length=1, max_length=6)
    asset_class: Literal["railway_signaling"] | None = None


class DataContextIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str | None = Field(default=None, min_length=1, max_length=64)
    filters: list[dict] = Field(default_factory=list, max_length=query.MAX_FILTERS)


MESSAGES = {
    "selection_required": ("Choose a report in Data for this chat first. I will not use a different or newest report automatically.", "اختر تقريراً من بيانات هذه المحادثة أولاً. لن أستخدم تقريراً آخر أو أحدث تقرير تلقائياً."),
    "unavailable": ("This report or its source is unavailable to this session owner. Choose an accessible completed analysis.", "هذا التقرير أو مصدره غير متاح لمالك هذه الجلسة. اختر تحليلاً مكتملاً متاحاً لك."),
    "stale": ("The selected source or analysis changed. Select the report again to review its current scope before asking.", "تغير المصدر أو التحليل المحدد. أعد اختيار التقرير لمراجعة نطاقه الحالي قبل السؤال."),
    "too_large": ("This analysis exceeds the bounded chat limit. Use the dashboard for this scope.", "يتجاوز هذا التحليل حدود الاستعلام في المحادثة. استخدم لوحة البيانات لهذا النطاق."),
    "invalid_request": ("Invalid data query or filters. Only the listed aggregate operations are supported.", "الاستعلام أو المرشحات غير صالحة. تتاح عمليات التجميع المحددة فقط."),
    "unsupported_question": ("I cannot safely calculate that question yet. Try total maintenance cost, production loss, recorded failures or availability. Results use only the explicitly selected scope; change its filters through the data-context API. No personal memory or model guess is used.", "لا أستطيع حساب هذا السؤال بأمان بعد. جرّب إجمالي تكلفة الصيانة أو خسائر الإنتاج أو عدد الأعطال المسجلة أو الإتاحة. تستخدم النتائج النطاق المحدد صراحةً فقط؛ يمكن تعديل مرشحاته عبر واجهة سياق البيانات. لا أستخدم الذاكرة الشخصية أو تخمين النموذج."),
}


class DataChatError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def text_for(code, language):
    return MESSAGES[code][1 if language == "ar" else 0]


def question_metrics(text, selected=False):
    """Small bilingual grammar; decline scope/forecast requests instead of guessing."""
    normal = re.sub(r"[\u064b-\u065f\u0670]", "", text).casefold().strip()
    if re.match(r"^(remember that|save this note|analyse |analyze |explain (the )?(latest )?report|تذكر أن|احفظ ملاحظة|حلل |اشرح التقرير)", normal):
        return None
    data_words = re.search(r"\b(data|dataset|report|csv|kpi|railway|signalling|signaling)\b|بيانات|داتا|تقرير|مؤشرات|عمر", normal)
    if selected and re.search(r"\b(costs?|losses?|failures?|age)\b|تكلفة|تكاليف|خسائر|أعطال|اعطال", normal):
        data_words = True
    patterns = (
        ("asset_age_summary", r"railway signal[li]*ng (?:asset )?age|age (?:of |for )?railway signal[li]*ng|asset[_ ]age(?:[_ ]years)?|عمر\s+(?:إشارات|اشارات)|أعمار الأصول|اعمار الاصول"),
        ("loss_to_maintenance_ratio", r"loss.{0,10}maintenance.{0,5}ratio|نسبة الخسائر.*الصيانة"),
        ("loss_per_downtime_hour", r"loss per downtime hour|خسائر.*ساعة توقف"),
        ("cost_per_operating_hour", r"cost per operating hour|تكلفة.*ساعة تشغيل"),
        ("loss_per_record", r"loss per record|خسائر.*لكل سجل"),
        ("maintenance_cost", r"maintenance cost|maintenance spend|تكلفة الصيانة|تكاليف الصيانة"),
        ("production_loss", r"production loss|خسائر الإنتاج|خسائر الانتاج|خسارة الإنتاج|خسارة الانتاج"),
        ("failure_count", r"recorded failures|failure count|how many failures|total failures|عدد الأعطال|عدد الاعطال"),
        ("availability", r"\bavailability\b|الإتاحة|الاتاحة|التوافر"),
        ("utilisation", r"\butili[sz]ation\b|نسبة الاستخدام|نسبة الاستغلال"),
        ("mtbf", r"\bmtbf\b|متوسط الوقت بين الأعطال|متوسط الوقت بين الاعطال"),
        ("mttr", r"\bmttr\b|متوسط وقت الإصلاح|متوسط وقت الاصلاح"),
        ("overdue_rate", r"overdue rate|نسبة أوامر العمل المتأخرة|نسبة اوامر العمل المتأخرة"),
        ("first_time_fix", r"first.time fix|الإصلاح من المرة الأولى|الاصلاح من المرة الاولى"),
        ("sla_attainment", r"service target met|sla attainment|تحقيق هدف الخدمة"),
    )
    matches = [(key, match) for key, pattern in patterns if (match := re.search(pattern, normal))]
    if not data_words and not matches:
        return None
    if re.search(r"\b(by|where|between|during|before|after|site|quarter|average|median|predict|forecast|tomorrow|next|why|not)\b|\b20\d{2}\b|حسب|خلال|موقع|الربع|توقع|تنبؤ|غدا|القادم|لماذا|لا تعرض", normal):
        return []
    remainder = normal
    for _, match in reversed(sorted(matches, key=lambda item: item[1].start())):
        remainder = remainder[:match.start()] + " " * (match.end() - match.start()) + remainder[match.end():]
    remainder = re.sub(r"\b(what|is|are|the|total|sum|how|many|much|show|me|and|in|my|our|selected|data|dataset|report|please|railway|signalling|signaling)\b", " ", remainder)
    remainder = re.sub(r"\b(كم|ما|هي|هو|اجمالي|إجمالي|مجموع|اعرض|أظهر|و|في|البيانات|الداتا|التقرير|المحدد|إشارات|اشارات|السكك|السكة|الحديدية)\b", " ", remainder)
    if matches and re.search(r"\w", remainder):
        return []  # unknown cohort/operation must not silently become a fleet total
    # Specific unit/ratio requests must not also emit overlapping cost/loss totals.
    keys, spans = [], []
    for key, match in matches:
        if any(start <= match.start() and match.end() <= end for start, end in spans):
            continue
        keys.append(key)
        spans.append(match.span())
    return keys[:6]


def natural_request(text, metrics):
    request = {"metrics": metrics}
    if re.search(r"railway signal[li]*ng|إشارات السكك|اشارات السكك|إشارات السكة|اشارات السكة", text, re.I):
        request["asset_class"] = "railway_signaling"
    return request


TOTALS = {
    "maintenance_cost": ("Maintenance cost", "تكلفة الصيانة", "Maintenance_Cost_USD", contract.MONEY),
    "production_loss": ("Production loss", "خسائر الإنتاج", "Production_Loss_USD", contract.MONEY),
    "failure_count": ("Recorded failures", "الأعطال المسجلة", "Failure_Count", "count"),
}


class DataChat:
    MAX_ROWS = 20_000
    MAX_SOURCE_BYTES = 8_000_000
    MAX_STORED_CHARS = 32_000_000

    def __init__(self, engine):
        self.engine = engine

    def _source(self, run_id, owner, principal):
        if principal is None or principal.subject != owner or not principal.can("read"):
            raise DataChatError("unavailable")
        store = self.engine.store
        run = store.get_run(run_id)
        if (not run or run.get("owner", "local-owner") != owner
                or store._exec("SELECT id FROM rmd_runs WHERE id = ?", (run_id,))):
            raise DataChatError("unavailable")
        if run.get("state") not in {"completed", "awaiting_approval"} or run.get("joins_json") not in (None, "", "[]"):
            # Joined-source provenance needs its own complete source ledger.
            raise DataChatError("unavailable")
        dataset = store.get_dataset(run.get("dataset_id"))
        if not dataset or dataset.get("owner") != owner:
            raise DataChatError("unavailable")
        content = dataset["content"].encode("utf-8")
        if len(content) > self.MAX_SOURCE_BYTES or (dataset.get("row_count") or 0) > self.MAX_ROWS:
            raise DataChatError("too_large")
        digest = hashlib.sha256(content).hexdigest()
        if digest != dataset["sha256"]:
            raise DataChatError("stale")
        try:
            _, stored, _ = self.engine.table_source(run_id)
        except (KeyError, ValueError, RuntimeError, TableNotReady):
            raise DataChatError("unavailable") from None
        if sum(len(value) for value in stored.values()) > self.MAX_STORED_CHARS:
            raise DataChatError("too_large")
        revision = hashlib.sha256()
        for name in sorted(stored):
            revision.update(name.encode())
            revision.update(stored[name].encode())
        revision.update(json.dumps([run.get("updated_at"), run.get("mapping_json"), digest]).encode())
        return run, dataset, stored, revision.hexdigest()

    def choices(self, owner, principal):
        if principal.subject != owner or not principal.can("read"):
            raise DataChatError("unavailable")
        return [{"run_id": run["id"], "dataset_name": run["dataset_name"], "state": run["state"]}
                for run in self.engine.list_runs(owner=owner)
                if run["state"] in {"completed", "awaiting_approval"}][:25]

    def bind(self, request, session, principal):
        if principal is None or principal.subject != session.owner or not principal.can("read"):
            raise DataChatError("unavailable")
        request = DataContextIn.model_validate(request)
        if request.run_id is None:
            if request.filters:
                raise DataChatError("invalid_request")
            return None
        if len(json.dumps(request.filters)) > 16_000:
            raise DataChatError("invalid_request")
        if any(set(item) - {"column", "op", "value", "values"} for item in request.filters):
            raise DataChatError("invalid_request")
        run, dataset, stored, revision = self._source(request.run_id, session.owner, principal)
        table = self.engine.load_table((run["id"], "data-chat", revision), stored)
        if len(table.rows) > self.MAX_ROWS or len(table.columns) > 200:
            raise DataChatError("too_large")
        try:
            selected, _ = query.filtered(table, request.filters)
        except query.QueryError:
            raise DataChatError("invalid_request") from None
        if self._source(run["id"], session.owner, principal)[3] != revision:
            raise DataChatError("stale")
        return {"run_id": run["id"], "dataset_id": dataset["id"], "dataset_name": run["dataset_name"],
                "source_sha256": dataset["sha256"], "analysis_revision": revision,
                "filters": copy.deepcopy(request.filters), "records": len(selected),
                "total_records": len(table.rows)}

    def answer(self, request, session, principal):
        language = session.agent.language()
        def tr(en, ar):
            return ar if language == "ar" else en
        try:
            selection = getattr(session, "data_context", None)
            if not selection:
                raise DataChatError("selection_required")
            run, dataset, stored, revision = self._source(selection["run_id"], session.owner, principal)
            if revision != selection["analysis_revision"] or dataset["id"] != selection["dataset_id"]:
                raise DataChatError("stale")
            if not request:
                raise DataChatError("unsupported_question")
            parsed = DataQueryIn.model_validate(request)
            table = self.engine.load_table((run["id"], "data-chat", revision), stored)
            filters = copy.deepcopy(selection["filters"])
            if parsed.asset_class:
                columns = [column for column in ("Asset_Class", "Asset_Type") if column in table.columns]
                if len(columns) != 1:
                    raise DataChatError("unsupported_question")
                column = columns[0]
                normalise = lambda value: re.sub(r"[\s_-]+", "", str(value)).casefold()
                aliases = {"railwaysignaling", "railwaysignalling", "إشاراتالسككالحديدية", "اشاراتالسككالحديدية", "إشاراتالسكةالحديدية", "اشاراتالسكةالحديدية"}
                values = sorted({row[table.columns.index(column)] for row in table.rows
                                 if normalise(row[table.columns.index(column)]) in aliases})
                if not values:
                    raise DataChatError("unsupported_question")
                filters.append({"column": column, "op": "in", "values": values})
            selected, _ = query.filtered(table, filters)
            if len(table.rows) > self.MAX_ROWS or len(table.columns) > 200:
                raise DataChatError("too_large")
            measures = []
            for key in dict.fromkeys(parsed.metrics):
                if key == "asset_age_summary":
                    if "Asset_Age_Years" not in table.columns:
                        measures.append({"key": key, "title": tr("Recorded age", "العمر المسجل"), "value": None,
                                         "reason": tr("Asset_Age_Years is unavailable.", "حقل Asset_Age_Years غير متاح.")})
                        continue
                    position = table.columns.index("Asset_Age_Years")
                    values = [row[position] for row in selected if type(row[position]) in (float, int)
                              and math.isfinite(row[position]) and row[position] >= 0]
                    n = len(values)
                    measures.append({"key": key, "title": tr("Mean recorded age (years)", "متوسط العمر المسجل (سنوات)"),
                        "value": math.fsum(value / n for value in values) if n else None,
                        "minimum": min(values) if n else None, "maximum": max(values) if n else None,
                        "records": n, "records_unmeasured": len(selected) - n, "scale": "years",
                        "formula": "mean/min/max/count(finite nonnegative Asset_Age_Years)",
                        "grain": "source records, not unique physical assets; identity unverified"})
                    continue
                total = TOTALS.get(key)
                measure = (kpis.Kpi(key, total[0], total[1], total[2], kpis.RECORDS,
                                   kpis.every_record, "all records", total[3],
                                   "Recorded total over measured records.") if total else kpis.REGISTER[key])
                needed = measure.source_columns
                if any(column not in table.columns for column in needed):
                    measures.append({"key": key, "title": tr(measure.title, measure.title_ar),
                                     "value": None, "reason": tr("Required columns are missing.", "الأعمدة المطلوبة غير متاحة.")})
                    continue
                positions = [(table.columns.index(column), column) for column in needed]
                rows = [{column: row[i] for i, column in positions} for row in selected]
                result = measure.compute(rows)
                result["title"] = tr(measure.title, measure.title_ar)
                if total:
                    result.update(value=result["numerator"] if result["records"] else None,
                                  denominator=None, formula=f"sum({total[2]})")
                if any(value is not None and not math.isfinite(value) for value in
                       (result.get("value"), result.get("numerator"), result.get("denominator"))):
                    raise DataChatError("invalid_request")
                measures.append(result)
            # Changes or ownership revocation during a query invalidate the answer.
            if self._source(run["id"], session.owner, principal)[3] != revision:
                raise DataChatError("stale")
            result = {**copy.deepcopy(selection), "filters": filters, "records": len(selected),
                      "currency": currency_of(run), "measures": measures,
                      "provenance": "deterministic_kpi_register", "llm_explanation": None}
            lines = [tr("Calculated from your selected analysis; no LLM contribution.", "حساب من التحليل الذي اخترته؛ دون مساهمة نموذج لغوي."),
                     f"{tr('Dataset', 'البيانات')}: {selection['dataset_name']} · {tr('Report', 'التقرير')}: {run['id']}",
                     f"{tr('Filters', 'المرشحات')}: {json.dumps(filters, ensure_ascii=False)}"]
            for item in measures:
                value = tr("undefined", "غير معرف") if item["value"] is None else format(item["value"], ".12g")
                suffix = "%" if item.get("scale") == contract.PERCENT else ""
                if item.get("scale") == contract.HOURS:
                    suffix = tr(" hours", " ساعة")
                lines.append(f"{item['title']}: {value}{suffix}")
                if "formula" in item:
                    lines.append(f"{item['formula']}; {tr('measured / unmeasured', 'مقاس / غير مقاس')}: {item['records']} / {item['records_unmeasured']}")
                    if item.get("denominator") is not None:
                        lines.append(f"{tr('Numerator / denominator', 'البسط / المقام')}: {item['numerator']:.12g} / {item['denominator']:.12g}")
                    if item["value"] is None:
                        lines.append(tr("Undefined because required measurements or a nonzero denominator are unavailable.", "غير معرف لعدم توفر القياسات المطلوبة أو مقام غير صفري."))
                    if item["key"] == "asset_age_summary":
                        low = item["minimum"] if item["minimum"] is not None else tr("undefined", "غير معرف")
                        high = item["maximum"] if item["maximum"] is not None else tr("undefined", "غير معرف")
                        lines.append(f"{tr('Minimum / maximum (years)', 'الحد الأدنى / الأعلى (سنوات)')}: {low} / {high}")
                        lines.append(tr("These are source-record observations, not verified unique physical assets. This is not the age of a single identified asset.", "هذه مشاهدات لسجلات المصدر وليست أصولاً مادية فريدة متحققاً منها. هذه ليست قيمة عمر أصل واحد محدد."))
                elif item.get("reason"):
                    lines.append(item["reason"])
            lines.extend([f"SHA-256: {dataset['sha256']}", f"{tr('Analysis revision', 'إصدار التحليل')}: {revision}",
                          tr("Recorded observations, not future failure probabilities. Currency: ", "مشاهدات مسجلة وليست احتمالات أعطال مستقبلية. العملة: ") + (currency_of(run) or tr("not declared", "غير محددة"))])
            return {"text": "\n".join(lines), "source": "rules", "action": "data_query", "result": result}
        except DataChatError as error:
            return {"text": text_for(error.code, language), "source": "rules", "action": "data_query", "why": error.code}
        except (ValueError, KeyError, TypeError):
            return {"text": text_for("invalid_request", language), "source": "rules", "action": "data_query", "why": "invalid_request"}
