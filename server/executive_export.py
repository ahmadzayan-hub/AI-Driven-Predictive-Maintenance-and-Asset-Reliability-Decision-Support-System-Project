"""Offline business documents from an already authorized executive snapshot.

Both formats consume the same human-readable sections. No models, rows, network
requests, publishing, office applications or additional dependencies are used.
"""

from dataclasses import dataclass, field
from html import escape
from io import BytesIO
import math
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


HTML_MIME = "text/html"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
CONTENT_POLICY = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ET.register_namespace("w", W)


def _clean(value):
    # XML 1.0 excludes control characters and unpaired JSON surrogates. Apply the
    # same normalization to HTML so the documents retain identical facts.
    return "".join(c if c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF
                   or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF
                   else "\ufffd" for c in str(value))


@dataclass
class Table:
    headers: tuple
    rows: list
    widths: tuple = (32, 68)


@dataclass
class Section:
    title: str
    paragraphs: list = field(default_factory=list)
    tables: list = field(default_factory=list)


def report_sections(brief):
    """Common document model; figures are formatted, never recalculated."""
    ar = brief["language"] == "ar"

    def tr(en, arabic):
        return arabic if ar else en

    def value(item):
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
        "count": ("Count", "عدد"), "score": ("Score", "درجة"),
        "category": ("Category", "فئة"), "date": ("Date", "تاريخ"), "identifier": ("Identifier", "معرّف"),
    }
    populations = {"all records": ("all records", "جميع السجلات"),
                   "corrective records": ("corrective records", "سجلات الصيانة التصحيحية")}
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
    summary = Section(tr("Executive summary", "الملخص التنفيذي"), [brief["headline"],
        tr("This document supports qualified human review. Exporting does not approve or publish the run.",
           "يدعم هذا المستند المراجعة البشرية المؤهلة. لا يعني التصدير اعتماد التشغيل أو نشره.")])
    summary.paragraphs.extend(brief["readiness"]["limitations"])
    kpis = Section(tr("Controlled KPIs", "مؤشرات الأداء المنضبطة"), [tr(
        "KPIs cover the selected records. Excluded records are outside a measure's population; unmeasured records are inside it but lack required measurements. Displayed numbers use up to 12 significant digits.",
        "تغطي المؤشرات السجلات المحددة. تقع السجلات المستبعدة خارج مجموعة القياس؛ أما غير المقاسة فتقع داخلها وتفتقر إلى القياسات المطلوبة. تُعرض الأرقام بما يصل إلى 12 خانة معنوية.")])
    if brief["kpis"]["measures"]:
        kpis.tables.append(Table((tr("Measure", "المؤشر"), tr("Value", "القيمة"),
            tr("Scale", "مقياس القيمة"), tr("Measured records", "السجلات المقاسة")),
            [(measure["title"], value(measure["value"]), labelled(measure["scale"], scales),
              value(measure["records"])) for measure in brief["kpis"]["measures"]], (42, 14, 26, 18)))
    for measure in brief["kpis"]["measures"]:
        kpis.tables.append(properties([
            (tr("Measure", "المؤشر"), measure["title"]),
            (tr("Evidence ID", "معرّف الدليل"), "executive.kpi." + measure["key"]),
            (tr("Value", "القيمة"), measure["value"]),
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
        ]))
    if not brief["kpis"]["measures"]:
        kpis.paragraphs.append(tr("No controlled KPI is computable for this scope.", "لا يمكن حساب مؤشر أداء منضبط لهذا النطاق."))
    if brief["kpis"]["unavailable"]:
        kpis.tables.append(Table((tr("Unavailable measure", "المؤشر غير المتاح"), tr("Required evidence", "الأدلة المطلوبة")),
            [(key, value(reason)) for key, reason in brief["kpis"]["unavailable"].items()]))
    priorities = Section(tr("Review priorities", "أولويات المراجعة"))
    for item in brief["priorities"]:
        priorities.tables.append(properties([(tr("Priority", "الأولوية"), item["title"]),
            (tr("Review", "المراجعة"), item["detail"]), (tr("Evidence references", "مراجع الأدلة"), item["evidence_refs"])]))
    if not priorities.tables:
        priorities.paragraphs.append(tr("No observed priority is identified in this scope.", "لم تُحدد أولوية مرصودة ضمن هذا النطاق."))
    questions = Section(tr("Decision questions", "أسئلة القرار"))
    for item in brief["questions"]:
        questions.paragraphs.extend([item["text"], refs(item)])
    if not questions.paragraphs:
        questions.paragraphs.append(tr("No additional question is recorded.", "لا يوجد سؤال إضافي مسجل."))
    whole = tr("These stored findings and model evaluations describe the whole run. They were not recomputed or retrained for the selected filters and do not establish future failure or remaining useful life.",
               "تصف النتائج وتقييمات النماذج المخزنة التشغيل الكامل. لم تُعد حساباتها أو تدريبها وفق المرشحات المحددة، ولا تثبت الأعطال المستقبلية أو العمر المتبقي.")
    findings = Section(tr("Whole-run findings", "نتائج التشغيل الكامل"), [whole])
    for item in brief["findings"]:
        findings.paragraphs.extend([item["text"], tr("Stage", "المرحلة") + ": " + value(item["stage"]), refs(item)])
    if not brief["findings"]:
        findings.paragraphs.append(tr("No verified findings are available in this briefing.", "لا تتوفر نتائج متحقق منها في هذا الموجز."))
    models = Section(tr("Whole-run model evaluations", "تقييمات نماذج التشغيل الكامل"), [whole])
    for card in brief["models"]:
        # Plugin model cards can contain arbitrary payloads. Only known scalar
        # evaluation metadata belongs in a document; never copy nested raw data.
        allowed = {"verdict", "reason", "decision", "horizon", "beats_baseline_margin",
                   "clearly_above_chance", "positive_rate_held_out", "baseline_majority",
                   "baseline_best_rule", "baseline_rule_column", "groups",
                   "share_of_spread_explained", "separation", "period", "season_length"}
        details = {k: v for k, v in (card.get("details") or {}).items()
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
        models.tables.append(properties(rows))
    if not brief["models"]:
        models.paragraphs.append(tr("No model evaluation is available; predictive performance is not claimed.", "لا يتوفر تقييم نموذج؛ ولا يُدّعى وجود أداء تنبؤي."))
    evidence = Section(tr("Evidence appendix", "ملحق الأدلة"), [tr(
        "Every reference below is part of this snapshot. Filtered calculations and whole-run calculations have different scopes.",
        "كل مرجع أدناه جزء من هذه اللقطة. يختلف نطاق الحسابات المرشحة عن حسابات التشغيل الكامل.")])
    evidence.tables.append(Table((tr("Evidence ID", "معرّف الدليل"), tr("Label and scope", "الوصف والنطاق"),
        tr("Value", "القيمة"), tr("Method", "الطريقة")), [(
            item["id"], item["label"] + "\n" + (tr("Selected scope", "النطاق المحدد") if item["scope"] == "filtered" else tr("Whole run", "التشغيل الكامل")),
            value(item["value"]), item["method"]) for item in brief["evidence"]], (24, 24, 12, 40)))
    return tr("Executive evidence brief", "موجز الأدلة التنفيذي"), [metadata, selected, summary, kpis, priorities, questions, findings, models, evidence]


STYLE = """
@page { size: Letter portrait; margin: 0.75in; }
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 8.5in; padding: 0.75in; color: #111; background: #fff; font: 11pt/1.5 Arial, Calibri, sans-serif; }
h1,h2 { color: #000; line-height: 1.25; break-after: avoid; }
h1 { font-size: 20pt; margin: 0 0 20pt; border-bottom: 2pt solid #000; padding-bottom: 10pt; }
h2 { font-size: 14pt; margin: 24pt 0 10pt; }
p { margin: 6pt 0 10pt; overflow-wrap: anywhere; }
table { border-collapse: collapse; table-layout: fixed; width: 100%; margin: 10pt 0 18pt; }
th,td { border: 0.6pt solid #d9d9d9; padding: 6pt 8pt; vertical-align: middle; text-align: start; overflow-wrap: anywhere; word-break: break-word; }
th { background: #eee; font-weight: bold; color: #000; }
thead { display: table-header-group; } tr { break-inside: avoid; }
bdi { unicode-bidi: isolate; }
@media print { body { max-width: none; padding: 0; } }
"""


def render_html(brief):
    title, sections = report_sections(brief)

    def text(item):
        return '<bdi dir="auto">' + escape(_clean(item)).replace("\n", "<br>") + "</bdi>"

    body = [f"<h1>{text(title)}</h1>"]
    for section in sections:
        body.append(f"<section><h2>{text(section.title)}</h2>")
        body.extend(f"<p>{text(p)}</p>" for p in section.paragraphs)
        for table in section.tables:
            body.append("<table><colgroup>" + "".join(f'<col style="width:{w}%">' for w in table.widths) + "</colgroup><thead><tr>")
            body.extend(f'<th scope="col">{text(h)}</th>' for h in table.headers)
            body.append("</tr></thead><tbody>")
            body.extend("<tr>" + "".join(f"<td>{text(cell)}</td>" for cell in row) + "</tr>" for row in table.rows)
            body.append("</tbody></table>")
        body.append("</section>")
    language = brief["language"]
    direction = "rtl" if language == "ar" else "ltr"
    return (f'<!doctype html><html lang="{language}" dir="{direction}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="{escape(CONTENT_POLICY, quote=True)}">'
            f"<title>{escape(title)}</title><style>{STYLE}</style></head><body>" + "".join(body) + "</body></html>").encode("utf-8")


def _w(parent, name, **attrs):
    return ET.SubElement(parent, f"{{{W}}}{name}", {f"{{{W}}}{key}": str(v) for key, v in attrs.items()})


def _paragraph(parent, text, ar, style=None, bold=False):
    p = _w(parent, "p")
    pr = _w(p, "pPr")
    if style:
        _w(pr, "pStyle", val=style)
    # Explicit false values also matter: an English document must not inherit
    # an RTL office profile. Logical start is right in RTL and left in LTR.
    _w(pr, "bidi", val="1" if ar else "0")
    _w(pr, "jc", val="start")
    # Latin identifiers/formulas stay in LTR runs inside Arabic paragraphs.
    parts = re.split(r"([A-Za-z0-9][A-Za-z0-9_./:+%(),<>= -]*)", _clean(text)) if ar else [_clean(text)]
    for part in parts:
        if not part:
            continue
        r = _w(p, "r")
        rp = _w(r, "rPr")
        _w(rp, "rFonts", ascii="Arial", hAnsi="Arial", cs="Arial", eastAsia="Arial")
        rtl = ar and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:+%(),<>= -]*", part)
        if bold:
            _w(rp, "b")
            _w(rp, "bCs")
        _w(rp, "rtl", val="1" if rtl else "0")
        _w(rp, "lang", val="ar-SA" if rtl else "en-US", bidi="ar-SA" if ar else "en-US")
        for i, line in enumerate(part.split("\n")):
            if i:
                _w(r, "br")
            t = _w(r, "t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = line
    return p


def render_docx(brief):
    """A real Office Open XML package, with internal relationships only."""
    title, sections = report_sections(brief)
    ar = brief["language"] == "ar"
    document = ET.Element(f"{{{W}}}document")
    body = _w(document, "body")
    _paragraph(body, title, ar, "Title")
    for section in sections:
        _paragraph(body, section.title, ar, "Heading1")
        for paragraph in section.paragraphs:
            _paragraph(body, paragraph, ar)
        for table in section.tables:
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
                    _paragraph(tc, cell, ar, bold=index == 0)
            # A following paragraph keeps adjacent tables distinct in Word.
            _paragraph(body, "", ar)
    section = _w(body, "sectPr")
    _w(section, "pgSz", w=12240, h=15840, orient="portrait")
    _w(section, "pgMar", top=1440, right=1440, bottom=1440, left=1440, header=720, footer=720, gutter=0)
    _w(section, "bidi", val="1" if ar else "0")
    styles = ET.Element(f"{{{W}}}styles")
    for identifier, name, size in (("Normal", "Normal", 22), ("Title", "Title", 36), ("Heading1", "heading 1", 28)):
        style = _w(styles, "style", type="paragraph", styleId=identifier)
        if identifier == "Normal":
            style.set(f"{{{W}}}default", "1")
        _w(style, "name", val=name)
        if identifier != "Normal":
            _w(style, "basedOn", val="Normal")
            _w(style, "next", val="Normal")
        pr = _w(style, "pPr")
        if identifier != "Normal":
            _w(pr, "keepNext")
            _w(pr, "keepLines")
        _w(pr, "spacing", before=200 if identifier == "Heading1" else 0, after=140,
           line=320 if ar else 280, lineRule="auto")
        rp = _w(style, "rPr")
        _w(rp, "rFonts", ascii="Arial", hAnsi="Arial", cs="Arial", eastAsia="Arial")
        if identifier != "Normal":
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
