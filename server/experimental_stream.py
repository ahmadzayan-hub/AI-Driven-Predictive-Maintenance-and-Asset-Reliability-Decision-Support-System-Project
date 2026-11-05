"""Isolated synthetic event-time monitoring foundation.

This is a deterministic ingest/health layer, NOT a network-facing stream API.
The authorized connector supplies authenticated events. The persistence layer
deduplicates (owner, source, event ID) and tracks lateness without inventing live KPIs.
"""
from __future__ import annotations
import json
import math
import sqlite3
import time
from datetime import datetime, timezone

class EventRejected(ValueError):
    pass

def _epoch(iso):
    try:
        parsed = datetime.fromisoformat(iso.replace("Z","+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
        return int(parsed.timestamp())
    except (AttributeError,TypeError,ValueError) as exc:
        raise EventRejected("event_time must be an offset-aware ISO-8601 timestamp") from exc

def _db(path):
    db=sqlite3.connect(path,timeout=15,isolation_level=None)
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("""CREATE TABLE IF NOT EXISTS synthetic_events(
        owner TEXT NOT NULL, source TEXT NOT NULL, event_id TEXT NOT NULL,
        event_time INTEGER NOT NULL, received_at INTEGER NOT NULL,
        payload TEXT NOT NULL, late INTEGER NOT NULL,
        PRIMARY KEY(owner,source,event_id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS synthetic_stream_health(
        owner TEXT NOT NULL, source TEXT NOT NULL, max_event_time INTEGER NOT NULL,
        last_received_at INTEGER NOT NULL, accepted INTEGER NOT NULL,
        late INTEGER NOT NULL, duplicates INTEGER NOT NULL,
        PRIMARY KEY(owner,source))""")
    return db

def accept(db_path, *, owner, source, event, received_at=None,
           allowed_lateness_s=120, max_future_skew_s=60):
    if not owner or not source or len(owner)>128 or len(source)>128:
        raise EventRejected("Invalid stream identity")
    event_id=event.get("id")
    if not isinstance(event_id,str) or not event_id or len(event_id)>256:
        raise EventRejected("Missing event ID")
    instant=_epoch(event.get("event_time"))
    now=int(time.time()) if received_at is None else int(received_at)
    if not 0<=allowed_lateness_s<=86400 or not 0<=max_future_skew_s<=3600:
        raise EventRejected("Invalid lateness/skew configuration")
    if instant>now+max_future_skew_s:
        raise EventRejected("Future-dated sensor event")
    payload=event.get("payload")
    if not isinstance(payload,dict):
        raise EventRejected("Payload must be a JSON object")
    encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
    if len(encoded.encode("utf-8"))>65536:
        raise EventRejected("Event payload too large")
    db=_db(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("""SELECT max_event_time,last_received_at,accepted,late,duplicates
            FROM synthetic_stream_health WHERE owner=? AND source=?""",(owner,source)).fetchone()
        previous=row[0] if row else instant
        watermark=max(previous,instant)-allowed_lateness_s
        late=int(instant<watermark)
        inserted=db.execute("""INSERT OR IGNORE INTO synthetic_events VALUES(?,?,?,?,?,?,?)""",
            (owner,source,event_id,instant,now,encoded,late)).rowcount
        if row:
            db.execute("""UPDATE synthetic_stream_health SET max_event_time=?,
                last_received_at=?, accepted=?, late=?, duplicates=?
                WHERE owner=? AND source=?""",
                (max(previous,instant),max(row[1],now),row[2]+int(bool(inserted)),
                 row[3]+late*int(bool(inserted)),row[4]+int(not inserted),owner,source))
        else:
            db.execute("""INSERT INTO synthetic_stream_health VALUES(?,?,?,?,?,?,?)""",
                       (owner,source,instant,now,1,late,0))
        db.commit()
        return {"status":"accepted" if inserted else "duplicate",
                "late":bool(late) if inserted else None,"watermark":watermark}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def health(db_path, *, owner, source, now=None, stale_after_s=300):
    if stale_after_s<=0:
        raise ValueError("Invalid stale threshold")
    with _db(db_path) as db:
        row=db.execute("""SELECT max_event_time,last_received_at,accepted,late,duplicates
            FROM synthetic_stream_health WHERE owner=? AND source=?""",(owner,source)).fetchone()
    if row is None:
        return {"state":"no_data","accepted":0,"late":0,"duplicates":0}
    now=int(time.time()) if now is None else int(now)
    return {"state":"stale" if now-row[1]>stale_after_s else "fresh",
            "accepted":row[2],"late":row[3],"duplicates":row[4],
            "event_lag_seconds":max(0,now-row[0]),
            "ingest_lag_seconds":max(0,now-row[1])}
