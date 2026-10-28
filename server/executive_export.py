"""Offline business documents from an already authorized executive snapshot.

Both formats consume the same human-readable sections. No models, rows, network
requests, publishing, office applications or additional dependencies are used.
"""

from dataclasses import dataclass, field
from base64 import b64encode
from functools import partial
from html import escape
from io import BytesIO
import math
import re
import unicodedata
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from server.report_fonts import verified_font, obfuscate_font, FONT_KEY
from server.report_contract import model_audit
from server.maintenance import performance
from server.maintenance.kpis import POPULATION_AR, REGISTER


HTML_MIME = "text/html"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
CONTENT_POLICY = "default-src 'none'; style-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ET.register_namespace("w", W)
PERFORMANCE_COLORS = {"good": "0F7A55", "okay": "1D4ED8", "bad": "B3323F",
                      "unassessed": "475467", "unavailable": "667085"}


class StatusText(str):
    """Text plus a semantic tone, shared by the HTML and OOXML writers."""
    def __new__(cls, text, status):
        item = super().__new__(cls, text)
        item.status = status
        return item


def status_label(status, language):
    en, ar = {
        "good": ("Good", "جيد"), "okay": ("Okay", "مقبول"),
        "bad": ("Bad", "غير مرضٍ"),
        "unassessed": ("Not assessed", "غير مقيّم"),
        "unavailable": ("Unavailable", "غير متاح"),
    }[status]
    return ar if language == "ar" else en


def _clean(value):
    # XML 1.0 excludes control characters and unpaired JSON surrogates. Apply the
    # same normalization to HTML so the documents retain identical facts.
    return "".join(c if c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF
                   or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF
                   else "\ufffd" for c in str(value))


def _synopsis(value, limit):
    """Bound front-page prose only. Full facts remain in the following sections."""
    text = " ".join(_clean(value).split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0] + "…"


@dataclass
class Table:
    headers: tuple
    rows: list
    widths: tuple = (32, 68)
    caption: str = ""


@dataclass
class Section:
    title: str
    paragraphs: list = field(default_factory=list)
    tables: list = field(default_factory=list)
    page_break_before: bool = False
    compact: bool = False
    after_paragraphs: list = field(default_factory=list)
    after_title: str = ""
    # The "nothing to report" statement of a section that has no other
    # content. Such a section is left out of the document and named once
    # in the decision context (ADR 2026-10-27-interactive-dashboard).
    absent: str = ""

    def has_content(self):
        return (any(str(p).strip() for p in self.paragraphs + self.after_paragraphs)
                or any(table.rows for table in self.tables))

    def note_absence(self, text):
        """Keep an explicit statement beside real content; otherwise mark absent."""
        if self.has_content():
            self.paragraphs.append(text)
        else:
            self.absent = text


