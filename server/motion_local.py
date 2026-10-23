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
STATES = ("QUEUED", "RUNNING", "FAILED", "RENDERED_DRAFT",
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

    def create(self, owner, run_id, run, audio: bytes | None, suffix=".wav", *, storyboard=None):
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
        name = job_id + suffix if audio else None
        sha = hashlib.sha256(audio).hexdigest() if audio else None
        if audio:
            target = self.base / name
            with target.open("xb") as stream:
                stream.write(audio)
            try:
                target.chmod(0o600)
            except OSError:
                pass
        with self.lock, self.connect() as con:
            con.execute("""INSERT INTO motion_jobs
                (id,run_id,owner,storyboard,storyboard_sha,audio_name,audio_sha,status,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (job_id,run_id,owner,story_raw,digest,name,sha,"QUEUED",datetime.now(UTC).isoformat()))
        WORKERS.submit(self._encode, job_id)
        return {"id": job_id, "status": "QUEUED", "publication_allowed": False}

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
            self._update(job_id, "RUNNING")
            story = json.loads(row["storyboard"])
            if hashlib.sha256(row["storyboard"].encode()).hexdigest() != row["storyboard_sha"]:
                raise MotionError("Source storyboard was changed")
            from scripts.motion_studio_render import mux_frames, probe_audio
            from scripts.motion_studio_frames import render_frames
            from scripts.motion_studio_qc import inspect_mp4
            font = Path(os.environ.get("AGENTIC_MOTION_FONT", ""))
            if not font.is_file() or font.suffix.lower() not in {".ttf",".otf"}:
                raise MotionError("Approved local TTF/OTF font not configured")
            audio = self.base / row["audio_name"] if row["audio_name"] else None
            if audio is not None and (
                not audio.is_file() or file_digest(audio) != row["audio_sha"]
            ):
                raise MotionError("Narration has changed")
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
