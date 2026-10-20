"""A shared conservative boundary for detected personal data sent to models.

These checks reuse the measured pattern detector. They do not anonymize data
or promise that an unrecognised identifier is safe. Human-readable reports
stay intact; model and runtime handoffs use the deterministic path instead.
"""

import json


def blocks_model(*, privacy=None, merged=None, texts=()):
    if (privacy or {}).get("personal_data") or (merged or {}).get("personal_data"):
        return True
    # Import lazily because analytics uses this guard when it narrates.
    from server.analytics import personal_data_findings
    # Inspect the exact outgoing text as well as the bounded dataset scan:
    # a leading group may appear after that scan's first 2,000 records.
    return bool(personal_data_findings(
        ["model_text"], [{"model_text": str(text)} for text in texts]))


def run_blocks_model(store, run_id):
    """Read the run's persisted privacy decisions, including joined data."""
    for task in store.get_tasks(run_id):
        if task["role"] not in ("privacy", "merge", "prescriptive"):
            continue
        raw = task.get("result_json")
        if not raw:
            continue
        try:
            output = json.loads(raw)["output"]
        except (KeyError, TypeError, ValueError):
            return True  # unreadable evidence cannot authorize a model call
        if output.get("personal_data") or output.get("exec_summary_privacy_reason"):
            return True
    return False


def notice(language="en"):
    if language == "ar":
        return ("اكتُشفت بيانات شخصية، لذلك أُعدّ الرد بالقواعد المحددة "
                "دون إرسالها إلى نموذج أو موجّه نماذج.")
    return ("Personal data was detected, so the response uses deterministic "
            "rules without sending it to a model or model router.")