def report_sections(brief):
    """Common document model; figures are formatted, never recalculated."""
    ar = brief["language"] == "ar"

    def tr(en, arabic):
        return arabic if ar else en

    def value(item):
        if isinstance(item, StatusText):
            return item
        if item is None:
            return tr("Not available", "غير متاح")
        if isinstance(item, bool):
            return tr("Yes", "نعم") if item else tr("No", "لا")
        if isinstance(item, float):
            return format(item, ".12g") if math.isfinite(item) else tr("Not available", "غير متاح")
        if isinstance(item, (tuple, list)):
            return "; ".join(value(v) for v in item) or tr("None", "لا يوجد")
        if isinstance(item, dict):
            return "; ".join(f"{_clean(k)}: {value(v)}" for k, v in item.items()) or tr("None", "لا يوجد")
        return _clean(item)

    prop = (tr("Item", "البند"), tr("Recorded value", "القيمة المسجلة"))

    def properties(rows):
        return Table(prop, [(label, value(v)) for label, v in rows])

    def refs(item):
        return tr("Evidence references", "مراجع الأدلة") + ": " + value(item.get("evidence_refs", []))

    def labelled(code, options):
        """Translate known codes while keeping the original source available."""
        if code not in options:
            return code
        label = tr(*options[code])
        return label if label == code else f"{label} ({code})"

    states = {
        "queued": ("Queued", "في قائمة الانتظار"), "running": ("Running", "قيد التشغيل"),
        "awaiting_approval": ("Awaiting approval", "بانتظار الاعتماد"),
        "completed": ("Completed", "مكتمل"), "partially_completed": ("Partially completed", "مكتمل جزئياً"),
        "failed": ("Failed", "فشل"), "cancelled": ("Cancelled", "ملغى"),
    }
    scales = {
        "percent": ("Percent, 0–100", "نسبة مئوية، من 0 إلى 100"),
        "fraction": ("Fraction, 0–1", "نسبة كسرية، من 0 إلى 1"),
        "hours": ("Hours", "ساعات"), "money": ("Monetary units", "وحدات نقدية"),
        "ratio": ("Times (one total over another)", "مرات (مجموع على مجموع)"),
        "count": ("Count", "عدد"), "score": ("Score", "درجة"),
        "category": ("Category", "فئة"), "date": ("Date", "تاريخ"), "identifier": ("Identifier", "معرّف"),
    }
    # One list of population names, kept by the register itself.
    populations = {code: (code, arabic) for code, arabic in POPULATION_AR.items()}
    policies = {"exclude": ("Exclude unmeasured records", "استبعاد السجلات غير المقاسة"),
                "zero": ("Treat missing values as measured zero", "اعتبار القيم المفقودة أصفاراً مقاسة")}
    run, scope = brief["run"], brief["scope"]
    metadata = Section(tr("Metadata", "بيانات الموجز"), tables=[properties([
        (tr("Dataset", "مجموعة البيانات"), run["dataset_name"]),
        (tr("Run ID", "معرّف التشغيل"), run["id"]),
        (tr("Run state", "حالة التشغيل"), labelled(run.get("state"), states)),
        (tr("Snapshot updated", "آخر تحديث للقطة"), run.get("updated_at")),
        (tr("Source", "المصدر"), tr("Deterministic evidence engine", "محرك الأدلة الحتمي")),
        (tr("Readiness", "الجاهزية"), {"ready": tr("Ready for review", "جاهز للمراجعة"),
          "limited": tr("Limited evidence", "أدلة محدودة"), "empty": tr("Empty scope", "نطاق فارغ")}.get(brief["readiness"]["status"], brief["readiness"]["status"])),
    ])])
    selected = Section(tr("Scope and filters", "النطاق والمرشحات"), tables=[properties([
        (tr("Selected records", "السجلات المحددة"), scope["records"]),
        (tr("Total records", "إجمالي السجلات"), scope["total_records"]),
    ])])
    operators = {
        "eq": tr("equals", "يساوي"), "ne": tr("does not equal", "لا يساوي"),
        "in": tr("is one of", "إحدى القيم التالية"), "not_in": tr("is not one of", "ليس من القيم التالية"),
        "gt": tr("is greater than", "أكبر من"), "gte": tr("is at least", "أكبر من أو يساوي"),
        "lt": tr("is less than", "أصغر من"), "lte": tr("is at most", "أصغر من أو يساوي"),
        "between": tr("is between (inclusive)", "بين القيمتين (شاملاً الطرفين)"),
        "empty": tr("is empty", "فارغ"),
        "not_empty": tr("is not empty", "غير فارغ"),
    }
    if scope["filters"]:
        rows = []
        for item in scope["filters"]:
            op = item["op"]
            terms = "" if op in {"empty", "not_empty"} else value(item.get("values") if op in {"in", "not_in", "between"} else item.get("value"))
            rows.append((item["column"], operators.get(op, op), terms))
        selected.tables.append(Table((tr("Field", "الحقل"), tr("Condition", "الشرط"), tr("Selected values", "القيم المحددة")), rows, (30, 30, 40)))
    else:
        selected.paragraphs.append(tr("No filters; all cleaned records are selected.", "لا توجد مرشحات؛ يشمل النطاق جميع السجلات المنظفة."))
    summary = Section(tr("Decision context", "سياق القرار"), [brief["headline"],
        tr("This document supports qualified human review. Exporting does not approve or publish the run.",
           "يدعم هذا المستند المراجعة البشرية المؤهلة. لا يعني التصدير اعتماد التشغيل أو نشره.")])
    limitations = Section(tr("Decision boundaries and unresolved issues", "حدود القرار والمسائل غير المحسومة"), brief["readiness"]["limitations"])
    advisory = brief.get("advisory")
    scorecards, decisions_requested, readiness_sections, source_sections = [], [], [], []
    if advisory:
        summary.paragraphs = [advisory["role"], advisory["subtitle"], advisory["recommendation"], brief["headline"], summary.paragraphs[-1]]
        scorecard = Section(tr("Maintenance and reliability scorecard", "بطاقة أداء الصيانة والموثوقية"))
        scorecard.tables.append(Table((tr("Decision area", "مجال القرار"), tr("Observed measure", "المؤشر المرصود"), tr("Value / status", "القيمة / الحالة"), tr("Management implication", "الدلالة الإدارية")), [
            (item["title"], item["measure"] + "\n" + labelled(item["scale"], scales),
             StatusText(value(item["value"]) + " — " + status_label(item["status"], brief["language"]), item["status"]),
             item["implication"] + "\n" + item["reason"] + "\n" + refs(item)) for item in advisory["domains"]], (15, 23, 20, 42)))
        decisions = Section(tr("Decisions requested and accountable roles", "القرارات المطلوبة والأدوار المسؤولة"), [tr(
            "These are proposed review responsibilities, not assignments or approved interventions.",
            "هذه مسؤوليات مراجعة مقترحة وليست تكليفات أو تدخلات معتمدة.")])
        if advisory["decisions"]:
            decisions.tables.append(Table((tr("Recommended decision", "القرار المقترح"), tr("Proposed accountable role / gate", "الدور المسؤول المقترح / شرط القرار")), [
                (item["title"] + "\n" + item["action"] + "\n" + refs(item), item["owner"] + "\n" + item["gate"]) for item in advisory["decisions"]]))
        if not decisions.tables:
            decisions.paragraphs.append(tr("No evidence-linked intervention priority is available in this scope.", "لا تتوفر أولوية تدخل مرتبطة بالأدلة ضمن هذا النطاق."))
        prediction = Section(tr("Predictive maintenance readiness", "جاهزية الصيانة التنبؤية"), [advisory["prediction"]])
        sources = Section(tr("Analytical basis and source reconciliation", "الأساس التحليلي ومطابقة المصادر"), [advisory["new_findings"]])
        sources.tables.append(Table((tr("Required source", "المصدر المطلوب"), tr("Verification status", "حالة التحقق")), [
            (item["title"], status_label(item["status"], brief["language"]) + " — " + item["detail"]) for item in advisory["sources"]]))
        sources.paragraphs.extend([advisory["preservation"], advisory["escalation"]])
        scorecards, decisions_requested = [scorecard], [decisions]
        readiness_sections, source_sections = [prediction], [sources]
    targets = Section(tr("Configured display targets", "أهداف العرض المحددة"), [tr(
        "Colours compare measured values with targets configured for this run: green means good, blue okay, red needs attention. Grey means no target or unavailable evidence. Configured targets are not approved standards or engineering authorizations.",
        "تقارن الألوان القيم المقاسة بأهداف محددة لهذا التشغيل: الأخضر جيد، والأزرق مقبول، والأحمر يحتاج إلى متابعة. يعني الرمادي عدم تحديد هدف أو عدم توفر الأدلة. الأهداف المحددة ليست معايير معتمدة أو تفويضات هندسية.")])
    for key, rule in brief.get("kpi_policy", {}).get("rules", {}).items():
        fields = performance.BOUNDARIES[rule["direction"]]
        targets.tables.append(properties([
            (tr("Target measure", "مؤشر الهدف"), REGISTER[key].title_ar if ar else REGISTER[key].title),
            (tr("Metric key", "رمز المؤشر"), key),
            (tr("Target direction", "اتجاه الهدف"), {"higher": tr("Higher is better", "الأعلى أفضل"),
             "lower": tr("Lower is better", "الأقل أفضل"), "range": tr("Within range", "ضمن النطاق")}[rule["direction"]]),
            (tr("Scale", "مقياس القيمة"), labelled(rule["scale"], scales)),
            *[(tr({"good_at": "Good at", "okay_at": "Okay at", "good_min": "Good minimum", "good_max": "Good maximum",
                   "okay_min": "Okay minimum", "okay_max": "Okay maximum"}[name],
                  {"good_at": "حد الجيد", "okay_at": "حد المقبول", "good_min": "الحد الأدنى للجيد",
                   "good_max": "الحد الأعلى للجيد", "okay_min": "الحد الأدنى للمقبول", "okay_max": "الحد الأعلى للمقبول"}[name]), rule[name]) for name in fields],
            (tr("Target source", "مصدر الهدف"), rule["source_ref"]),
        ]))
    if not targets.tables:
        targets.paragraphs.append(tr("No display targets are configured for this run.", "لم تُحدد أهداف عرض لهذا التشغيل."))
    kpis = Section(tr("Controlled KPIs", "مؤشرات الأداء المنضبطة"), [tr(
        "KPIs cover the selected records. Excluded records are outside a measure's population; unmeasured records are inside it but lack required measurements. Displayed numbers use up to 12 significant digits.",
        "تغطي المؤشرات السجلات المحددة. تقع السجلات المستبعدة خارج مجموعة القياس؛ أما غير المقاسة فتقع داخلها وتفتقر إلى القياسات المطلوبة. تُعرض الأرقام بما يصل إلى 12 خانة معنوية.")])
    if brief["kpis"]["measures"]:
        kpis.tables.append(Table((tr("Measure", "المؤشر"), tr("Value", "القيمة"),
            tr("Scale", "مقياس القيمة"), tr("Measured records", "السجلات المقاسة")),
            [(measure["title"], StatusText(value(measure["value"]), measure.get("assessment", {}).get("status", "unassessed")), labelled(measure["scale"], scales),
              value(measure["records"])) for measure in brief["kpis"]["measures"]], (38, 20, 24, 18)))
    for measure in brief["kpis"]["measures"]:
        kpis.tables.append(properties([
            (tr("Measure", "المؤشر"), measure["title"]),
            (tr("Evidence ID", "معرّف الدليل"), "executive.kpi." + measure["key"]),
            (tr("Value", "القيمة"), StatusText(value(measure["value"]), measure.get("assessment", {}).get("status", "unassessed"))),
            (tr("Scale", "مقياس القيمة"), labelled(measure["scale"], scales)),
            (tr("Formula", "الصيغة"), measure["formula"]),
            (tr("Numerator", "البسط"), measure["numerator"]),
            (tr("Denominator", "المقام"), measure["denominator"]),
            (tr("Population", "مجموعة القياس"), labelled(measure["population"], populations)),
            (tr("Measured records", "السجلات المقاسة"), measure["records"]),
            (tr("Unmeasured records", "السجلات غير المقاسة"), measure["records_unmeasured"]),
            (tr("Excluded records", "السجلات المستبعدة"), measure["records_excluded"]),
            (tr("Missing-value policy", "سياسة القيم المفقودة"), labelled(measure["missing_policy"], policies)),
            (tr("Undefined value reason", "سبب عدم تحديد القيمة"), measure.get("undefined_reason")),
            (tr("Definition boundaries", "حدود التعريف"), measure.get("edge_cases")),
            (tr("Performance status", "حالة الأداء"), StatusText(
                status_label(measure.get("assessment", {}).get("status", "unassessed"), brief["language"]),
                measure.get("assessment", {}).get("status", "unassessed"))),
            (tr("Assessment reason", "سبب التقييم"), measure.get("assessment", {}).get("reason")),
            (tr("Target source", "مصدر الهدف"), measure.get("assessment", {}).get("source_ref")),
        ]))
    if brief["kpis"]["unavailable"]:
        kpis.tables.append(Table((tr("Unavailable measure", "المؤشر غير المتاح"), tr("Required evidence", "الأدلة المطلوبة")),
            [(key, value(reason)) for key, reason in brief["kpis"]["unavailable"].items()]))
    if not brief["kpis"]["measures"]:
        kpis.note_absence(tr("No controlled KPI is computable for this scope.", "لا يمكن حساب مؤشر أداء منضبط لهذا النطاق."))
    priorities = Section(tr("Review priorities", "أولويات المراجعة"))
    for item in brief["priorities"]:
        priorities.tables.append(properties([(tr("Priority", "الأولوية"), item["title"]),
            (tr("Review", "المراجعة"), item["detail"]), (tr("Evidence references", "مراجع الأدلة"), item["evidence_refs"])]))
    if not priorities.tables:
        priorities.note_absence(tr("No observed priority is identified in this scope.", "لم تُحدد أولوية مرصودة ضمن هذا النطاق."))
    questions = Section(tr("Decision questions", "أسئلة القرار"))
    for item in brief["questions"]:
        questions.paragraphs.extend([item["text"], refs(item)])
    if not questions.paragraphs:
        questions.note_absence(tr("No additional question is recorded.", "لا يوجد سؤال إضافي مسجل."))
    whole = tr("These stored findings and model evaluations describe the whole run. They were not recomputed or retrained for the selected filters and do not establish future failure or remaining useful life.",
               "تصف النتائج وتقييمات النماذج المخزنة التشغيل الكامل. لم تُعد حساباتها أو تدريبها وفق المرشحات المحددة، ولا تثبت الأعطال المستقبلية أو العمر المتبقي.")
    findings = Section(tr("Whole-run findings", "نتائج التشغيل الكامل"), [whole] if brief["findings"] else [])
    for item in brief["findings"]:
        findings.paragraphs.extend([item["text"], tr("Stage", "المرحلة") + ": " + value(item["stage"]), refs(item)])
    if not brief["findings"]:
        findings.note_absence(tr("No verified findings are available in this briefing.", "لا تتوفر نتائج متحقق منها في هذا الموجز."))
    models = Section(tr("Whole-run model evaluations", "تقييمات نماذج التشغيل الكامل"), [whole] if brief["models"] else [])
    for card in brief["models"]:
        # Plugin model cards can contain arbitrary payloads. Only known scalar
        # evaluation metadata belongs in a document; never copy nested raw data.
        allowed = {"verdict", "reason", "decision", "horizon", "beats_baseline_margin",
                   "clearly_above_chance", "positive_rate_held_out", "baseline_majority",
                   "baseline_best_rule", "baseline_rule_column", "groups",
                   "share_of_spread_explained", "separation", "period", "season_length"}
        saved_details = card.get("details") if isinstance(card.get("details"), dict) else {}
        details = {k: v for k, v in saved_details.items()
                   if k in allowed and (v is None or isinstance(v, (str, int, float, bool)))}
        unsupported = card.get("fitted") is False or details.get("verdict") == "not_supported"
        verdict = tr("Not fitted / unsupported", "غير مدرّب / غير مدعوم") if unsupported else (
            tr("Weak or below acceptance", "ضعيف أو دون حد القبول") if details.get("verdict") == "weak" or card.get("beats_baseline") is False
            else tr("Recorded evaluation; inspect its acceptance and limitations", "تقييم مسجل؛ راجع قبوله وحدوده"))
        rows = [(tr("Model", "النموذج"), card.get("title", card.get("kind"))),
                (tr("Target", "الهدف"), card.get("target")), (tr("Verdict", "التقييم"), verdict),
                (tr("Scope", "النطاق"), tr("Whole run", "التشغيل الكامل"))]
        if not unsupported:
            for key, en, arabic in (("metric", "Metric and baseline", "المقياس والخط المرجعي"),
                    ("train_records", "Training records", "سجلات التدريب"), ("test_records", "Test records", "سجلات الاختبار"),
                    ("split", "Evaluation split", "تقسيم التقييم"), ("inputs", "Inputs", "المدخلات"),
                    ("improvement", "Recorded improvement", "التحسن المسجل")):
                if key in card:
                    item = card[key]
                    if key in {"metric", "split"} and isinstance(item, dict):
                        keys = {"name", "model", "baseline", "baseline_name"} if key == "metric" else {"kind", "first_held_out"}
                        item = {k: v for k, v in item.items() if k in keys and (v is None or isinstance(v, (str, int, float, bool)))}
                    elif key == "inputs" and isinstance(item, list):
                        item = [v for v in item if isinstance(v, str)]
                    elif isinstance(item, (dict, list)):
                        continue
                    rows.append((tr(en, arabic), item))
        if details:
            rows.append((tr("Decision, horizon and limitations", "القرار والأفق والحدود"), details))
        rows.extend((item["label_ar" if ar else "label_en"], item["value"]) for item in model_audit(card))
        models.tables.append(properties(rows))
    if not brief["models"]:
        models.note_absence(tr("No model evaluation is available; predictive performance is not claimed.", "لا يتوفر تقييم نموذج؛ ولا يُدّعى وجود أداء تنبؤي."))
    evidence = Section(tr("Evidence appendix", "ملحق الأدلة"), [tr(
        "Every reference below is part of this snapshot. Filtered calculations and whole-run calculations have different scopes.",
        "كل مرجع أدناه جزء من هذه اللقطة. يختلف نطاق الحسابات المرشحة عن حسابات التشغيل الكامل.")])
    evidence.tables.append(Table((tr("Evidence ID", "معرّف الدليل"), tr("Label and scope", "الوصف والنطاق"),
        tr("Value", "القيمة"), tr("Method", "الطريقة")), [(
            item["id"], item["label"] + "\n" + (tr("Selected scope", "النطاق المحدد") if item["scope"] == "filtered" else tr("Whole run", "التشغيل الكامل")),
            value(item["value"]), item["method"]) for item in brief["evidence"]], (22, 22, 20, 36)))
    contract_sections = []
    report_contract = brief.get("report_contract")
    if report_contract:
        coverage = Section(tr("Analysis coverage and review status", "تغطية التحليل وحالة المراجعة"), [tr(
            "This is an unapproved projection of existing evidence, not a completed expert-agent assessment. Missing sections remain explicit; no new analytical claims or financial estimates are added.",
            "هذا عرض غير معتمد للأدلة الموجودة، وليس تقييماً مكتملاً من وكلاء خبراء. تُذكر الأقسام غير المدعومة صراحةً؛ ولا تُضاف ادعاءات تحليلية أو تقديرات مالية جديدة.")])
        labels = {
            "business_context": ("Business context and questions", "سياق العمل والأسئلة", "Existing decision questions only; organizational context is not recorded.", "أسئلة القرار الموجودة فقط؛ لم يُسجل السياق المؤسسي."),
            "dataset_scope": ("Dataset scope", "نطاق البيانات", "Filtered scope is recorded; grain, period and source fingerprint are not recorded in this brief.", "النطاق المرشح مسجل؛ لم تُسجل وحدة السجل أو الفترة أو بصمة المصدر في هذا الموجز."),
            "methodology": ("Methodology and governance", "المنهجية والحوكمة", "Controlled KPI definitions are recorded; detailed cleaning and quality checks are not projected here.", "تعريفات المؤشرات المضبوطة مسجلة؛ لا تُعرض هنا تفاصيل التنظيف وفحوص الجودة."),
            "analytical_findings": ("Analytical findings", "النتائج التحليلية", "Only verified saved findings are included; absent findings remain unavailable.", "تُعرض النتائج المخزنة المتحقق منها فقط؛ وتظل النتائج الغائبة غير متاحة."),
            "model_evaluation": ("Model evaluation", "تقييم النماذج", "Only recorded cards and known audit fields are included; absence is not model success.", "تُعرض البطاقات المسجلة وحقول تدقيقها المعروفة فقط؛ ولا يعني غيابها نجاح النموذج."),
            "executive_actions": ("Executive actions", "الإجراءات التنفيذية", "Evidence-linked review proposals only; roles are not assigned and actions are not approved.", "مقترحات مراجعة مرتبطة بالأدلة فقط؛ لم تُكلّف الأدوار ولم تُعتمد الإجراءات."),
            "financial_scenarios": ("Financial scenarios", "السيناريوهات المالية", "Not evaluated in this brief; no savings, ROI or intervention cost is inferred.", "لم تُقيّم في هذا الموجز؛ ولا تُستنتج وفورات أو عوائد استثمار أو تكلفة تدخل."),
            "implementation_plan": ("Implementation plan", "خطة التنفيذ", "No approved schedule, operational constraints or assigned owner is recorded.", "لم يُسجل جدول معتمد أو قيود تشغيلية أو مسؤول مكلّف."),
            "ai_participation": ("AI participation and expert review", "مشاركة الذكاء الاصطناعي ومراجعة الخبراء", "Deterministic evidence projection; completed expert-agent review is not demonstrated by this view.", "عرض حتمي للأدلة؛ لا يثبت هذا العرض اكتمال مراجعة وكلاء خبراء."),
        }
        coverage.tables.append(Table((tr("Report section", "قسم التقرير"), tr("Evidence coverage / missing support", "تغطية الأدلة / الدعم المفقود")),
            [(tr(*labels[item["section"]][:2]), tr(*labels[item["section"]][2:])) for item in report_contract["coverage"]]))
        records = Section(tr("Evidence-bound decision records", "سجلات القرار المرتبطة بالأدلة"))
        for item in report_contract["decisions"]:
            records.tables.append(properties([
                (tr("Problem", "المشكلة"), item["problem"]),
                (tr("Recorded evidence", "الأدلة المسجلة"), [fact["label"] + ": " + value(fact["value"]) + " · " + tr("Selected scope", "النطاق المحدد") if fact["scope"] == "filtered" else fact["label"] + ": " + value(fact["value"]) + " · " + tr("Whole run", "التشغيل الكامل") for fact in item["demonstrated_finding"]]),
                (tr("Review rationale", "مبرر المراجعة"), item["review_rationale"]),
                (tr("Proposed next action", "الإجراء التالي المقترح"), item["proposed_action"]),
                (tr("Proposed role, not assigned", "دور مقترح، غير مكلّف"), item["proposed_owner"]),
                (tr("Review gate", "شرط المراجعة"), item["next_step"]),
                (tr("Controlled KPI references", "مراجع المؤشرات المضبوطة"), item["controlled_kpis"]),
                (tr("Evidence references", "مراجع الأدلة"), item["evidence_refs"]),
                (tr("Evidence limits", "حدود الأدلة"), tr("See Reading limits and Decision boundaries; all apply to this proposal.", "راجع حدود القراءة وحدود القرار؛ تنطبق جميعها على هذا المقترح.")),
                (tr("Operational constraints / schedule", "القيود التشغيلية / الجدول"), tr("Not recorded; requires independent review.", "غير مسجلة؛ تتطلب مراجعة مستقلة.")),
                (tr("Impact estimate", "تقدير الأثر"), tr("Not evaluated; no financial or forecast assumption is approved.", "غير مقيّم؛ لم يُعتمد افتراض مالي أو تنبؤي.")),
            ]))
        contract_sections = [coverage, records]
    title = "معيار | Miyaar"
    front = Section(tr("Executive summary", "الملخص التنفيذي"), compact=True)
    front.paragraphs.append(tr("Scope", "النطاق") + ": " + str(scope["records"]) + "/" + str(scope["total_records"]) + " · " + _synopsis(run["dataset_name"], 90))
    front.paragraphs.append(tr("Data period not specified", "فترة البيانات غير محددة"))
    if scope["filters"]:
        front.paragraphs.append(tr("Filtered selection; exact filters follow in Scope and filters.", "نطاق مرشح؛ ترد المرشحات الدقيقة في قسم النطاق والمرشحات."))
    else:
        front.paragraphs.append(selected.paragraphs[0])
    if advisory:
        # Existing source order is retained. This is not a new risk ranking.
        decisions_front = advisory["decisions"][:3]
        common_gate = decisions_front[0]["gate"] if decisions_front and len({item["gate"] for item in decisions_front}) == 1 else None
        if common_gate:
            front.paragraphs.append(tr("Review gate", "شرط المراجعة") + ": " + _synopsis(common_gate, 100))
        front.tables.append(Table((tr("Review priority", "أولوية المراجعة"), tr("Proposed role, not assigned", "دور مقترح، غير مكلّف")), [
            (_synopsis(item["title"], 90), _synopsis(item["owner"], 55)) for item in decisions_front], (65, 35)))
        measured = [item for item in advisory["domains"] if item["value"] is not None][:3]
        if measured:
            front.tables.append(Table((tr("Observed measure", "المؤشر المرصود"), tr("Value / status", "القيمة / الحالة")), [
                (_synopsis(item["measure"], 85), value(item["value"]) + " " + labelled(item["scale"], scales) + " · " + status_label(item["status"], brief["language"])) for item in measured], (55, 45)))
        unknown = [item["title"] for item in advisory["domains"] if item["value"] is None]
        if unknown:
            front.after_paragraphs.append(tr("Some decision areas lack measurements; see the scorecard.", "تفتقر بعض مجالات القرار إلى قياسات؛ راجع بطاقة الأداء."))
    front.after_title = tr("Reading limits", "حدود القراءة")
    # Keep the cover bounded without shrinking type or hiding overflow. The
    # complete limitations, exact filters and unabridged proposals follow.
    front.after_paragraphs.append(tr("Selected-scope measurements and whole-run models have different populations. Historical associations are not future failures or causal effects. Read all decision boundaries before acting.",
        "تختلف مجتمعات القياسات المرشحة عن نماذج التشغيل الكامل. الارتباطات التاريخية ليست أعطالاً مستقبلية أو آثاراً سببية. راجع جميع حدود القرار قبل التصرف."))
    front.after_paragraphs.append(tr("Review only. Roles are proposed; no intervention, forecast or savings is approved. Full evidence and remaining priorities follow.",
                               "للمراجعة فقط. الأدوار مقترحة؛ لم يُعتمد تدخل أو تنبؤ أو وفورات. تلي ذلك الأدلة الكاملة وبقية الأولويات."))
    definitions = []
    if glossary := brief.get("method_glossary"):
        definitions.append(Section(glossary["title"], [glossary["caution"]], tables=[Table(
            (tr("Term", "المصطلح"), tr("Definition", "التعريف")),
            [(entry["term"], entry["definition"]) for entry in glossary["entries"]])]))
    # Order the actual evidence, not a decorative list of promised methods.
    # Missing governance/model support stays explicit in its recorded status.
    summary.page_break_before = True
    models.title = tr("Recorded model evidence and limitations", "أدلة النماذج المسجلة وحدودها")
    metadata.title = tr("Source and snapshot provenance", "مصدر البيانات وتتبع اللقطة")
    coverage_sections = contract_sections[:1]
    decision_records = contract_sections[1:]
    sections = [front, summary, questions, selected, metadata, *source_sections,
                *coverage_sections, *definitions, targets, kpis, *scorecards,
                findings, models, *readiness_sections, priorities,
                *decisions_requested, *decision_records, limitations, evidence]
    # Sections with nothing to report are left out, and named once here so
    # their absence stays explicit without an empty heading each.
    omitted = [section for section in sections if section.absent and not section.has_content()]
    if omitted:
        summary.paragraphs.append(
            tr("Left out because there is nothing to report: ", "أُسقطت الأقسام التالية لعدم وجود ما يُبلَّغ عنه: ")
            + (tr("; ", "؛ ")).join(f"{section.title} ({section.absent})" for section in omitted))
    return title, _present_sections(sections)


