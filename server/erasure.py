"""Erase everything belonging to one owner, and say what survived.

A deletion feature is judged by the things it misses. This one is built
to be checked rather than believed: it counts what it removes, it walks
the disk as well as the database, and it names — every time, in the same
report — the copies it cannot reach.

The honest part is the last one. An erasure that quietly leaves the
owner's rows inside last night's backup, or the markdown note somebody
synced into their own Obsidian vault, has not erased anything; it has
only stopped showing it. Saying so is not a disclaimer, it is the
result.
"""

import json
from pathlib import Path

# Children before parents, so foreign keys hold at every step.
DELETE_ORDER = ("tasks", "approvals", "artifacts", "vault_notes", "connectors", "kpi_policies",
                "runs", "datasets", "sessions", "memory_kv")

# Tables that carry an owner directly. Everything else in DELETE_ORDER
# belongs to an owner through the run it hangs off.
OWNED_DIRECTLY = ("runs", "datasets", "sessions", "memory_kv", "connectors")


def owned_run_ids(store, owner):
    return [row["id"] for row in
            store._exec("SELECT id FROM runs WHERE owner = ?", (owner,))]


def _target_runs(store, owner, plan):
    # Shared evidence survives a creator's personal erasure. Conversely, a
    # deleted sole-member organization can hold a report created by an earlier
    # member. Follow the pack boundary rather than the run creator alone.
    ids = {row["id"] for row in store._exec(
        "SELECT id FROM runs WHERE owner = ? AND id NOT IN (SELECT id FROM rmd_runs)", (owner,))}
    for row in store._exec("SELECT r.id,p.owner,p.organization_id FROM rmd_runs r JOIN rmd_packs p ON p.id=r.pack_id"):
        if ((not row["organization_id"] and row["owner"] == owner)
                or row["organization_id"] in plan.get("delete_organizations", [])):
            ids.add(row["id"])
    return sorted(ids)


def _owner_counts(store, owner, run_ids):
    counts = {}
    for table in DELETE_ORDER:
        if table in OWNED_DIRECTLY and table != "runs":
            rows = store._exec(f"SELECT COUNT(*) AS n FROM {table} WHERE owner = ?", (owner,))
        elif not run_ids:
            counts[table] = 0
            continue
        else:
            # One query per run avoids SQLite parameter limits for long-lived
            # workspaces and uses only the registered table/column constants.
            column = "id" if table == "runs" else "run_id"
            rows = [{"n": sum(store._exec(f"SELECT COUNT(*) AS n FROM {table} WHERE {column} = ?", (rid,))[0]["n"]
                              for rid in run_ids)}]
        counts[table] = int(rows[0]["n"]) if rows else 0
    return counts


def survey(store, owner):
    """What this owner has, without changing anything."""
    counts = {}
    from server.operations import operations_erasure_plan, operations_erasure_counts, OperationsError
    try:
        operations = operations_erasure_plan(store, owner)
        run_ids = _target_runs(store, owner, operations)
        counts.update(_owner_counts(store, owner, run_ids))
        counts.update(operations_erasure_counts(store, owner, operations))
    except OperationsError as error:
        operations = {"blocked": error.code, "message": error.message}
        run_ids = _target_runs(store, owner, {})
        counts.update(_owner_counts(store, owner, run_ids))
    from server.rmd_schema import rmd_counts
    counts.update(rmd_counts(store, owner, operations.get("delete_organizations", [])))
    return {"owner": owner, "runs": len(run_ids), "rows": counts,
            "total_rows": sum(counts.values()), "operations": operations}


def published_paths(store, run_ids):
    """Vault notes belonging to these runs, as repository-relative paths."""
    if not run_ids:
        return []
    marks = ", ".join("?" * len(run_ids))
    return [row["path"] for row in store._exec(
        f"SELECT path FROM vault_notes WHERE run_id IN ({marks})",
        tuple(run_ids))]


