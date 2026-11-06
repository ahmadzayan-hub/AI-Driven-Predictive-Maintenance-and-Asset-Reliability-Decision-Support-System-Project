"""Isolated worker adapter: executes an injected synthetic/local renderer only.

Not connected to public routes or hosted storage. The trusted backend supplies
render(kind, job) returning bytes; NEVER expose the callback to untrusted input.
Actual Chromium/FFmpeg integration requires a separate approved deployment.
"""
from __future__ import annotations
import hashlib
import os
import tempfile
from pathlib import Path

from server.experimental_jobs import claim, finish

MAX_ARTIFACT_BYTES = 30_000_000

def process_one(db_path, storage_root, *, worker_id, kind, render):
    if not callable(render):
        raise ValueError("A trusted render callback is required")
    job=claim(db_path,worker=worker_id,kind=kind)
    if not job:
        return None
    root=Path(storage_root)
    # Job ID generated server-side as UUID hex. Never derive paths from owner input.
    artifact=root / (job["id"] + (".mp4" if kind=="video" else ".bin"))
    temp_name=None
    try:
        if root.is_symlink():
            raise ValueError("Storage root must not be a symbolic link")
        root.mkdir(parents=True,exist_ok=True,mode=0o700)
        if artifact.exists() or artifact.is_symlink():
            raise ValueError("Existing artifact path; refusing overwrite")
        content=render(kind,dict(job))
        if not isinstance(content,bytes) or not 0<len(content)<=MAX_ARTIFACT_BYTES:
            raise ValueError("Invalid or oversized artifact")
        fd,temp_name=tempfile.mkstemp(prefix=".partial-",dir=root)
        with os.fdopen(fd,"wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp_name,0o600)
        if artifact.exists() or artifact.is_symlink():
            raise ValueError("Artifact path became occupied")
        os.replace(temp_name,artifact)
        temp_name=None
        digest=hashlib.sha256(content).hexdigest()
        accepted=finish(db_path,owner=job["owner"],job_id=job["id"],
                        worker=worker_id,success=True,artifact_sha256=digest)
        if not accepted:
            artifact.unlink(missing_ok=True)
            raise RuntimeError("Job lease expired; artifact withheld")
        return {"id":job["id"],"state":"awaiting_review","sha256":digest}
    except Exception as exc:
        # Failed render only records an error, never publishes a partial artifact.
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
        finish(db_path,owner=job["owner"],job_id=job["id"],
               worker=worker_id,success=False,error=type(exc).__name__)
        raise