def _present_sections(sections):
    """Do not advertise empty headings; explicit unavailable statements remain."""
    return [section for section in sections if section.has_content()]


def _section_label(index, section):
    return section.title if index == 0 else f"{index}. {section.title}"


def _table_catalog(sections, language):
    catalog = {}
    for section_index, section in enumerate(sections):
        for table_index, table in enumerate(section.tables):
            if not table.rows:
                continue
            number = len(catalog) + 1
            detail = ""
            if len(table.headers) == 2 and table.rows[0][0] in {
                    "Measure", "Priority", "Problem", "Target measure", "Model",
                    "المؤشر", "الأولوية", "المشكلة", "مؤشر الهدف", "النموذج"}:
                detail = " — " + _synopsis(table.rows[0][1], 70)
            elif table.headers and table.headers[0] not in {"Item", "البند"}:
                detail = " — " + _synopsis(table.headers[0], 70)
            title = table.caption or section.title + detail
            catalog[section_index, table_index] = {
                "anchor": f"table-{number}", "number": number,
                "caption": ("جدول" if language == "ar" else "Table") + f" {number}. " + title}
    return catalog


def _frontmatter_labels(language):
    return (("قائمة الجداول", "قائمة الأشكال", "لا توجد أشكال في هذا التقرير؛ تُعرض الأدلة التحليلية المتاحة في جداول.")
            if language == "ar" else
            ("List of Tables", "List of Figures", "No figures are included in this report; available analytical evidence is presented in tables."))