def erase_vault_paths(vault_dir, notes):
    """Remove contained local publications; identify copies left out of reach."""
    deleted, missing = [], []
    if not vault_dir:
        return deleted, list(notes)
    root = Path(vault_dir).resolve()
    for relative in notes:
        path = root / relative
        try:
            path.resolve().relative_to(root)
        except (ValueError, OSError):
            missing.append(f"{relative} (outside the vault; left alone)")
            continue
        try:
            path.unlink()
            deleted.append(relative)
        except FileNotFoundError:
            missing.append(relative)
        except OSError:
            missing.append(f"{relative} (local removal failed)")
    return deleted, missing


def erase(store, owner, vault_dir=None, memory_file=None):
    """Delete one owner's data. Returns a report of what happened.

    The database and the disk are both walked, because a published
    report exists in two places and deleting one of them is the mistake
    this function is written to avoid.
    """
    from server.operations import operations_erasure_plan, erase_operations
    with store.atomic("operations:create:" + owner):
        memberships = store._exec("SELECT org_id FROM organization_members WHERE subject = ? ORDER BY org_id", (owner,))
        for membership in memberships:
            store._lock_transaction("operations:" + membership["org_id"])
        operations_plan = operations_erasure_plan(store, owner)
        run_ids = _target_runs(store, owner, operations_plan)
        notes = published_paths(store, run_ids)
        before = _owner_counts(store, owner, run_ids)
        from server.rmd_schema import erase_owner_rmd, rmd_counts
        evidence_counts = rmd_counts(store, owner, operations_plan["delete_organizations"])
        erase_owner_rmd(store, owner)
        deleted = erase_operations(store, owner, operations_plan)
        deleted.update(evidence_counts)
        for table in DELETE_ORDER:
            if table in OWNED_DIRECTLY and table != "runs":
                store._exec_rowcount(
                    f"DELETE FROM {table} WHERE owner = ?", (owner,))
            else:
                column = "id" if table == "runs" else "run_id"
                for rid in run_ids:
                    store._exec_rowcount(f"DELETE FROM {table} WHERE {column} = ?", (rid,))
            # Evidence lifecycle may already have removed these rows in this
            # transaction. Count all removals once, from the captured targets.
            deleted[table] = before[table]

    files_deleted, files_missing = erase_vault_paths(vault_dir, notes)

    memory_file_cleared = False
    if memory_file and owner == "local-owner":
        # Local mode keeps memory in data/memory.json, outside the
        # database entirely. Erasing the database and leaving that file
        # would be the clearest possible version of this function's
        # failure mode.
        path = Path(memory_file)
        if path.exists():
            path.write_text(json.dumps({}, indent=4), encoding="utf-8")
            memory_file_cleared = True

    return {
        "owner": owner,
        "runs": len(run_ids),
        "deleted": deleted,
        "total_rows": sum(deleted.values()),
        "vault_files_deleted": files_deleted,
        "vault_files_not_found": files_missing,
        "memory_file_cleared": memory_file_cleared,
        "organization_data_retained": operations_plan["retained_organizations"],
        "not_reached": not_reached(),
    }


def not_reached():
    """Copies this command cannot touch, listed every time.

    Not a disclaimer — the point of the report. A data-subject request
    answered with "deleted" when these exist is answered wrongly.
    """
    return [
        "Database backups: every backup taken before this erasure still "
        "contains the owner's rows. Restoring one restores them. Delete or "
        "rotate the backups as well (scripts/backup.py writes to backups/).",
        "Shared organization business records, maintenance outcomes, evidence "
        "snapshots and original actor audit identifiers belong to the organization "
        "and are retained. Personal erasure removes membership and replay receipts. "
        "The final owner must transfer ownership first. Sole-member organizations "
        "are deleted with their operational records. Worker heartbeats contain "
        "service identifiers and are retained as operational metadata.",
        "Obsidian vaults synced elsewhere: a published report copied into "
        "someone's own vault, a cloud sync, or a git repository is beyond "
        "this database and this machine.",
        "Exports the owner downloaded themselves, and anything a reader "
        "saved from a report before it was erased.",
        "Operational logs and CI artifacts, which may quote a goal or a "
        "dataset name in passing.",
    ]
