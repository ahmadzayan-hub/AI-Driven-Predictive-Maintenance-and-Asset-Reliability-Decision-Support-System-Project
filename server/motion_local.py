"""Opt-in LOCAL Motion Studio MP4 queue, restricted to owned run evidence.

Not mounted on serverless Vercel: video encoding needs an isolated, persistent
filesystem worker and reviewed infrastructure. This module never publishes media.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from server.motion_storyboard import from_run, MotionStoryRefused

WORKERS = ThreadPoolExecutor(max_workers=1, thread_name_prefix="motion-local")
MAX_BYTES = 24_000_000
STATES = ("SCRIPT_REVIEW_REQUESTED", "SCRIPT_APPROVED", "QUEUED", "RUNNING", "FAILED", "RENDERED_DRAFT",
          "REVIEW_REQUESTED", "INTERNAL_APPROVED", "RETURNED")


class MotionError(ValueError):
    pass


def file_digest(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def root():
    raw = os.environ.get("AGENTIC_MOTION_ROOT", "")
    if not raw:
        raise MotionError("AGENTIC_MOTION_ROOT must point to an approved persistent local directory")
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        raise MotionError("Motion rendering requires persistent isolated infrastructure, not ephemeral serverless")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise MotionError("Motion media root must be absolute")
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


class LocalMotion:
    def __init__(self):
        self.base = root()
        self.database = self.base / "motion.sqlite3"
        self.lock = threading.RLock()
        self._initialize()
        try:
            self.database.chmod(0o600)
        except OSError:
            pass

    def connect(self):
        con = sqlite3.connect(str(self.database), timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def _initialize(self):
        with self.lock, self.connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS motion_jobs (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL, owner TEXT NOT NULL,
                storyboard TEXT NOT NULL, storyboard_sha TEXT NOT NULL,
                audio_name TEXT, audio_sha TEXT, status TEXT NOT NULL,
                video_name TEXT, video_sha TEXT, qa_json TEXT, error TEXT,
                reviewer TEXT, reviewer_note TEXT, review_checks TEXT,
                created_at TEXT NOT NULL, reviewed_at TEXT
            )""")
            # A restarted worker never reports an incomplete job as completed.
            con.execute("UPDATE motion_jobs SET status='FAILED', error='Interrupted by server restart'"
                        " WHERE status IN ('RUNNING','QUEUED')")

    def _record(self, job_id):
        """Internal lookup; HTTP callers must apply current source ACL first."""
        with self.lock, self.connect() as con:
            row = con.execute("SELECT * FROM motion_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise MotionError("Video unavailable / الفيديو غير متاح")
        return dict(row)

    def record(self, job_id, owner):
        with self.lock, self.connect() as con:
            row = con.execute("SELECT * FROM motion_jobs WHERE id=? AND owner=?", (job_id, owner)).fetchone()
        if row is None:
            raise MotionError("No such video job owned by this account")
        return dict(row)

    def create(self, *args, **kwargs):
        created = []
        try:
            with self.lock, self.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                result = self._create(*args, **kwargs, con=con, created=created)
        except Exception:
            # Only this request's exclusively created narration files, never old
            # media. A database rollback must not leak a large orphan upload.
            for path in created:
                path.unlink(missing_ok=True)
            raise
        if result["status"] == "QUEUED":
            self._enqueue(result["id"])
        return result

    def _enqueue(self, job_id):
        try:
            WORKERS.submit(self._encode, job_id)
        except Exception:
            self._update(job_id, "FAILED", error="Render worker unavailable; create a reviewed repair draft")
            raise MotionError("Render worker unavailable; job failed, not queued for execution") from None

    def _create(self, owner, run_id, run, audio: bytes | None, suffix=".wav", *, storyboard=None, workflow=None, con, created):
        if not isinstance(owner, str) or not owner.strip():
            raise MotionError("Owner is missing")
        if audio and (len(audio) > MAX_BYTES or len(audio) == 0):
            raise MotionError("Invalid narration size")
        if suffix not in {".wav",".mp3",".m4a",".aac",".flac"}:
            raise MotionError("Unsupported narration format")
        story = from_run(run) if storyboard is None else storyboard
        if story["language"] == "ar" and not audio:
            raise MotionError("Arabic media requires an attached human-approved narration")
        story_raw = json.dumps(story, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(story_raw.encode()).hexdigest()
        job_id = "MOT-" + uuid.uuid4().hex[:20]
        if workflow:
            workflow = dict(workflow)
            workflow["root_id"] = workflow.get("root_id") or job_id
            if workflow.get("parent_id"):
                parent = con.execute("SELECT * FROM motion_jobs WHERE id=? AND owner=?",
                                     (workflow["parent_id"], owner)).fetchone()
                prior = self.workflow(parent) if parent else None
                if (not prior or parent["run_id"] != run_id or parent["status"] not in {"FAILED", "RETURNED"}
                        or workflow["root_id"] != prior["root_id"]
                        or workflow.get("repair_attempt") != prior["repair_attempt"] + 1
                        or workflow["repair_attempt"] > 2 or not workflow.get("repair_note", "").strip()):
                    raise MotionError("Invalid repair lineage or exhausted repair budget")
                rows = con.execute("SELECT review_checks FROM motion_jobs WHERE owner=?", (owner,)).fetchall()
                existing = [self.workflow(row) for row in rows]
                siblings = [f for f in existing if f and f.get("root_id") == workflow["root_id"] and f.get("parent_id")]
                if len(siblings) >= 2 or any(f["parent_id"] == workflow["parent_id"] for f in siblings):
                    raise MotionError("Repair budget consumed or child draft already exists; human escalation required")
        name = job_id + suffix if audio else None
        sha = hashlib.sha256(audio).hexdigest() if audio else None
        if audio:
            target = self.base / name
            with target.open("xb") as stream:
                created.append(target)
                stream.write(audio)
            try:
                target.chmod(0o600)
            except OSError:
                pass
        con.execute("""INSERT INTO motion_jobs
            (id,run_id,owner,storyboard,storyboard_sha,audio_name,audio_sha,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (job_id,run_id,owner,story_raw,digest,name,sha,
             "SCRIPT_REVIEW_REQUESTED" if workflow else "QUEUED",datetime.now(UTC).isoformat()))
        if workflow:
            workflow = dict(workflow)
            workflow["binding"] = self.script_binding(digest, sha, workflow)
            con.execute("UPDATE motion_jobs SET review_checks=? WHERE id=?",
                        (json.dumps({"workflow": workflow}), job_id))
        return {"id": job_id, "status": "SCRIPT_REVIEW_REQUESTED" if workflow else "QUEUED",
                "publication_allowed": False}

    @staticmethod
    def script_binding(story_sha, audio_sha, workflow):
        payload = {"storyboard_sha": story_sha, "audio_sha": audio_sha,
                   **{key: workflow.get(key) for key in ("audience", "format", "parent_id", "repair_attempt", "repair_note", "root_id")}}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    @staticmethod
    def workflow(row):
        return json.loads(row["review_checks"] or "{}").get("workflow")

    def script(self, job_id, owner):
        row = self.record(job_id, owner)
        self.verify_content(row)
        flow = self.workflow(row)
        if not flow:
            raise MotionError("This legacy job has no script approval workflow; create a new draft")
        return {"id": job_id, "status": row["status"], "storyboard": json.loads(row["storyboard"]),
                "workflow": flow, "narration_attached": bool(row["audio_sha"]), "publication_allowed": False}

    def approve_script(self, job_id, reviewer, binding, checks):
        with self.lock, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM motion_jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row["status"] != "SCRIPT_REVIEW_REQUESTED":
                raise MotionError("Script is not waiting for review")
            if reviewer == row["owner"]:
                raise MotionError("Four-eyes rule: script author cannot approve")
            self.verify_content(row)
            flow = self.workflow(row)
            if not flow or binding != flow["binding"] or binding != self.script_binding(row["storyboard_sha"], row["audio_sha"], flow):
                raise MotionError("Script approval binding changed; create a new draft")
            required = ("reviewed_script", "checked_evidence", "checked_audience_format", "checked_narration_rights")
            if not all(checks.get(k) is True for k in required):
                raise MotionError("Human script checklist incomplete")
            flow["approval"] = {"reviewer": reviewer, "binding": binding, "checks": checks,
                                "approved_at": datetime.now(UTC).isoformat()}
            con.execute("UPDATE motion_jobs SET status='SCRIPT_APPROVED', review_checks=? WHERE id=?",
                        (json.dumps({"workflow": flow}), job_id))
        return {"id": job_id, "status": "SCRIPT_APPROVED", "publication_allowed": False}

    def render_approved(self, job_id, owner):
        with self.lock, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM motion_jobs WHERE id=? AND owner=?", (job_id, owner)).fetchone()
            if row is None or row["status"] != "SCRIPT_APPROVED":
                raise MotionError("Explicit human script approval is required before rendering")
            if not self.workflow(row):
                raise MotionError("Explicit human script approval is required before rendering")
            self.verify_script_approval(row)
            con.execute("UPDATE motion_jobs SET status='QUEUED' WHERE id=?", (job_id,))
        self._enqueue(job_id)
        return {"id": job_id, "status": "QUEUED", "publication_allowed": False}

    def verify_content(self, row):
        if hashlib.sha256(row["storyboard"].encode()).hexdigest() != row["storyboard_sha"]:
            raise MotionError("Source storyboard was changed")
        if row["audio_name"]:
            audio = self.base / row["audio_name"]
            if not audio.is_file() or file_digest(audio) != row["audio_sha"]:
                raise MotionError("Narration has changed")

    def verify_script_approval(self, row):
        self.verify_content(row)
        flow = self.workflow(row)
        if flow:
            approval = flow.get("approval", {})
            binding = self.script_binding(row["storyboard_sha"], row["audio_sha"], flow)
            if (approval.get("binding") != binding or flow.get("binding") != binding
                    or not approval.get("reviewer") or approval["reviewer"] == row["owner"]):
                raise MotionError("Script approval is missing or stale")

    def _update(self, job_id, status, **fields):
        parts = ["status=?"] + [f"{key}=?" for key in fields]
        with self.lock, self.connect() as con:
            con.execute("UPDATE motion_jobs SET " + ",".join(parts) + " WHERE id=?",
                        [status, *fields.values(), job_id])

    def _encode(self, job_id):
        try:
            with self.lock, self.connect() as con:
                row = con.execute("SELECT * FROM motion_jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                return
            self.verify_script_approval(row)
            self._update(job_id, "RUNNING")
            story = json.loads(row["storyboard"])
            if hashlib.sha256(row["storyboard"].encode()).hexdigest() != row["storyboard_sha"]:
                raise MotionError("Source storyboard was changed")
            audio = self.base / row["audio_name"] if row["audio_name"] else None
            if audio is not None and (
                not audio.is_file() or file_digest(audio) != row["audio_sha"]
            ):
                raise MotionError("Narration has changed")
            from scripts.motion_studio_render import mux_frames, probe_audio
            from scripts.motion_studio_frames import render_frames
            from scripts.motion_studio_qc import inspect_mp4
            font = Path(os.environ.get("AGENTIC_MOTION_FONT", ""))
            if not font.is_file() or font.suffix.lower() not in {".ttf",".otf"}:
                raise MotionError("Approved local TTF/OTF font not configured")
            duration = probe_audio(audio) if audio else float(story["duration"])
            if duration > 60:
                raise MotionError("Local worker limited to 60 seconds; use approved dedicated renderer")
            video = self.base / (job_id + ".mp4")
            with tempfile.TemporaryDirectory(prefix="frames-", dir=self.base) as temporary:
                frames = Path(temporary)
                render_frames(story, frames, font, duration=duration)
                mux_frames(frames, video, audio, duration=duration)
            qa = inspect_mp4(video, expected_seconds=duration,
                             narration_expected=bool(audio), expected_format=story["format"])
            try:
                video.chmod(0o600)
            except OSError:
                pass
            self._update(job_id, "RENDERED_DRAFT", video_name=video.name,
                         video_sha=qa["sha256"], qa_json=json.dumps(qa))
        except Exception as exc:  # job failure must not terminate the shared worker
            self._update(job_id, "FAILED", error=f"{type(exc).__name__}: {str(exc)[:400]}")

    def view(self, job_id, owner):
        row = self.record(job_id, owner)
        return {k:row[k] for k in ("id","run_id","status","error","video_sha","reviewer",
                                  "reviewer_note","reviewed_at")} | {
            "qa": json.loads(row["qa_json"]) if row["qa_json"] else None,
            "publication_allowed": False,
        }

    def preview(self, job_id, owner):
        row = self.record(job_id, owner)
        if row["status"] not in {"RENDERED_DRAFT","REVIEW_REQUESTED","INTERNAL_APPROVED","RETURNED"}:
            raise MotionError("MP4 not ready")
        path = self.base / row["video_name"]
        if not path.is_file() or file_digest(path) != row["video_sha"]:
            raise MotionError("Rendered media was removed or altered")
        return path

    def submit(self, job_id, owner):
        row = self.record(job_id, owner)
        if row["status"] != "RENDERED_DRAFT":
            raise MotionError("Video must be rendered before review submission")
        self._update(job_id, "REVIEW_REQUESTED")
        return self.view(job_id, owner)

    def decide(self, job_id, reviewer, outcome, note, checks, approval_allowed=False):
        if not approval_allowed:
            raise MotionError("Reviewer needs an approval-capable identity")
        if outcome not in ("approve","return"):
            raise MotionError("Unsupported decision")
        with self.lock, self.connect() as con:
            # One terminal human decision, including across separate instances.
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM motion_jobs WHERE id=?", (job_id,)).fetchone()
            if row is None or row["status"] != "REVIEW_REQUESTED":
                raise MotionError("Video is not waiting for review")
            if reviewer == row["owner"]:
                raise MotionError("Four-eyes rule: video author cannot approve")
            required = ("watched_full_video","checked_audio_alignment","checked_arabic",
                        "checked_evidence","checked_brand_and_rights")
            if outcome == "approve" and not all(checks.get(k) is True for k in required):
                raise MotionError("Human checklist incomplete")
            if outcome == "return" and not (note or "").strip():
                raise MotionError("A return requires an explanation")
            if hashlib.sha256(row["storyboard"].encode()).hexdigest() != row["storyboard_sha"]:
                raise MotionError("Source storyboard was changed")
            self.preview(job_id, row["owner"])
            status = "INTERNAL_APPROVED" if outcome == "approve" else "RETURNED"
            con.execute("UPDATE motion_jobs SET status=?, reviewer=?, reviewer_note=?, review_checks=?, reviewed_at=? WHERE id=?",
                        (status, reviewer, (note or "")[:2000],
                         json.dumps({**json.loads(row["review_checks"] or "{}"), **checks}),
                         datetime.now(UTC).isoformat(), job_id))
        return {"status": status, "reviewer": reviewer, "publication_allowed": False}