STYLE = """
@page { size: Letter portrait; margin: 0.75in; }
@page { @bottom-center { content: counter(page); font: 10pt Dubai, Arial, sans-serif; color: #475467; } }
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 8.5in; padding: 0.75in; color: #111; background: #fff; font: 11pt/1.45 Arial, Calibri, sans-serif; text-align: start; }
h1,h2 { color: #000; line-height: 1.25; break-after: avoid; }
h1 { font-size: 20pt; margin: 0 0 12pt; border-bottom: 1pt solid #475467; padding-bottom: 8pt; }
h2 { font-size: 14pt; margin: 24pt 0 10pt; }
p { margin: 6pt 0 10pt; overflow-wrap: break-word; orphans: 3; widows: 3; }
table { border-collapse: collapse; table-layout: fixed; width: 100%; margin: 10pt 0 18pt; }
th,td { border: 0.6pt solid #d9d9d9; padding: 6pt 8pt; vertical-align: top; text-align: start; overflow-wrap: anywhere; word-break: normal; hyphens: none; }
th { background: #eee; font-weight: bold; color: #000; }
thead { display: table-header-group; } tr { break-inside: avoid; }
bdi { unicode-bidi: isolate; }
.compact { font-size: 11pt; line-height: 1.25; }
.compact p { margin: 4pt 0; }
.compact td, .compact th { padding: 4pt 6pt; }
.compact h2 { margin-top: 6pt; }
.contents { break-before: page; break-after: page; }
.contents ol { padding-inline-start: 22pt; }
.contents ol, .catalog ol { list-style: none; padding-inline-start: 0; }
.contents li { margin: 4pt 0; break-inside: avoid; }
.catalog { break-before: page; break-after: page; }
.catalog li { margin: 4pt 0; break-inside: avoid; }
caption { text-align: start; font-weight: bold; margin-bottom: 5pt; break-after: avoid; }
a { color: #1d4ed8; text-decoration: underline; text-underline-offset: 2pt; }
.back { font-size: 10pt; margin-top: 18pt; }
@media screen and (max-width: 700px) { body { padding: 18px; } table { table-layout: auto; } }
@media print { body { max-width: none; padding: 0; } .back { display: none; } }
"""


