"""One human review step for every executive output (ADR 2026-11-04-shared-review).

The dashboard brief, the HTML report, the Word document, the slides and the
video are all built from one brief snapshot. A review records who decided what
about one of them, with a comment and a time, against that snapshot and the
digest of the exact bytes reviewed. It is append-only. A decision counts only
while both still match: the moment the data, the filters, the language or the
file changes, the artifact reads as changed since review and needs a new one.
A review never publishes anything; release still goes through the run's own
human approval gate.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

FORMATS = ("dashboard", "html", "docx", "slides", "video")
DECISIONS = ("approved", "changes_requested")
MAX_COMMENT = 2000


class ReviewError(ValueError):
    def __init__(self, code, status=422):
        super().__init__(code)
        self.code, self.status = code, status


MESSAGES = {
    "stale": ("The report changed after you opened it. Refresh, then review the current version.",
              "تغير التقرير بعد فتحه. حدّثه ثم راجع النسخة الحالية."),
    "artifact_changed": ("This file is not the one now produced from the report. Review the current file.",
                         "هذا الملف ليس الملف الناتج حالياً من التقرير. راجع الملف الحالي."),
    "no_video": ("No rendered video exists for this version of the report. Render it first.",
                 "لا يوجد فيديو منتج لهذه النسخة من التقرير. أنتجه أولاً."),
    "comment_required": ("Say what must change before asking for changes.",
                         "اذكر ما يجب تغييره قبل طلب التعديل."),
    "invalid": ("Choose a known output and decision.", "اختر مخرجاً وقراراً معروفين."),
}


def message(code, language):
    en, ar = MESSAGES.get(code, MESSAGES["invalid"])
    return ar if language == "ar" else en


def digest(content):
    return hashlib.sha256(content).hexdigest()


def current_video(videos, snapshot_id, language):
    """The newest rendered video of this snapshot and language, or the newest
    failure if rendering last failed, or None."""
    for row in videos:
        if row["snapshot_id"] == snapshot_id and row["language"] == language:
            return row
    return None


def status(reviews, artifacts, snapshot_id, language):
    """Per format: draft, approved or changes_requested on the current bytes,
    changed_since_review when an earlier decision no longer matches, failed or
    not_rendered for a video. `artifacts` maps format to the current digest
    (None when nothing exists yet) or to "failed"."""
    out = {}
    for fmt in FORMATS:
        current = artifacts.get(fmt)
        mine = [r for r in reviews if r["format"] == fmt and r["language"] == language]
        exact = [r for r in mine if r["snapshot_id"] == snapshot_id and r["artifact_sha256"] == current]
        entry = {"artifact_sha256": current if current not in (None, "failed") else None, "review": None}
        if current == "failed":
            entry["state"] = "failed"
        elif current is None:
            entry["state"] = "not_rendered"
        elif exact:
            entry["state"], entry["review"] = exact[0]["decision"], exact[0]
        elif mine:
            entry["state"], entry["review"] = "changed_since_review", mine[0]
        else:
            entry["state"] = "draft"
        out[fmt] = entry
    return out


def record(store, *, run_id, snapshot_id, fmt, language, artifact_sha256, decision, comment, reviewer):
    if fmt not in FORMATS or decision not in DECISIONS or language not in ("en", "ar"):
        raise ReviewError("invalid")
    comment = (comment or "").strip()
    if len(comment) > MAX_COMMENT:
        raise ReviewError("invalid")
    if decision == "changes_requested" and not comment:
        raise ReviewError("comment_required")
    row = {"id": uuid.uuid4().hex, "run_id": run_id, "snapshot_id": snapshot_id, "format": fmt,
           "language": language, "artifact_sha256": artifact_sha256, "decision": decision,
           "comment": comment, "reviewer": reviewer,
           "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    return store.add_export_review(row)
