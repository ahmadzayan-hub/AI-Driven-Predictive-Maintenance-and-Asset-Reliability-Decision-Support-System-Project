"""Portable evidence tables. Actual private sources are data, never Git fixtures."""

RMD_TABLES = (
    "rmd_packs", "rmd_sources", "rmd_analyses", "rmd_analysis_sources", "rmd_runs", "rmd_links", "rmd_actions",
    "rmd_incidents", "rmd_audit", "rmd_requests",
)
RMD_RESTORE_ORDER = RMD_TABLES

RMD_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS rmd_packs (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, organization_id TEXT,
      title TEXT NOT NULL, revision INTEGER NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS rmd_sources (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      name TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL,
      revision INTEGER NOT NULL, metadata_json TEXT NOT NULL,
      mapping_json TEXT NOT NULL, original_base64 TEXT NOT NULL,
      artifacts_json TEXT NOT NULL, applicability_json TEXT NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(pack_id, name, kind, sha256))""",
    """CREATE TABLE IF NOT EXISTS rmd_analyses (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      created_at TEXT NOT NULL, pack_revision INTEGER NOT NULL,
      fingerprint TEXT NOT NULL, language TEXT NOT NULL,
      filters_json TEXT NOT NULL, result_json TEXT NOT NULL,
      records_json TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS rmd_links (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES rmd_analyses(id),
      left_record_id TEXT NOT NULL, right_record_id TEXT NOT NULL,
      method TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
      detail_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS rmd_analysis_sources (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES rmd_analyses(id),
      sources_json TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS rmd_runs (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES rmd_analyses(id), created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS rmd_actions (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      analysis_id TEXT NOT NULL REFERENCES rmd_analyses(id),
      priority_id TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
      body_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(pack_id, analysis_id, priority_id))""",
    """CREATE TABLE IF NOT EXISTS rmd_incidents (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      title TEXT NOT NULL, record_ids_json TEXT NOT NULL,
      revision INTEGER NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS rmd_audit (
      id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES rmd_packs(id),
      actor TEXT NOT NULL, action TEXT NOT NULL, entity_id TEXT NOT NULL,
      revision INTEGER NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS rmd_requests (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, pack_id TEXT,
      operation TEXT NOT NULL, request_key TEXT NOT NULL,
      payload_hash TEXT NOT NULL, response_json TEXT NOT NULL,
      created_at TEXT NOT NULL, UNIQUE(owner, operation, request_key))""",
]


def ensure_schema(store):
    """Used by direct-service consumers; application storage also registers DDL."""
    for statement in RMD_SCHEMA:
        store._exec(statement)


def erase_pack_rmd(store, pack_id):
    """Child-first deletion works even when a local SQLite FK pragma is off."""
    # The binding is part of the run's authorization boundary. It must never be
    # removed while leaving an otherwise generic, accessible report behind.
    for run in store._exec("SELECT id FROM rmd_runs WHERE pack_id = ?", (pack_id,)):
        for table in ("tasks", "approvals", "artifacts", "vault_notes", "kpi_policies"):
            store._exec(f"DELETE FROM {table} WHERE run_id = ?", (run["id"],))
        store._exec("DELETE FROM runs WHERE id = ?", (run["id"],))
    for table in reversed(RMD_TABLES[1:]):
        store._exec(f"DELETE FROM {table} WHERE pack_id = ?", (pack_id,))
    store._exec("DELETE FROM rmd_packs WHERE id = ?", (pack_id,))


def erase_owner_rmd(store, owner):
    # Shared organization evidence belongs to the organization. Removing its
    # original creator does not erase other members' evidence or audit history.
    for row in store._exec("SELECT id FROM rmd_packs WHERE owner = ? AND (organization_id IS NULL OR organization_id = '')", (owner,)):
        erase_pack_rmd(store, row["id"])
    store._exec("DELETE FROM rmd_requests WHERE owner = ?", (owner,))


def erase_org_rmd(store, org_id):
    for row in store._exec("SELECT id FROM rmd_packs WHERE organization_id = ?", (org_id,)):
        erase_pack_rmd(store, row["id"])


def rmd_counts(store, owner=None, org_ids=()):
    """Count exactly the personal/shared packs erased by lifecycle operations."""
    pack_ids = set()
    if owner is not None:
        pack_ids.update(r["id"] for r in store._exec(
            "SELECT id FROM rmd_packs WHERE owner = ? AND (organization_id IS NULL OR organization_id = '')", (owner,)))
    for org_id in org_ids:
        pack_ids.update(r["id"] for r in store._exec("SELECT id FROM rmd_packs WHERE organization_id = ?", (org_id,)))
    result = {table: 0 for table in RMD_TABLES}
    result["rmd_packs"] = len(pack_ids)
    for table in RMD_TABLES[1:]:
        # Per-pack queries avoid backend placeholder/parameter ceilings.
        result[table] = sum(store._exec(f"SELECT COUNT(*) AS n FROM {table} WHERE pack_id = ?", (p,))[0]["n"] for p in pack_ids)
    if owner is not None:
        for row in store._exec("SELECT pack_id FROM rmd_requests WHERE owner = ?", (owner,)):
            if row["pack_id"] not in pack_ids:
                result["rmd_requests"] += 1
    return result
