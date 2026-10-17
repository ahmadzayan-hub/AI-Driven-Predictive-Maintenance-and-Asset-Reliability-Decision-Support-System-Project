"""Governed diagnostics: the detectors, inside the pipeline (milestone S2).

`server/detectors.py` finds structural problems. On its own that is a
report nobody is obliged to read. This stage puts those findings where
the rest of the system already looks: each one becomes a *calculation*
carrying the numbers it fired on and a *claim* citing that calculation,
in English and Arabic, in the ADR 0020 shape. Provenance then chains the
calculations, the Validation Expert checks the claims for evidence and
jargon exactly as it checks a built-in stage's, and the section lands in
the report the approval gate binds to.

That is the whole point of wiring it in rather than bolting it on: a
finding that a key identifies nothing cannot be quietly dropped between
the detector and the reader, because it travels as evidence.

Two deliberate choices:

**It does not fail the run by default.** A structural finding is a
restriction on what may be concluded, not a reason to refuse to compute.
Set `fail_on_high=True` where the opposite is wanted - a pipeline feeding
an automated decision, say - and the run stops on a high-severity
finding instead of carrying it forward as a caveat.

**It says what it did not check.** The identity and leakage detectors are
quadratic in the columns, so beyond a cell budget they are skipped - and
the skip is reported by name as a quality check, never passed over in
silence. A diagnostic stage that hides its own gaps is worse than none.
"""

from .. import detectors
from . import contract

# Rows x columns above which the quadratic detectors are skipped rather
# than left to run for minutes inside a stage. The platform's own limits
# are 50,000 rows and 500 columns, so this admits the ordinary case and
# declines the extreme one out loud.
MAX_CELLS = 2_000_000

# Headline and body text, per detector, in both languages. Kept here
# rather than in the detectors so the detectors stay a pure analysis
# module with no presentation in them.
# `{subject}` is the finding's *first* column, which is the one the
# headline is about; the others are context and belong in the detail, not
# in the subject slot of a sentence.
ARABIC_HEADLINES = {
    "identity_collapse": "لا يُعرِّف العمود {subject} كياناً",
    "target_leakage": "{count} أعمدة تُرمِّز التقسيم نفسه للبيانات",
    "placeholder_rates": "العمود {subject} قيمة نائبة في جزء من البيانات",
    "scale_mislabelled": "العمود {subject} كسر من 0 إلى 1 وليس نسبة مئوية",
    "broken_identity": "المجموع في {subject} لا يساوي مركّباته",
    "uneven_periods": "الفترات في {subject} تضم أعداداً غير متساوية من السجلات",
}
ARABIC_CONSEQUENCE = {
    "identity_collapse": "لذلك لا يمكن بناء تاريخ لكل أصل أو التنقل إليه من هذه البيانات.",
    "target_leakage": "لذلك سيبدو أي نموذج مبني عبر هذا التقسيم شبه مثالي دون أن يتعلم شيئاً.",
    "placeholder_rates": "لذلك يجب احتساب المعدل على المجتمع الذي قيس عليه فعلاً.",
    "scale_mislabelled": "لذلك يجب تحديد المقياس قبل عرض الرقم.",
    "broken_identity": "لذلك لا تُعرض هذه الأعمدة باعتبارها هوية محاسبية.",
    "uneven_periods": "لذلك تُقارن الفترات لكل سجل لا بالمجاميع.",
}
# A high-severity structural finding restricts what may be concluded; a
# medium one qualifies it. The claim types follow that distinction.
CLAIM_TYPE = {"high": "warning", "medium": "limitation", "low": "limitation"}


def _rows(ctx):
    """The analysis table, merged where a run joined datasets (ADR 0030)."""
    merged = ctx.get("merge")
    return merged["rows"] if merged else ctx["cleaner"]["rows"]


def _columns(ctx):
    merged = ctx.get("merge")
    return merged["columns"] if merged else ctx["collector"]["columns"]


def _clip(text, limit=990):
    """Keep inside the contract's text limit without cutting mid-word."""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