def render_html(brief):
    title, sections = report_sections(brief)
    return render_sections_html(title, sections, brief["language"])


def render_sections_html(title, sections, language):
    """Common offline typography/navigation for executive and RMD HTML exports."""
    sections = _present_sections(sections)
    catalog = _table_catalog(sections, language)
    lot, lof, no_figures = _frontmatter_labels(language)
    font = verified_font()
    font_css = ("@font-face { font-family: Dubai; src: url(data:font/ttf;base64," +
                b64encode(font).decode("ascii") + ") format('truetype'); } body { font-family: Dubai, Arial, sans-serif; }"
                if font else "")

    def text(item):
        shown = '<bdi dir="auto">' + escape(_clean(item)).replace("\n", "<br>") + "</bdi>"
        if isinstance(item, StatusText):
            label = status_label(item.status, language)
            return f'<span class="performance--{item.status}" title="{escape(label)}" aria-label="{escape(str(item) + " — " + label)}">{shown}</span>'
        return shown

    body = [f"<h1>{text(title)}</h1>"]
    for index, section in enumerate(sections):
        if index == 1:
            # No guessed printed page numbers: these destinations survive PDF printing.
            body.append('<nav class="contents" id="contents" aria-label="' +
                        ("المحتويات" if language == "ar" else "Contents") + '"><h2>' +
                        ("المحتويات" if language == "ar" else "Contents") + '</h2><ol>')
            body.extend(f'<li><a href="#{anchor}">{text(label)}</a></li>' for anchor, label in
                        [("list-of-tables", lot), ("list-of-figures", lof)] +
                        [(f"section-{i}", _section_label(i, s)) for i, s in enumerate(sections)])
            body.append('</ol></nav>')
            body.append(f'<section class="catalog" id="list-of-tables"><h2>{text(lot)}</h2><ol>')
            body.extend(f'<li><a href="#{item["anchor"]}">{text(item["caption"])}</a></li>' for item in catalog.values())
            body.append('</ol>' + ('' if catalog else '<p>' + text("لا توجد جداول في هذا التقرير." if language == 'ar' else "No tables are included in this report.") + '</p>') + '</section>')
            body.append(f'<section class="catalog" id="list-of-figures"><h2>{text(lof)}</h2><p>{text(no_figures)}</p></section>')
        attributes = (' class="compact"' if section.compact else '') + (' style="break-before:page"' if section.page_break_before and index != 1 else '')
        body.append(f'<section id="section-{index}"{attributes}><h2>{text(_section_label(index, section))}</h2>')
        body.extend(f"<p>{text(p)}</p>" for p in section.paragraphs)
        for table_index, table in enumerate(section.tables):
            if not table.rows:
                continue
            entry = catalog[index, table_index]
            widths = table.widths if len(table.widths) == len(table.headers) else [100 / len(table.headers)] * len(table.headers)
            body.append(f'<table id="{entry["anchor"]}"><caption>{text(entry["caption"])}</caption><colgroup>' + "".join(f'<col style="width:{w}%">' for w in widths) + "</colgroup><thead><tr>")
            body.extend(f'<th scope="col">{text(h)}</th>' for h in table.headers)
            body.append("</tr></thead><tbody>")
            body.extend("<tr>" + "".join(f"<td>{text(cell)}</td>" for cell in row) + "</tr>" for row in table.rows)
            body.append("</tbody></table>")
        if section.after_title:
            body.append(f"<h3>{text(section.after_title)}</h3>")
        body.extend(f"<p>{text(p)}</p>" for p in section.after_paragraphs)
        body.append('<p class="back"><a href="#contents">' + ("المحتويات" if language == "ar" else "Contents") + "</a></p>")
        body.append("</section>")
    direction = "rtl" if language == "ar" else "ltr"
    return (f'<!doctype html><html lang="{language}" dir="{direction}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="miyaar-export-font" content="{"Dubai" if font else "Arial-fallback"}">'
            f'<meta http-equiv="Content-Security-Policy" content="{escape(CONTENT_POLICY, quote=True)}">'
            f"<title>{escape(title)}</title><style>{STYLE}{font_css}" +
            "".join(f".performance--{status} {{ color: #{color}; font-weight: 600; }}" for status, color in PERFORMANCE_COLORS.items()) +
            "</style></head><body>" + "".join(body) + "</body></html>").encode("utf-8")


