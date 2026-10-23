"""Server-verified video brief over one authorized analytics run.

The web client cannot supply its own KPI, evidence status or model score.
Human editing after export is a new unverified draft.
"""
from __future__ import annotations


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
    report = run.get("report") or {}
    headlines = [r.get("headline", "").strip() for r in (run.get("reports") or [])
                 if isinstance(r, dict) and r.get("headline", "").strip()]
    if not report.get("id") or not report.get("version") or not headlines:
        raise MotionStoryRefused("A versioned report with a finding is required")
    headline = headlines[0]
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