class MaintenanceGovernance:
    """What this dataset can and cannot support, as governed evidence."""

    role = "maintenance_governance"
    title = "Maintenance Governance Agent — what can this data support?"
    title_ar = "وكيل حوكمة الصيانة: ما الذي تدعمه هذه البيانات؟"
    after = "governance"
    question = "What can this dataset support, and what can it not?"
    can_fail_run = False

    def __init__(self, fail_on_high=False, max_cells=MAX_CELLS, max_findings=12):
        self.fail_on_high = bool(fail_on_high)
        # The engine decides whether a failed stage stops the run by
        # reading this off the descriptor, not by inspecting the result.
        # Leaving it at the class default made `fail_on_high` a promise
        # the descriptor contradicted: the stage returned "failed" and
        # the run carried on to a report and an approval request. The
        # option and the policy are one thing, so they are set together.
        self.can_fail_run = self.fail_on_high
        self.max_cells = int(max_cells)
        # The contract allows 50 claims. A cap well under it keeps the
        # report readable and the most severe findings at the top.
        self.max_findings = int(max_findings)

    # -- the stage ------------------------------------------------------
    def run(self, ctx):
        rows, columns = _rows(ctx), _columns(ctx)
        prefix = self.role
        if not rows or not columns:
            return self._empty(prefix, "The analysis table is empty, so there is "
                                       "nothing to diagnose.")

        tier = contract.tier(columns)
        date_column = (ctx.get("cleaner") or {}).get("date_col")
        budget_ok = len(rows) * len(columns) <= self.max_cells
        findings, skipped = self._detect(columns, rows, date_column, budget_ok)
        findings = findings[:self.max_findings]
        usable, excluded = contract.model_inputs(columns)

        calculations = self._calculations(prefix, findings, tier, rows, columns,
                                          usable, excluded)
        claims = self._claims(prefix, findings, tier, usable, excluded)
        checks = self._checks(findings, skipped, tier)
        summary = self._summary(findings, tier, excluded)

        failed = self.fail_on_high and any(f["severity"] == "high" for f in findings)
        return {
            "status": "failed" if failed else "succeeded",
            "summary": _clip(summary, 490),
            "claims": claims,
            "calculations": calculations,
            "quality_checks": checks,
            "output": {
                "tier": tier,
                "findings": findings,
                "skipped_detectors": skipped,
                "model_inputs_usable": usable,
                "model_inputs_excluded": dict(excluded),
                "headline": summary,
                "question": self.question,
                "report_markdown": self._report(ctx, findings, tier, usable,
                                                excluded, skipped),
            },
        }

    # -- parts ----------------------------------------------------------
    def _detect(self, columns, rows, date_column, budget_ok):
        """Findings, and the detectors deliberately not run."""
        if budget_ok:
            return detectors.run_all(columns, rows, date_column), []
        cheap = (detectors.scale_mislabelled, detectors.uneven_periods)
        found = []
        for detector in cheap:
            found += (detector(columns, rows, date_column)
                      if detector is detectors.uneven_periods
                      else detector(columns, rows))
        skipped = [d.__name__ for d in detectors.DETECTORS if d not in cheap]
        return sorted(found, key=lambda f: detectors.SEVERITY_ORDER[f["severity"]]), skipped

    def _calculations(self, prefix, findings, tier, rows, columns, usable, excluded):
        calculations = [
            {"id": f"{prefix}.c_tier", "name": "support_tier", "value": tier,
             "method": "maintenance when the contract's required fields and at "
                       "least three measures are present; general when tabular "
                       "but not maintenance; unusable otherwise"},
            {"id": f"{prefix}.c_shape", "name": "rows_x_columns",
             "value": f"{len(rows)} x {len(columns)}",
             "method": "rows and columns of the analysis table after cleaning "
                       "and any merge"},
            {"id": f"{prefix}.c_inputs", "name": "model_inputs_usable",
             "value": len(usable),
             "method": "columns knowable before the decision, from the "
                       "maintenance contract's timing field"},
            {"id": f"{prefix}.c_excluded", "name": "model_inputs_excluded",
             "value": len(excluded),
             "method": "columns excluded as outcomes, derived from outcomes, "
                       "identifiers, or of unestablished timing"},
        ]
        for index, finding in enumerate(findings, start=1):
            numbers = finding["numbers"]
            headline_number = next(iter(numbers.values()), len(finding["columns"]))
            calculations.append({
                "id": f"{prefix}.c_f{index}",
                "name": f"{finding['detector']}:{'+'.join(finding['columns'][:2])}",
                "value": headline_number,
                "method": _clip(f"{finding['detector']} over "
                                f"{', '.join(finding['columns'])}; "
                                + "; ".join(f"{k}={v}" for k, v in numbers.items())),
            })
        return calculations

    def _claims(self, prefix, findings, tier, usable, excluded):
        claims = []
        if tier == "maintenance":
            text = ("The dataset meets the maintenance contract, so reliability, "
                    "work-order, cost and risk measures apply to it.")
            text_ar = ("تستوفي البيانات عقد الصيانة، لذلك تنطبق عليها مقاييس "
                       "الموثوقية وأوامر العمل والتكلفة والمخاطر.")
        elif tier == "general":
            text = ("The dataset is tabular but does not meet the maintenance "
                    "contract. Governance and descriptive work apply; the "
                    "reliability, failure, work-order, cost and risk agents "
                    "stand down.")
            text_ar = ("البيانات جدولية لكنها لا تستوفي عقد الصيانة. تنطبق "
                       "الحوكمة والتحليل الوصفي، بينما تتوقف وكلاء الموثوقية "
                       "والأعطال وأوامر العمل والتكلفة والمخاطر.")
        else:
            text = "The dataset cannot be analysed as a table."
            text_ar = "لا يمكن تحليل البيانات كجدول."
        claims.append({"id": f"{prefix}.cl_tier", "type": "fact", "text": text,
                       "text_ar": text_ar, "evidence": [f"{prefix}.c_tier",
                                                        f"{prefix}.c_shape"],
                       "status": "verified"})

        if excluded:
            claims.append({
                "id": f"{prefix}.cl_inputs", "type": "limitation",
                "text": _clip(
                    f"{len(usable)} of {len(usable) + len(excluded)} columns are "
                    f"usable to predict; {len(excluded)} are excluded because they "
                    f"record the outcome, are derived from it, identify a row, or "
                    f"have no established recording time. A model given the "
                    f"excluded columns restates the answer rather than learning it."),
                "text_ar": _clip(
                    f"{len(usable)} عموداً فقط صالحة للتنبؤ من أصل "
                    f"{len(usable) + len(excluded)}، واستُبعد {len(excluded)} لأنها "
                    f"تسجل النتيجة أو مشتقة منها أو مُعرِّفات أو غير محددة التوقيت. "
                    f"النموذج الذي يأخذ الأعمدة المستبعدة يعيد صياغة الإجابة بدل أن يتعلمها."),
                "evidence": [f"{prefix}.c_inputs", f"{prefix}.c_excluded"],
                "status": "verified"})

        for index, finding in enumerate(findings, start=1):
            detector = finding["detector"]
            arabic = ARABIC_HEADLINES.get(detector, "{subject}").format(
                subject=finding["columns"][0] if finding["columns"] else "",
                count=finding["numbers"].get("columns_involved",
                                             len(finding["columns"])))
            claims.append({
                "id": f"{prefix}.cl_f{index}",
                "type": CLAIM_TYPE.get(finding["severity"], "limitation"),
                "text": _clip(f"{finding['headline']}. {finding['detail']}"),
                "text_ar": _clip(f"{arabic}. "
                                 + ARABIC_CONSEQUENCE.get(detector, "")),
                "evidence": [f"{prefix}.c_f{index}"],
                "status": "verified"})
        return claims

    def _checks(self, findings, skipped, tier):
        fired = {f["detector"] for f in findings}
        checks = [{"name": "support_tier", "passed": tier != "unusable",
                   "detail": f"tier = {tier}"}]
        for detector in detectors.DETECTORS:
            name = detector.__name__
            if name in skipped:
                checks.append({"name": name, "passed": True,
                               "detail": "not run: the table is larger than this "
                                         "stage's cell budget, so this detector "
                                         "was skipped rather than left to run"})
            else:
                hits = sum(1 for f in findings if f["detector"] == name)
                checks.append({
                    "name": name, "passed": not hits,
                    "detail": "no finding" if not hits else f"{hits} finding(s)"})
        return checks

    def _summary(self, findings, tier, excluded):
        if not findings:
            return (f"No structural problem found; the dataset is {tier} tier and "
                    f"{len(excluded)} columns are excluded from model inputs.")
        high = sum(1 for f in findings if f["severity"] == "high")
        lead = findings[0]["headline"]
        return (f"{len(findings)} structural finding(s), {high} of them high: "
                f"{lead}.")

    def _report(self, ctx, findings, tier, usable, excluded, skipped):
        lines = [
            f"# {self.title.split(' — ')[0]} — {self.question}", "",
            f"**Dataset:** {ctx.get('dataset_name', 'dataset')} · "
            f"**Support tier:** {tier}", "",
        ]
        if findings:
            lines += [f"> **{len(findings)} structural finding(s).** These restrict "
                      f"what may be concluded; they are not reasons the figures "
                      f"below are wrong.", "",
                      "| Severity | Finding | Columns |", "| --- | --- | --- |"]
            lines += [f"| {f['severity']} | {f['headline']} | "
                      f"{', '.join(f['columns'][:3])} |" for f in findings]
        else:
            lines.append("> **No structural problem found.**")
        lines += ["", "## What may be used to predict", "",
                  f"{len(usable)} of {len(usable) + len(excluded)} columns were "
                  f"knowable before the decision: "
                  + (", ".join(usable) if usable else "none") + ".", ""]
        if excluded:
            lines += ["| Column | Why it is excluded |", "| --- | --- |"]
            lines += [f"| {c} | {why} |" for c, why in list(excluded.items())[:20]]
        if skipped:
            lines += ["", "## Not checked", "",
                      "These detectors were skipped because the table exceeds this "
                      "stage's cell budget: " + ", ".join(skipped) + "."]
        return "\n".join(lines)

    def _empty(self, prefix, message):
        return {"status": "succeeded", "summary": message,
                "claims": [{"id": f"{prefix}.cl_empty", "type": "limitation",
                            "text": message,
                            "text_ar": "جدول التحليل فارغ، فلا يوجد ما يُفحص.",
                            "evidence": [], "status": "verified"}],
                "calculations": [], "quality_checks": [
                    {"name": "analysis_table_not_empty", "passed": False,
                     "detail": message}],
                "output": {"tier": "unusable", "findings": [],
                           "question": self.question,
                           "report_markdown": f"# {self.title}\n\n{message}"}}
