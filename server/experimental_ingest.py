"""Isolated, opt-in disk-backed large table ingestion; NOT wired to public upload API.

For 300 MB uploads use authenticated multipart object storage, not Vercel request bodies.
The main analytics contract retains its current independent limits.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

MAX_UPLOAD_BYTES = 300_000_000

class LargeIntakeError(ValueError):
    pass

def spool(chunks, dest, *, max_bytes=MAX_UPLOAD_BYTES):
    dest=Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=dest.parent,prefix=".incoming-")
    size=0
    digest=hashlib.sha256()
    try:
        with os.fdopen(fd,"wb") as output:
            for chunk in chunks:
                if not isinstance(chunk,bytes):
                    raise LargeIntakeError("Non-byte upload segment")
                size+=len(chunk)
                if size>max_bytes:
                    raise LargeIntakeError("Upload exceeds limit")
                output.write(chunk)
                digest.update(chunk)
        if not size:
            raise LargeIntakeError("Empty upload")
        os.replace(tmp,dest)
        return {"bytes":size,"sha256":digest.hexdigest()}
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def index_csv(source, database, *, batch_size=500):
    """Store a wide table as one JSON array per row, not one SQLite column per field.

    Stream rows using O(batch_size * row_width) memory, not O(number_of_rows).
    Client must authorize both paths. Column projection and analytics remain separate.
    """
    source=Path(source)
    database=Path(database)
    database.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(database)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS wide_records (ordinal INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS wide_meta (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM wide_records")
        db.execute("DELETE FROM wide_meta")
        with source.open(newline="",encoding="utf-8-sig") as stream:
            rows=csv.reader(stream)
            header=next(rows,None)
            if not header or not all(header) or len(set(header))!=len(header):
                raise LargeIntakeError("Missing or duplicate headers")
            batch=[]
            count=0
            for ordinal,row in enumerate(rows,1):
                if len(row)!=len(header):
                    raise LargeIntakeError(f"Incorrect field count on row {ordinal+1}")
                batch.append((ordinal,json.dumps(row,ensure_ascii=False,separators=(",",":"))))
                count+=1
                if len(batch)>=batch_size:
                    db.executemany("INSERT INTO wide_records VALUES (?,?)",batch)
                    batch.clear()
            if batch:
                db.executemany("INSERT INTO wide_records VALUES (?,?)",batch)
            db.execute("INSERT OR REPLACE INTO wide_meta VALUES (?,?)",("columns",json.dumps(header,ensure_ascii=False)))
            db.commit()
        return {"rows":count,"columns":len(header)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def page(database, *, after=0, size=100):
    if not 1<=size<=1000:
        raise LargeIntakeError("Page size must be 1 to 1000")
    with sqlite3.connect(database) as db:
        columns=json.loads(db.execute("SELECT value FROM wide_meta WHERE name='columns'").fetchone()[0])
        entries=db.execute("SELECT ordinal,payload FROM wide_records WHERE ordinal>? ORDER BY ordinal LIMIT ?",(after,size)).fetchall()
    return {"columns":columns,"rows":[{"ordinal":n,"values":json.loads(v)} for n,v in entries],"next":entries[-1][0] if entries else None}
