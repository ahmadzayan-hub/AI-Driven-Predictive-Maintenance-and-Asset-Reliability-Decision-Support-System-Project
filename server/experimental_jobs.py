"""Isolated prototype of a durable, owner-scoped video/ingest job queue.

No HTTP endpoints, production deployment, secrets, network calls or video rendering.
Only a trusted backend service may call this module. SQLite is for local acceptance;
hosted operation needs an approved transactional queue and private object storage.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

MAX_ATTEMPTS = 3

def _connect(db_path):
    db = sqlite3.connect(db_path, timeout=15, isolation_level=None)
    db.execute("PRAGMA busy_timeout = 15000")
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS isolated_jobs (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL,
        request_sha256 TEXT NOT NULL, state TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0, lease_until INTEGER NOT NULL DEFAULT 0,
        worker TEXT, artifact_sha256 TEXT, error TEXT,
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
        UNIQUE(owner,kind,request_sha256)
    )""")
    return db

def submit(db_path, *, owner, kind, request_sha256):
    if not owner or kind not in ("video", "ingest") or len(request_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in request_sha256):
        raise ValueError("Invalid owner, kind, or digest")
    with _connect(db_path) as db:
        now = int(time.time())
        job_id = uuid.uuid4().hex
        db.execute("""INSERT OR IGNORE INTO isolated_jobs
            (id,owner,kind,request_sha256,state,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?)""",
            (job_id, owner, kind, request_sha256, "queued", now, now))
        row = db.execute("""SELECT id,state FROM isolated_jobs WHERE
            owner=? AND kind=? AND request_sha256=?""",
            (owner,kind,request_sha256)).fetchone()
        return {"id":row[0],"state":row[1]}

def claim(db_path, *, worker, kind, lease_seconds=120):
    if not worker or kind not in ("video","ingest") or not 30 <= lease_seconds <= 3600:
        raise ValueError("Invalid worker, kind or lease")
    db=_connect(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        now = int(time.time())
        row = db.execute("""SELECT id,owner,request_sha256,attempts
            FROM isolated_jobs WHERE kind=? AND attempts<? AND
            (state='queued' OR (state='running' AND lease_until<?))
            ORDER BY created_at,id LIMIT 1""", (kind,MAX_ATTEMPTS,now)).fetchone()
        if row is None:
            db.commit()
            return None
        job_id, owner, digest, attempts = row
        db.execute("""UPDATE isolated_jobs SET state='running', attempts=?,
            worker=?, lease_until=?, updated_at=? WHERE id=?""",
            (attempts+1,worker,now+lease_seconds,now,job_id))
        db.commit()
        return {"id":job_id,"owner":owner,"kind":kind,"request_sha256":digest,"attempt":attempts+1}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def finish(db_path, *, owner, job_id, worker, success, artifact_sha256=None, error=None):
    if success and (not artifact_sha256 or len(artifact_sha256)!=64 or
        any(c not in "0123456789abcdef" for c in artifact_sha256)):
        raise ValueError("Successful work requires SHA-256")
    db=_connect(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        now=int(time.time())
        updated=db.execute("""UPDATE isolated_jobs SET state=?, artifact_sha256=?,
            error=?, lease_until=0, worker=NULL, updated_at=?
            WHERE id=? AND owner=? AND worker=? AND state='running' AND lease_until>=?""",
            ("awaiting_review" if success else "failed",artifact_sha256,
             None if success else (error or "Worker failed")[:500],now,
             job_id,owner,worker,now)).rowcount
        db.commit()
        return updated==1
    finally:
        db.close()

def status(db_path, *, owner, job_id):
    with _connect(db_path) as db:
        row=db.execute("""SELECT id,kind,state,attempts,artifact_sha256,error
            FROM isolated_jobs WHERE owner=? AND id=?""",(owner,job_id)).fetchone()
    return dict(zip(("id","kind","state","attempts","artifact_sha256","error"),row)) if row else None