def _w(parent, name, **attrs):
    return ET.SubElement(parent, f"{{{W}}}{name}", {f"{{{W}}}{key}": str(v) for key, v in attrs.items()})


def _paragraph(parent, text, ar, style=None, bold=False, auto_direction=False, font_name="Arial"):
    tone = getattr(text, "status", None)
    cleaned = _clean(text)
    paragraph_ar = ar
    neutral_cell = False
    if auto_direction:
        # Tables retain the document's column order, while each technical
        # value follows its own first strong character, like HTML's bdi auto.
        # With no strong character, keep signs, numbers and ranges in one LTR
        # run; inheriting RTL splits the sign from the number and reverses it.
        paragraph_ar = False
        neutral_cell = True
        for character in cleaned:
            direction = unicodedata.bidirectional(character)
            if direction in {"L", "R", "AL"}:
                paragraph_ar = direction != "L"
                neutral_cell = False
                break
    p = _w(parent, "p")
    pr = _w(p, "pPr")
    if style:
        _w(pr, "pStyle", val=style)
    # Explicit false values also matter: an English document must not inherit
    # an RTL office profile. Logical start is right in RTL and left in LTR.
    _w(pr, "bidi", val="1" if paragraph_ar else "0")
    # Numeric-only cells retain their Arabic table's right alignment, while
    # their mathematical content reads from left to right.
    _w(pr, "jc", val="end" if ar and neutral_cell else "start")
    # Latin identifiers/formulas stay in LTR runs inside Arabic paragraphs.
    parts = re.split(r"([A-Za-z0-9][A-Za-z0-9_./:+%(),<>= -]*)", cleaned) if paragraph_ar else [cleaned]
    for part in parts:
        if not part:
            continue
        r = _w(p, "r")
        rp = _w(r, "rPr")
        _w(rp, "rFonts", ascii=font_name, hAnsi=font_name, cs=font_name, eastAsia=font_name)
        rtl = paragraph_ar and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:+%(),<>= -]*", part)
        if bold:
            _w(rp, "b")
            _w(rp, "bCs")
        if tone in PERFORMANCE_COLORS:
            _w(rp, "color", val=PERFORMANCE_COLORS[tone])
        _w(rp, "rtl", val="1" if rtl else "0")
        _w(rp, "lang", val="ar-SA" if rtl else "en-US", bidi="ar-SA" if paragraph_ar else "en-US")
        for i, line in enumerate(part.split("\n")):
            if i:
                _w(r, "br")
            t = _w(r, "t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = line
    return p


def _bookmark(paragraph, index, name=None):
    start = ET.Element(f"{{{W}}}bookmarkStart", {f"{{{W}}}id": str(index), f"{{{W}}}name": name or f"section_{index}"})
    paragraph.insert(1, start)
    _w(paragraph, "bookmarkEnd", id=index)


def _contents(body, sections, catalog, ar, add_paragraph):
    heading = add_paragraph(body, "المحتويات" if ar else "Contents", ar, "ContentsTitle")
    _w(heading.find(f"{{{W}}}pPr"), "pageBreakBefore")
    add_paragraph(body, "روابط الأقسام أدناه. يحدّث Word أرقام الصفحات عند فتح الملف؛ يمكن تحديثها أيضاً بتحديد الكل ثم F9." if ar else
                  "Section links below. Word updates page references on opening; Select All then F9 also refreshes them.", ar)
    def entry(label, anchor):
        p = add_paragraph(body, label, ar, "ContentsEntry")
        link = _w(p, "hyperlink", anchor=anchor, history="1")
        for run in list(p.findall(f"{{{W}}}r")):
            p.remove(run)
            _w(run.find(f"{{{W}}}rPr"), "color", val="1D4ED8")
            _w(run.find(f"{{{W}}}rPr"), "u", val="single")
            link.append(run)
        # Dirty PAGEREF fields are calculated by the actual pagination engine.
        # An em dash is deliberately not a cached, invented page number.
        field = _w(p, "fldSimple", instr=f" PAGEREF {anchor} \\h ", dirty="true")
        temporary = add_paragraph(body, " — ", ar)
        for run in list(temporary.findall(f"{{{W}}}r")):
            field.append(run)
        body.remove(temporary)
    lot, lof, no_figures = _frontmatter_labels("ar" if ar else "en")
    for label, anchor in [(lot, "list_of_tables"), (lof, "list_of_figures")]:
        entry(label, anchor)
    for index, section in enumerate(sections):
        entry(_section_label(index, section), f"section_{index}")
    heading = add_paragraph(body, lot, ar, "Heading1")
    _w(heading.find(f"{{{W}}}pPr"), "pageBreakBefore")
    _bookmark(heading, len(sections), "list_of_tables")
    for item in catalog.values():
        entry(item["caption"], item["anchor"].replace("-", "_"))
    if not catalog:
        add_paragraph(body, "لا توجد جداول في هذا التقرير." if ar else "No tables are included in this report.", ar)
    heading = add_paragraph(body, lof, ar, "Heading1")
    _w(heading.find(f"{{{W}}}pPr"), "pageBreakBefore")
    _bookmark(heading, len(sections) + 1, "list_of_figures")
    add_paragraph(body, no_figures, ar)


def render_docx(brief):
    """A real Office Open XML package, with internal relationships only."""
    font = verified_font()
    font_name = "Dubai" if font else "Arial"
    add_paragraph = partial(_paragraph, font_name=font_name)
    title, sections = report_sections(brief)
    ar = brief["language"] == "ar"
    catalog = _table_catalog(sections, brief["language"])
    document = ET.Element(f"{{{W}}}document")
    body = _w(document, "body")
    add_paragraph(body, title, ar, "Title")
    for section_index, section in enumerate(sections):
        if section_index == 1:
            _contents(body, sections, catalog, ar, add_paragraph)
        heading = add_paragraph(body, _section_label(section_index, section), ar, "Heading1")
        _bookmark(heading, section_index)
        if section.page_break_before:
            _w(heading.find(f"{{{W}}}pPr"), "pageBreakBefore")
        section_style = "Compact" if section.compact else None
        for paragraph in section.paragraphs:
            add_paragraph(body, paragraph, ar, style=section_style)
        for table_index, table in enumerate(section.tables):
            if not table.rows:
                continue
            entry = catalog[section_index, table_index]
            caption = add_paragraph(body, entry["caption"], ar, "Caption")
            _bookmark(caption, len(sections) + 1 + entry["number"], entry["anchor"].replace("-", "_"))
            tbl = _w(body, "tbl")
            pr = _w(tbl, "tblPr")
            _w(pr, "bidiVisual", val="1" if ar else "0")
            _w(pr, "tblW", w=9360, type="dxa")
            borders = _w(pr, "tblBorders")
            for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
                _w(borders, side, val="single", sz=6, color="D9D9D9")
            _w(pr, "tblLayout", type="fixed")
            margins = _w(pr, "tblCellMar")
            for side in ("top", "bottom", "left", "right"):
                _w(margins, side, w=80, type="dxa")
            widths = [round(9360 * pct / 100) for pct in table.widths]
            widths[-1] = 9360 - sum(widths[:-1])
            grid = _w(tbl, "tblGrid")
            for width in widths:
                _w(grid, "gridCol", w=width)
            for index, row in enumerate([table.headers] + table.rows):
                tr = _w(tbl, "tr")
                trp = _w(tr, "trPr")
                if index == 0:
                    _w(trp, "tblHeader")
                _w(trp, "cantSplit")
                for width, cell in zip(widths, row):
                    tc = _w(tr, "tc")
                    tcp = _w(tc, "tcPr")
                    _w(tcp, "tcW", w=width, type="dxa")
                    if index == 0:
                        _w(tcp, "shd", val="clear", fill="EEEEEE")
                    _w(tcp, "vAlign", val="center")
                    add_paragraph(tc, cell, ar, style=section_style, bold=index == 0, auto_direction=True)
            # A following paragraph keeps adjacent tables distinct in Word.
            add_paragraph(body, "", ar, style=section_style)
        if section.after_title:
            add_paragraph(body, section.after_title, ar, style=section_style, bold=True)
        for paragraph in section.after_paragraphs:
            add_paragraph(body, paragraph, ar, style=section_style)
    section = _w(body, "sectPr")
    footer_ref = _w(section, "footerReference", type="default")
    footer_ref.set("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", "rIdFooter")
    _w(section, "pgSz", w=12240, h=15840, orient="portrait")
    _w(section, "pgMar", top=1440, right=1440, bottom=1440, left=1440, header=720, footer=720, gutter=0)
    _w(section, "bidi", val="1" if ar else "0")
    styles = ET.Element(f"{{{W}}}styles")
    for identifier, name, size in (("Normal", "Normal", 22), ("Title", "Title", 36), ("Heading1", "heading 1", 28), ("Compact", "Compact", 22),
                                  ("ContentsTitle", "Contents title", 28), ("ContentsEntry", "Contents entry", 22), ("Caption", "Caption", 22)):
        style = _w(styles, "style", type="paragraph", styleId=identifier)
        if identifier == "Normal":
            style.set(f"{{{W}}}default", "1")
        _w(style, "name", val=name)
        if identifier != "Normal":
            _w(style, "basedOn", val="Normal")
            _w(style, "next", val="Normal")
        pr = _w(style, "pPr")
        _w(pr, "widowControl")
        if identifier in {"Title", "Heading1", "ContentsTitle", "Caption"}:
            _w(pr, "keepNext")
            _w(pr, "keepLines")
        if identifier == "Heading1":
            _w(pr, "outlineLvl", val=0)
        _w(pr, "spacing", before=200 if identifier == "Heading1" else 0, after=60 if identifier == "Compact" else 140,
           line=240 if identifier == "Compact" else (320 if ar else 280), lineRule="auto")
        rp = _w(style, "rPr")
        _w(rp, "rFonts", ascii=font_name, hAnsi=font_name, cs=font_name, eastAsia=font_name)
        if identifier in {"Title", "Heading1", "ContentsTitle"}:
            _w(rp, "b")
            _w(rp, "bCs")
        _w(rp, "color", val="000000")
        _w(rp, "sz", val=size)
        _w(rp, "szCs", val=size)
    content_types = b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'
    relationships = b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    document_rels = b'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    parts = {"[Content_Types].xml": content_types, "_rels/.rels": relationships,
             "word/document.xml": ET.tostring(document, encoding="utf-8", xml_declaration=True),
             "word/styles.xml": ET.tostring(styles, encoding="utf-8", xml_declaration=True),
             "word/_rels/document.xml.rels": document_rels}
    settings = ET.Element(f"{{{W}}}settings")
    _w(settings, "updateFields", val="true")
    _w(settings, "doNotHyphenateCaps")
    parts["word/settings.xml"] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    footer = ET.Element(f"{{{W}}}ftr")
    footer_p = add_paragraph(footer, "", ar)
    _w(footer_p, "fldSimple", instr=" PAGE ")
    parts["word/footer.xml"] = ET.tostring(footer, encoding="utf-8", xml_declaration=True)
    if font:
        rel_base = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
        font_table = ET.Element(f"{{{W}}}fonts")
        entry = _w(font_table, "font")
        entry.set(f"{{{W}}}name", "Dubai")
        embedded = _w(entry, "embedRegular", fontKey=FONT_KEY, subsetted="0")
        embedded.set("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", "rId1")
        parts["word/fontTable.xml"] = ET.tostring(font_table, encoding="utf-8", xml_declaration=True)
        parts["word/fonts/Dubai-Regular.odttf"] = obfuscate_font(font)
        parts["word/_rels/fontTable.xml.rels"] = (f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{rel_base}font" Target="fonts/Dubai-Regular.odttf"/></Relationships>').encode()
        parts["word/_rels/document.xml.rels"] = document_rels.replace(b"</Relationships>", (f'<Relationship Id="rId2" Type="{rel_base}fontTable" Target="fontTable.xml"/></Relationships>').encode())
        parts["[Content_Types].xml"] = content_types.replace(b"</Types>", b'<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/><Default Extension="odttf" ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/></Types>')
    parts["word/_rels/document.xml.rels"] = parts["word/_rels/document.xml.rels"].replace(b"</Relationships>",
        b'<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/><Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer.xml"/></Relationships>')
    parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(b"</Types>",
        b'<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/><Override PartName="/word/footer.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            # Fixed package timestamps make identical snapshots byte-identical.
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    return stream.getvalue()


def attachment_name(run_id, language, format):
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(run_id))[:100] or "run"
    return f"miyaar-executive-{safe}-{language}.{format}"
