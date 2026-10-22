"""Real governed reports from immutable evidence snapshots.

Completed stages record work already performed and independently replayed.
They do not imply that the generic forecasting pipeline ran. Publication uses
the existing run engine, artifact hash, approval and confirmed vault write.
"""

import hashlib
import json

from server import quota, rmd_analytics
from server.rmd_service import RmdError, bi, canonical, fail, now


def authorize_run(service, principal, run_id, permission="read"):
    rows = service.store._exec("SELECT pack_id FROM rmd_runs WHERE id = ?", (run_id,))
    if not rows:
        return None
    try:
        service._pack(principal, rows[0]["pack_id"], permission)
    except RmdError:
        return False
    return True


def _md(value):
    value = str(value).replace("\n", " ").replace("\r", " ")
    for char in "\\*_{}[]()<>#|!" + chr(96):
        value = value.replace(char, "\\" + char)
    return value


def report_markdown(analysis):
    language, ar = analysis.get("language", "en"), analysis.get("language") == "ar"
    lines = ["# " + ("أدلة ورؤى RMD" if ar else "RMD Evidence and Insights"), "",
             ("لقطة التحليل: " if ar else "Analysis snapshot: ") + analysis["id"],
             ("بصمة النطاق: " if ar else "Scope fingerprint: ") + analysis["fingerprint"],
             ("الفلاتر: " if ar else "Filters: ") + _md(canonical(analysis.get("filters", {}))), "",
             "## " + ("المؤشرات المسجلة" if ar else "Recorded measures"), "",
             "| " + ("المؤشر | القيمة | الوحدة | الحساب |" if ar else "Measure | Value | Unit | Calculation |"),
             "| --- | --- | --- | --- |"]
    for kpi in analysis.get("kpis", []):
        lines.append("| " + " | ".join(_md(v) for v in (
            bi(kpi["title"], language), kpi["value"], kpi["unit"], kpi["calculation_id"])) + " |")
    labels = [
        (("Management implication", "الأثر الإداري"), "management_implication"),
        (("Uncertainty", "عدم اليقين"), "uncertainty"),
        (("Proposed action", "الإجراء المقترح"), "proposed_action"),
        (("Suggested owner", "المسؤول المقترح"), "owner_role"),
        (("Due-date basis", "أساس الموعد"), "due_date_basis"),
        (("Closure evidence", "أدلة الإغلاق"), "closure_evidence"),
    ]
    for priority in analysis.get("priorities", []):
        lines += ["", "## " + _md(bi(priority["finding"], language))]
        lines += [f"**{label[ar]}:** " + _md(bi(priority.get(key), language)) for label, key in labels]
        lines += [", ".join(priority["evidence"]["calculation_ids"])]
    for chart in analysis.get("charts", []):
        lines += ["", "## " + _md(bi(chart["title"], language)), chart["calculation_id"], "",
                  "| " + ("القيمة | السجلات |" if ar else "Value | Records |"), "| --- | --- |"]
        lines += ["| " + _md(r["label"]) + " | " + str(r["value"]) + " |" for r in chart["table"]]
    lines += ["", "## " + ("القيود" if ar else "Limitations")]
    lines += ["- " + _md(bi(item, language)) for item in analysis.get("limitations", [])]
    lines += ["", "## " + ("مصادر وحسابات" if ar else "Sources and calculations")]
    lines += ["- " + _md(canonical(source)) for source in analysis.get("source_versions", [])]
    for calc in analysis.get("calculations", []):
        lines += ["", "### " + calc.get("calculation_id", calc["id"]), _md(canonical(calc))]
    lines += ["", (
        "الموافقة تخص نشر هذا التقرير فقط، ولا تمنح صلاحية تنفيذ صيانة أو اتخاذ قرار سلامة."
        if ar else
        "Approval concerns publication of this report only. It does not authorize maintenance execution or a safety decision.")]
    return "\n".join(lines) + "\n"


