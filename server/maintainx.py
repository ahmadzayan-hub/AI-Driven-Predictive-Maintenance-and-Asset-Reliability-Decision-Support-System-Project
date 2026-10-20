"""Bounded read-only MaintainX synchronization through the existing egress fence.

Contract: public OpenAPI /v1/assets and /v1/workorders, reviewed 2026-10-21.
Never follows nextPageUrl. A failed/incomplete collection produces no snapshot
or new watermark. The caller commits the returned snapshot atomically.
"""
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from server.connectors import fetch

BASE_URL = "https://api.getmaintainx.com/v1/"
MAX_PAGES = 30
MAX_RECORDS = 5000
MAX_BYTES = 8_000_000
TOTAL_SECONDS = 60
OVERLAP_SECONDS = 300


class MaintainXError(ValueError):
    pass


def instant(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not result.tzinfo:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (AttributeError, ValueError, TypeError):
        raise MaintainXError("The source timestamp contract changed; no snapshot was committed.") from None


def scalar_text(value, limit=500):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 for c in value):
        raise MaintainXError("The source text contract changed; no snapshot was committed.")
    return value


def source_id(value):
    if type(value) is not int or value <= 0:
        raise MaintainXError("A source identifier is invalid; no snapshot was committed.")
    return str(value)


def normalize(kind, row):
    if not isinstance(row, dict):
        raise MaintainXError("The source record contract changed.")
    item = {"id": source_id(row.get("id")), "updated_at": instant(row.get("updatedAt")).isoformat()}
    if kind == "assets":
        item["name"] = scalar_text(row.get("name"), 160)
        item["location_id"] = source_id(row["locationId"]) if row.get("locationId") is not None else None
    else:
        item["title"] = scalar_text(row.get("title"), 200)
        if row.get("status") not in {"OPEN", "IN_PROGRESS", "ON_HOLD", "DONE", "CANCELED", "SKIPPED"}:
            raise MaintainXError("A work-order status is unsupported; no snapshot was committed.")
        item["status"] = row["status"]
        item["completed_at"] = instant(row["completedAt"]).isoformat() if row.get("completedAt") else None
        if "asset" not in row or (row["asset"] is not None and not isinstance(row["asset"], dict)):
            raise MaintainXError("The expanded asset contract changed; no snapshot was committed.")
        item["asset_id"] = source_id(row["asset"].get("id")) if row["asset"] is not None else None
        # Ambiguous/multi-asset work must be mapped explicitly; never infer a link.
    item["deleted_at"] = instant(row["deletedAt"]).isoformat() if row.get("deletedAt") else None
    return item


