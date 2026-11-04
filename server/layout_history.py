"""Designed-page layouts kept on the server (ADR 2026-11-04-layout-history).

Each reader has their own history per run: the layouts they designed, the one
shown and the pinned sections, the same document the browser keeps. Every save
is a new numbered version, so the history is also the audit trail, and a save
names the version it started from: two tabs or devices saving from the same
version cannot both win; the second is told and shown the latest. Every layout
is validated again against the run's own table before it is stored, so a stored
history can never hold a section the planner would refuse.
"""
from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone

from server import layout_plan

ACTIONS = ("designed", "restored", "pinned", "unpinned", "restored_version")
MAX_VERSIONS = 5            # layouts inside one history document, as in the browser
MAX_BYTES = 200_000         # one stored document
AUDIT_LIMIT = 50


class HistoryError(ValueError):
    def __init__(self, code, status=422, head=None):
        super().__init__(code)
        self.code, self.status, self.head = code, status, head


MESSAGES = {
    "invalid": ("This layout history is not valid for this report.", "سجل التصميم هذا غير صالح لهذا التقرير."),
    "conflict": ("This layout was changed in another tab or device. The latest version is shown.",
                 "تغير هذا التصميم في تبويب أو جهاز آخر. تُعرض أحدث نسخة."),
    "missing": ("That saved version does not exist.", "هذه النسخة المحفوظة غير موجودة."),
}


def message(code, language):
    en, ar = MESSAGES.get(code, MESSAGES["invalid"])
    return ar if language == "ar" else en


def clean(history, table, stages=()):
    """The history with every layout validated against this table, or HistoryError."""
    if not isinstance(history, dict) or set(history) - {"fingerprint", "versions", "current", "pinned"}:
        raise HistoryError("invalid")
    prof = layout_plan.profile(table)
    caps = layout_plan.capabilities(prof, stages)
    fingerprint = layout_plan.fingerprint(prof)
    versions, current, pinned = history.get("versions"), history.get("current"), history.get("pinned")
    if (history.get("fingerprint") != fingerprint or not isinstance(versions, list)
            or not 1 <= len(versions) <= MAX_VERSIONS or not isinstance(current, int)
            or not 0 <= current < len(versions) or not isinstance(pinned, list)
            or any(not isinstance(p, str) for p in pinned) or len(pinned) > layout_plan.MAX_SECTIONS):
        raise HistoryError("invalid")
    kept = []
    for version in versions:
        if not isinstance(version, dict) or set(version) - {"result", "at"} or not isinstance(version.get("at"), str):
            raise HistoryError("invalid")
        result = version.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("plan"), dict):
            raise HistoryError("invalid")
        plan = copy.deepcopy(result["plan"])
        for section in plan.get("sections") or []:
            if isinstance(section, dict):
                section.pop("reason", None)        # the server adds a gap's reason itself
        checked, problems = layout_plan.validate(plan, table, prof, caps)
        if checked is None or problems:
            raise HistoryError("invalid")
        notes = result.get("notes") if isinstance(result.get("notes"), list) else []
        kept.append({"result": {"plan": checked, "source": result.get("source") if result.get("source") in ("model", "rules") else "rules",
                                "provider": result.get("provider") if isinstance(result.get("provider"), str) else None,
                                "notes": [n for n in notes if isinstance(n, dict)][:6], "problems": [],
                                "capabilities": caps, "fingerprint": fingerprint,
                                "domain": {"name": layout_plan.domain(prof), "basis": "inferred from field names"}},
                     "at": version["at"][:40]})
    document = {"fingerprint": fingerprint, "versions": kept, "current": current, "pinned": pinned}
    if len(json.dumps(document)) > MAX_BYTES:
        raise HistoryError("invalid")
    return document


def view(rows):
    """The newest version and the audit trail, newest first."""
    head = rows[0] if rows else None
    return {"head": None if head is None else {"version": head["version"], "action": head["action"],
                                               "created_at": head["created_at"], "history": json.loads(head["result_json"])},
            "audit": [{"version": r["version"], "action": r["action"], "created_at": r["created_at"]} for r in rows[:AUDIT_LIMIT]]}


def save(store, owner, run_id, document, action, expected_version):
    """Store `document` as version expected_version + 1, or raise a conflict carrying the head."""
    if action not in ACTIONS or not isinstance(expected_version, int) or expected_version < 0:
        raise HistoryError("invalid")
    rows = store.layout_versions(owner, run_id)
    latest = rows[0]["version"] if rows else 0
    if latest != expected_version:
        raise HistoryError("conflict", 409, view(rows))
    row = {"id": uuid.uuid4().hex, "owner": owner, "run_id": run_id, "version": expected_version + 1,
           "action": action, "fingerprint": document["fingerprint"], "result_json": json.dumps(document),
           "pinned_json": json.dumps(document["pinned"]),
           "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    if store.add_layout_version(row) is None:   # another writer took this version first
        raise HistoryError("conflict", 409, view(store.layout_versions(owner, run_id)))
    return view(store.layout_versions(owner, run_id))