def create_review_run(service, engine, principal, pack_id, analysis_id, payload):
    service.vault_dir = getattr(engine, "vault_dir", service.vault_dir)
    with service.store.atomic("rmd-pack:" + pack_id):
        service._pack(principal, pack_id, "write")
        row = service._analysis(principal, pack_id, analysis_id)

        def create():
            previous = service.store._exec("SELECT id FROM rmd_runs WHERE analysis_id = ?", (analysis_id,))
            if previous:
                return {"run_id": previous[0]["id"], "analysis_id": analysis_id}
            stored, records = json.loads(row["result_json"]), json.loads(row["records_json"])
            replay = rmd_analytics.analyse_records(
                records, source_versions=stored["source_versions"], filters=json.loads(row["filters_json"]),
                language=row["language"], calculated_at=stored["calculated_at"])
            keys = ("calculation_version", "counts_by_grain", "kpis", "charts",
                    "calculations", "evidence_index", "priorities", "readiness")
            detail = ("الأرقام والجداول والمراجع تطابق إعادة حساب السجلات المحفوظة."
                      if row["language"] == "ar" else
                      "Figures, tables and evidence identifiers match a deterministic replay of immutable records.")
            checks = [{"name": "immutable_snapshot_replay",
                       "passed": all(stored.get(k) == replay.get(k) for k in keys), "detail": detail}]
            if not all(check["passed"] for check in checks):
                fail("snapshot_validation_failed", "The stored evidence could not be independently reproduced.", 409)
            if engine.limits:
                quota.check_run(service.store, principal.subject, engine.limits)
            stamp, run_id = now(), engine.new_id()
            language, ar = row["language"], row["language"] == "ar"
            report = report_markdown(stored)
            service.store.insert("runs", {
                "id": run_id, "owner": principal.subject,
                "goal": "مراجعة ونشر لقطة أدلة RMD" if ar else "Review and publish an RMD evidence snapshot",
                "dataset_name": "لقطة أدلة خاصة" if ar else "Private evidence snapshot",
                "dataset_text": "", "dataset_id": None, "state": "queued",
                "created_at": stamp, "updated_at": stamp, "error": None, "report_language": language})
            tasks = [
                ("rmd_evidence", "لقطة الأدلة" if ar else "Evidence snapshot",
                 {"snapshot_id": analysis_id, "fingerprint": stored["fingerprint"]}, []),
                ("rmd_assurance", "إعادة حساب لقطة الأدلة" if ar else "Snapshot calculation replay", {"passed": True}, checks),
                ("rmd_report", "تقرير للمراجعة" if ar else "Report for review", {"report_markdown": report}, []),
            ]
            for index, (role, title, output, quality) in enumerate(tasks):
                result = {"status": "succeeded", "summary": title, "claims": [], "calculations": [],
                          "quality_checks": quality, "output": output}
                service.store.insert("tasks", {
                    "id": engine.new_id(), "run_id": run_id, "idx": index, "role": role, "title": title,
                    "state": "succeeded", "summary": title, "result_json": canonical(result), "updated_at": stamp})
            service.store.insert("tasks", {
                "id": engine.new_id(), "run_id": run_id, "idx": 3, "role": "publish",
                "title": "بوابة النشر" if ar else "Publication gate", "state": "pending",
                "summary": None, "result_json": None, "updated_at": stamp})
            service.store.insert("artifacts", {
                "id": engine.new_id(), "run_id": run_id, "name": "rmd-evidence-report",
                "kind": "markdown", "version": 1, "content": report, "published_path": None, "created_at": stamp})
            service.store.insert("rmd_runs", {
                "id": run_id, "pack_id": pack_id, "analysis_id": analysis_id, "created_at": stamp})
            service._audit(principal, pack_id, "review_run_created", run_id, 1, {
                "analysis_id": analysis_id, "artifact_sha256": hashlib.sha256(report.encode()).hexdigest()})
            return {"run_id": run_id, "analysis_id": analysis_id}

        return service._request(principal, "review-run:" + analysis_id, payload, create, pack_id)