def synchronize(kind, owner, credential_id, previous=None, env=None, fetcher=fetch,
                clock=time.monotonic, now=None):
    if kind not in ("assets", "workorders") or not owner or not credential_id:
        raise MaintainXError("Choose assets or workorders and an operator-configured owner credential alias.")
    now = now or datetime.now(timezone.utc)
    records, since = {}, None
    if previous is not None:
        if not isinstance(previous, dict):
            raise MaintainXError("The previous snapshot is invalid; no snapshot was committed.")
        expected = (previous.get("schema_version"), previous.get("provider"), previous.get("kind"),
                    previous.get("owner"), previous.get("credential_id"))
        if expected != (1, "maintainx", kind, owner, credential_id):
            raise MaintainXError("The previous snapshot belongs to a different source or owner.")
        prior = previous.get("records")
        if not isinstance(prior, list) or len(prior) > MAX_RECORDS:
            raise MaintainXError("The previous snapshot is invalid or exceeds the record limit.")
        for row in prior:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].isdigit():
                raise MaintainXError("The previous snapshot has an invalid identifier.")
            instant(row.get("updated_at"))
            if row["id"] in records:
                raise MaintainXError("The previous snapshot contains duplicate identifiers.")
            records[row["id"]] = row
        if previous.get("watermark"):
            watermark = instant(previous["watermark"])
            if watermark > now:
                raise MaintainXError("The previous snapshot watermark is in the future.")
            since = (watermark - timedelta(seconds=OVERLAP_SECONDS)).isoformat()
    deadline, size, seen_cursors = clock() + TOTAL_SECONDS, 0, set()
    cursor, latest, fetched = None, instant(previous["watermark"]) if previous and previous.get("watermark") else None, 0
    for page_number in range(MAX_PAGES):
        params = {"limit": 200, "sort": "updatedAt", "updatedAt[lte]": now.isoformat()}
        if kind == "workorders":
            params["expand"] = "asset"
        if since:
            params["updatedAt[gte]"] = since
        if cursor:
            params["cursor"] = cursor
        remaining = deadline - clock()
        if remaining <= 0 or size >= MAX_BYTES:
            raise MaintainXError("The sync budget was reached; no snapshot was committed.")
        body = fetcher(BASE_URL + kind + "?" + urlencode(params), env=env, credential_id=credential_id,
                       owner=owner, timeout=min(15, remaining), limit=MAX_BYTES - size)
        size += len(body)
        if size > MAX_BYTES or clock() > deadline:
            raise MaintainXError("The sync budget was reached; no snapshot was committed.")
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError):
            raise MaintainXError("The source did not return valid JSON.") from None
        key = "assets" if kind == "assets" else "workOrders"
        if not isinstance(payload, dict) or not isinstance(payload.get(key), list) or "nextCursor" not in payload:
            raise MaintainXError("The source pagination contract changed; no snapshot was committed.")
        if len(payload[key]) > 200:
            raise MaintainXError("The source exceeded the requested page size.")
        for raw in payload[key]:
            item = normalize(kind, raw)
            changed = instant(item["updated_at"])
            if changed > now:
                raise MaintainXError("The source returned records beyond the requested snapshot time.")
            old = records.get(item["id"])
            if old is None or instant(old["updated_at"]) <= changed:
                records[item["id"]] = item
            latest = max(latest, changed) if latest else changed
            fetched += 1
            if len(records) > MAX_RECORDS:
                raise MaintainXError("The source exceeds this pilot's record limit; narrow the source before syncing.")
        cursor = payload["nextCursor"]
        if cursor is None:
            if payload.get("nextPageUrl"):
                raise MaintainXError("Pagination is incomplete; no snapshot was committed.")
            return {"schema_version": 1, "provider": "maintainx", "kind": kind, "owner": owner,
                    "credential_id": credential_id, "checked_at": now.isoformat(),
                    "watermark": latest.isoformat() if latest else None,
                    "records": sorted(records.values(), key=lambda r: r["id"]),
                    "fetched": fetched, "pages": page_number + 1,
                    "limitations": ["deletions_only_when_returned_by_source", "comments_not_in_updated_timestamp",
                                    "source_field_semantics_require_customer_validation"]}
        if not isinstance(cursor, str) or not cursor or len(cursor) > 2000 or cursor in seen_cursors:
            raise MaintainXError("The source cursor repeated or is invalid; no snapshot was committed.")
        seen_cursors.add(cursor)
    raise MaintainXError("The page limit was reached; no snapshot was committed.")


def asset_import(snapshot, site_id, idempotency_key, location_id, asset_ids, criticality):
    if snapshot.get("kind") != "assets" or snapshot.get("provider") != "maintainx":
        raise MaintainXError("An asset snapshot is required.")
    if criticality not in {"low", "medium", "high", "critical"} or not asset_ids:
        raise MaintainXError("Explicitly review the asset selection and criticality before import.")
    chosen = set(asset_ids)
    assets = [{"site_id": site_id, "source_system": "maintainx", "external_id": row["id"],
               "name": row["name"], "criticality": criticality}
              for row in snapshot["records"] if not row.get("deleted_at") and row["id"] in chosen
              and row.get("location_id") == str(location_id)]
    if {a["external_id"] for a in assets} != chosen:
        raise MaintainXError("Every selected asset must exist, be active and match the reviewed source location.")
    if not assets or len(assets) > 500:
        raise MaintainXError("Import one site containing between one and 500 reviewed assets per batch.")
    return {"schema_version": 1, "idempotency_key": idempotency_key, "assets": assets}
