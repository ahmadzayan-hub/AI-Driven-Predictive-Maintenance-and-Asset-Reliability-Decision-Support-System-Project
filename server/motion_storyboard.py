"""Server-verified video brief over one authorized analytics run.

The web client cannot supply its own KPI, evidence status or model score.
Human editing after export is a new unverified draft.
"""
from __future__ import annotations

import hashlib
import json


class MotionStoryRefused(ValueError):
    pass


def from_run(run: dict) -> dict:
    if not isinstance(run, dict):
        raise MotionStoryRefused("Run is unavailable")
    tasks = [t for t in (run.get("tasks") or []) if t.get("role") != "publish"]
    validator = next((t for t in tasks if t.get("role") == "validator"), None)
    if (
        not tasks or any(t.get("state") != "succeeded" for t in tasks)
        or not validator or not validator.get("quality_checks")
        or any(not check.get("passed") for check in validator["quality_checks"])
    ):
        raise MotionStoryRefused("The full recorded pipeline must pass independent validation")
    headlines = [r["headline"].strip() for r in (run.get("reports") or [])
                 if isinstance(r, dict) and isinstance(r.get("headline"), str) and r["headline"].strip()]
    if not headlines:
        raise MotionStoryRefused("A versioned report with a finding is required")
    return _compose(run, headlines[0])


def _compose(run, headline):
    """Shared composition only; each caller first passes its own evidence gate."""
    report = run.get("report") or {}
    if not isinstance(report, dict) or not isinstance(report.get("content"), str):
        raise MotionStoryRefused("A saved report body is required / يلزم نص تقرير محفوظ")
    if not report.get("id") or not report.get("version") or not report.get("content"):
        raise MotionStoryRefused("A versioned report with a finding is required")
    goal = str(run.get("goal") or "").strip()
    if not goal or max(len(goal), len(headline)) > 480:
        raise MotionStoryRefused("Video narrative requires a human-reviewed summary")
    language = run.get("report_language") or "en"
    if language not in ("en", "ar"):
        raise MotionStoryRefused("Unsupported report language")
    # Link directly to the immutable saved run and report version.
    evidence = [{
        "source_id": run["id"],
        "revision": f'v{report["version"]}',
        "locator": f'report:{report["id"]}',
        "data_status": "RECORDED_IN_REGISTER",
    }]
    final = ("راجع التقرير وحساباته واعتمد المحتوى بشريًا قبل النشر."
             if language == "ar" else
             "Review the report and calculations before human approval or release.")
    return {
        "schema": "motion-evidence-v1",
        "language": language,
        "format": "wide",
        "classification": "INTERNAL",
        "duration": 15,
        "source_context": {
            "run_id": run["id"],
            "report_id": report["id"],
            "report_version": report["version"],
            "report_sha256": hashlib.sha256(report["content"].encode()).hexdigest(),
            "dataset": run.get("dataset_name"),
            "scope": "run-level validation only, not field model accuracy",
        },
        "approval": {"state": "DRAFT_VIDEO", "issued": False},
        "scenes": [
            {"kind": "hook", "text": goal, "evidence": evidence},
            {"kind": "evidence", "text": headline, "evidence": evidence},
            {"kind": "action", "text": final, "evidence": evidence},
        ],
    }


def from_evidence_run(service, principal, run):
    """Explicit RMD adapter: replay immutable evidence, never bypass validator.

    Generic runs still go through from_run unchanged. This path requires the
    recorded RMD assurance and a fresh replay plus exact report correspondence.
    """
    from server import rmd_analytics
    from server.rmd_workflow import report_markdown
    from server.rmd_service import canonical, bi

    links = service.store._exec("SELECT pack_id, analysis_id FROM rmd_runs WHERE id = ?", (run["id"],))
    if not links:
        return from_run(run)
    pack_id, analysis_id = links[0]["pack_id"], links[0]["analysis_id"]
    row = service._analysis(principal, pack_id, analysis_id)
    stored = json.loads(row["result_json"])
    tasks = [task for task in run.get("tasks", []) if task.get("role") != "publish"]
    assurance = next((task for task in tasks if task.get("role") == "rmd_assurance"), {})
    checks = assurance.get("quality_checks", [])
    if (not tasks or any(task.get("state") != "succeeded" for task in tasks)
            or not any(check.get("name") == "immutable_snapshot_replay" and check.get("passed") is True for check in checks)
            or any(check.get("passed") is not True for check in checks)):
        raise MotionStoryRefused("RMD snapshot assurance is required / يلزم تحقق لقطة الأدلة")
    for source in stored.get("source_versions", []):
        source_id = source.get("source_id") or source.get("id")
        if not source_id:
            raise MotionStoryRefused("Source identity is missing / هوية المصدر مفقودة")
        current = service._source(principal, pack_id, source_id)
        if current["sha256"] != source.get("sha256") or current["revision"] != source.get("version"):
            raise MotionStoryRefused("Source version changed; create a new reviewed draft / تغير إصدار المصدر؛ أنشئ مسودة جديدة للمراجعة")
    filters = json.loads(row["filters_json"])
    fingerprint = hashlib.sha256(canonical([stored["source_versions"], filters, stored["calculation_version"]]).encode()).hexdigest()
    replay = rmd_analytics.analyse_records(json.loads(row["records_json"]),
        source_versions=stored["source_versions"], filters=filters,
        language=row["language"], calculated_at=stored["calculated_at"])
    keys = ("calculation_version", "counts_by_grain", "kpis", "charts", "calculations", "evidence_index", "priorities", "readiness")
    if (fingerprint != row["fingerprint"] or fingerprint != stored["fingerprint"]
            or any(stored.get(key) != replay.get(key) for key in keys)
            or (run.get("report") or {}).get("content") != report_markdown(stored)):
        raise MotionStoryRefused("RMD source/report changed; create a new reviewed draft / تغير المصدر أو التقرير؛ أنشئ مسودة جديدة للمراجعة")
    language = row["language"]
    if run.get("report_language") != language:
        raise MotionStoryRefused("Report and snapshot languages differ / لغة التقرير تختلف عن اللقطة")
    findings = [bi(item["finding"], language) for item in stored.get("priorities", []) if item.get("finding")]
    if not findings:
        raise MotionStoryRefused("A verified finding is required / يلزم استنتاج موثق")
    # No synthetic validator task: RMD has its own independently replayed gate.
    story = _compose(run, findings[0])
    story["source_context"].update({"pack_id": pack_id, "analysis_id": analysis_id,
        "fingerprint": fingerprint, "source_versions": stored["source_versions"],
        "scope": "immutable RMD snapshot replay, not a prediction or verified root cause"})
    service._pack(principal, pack_id)
    return story
