"""Storage adapters for the run engine.

One narrow SQL store interface with two implementations:

- SQLiteStore — the local-first default (WAL journal, zero setup).
- PostgresStore — hosted mode via DATABASE_URL (psycopg2), pointed at a
  managed PostgreSQL such as Supabase. Imported lazily so the local app
  keeps working without the driver installed.

Both dialects share the same DDL and column names; only the parameter
placeholder differs. Rows cross the boundary as plain dicts, so the
engine never sees a driver type.
"""

import hashlib
import threading
from contextlib import contextmanager

# The single source of truth for which tables exist. Backup, restore and
# test teardown all derive from this, so adding a table cannot leave one
# of them stale (a bug that has already bitten once).
TABLES = (
    "runs",
    "tasks",
    "approvals",
    "artifacts",
    "sessions",
    "memory_kv",
    "vault_notes",
    "datasets",
    "connectors",
    "kpi_policies",
    "organizations", "organization_members", "operation_sites", "operation_assets",
    "work_orders", "operation_audit", "operation_requests", "worker_heartbeats", "reliability_trials",
)

# Restore must insert parents before children.
RESTORE_ORDER = (
    "datasets",
    "runs",
    "kpi_policies",
    "tasks",
    "approvals",
    "artifacts",
    "sessions",
    "memory_kv",
    "vault_notes",
    "connectors",
    "organizations", "organization_members", "operation_sites", "operation_assets",
    "work_orders", "operation_audit", "operation_requests", "worker_heartbeats", "reliability_trials",
)

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS organizations (
      id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS organization_members (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      subject TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, subject))""",
    """CREATE TABLE IF NOT EXISTS operation_sites (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      code TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, code))""",
    """CREATE TABLE IF NOT EXISTS operation_assets (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      site_id TEXT NOT NULL REFERENCES operation_sites(id),
      external_id TEXT NOT NULL, source_system TEXT NOT NULL, name TEXT NOT NULL,
      criticality TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, source_system, external_id))""",
    """CREATE TABLE IF NOT EXISTS work_orders (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      asset_id TEXT NOT NULL REFERENCES operation_assets(id), title TEXT NOT NULL,
      rationale TEXT NOT NULL, status TEXT NOT NULL, priority TEXT NOT NULL,
      assignee TEXT NOT NULL, due_date TEXT NOT NULL, evidence_json TEXT NOT NULL,
      completion_json TEXT NOT NULL, version INTEGER NOT NULL,
      created_by TEXT NOT NULL, authorized_by TEXT, created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS operation_audit (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      entity_id TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
      version INTEGER NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS operation_requests (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      actor TEXT NOT NULL, request_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
      response_json TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(org_id, actor, request_key))""",
    """CREATE TABLE IF NOT EXISTS worker_heartbeats (
      id TEXT PRIMARY KEY, seen_at TEXT NOT NULL, state TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS reliability_trials (
      id TEXT PRIMARY KEY, org_id TEXT NOT NULL REFERENCES organizations(id),
      created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      revision INTEGER NOT NULL, protocol_json TEXT NOT NULL, predictions_json TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY, goal TEXT NOT NULL, dataset_name TEXT NOT NULL,
      dataset_text TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, error TEXT)""",
    """CREATE TABLE IF NOT EXISTS tasks (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      idx INTEGER NOT NULL, role TEXT NOT NULL, title TEXT NOT NULL,
      state TEXT NOT NULL, summary TEXT, result_json TEXT, updated_at TEXT)""",
    # Display policies are append-only audit history, never report artifacts.
    # The unique version is also the cross-process optimistic-write guard.
    """CREATE TABLE IF NOT EXISTS kpi_policies (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      version INTEGER NOT NULL, revision TEXT NOT NULL, rules_json TEXT NOT NULL,
      actor TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE (run_id, version))""",
    """CREATE TABLE IF NOT EXISTS approvals (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      action TEXT NOT NULL, target TEXT NOT NULL, risk TEXT NOT NULL,
      impact TEXT NOT NULL, reversibility TEXT NOT NULL,
      content_hash TEXT NOT NULL, state TEXT NOT NULL,
      created_at TEXT NOT NULL, decided_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS artifacts (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
      name TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
      content TEXT NOT NULL, published_path TEXT, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      ended INTEGER NOT NULL, preferences_json TEXT NOT NULL,
      history_json TEXT NOT NULL, transcript_json TEXT NOT NULL,
      next_entry_id INTEGER NOT NULL)""",
    # Memory is per owner. The composite key matters as much as the
    # column: keys are handed out per owner, so the first thing two
    # tenants save is "memory_1" for both, and a single-column primary
    # key would make the second one collide.
    """CREATE TABLE IF NOT EXISTS memory_kv (
      owner TEXT NOT NULL, key TEXT NOT NULL, text TEXT NOT NULL,
      category TEXT NOT NULL, updated TEXT,
      PRIMARY KEY (owner, key))""",
    """CREATE TABLE IF NOT EXISTS vault_notes (
      path TEXT PRIMARY KEY, run_id TEXT NOT NULL,
      content TEXT NOT NULL, created_at TEXT NOT NULL)""",
    # Datasets are content-addressed: uploading the same file twice
    # stores one row, and runs reference it instead of duplicating it.
    """CREATE TABLE IF NOT EXISTS datasets (
      id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, name TEXT NOT NULL,
      content TEXT NOT NULL, byte_size INTEGER NOT NULL,
      owner TEXT NOT NULL, created_at TEXT NOT NULL)""",
    # Live data (ADR 0034): an owner's saved source, what its last
    # refresh found, when the next one is due, and the worker's lease.
    """CREATE TABLE IF NOT EXISTS connectors (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
      url TEXT NOT NULL, format TEXT, sheet TEXT, every_minutes INTEGER,
      goal TEXT NOT NULL, language TEXT NOT NULL, profile TEXT,
      enabled INTEGER NOT NULL, failures INTEGER NOT NULL,
      last_status TEXT, last_error TEXT, last_checked_at TEXT,
      last_dataset_id TEXT, last_sha256 TEXT, last_run_id TEXT,
      next_due_at TEXT, lease_owner TEXT, lease_expires_at TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
]


# Runs listed by state (the approval queue) are capped far above the page.
STATE_LIST_LIMIT = 1000


class SqlStore:
    """Shared SQL behaviour. Subclasses supply the connection and dialect."""

    def __init__(self):
        self._operation_lock = threading.RLock()
        self._transaction_depth = 0

    @contextmanager
    def atomic(self, key):
        """Serialize one logical mutation, including its checks and writes.

        Nested calls share the outer transaction. PostgreSQL locks only the
        named owner/run; SQLite serializes writers as its local-mode contract.
        A lost connection aborts the operation, never retries a fragment of it.
        """
        with self._operation_lock:
            if self._transaction_depth:
                self._transaction_depth += 1
                try:
                    yield
                finally:
                    self._transaction_depth -= 1
                return
            self._begin_transaction()
            self._transaction_depth = 1
            try:
                self._lock_transaction(key)
                yield
                self._finish_transaction("COMMIT")
            except BaseException:
                try:
                    self._finish_transaction("ROLLBACK")
                except Exception:
                    pass  # Preserve the original failure, including connection loss.
                raise
            finally:
                self._transaction_depth = 0

    def _begin_transaction(self):
        self._conn.execute("BEGIN IMMEDIATE")

    def _lock_transaction(self, key):
        pass  # SQLite's BEGIN IMMEDIATE already owns the write reservation.

    def _finish_transaction(self, statement):
        cursor = self._conn.cursor()
        try:
            cursor.execute(statement)
        finally:
            cursor.close()

    def close(self):
        """Release the connection.

        Windows will not delete a file another handle still has open, so
        a test that drops its temporary directory while the database is
        connected fails in cleanup with WinError 32 - noise that buries
        whatever the test was actually asserting. Closing is cheap and
        idempotent; callers that never close are unaffected.
        """
        connection = getattr(self, "_conn", None)
        if connection is None:
            return
        try:
            connection.close()
        except Exception:
            # Already closed, or a backend mid-reconnect. Nothing here is
            # worth failing a teardown over.
            pass
        self._conn = None

    """Dialect-neutral SQL access. Subclasses provide the connection and
    the parameter placeholder."""

    placeholder = "?"

    def _rows(self, cursor):
        if cursor.description is None:
            return []
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _exec(self, sql, params=()):
        with self._operation_lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql.replace("?", self.placeholder), params)
                rows = self._rows(cursor)
                self._commit()
                return rows
            finally:
                cursor.close()

    def _exec_rowcount(self, sql, params=()):
        """Like _exec, but reports how many rows the statement changed —
        which is how a lease claim knows whether it won the race."""
        with self._operation_lock:
            cursor = self._conn.cursor()
            try:
                cursor.execute(sql.replace("?", self.placeholder), params)
                count = cursor.rowcount
                self._commit()
                return count
            finally:
                cursor.close()

    def _create_schema(self):
        for statement in SCHEMA_STATEMENTS:
            self._exec(statement)
        self._migrate()

    def _migrate(self):
        """Additive migrations for databases created by earlier versions.

        ADD COLUMN errors when the column already exists in both dialects,
        which makes this safely repeatable on every startup."""
        for table in ("runs", "sessions"):
            try:
                self._exec(f"ALTER TABLE {table} ADD COLUMN owner TEXT")
            except Exception:
                self._rollback()
            else:
                # Rows written before ownership existed belong to the
                # local owner, matching pre-auth behavior.
                self._exec(
                    f"UPDATE {table} SET owner = 'local-owner' WHERE owner IS NULL")
        # report_language: NULL for runs written before reports had a
        # language, which were all English (ADR 0022).
        # joins_json: the datasets a run joins and on what (ADR 0030); NULL
        # for a run of one dataset, which is every run before it.
        # connector_id: the source a refresh made the run from (ADR 0034).
        # assumptions_json: the decision inputs a run stated (slice three
        # of the release gate, A2 and A13); NULL for every run before it.
        # idempotency_key: the caller's key for a run creation, unique per
        # owner, so a retried POST returns the run it already made (B14).
        for column in ("dataset_id", "lease_owner", "lease_expires_at",
                       "report_language", "mapping_json", "joins_json",
                       "connector_id", "assumptions_json", "idempotency_key"):
            try:
                self._exec(f"ALTER TABLE runs ADD COLUMN {column} TEXT")
            except Exception:
                self._rollback()
        try:
            self._exec("CREATE UNIQUE INDEX IF NOT EXISTS runs_idempotency "
                       "ON runs (owner, idempotency_key)")
        except Exception:
            self._rollback()
        try:
            # decided_by: the approver's subject, written by the gate (A13).
            self._exec("ALTER TABLE approvals ADD COLUMN decided_by TEXT")
        except Exception:
            self._rollback()
        try:
            # NULL means "never paused", which reads as not paused.
            self._exec("ALTER TABLE runs ADD COLUMN paused INTEGER")
        except Exception:
            self._rollback()
        # What a dataset is (ADR 0024). NULL for rows stored before the
        # dataset API, until the same data is stored again.
        # The owner's column mapping (ADR 0025), and the copy a run takes.
        for column, kind in (("source_format", "TEXT"), ("row_count", "INTEGER"),
                             ("column_count", "INTEGER"), ("mapping_json", "TEXT"),
                             ("mapping_updated_at", "TEXT")):
            try:
                self._exec(f"ALTER TABLE datasets ADD COLUMN {column} {kind}")
            except Exception:
                self._rollback()
        self._migrate_memory_owner()
        try:
            self._exec("ALTER TABLE connectors ADD COLUMN credential_id TEXT")
        except Exception:
            self._rollback()

    def upsert_worker_heartbeat(self, worker_id, seen_at, state):
        with self.atomic("worker-heartbeats"):
            self._exec("INSERT INTO worker_heartbeats (id, seen_at, state) VALUES (?, ?, ?) "
                       "ON CONFLICT (id) DO UPDATE SET seen_at = excluded.seen_at, "
                       "state = excluded.state", (worker_id, seen_at, state))
            stale = self._exec("SELECT id FROM worker_heartbeats ORDER BY seen_at DESC, id LIMIT 1000 OFFSET 100")
            for row in stale:
                self._exec("DELETE FROM worker_heartbeats WHERE id = ?", (row["id"],))

    def list_worker_heartbeats(self):
        return self._exec("SELECT * FROM worker_heartbeats ORDER BY seen_at DESC, id LIMIT 100")

    def _migrate_memory_owner(self):
        """Give memory_kv an owner, rebuilding the table if it predates one.

        This one cannot be an ADD COLUMN: the primary key has to move
        from (key) to (owner, key), or the second tenant to save a
        memory collides with the first. Rebuild-and-copy is the only
        shape both SQLite and PostgreSQL accept, and the guard makes it
        run exactly once.

        Existing rows are attributed to `local-owner` — the same
        assumption the runs and sessions migrations made, and the right
        one: a database written before ownership existed was written by
        a single-user install.
        """
        try:
            self._exec("SELECT owner FROM memory_kv LIMIT 1")
            return  # already migrated
        except Exception:
            self._rollback()
        try:
            self._exec("ALTER TABLE memory_kv RENAME TO memory_kv_pre_owner")
            for statement in SCHEMA_STATEMENTS:
                if "memory_kv (" in statement:
                    self._exec(statement)
            self._exec(
                "INSERT INTO memory_kv (owner, key, text, category, updated) "
                "SELECT 'local-owner', key, text, category, updated "
                "FROM memory_kv_pre_owner")
            self._exec("DROP TABLE memory_kv_pre_owner")
        except Exception:
            # A half-finished rebuild would lose memory, so leave the
            # old table in place and let the failure be visible rather
            # than deleting anything on the way out.
            self._rollback()
            raise

    def _rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    # -- generic helpers --------------------------------------------------
    def insert(self, table, row):
        columns = ", ".join(row)
        marks = ", ".join(["?"] * len(row))
        self._exec(f"INSERT INTO {table} ({columns}) VALUES ({marks})",
                   tuple(row.values()))

    def update(self, table, key, fields):
        assignments = ", ".join(f"{column} = ?" for column in fields)
        self._exec(f"UPDATE {table} SET {assignments} WHERE id = ?",
                   tuple(fields.values()) + (key,))

    # -- domain queries ---------------------------------------------------
    def get_run(self, run_id):
        rows = self._exec("SELECT * FROM runs WHERE id = ?", (run_id,))
        return rows[0] if rows else None

    def find_run_by_key(self, owner, idempotency_key):
        """The run an owner already created under this key, or None (B14)."""
        rows = self._exec("SELECT * FROM runs WHERE owner = ? AND idempotency_key = ? LIMIT 1",
                          (owner, idempotency_key))
        return rows[0] if rows else None

    def list_runs(self, owner=None, limit=50, state=None):
        """The newest `limit` runs, or every run in one `state` up to a
        larger ceiling: the approval queue must never lose its oldest
        request to the page size (assessment finding U1)."""
        where, params = [], []
        if owner is not None:
            where.append("owner = ?"); params.append(owner)
        if state is not None:
            where.append("state = ?"); params.append(state)
            limit = max(limit, STATE_LIST_LIMIT)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        return self._exec(
            "SELECT id, goal, dataset_name, state, created_at, updated_at "
            f"FROM runs{clause} ORDER BY created_at DESC LIMIT ?", (*params, limit))

    def get_tasks(self, run_id):
        return self._exec(
            "SELECT * FROM tasks WHERE run_id = ? ORDER BY idx", (run_id,))

    def latest_kpi_policy(self, run_id):
        rows = self._exec("SELECT * FROM kpi_policies WHERE run_id = ? "
                          "ORDER BY version DESC LIMIT 1", (run_id,))
        return rows[0] if rows else None

    def save_kpi_policy(self, identifier, run_id, expected_revision, revision,
                        rules_json, actor, created_at, empty_revision):
        """One conditional insert; unique run/version excludes a second winner.

        Works with SQLite and PostgreSQL autocommit. Reconnection may repeat an
        acknowledged-lost INSERT; the unique attempt id distinguishes our own
        successful write from somebody else's conflicting revision.
        """
        sql = ("INSERT INTO kpi_policies "
               "(id, run_id, version, revision, rules_json, actor, created_at) "
               "SELECT ?, ?, COALESCE(MAX(version), 0) + 1, ?, ?, ?, ? "
               "FROM kpi_policies WHERE run_id = ? "
               "HAVING COALESCE((SELECT revision FROM kpi_policies WHERE run_id = ? "
               "ORDER BY version DESC LIMIT 1), ?) = ?")
        params = (identifier, run_id, revision, rules_json, actor, created_at,
                  run_id, run_id, empty_revision, expected_revision)
        try:
            changed = self._exec_rowcount(sql, params)
        except Exception as error:
            import sqlite3
            self._rollback()
            unique = (getattr(error, "pgcode", None) == "23505"
                      or getattr(error, "sqlite_errorcode", None) in
                      (sqlite3.SQLITE_CONSTRAINT_UNIQUE, sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY))
            if not unique:
                raise
            changed = 0
        if changed:
            return True
        own_attempt = self._exec("SELECT id FROM kpi_policies WHERE id = ?", (identifier,))
        return bool(own_attempt)

    def latest_artifact(self, run_id):
        rows = self._exec(
            "SELECT * FROM artifacts WHERE run_id = ? "
            "ORDER BY version DESC LIMIT 1", (run_id,))
        return rows[0] if rows else None

    def approvals_for_run(self, run_id):
        return self._exec(
            "SELECT * FROM approvals WHERE run_id = ?", (run_id,))

    def pending_approval(self, run_id):
        rows = self._exec(
            "SELECT * FROM approvals WHERE run_id = ? AND state = 'pending'",
            (run_id,))
        return rows[0] if rows else None

    def get_approval(self, approval_id, run_id):
        rows = self._exec(
            "SELECT * FROM approvals WHERE id = ? AND run_id = ?",
            (approval_id, run_id))
        return rows[0] if rows else None

    # -- worker leases ----------------------------------------------------
    # A lease is a row-level claim with an expiry. A worker that crashes
    # stops renewing, the expiry passes, and another worker picks the run
    # up — no lock to clean up, no heartbeat table to keep consistent.
    def claim_run(self, worker_id, now, expires_at):
        """Take the lease on one runnable run. Returns its id, or None."""
        candidates = self._exec(
            "SELECT id FROM runs WHERE state IN ('queued', 'running') "
            "AND (paused IS NULL OR paused = 0) "
            "AND (lease_owner IS NULL OR lease_expires_at < ?) "
            "ORDER BY created_at LIMIT 5", (now,))
        for row in candidates:
            # The guard repeats inside the UPDATE, so two workers that
            # both selected this candidate cannot both win: the loser
            # changes zero rows and tries the next one. The SELECT alone
            # would not be enough — it is a read, not a claim.
            if self._exec_rowcount(
                    "UPDATE runs SET lease_owner = ?, lease_expires_at = ? "
                    "WHERE id = ? AND state IN ('queued', 'running') "
                    "AND (paused IS NULL OR paused = 0) "
                    "AND (lease_owner IS NULL OR lease_expires_at < ?)",
                    (worker_id, expires_at, row["id"], now)):
                return row["id"]
            # Zero rows changed usually means another worker got there
            # first. It can also mean this worker won, the connection
            # died before the acknowledgement arrived, and the repeat
            # then failed its own guard — because we are now the holder.
            # Losing a race and winning one invisibly are different
            # things, and only the first should end quietly.
            if self._won_after_a_retry(row["id"], worker_id, expires_at):
                return row["id"]
        return None

    def _won_after_a_retry(self, run_id, worker_id, expires_at):
        """Did this exact claim land after all? Matching the expiry we
        tried to write distinguishes it from an older lease of ours."""
        rows = self._exec(
            "SELECT lease_owner, lease_expires_at FROM runs WHERE id = ?",
            (run_id,))
        return bool(rows) and (rows[0]["lease_owner"] == worker_id
                               and rows[0]["lease_expires_at"] == expires_at)

    def renew_lease(self, run_id, worker_id, expires_at):
        """Heartbeat. False means the lease was lost and must not be used."""
        return self._exec_rowcount(
            "UPDATE runs SET lease_expires_at = ? "
            "WHERE id = ? AND lease_owner = ?",
            (expires_at, run_id, worker_id)) == 1

    def release_lease(self, run_id, worker_id):
        """Release only our own lease, never a successor's."""
        self._exec(
            "UPDATE runs SET lease_owner = NULL, lease_expires_at = NULL "
            "WHERE id = ? AND lease_owner = ?", (run_id, worker_id))

    # -- connectors (ADR 0034) ----------------------------------------------
    def get_connector(self, connector_id):
        rows = self._exec("SELECT * FROM connectors WHERE id = ?", (connector_id,))
        return rows[0] if rows else None

    def list_connectors(self, owner):
        return self._exec(
            "SELECT * FROM connectors WHERE owner = ? ORDER BY created_at", (owner,))

    def count_connectors(self, owner):
        rows = self._exec(
            "SELECT COUNT(*) AS n FROM connectors WHERE owner = ?", (owner,))
        return int(rows[0]["n"]) if rows else 0

    def delete_connector(self, connector_id):
        self._exec("DELETE FROM connectors WHERE id = ?", (connector_id,))

    def claim_connector(self, worker_id, now, expires_at):
        """Take the lease on one connector whose refresh is due, as
        claim_run does for runs. Returns its id, or None."""
        candidates = self._exec(
            "SELECT id FROM connectors WHERE enabled = 1 "
            "AND next_due_at IS NOT NULL AND next_due_at <= ? "
            "AND (lease_owner IS NULL OR lease_expires_at < ?) "
            "ORDER BY next_due_at LIMIT 5", (now, now))
        for row in candidates:
            if self._exec_rowcount(
                    "UPDATE connectors SET lease_owner = ?, lease_expires_at = ? "
                    "WHERE id = ? AND enabled = 1 AND next_due_at <= ? "
                    "AND (lease_owner IS NULL OR lease_expires_at < ?)",
                    (worker_id, expires_at, row["id"], now, now)):
                return row["id"]
        return None

    def take_connector(self, connector_id, holder, now, expires_at):
        """The lease for a refresh asked for now, due or not. False when a
        refresh is already under way."""
        return self._exec_rowcount(
            "UPDATE connectors SET lease_owner = ?, lease_expires_at = ? "
            "WHERE id = ? AND (lease_owner IS NULL OR lease_expires_at < ?)",
            (holder, expires_at, connector_id, now)) == 1

    def release_connector(self, connector_id, holder):
        self._exec(
            "UPDATE connectors SET lease_owner = NULL, lease_expires_at = NULL "
            "WHERE id = ? AND lease_owner = ?", (connector_id, holder))

    # -- pushed updates (ADR 0034) -----------------------------------------
    def changes_since(self, owner, since, limit=200, before=None):
        """An owner's runs and connectors changed at or after `since` (and
        before `before`, when given), oldest first, for the event stream.
        Timestamps are compared as text, which orders them because they
        share one format and offset."""
        until, args = ("AND updated_at < ? ", (before,)) if before else ("", ())
        runs = self._exec(
            "SELECT id, goal, state, connector_id, created_at, updated_at FROM runs "
            f"WHERE owner = ? AND updated_at >= ? {until}ORDER BY updated_at LIMIT ?",
            (owner, since, *args, limit))
        connectors = self._exec(
            "SELECT id, name, enabled, last_status, last_error, last_run_id, "
            "last_checked_at, next_due_at, updated_at FROM connectors "
            f"WHERE owner = ? AND updated_at >= ? {until}ORDER BY updated_at LIMIT ?",
            (owner, since, *args, limit))
        return runs, connectors

    # -- sessions ---------------------------------------------------------
    def get_session(self, session_id):
        rows = self._exec("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return rows[0] if rows else None

    def upsert_session(self, row):
        fields = {k: v for k, v in row.items() if k != "id"}
        assignments = ", ".join(f"{column} = ?" for column in fields)
        cursor = self._conn.cursor()
        cursor.execute(
            f"UPDATE sessions SET {assignments} WHERE id = ?".replace(
                "?", self.placeholder),
            tuple(fields.values()) + (row["id"],))
        if cursor.rowcount == 0:
            self.insert("sessions", row)
        else:
            self._commit()

    def trim_sessions(self, keep, owner=None):
        """Keep an owner's `keep` most recent sessions. Retention is per
        owner: one tenant's new sessions never delete another's (audit
        finding, 22 October). Without an owner, every owner is trimmed to
        the same count."""
        if owner is None:
            owners = [row["owner"] for row in
                      self._exec("SELECT DISTINCT owner FROM sessions")]
            for each in owners:
                self.trim_sessions(keep, each)
            return
        self._exec(
            "DELETE FROM sessions WHERE owner = ? AND id NOT IN "
            "(SELECT id FROM sessions WHERE owner = ? ORDER BY updated_at DESC LIMIT ?)",
            (owner, owner, keep))

    # -- shared memory ----------------------------------------------------
    def memory_load(self, owner="local-owner"):
        return {
            row["key"]: {"text": row["text"], "category": row["category"],
                         "updated": row["updated"]}
            for row in self._exec(
                "SELECT * FROM memory_kv WHERE owner = ?", (owner,))
        }

    def memory_save(self, payload, owner="local-owner"):
        """Replace one owner's memory. The DELETE is scoped for the same
        reason the SELECT is: unscoped, saving a memory deleted
        everybody else's."""
        self._exec("DELETE FROM memory_kv WHERE owner = ?", (owner,))
        for key, entry in payload.items():
            self.insert("memory_kv", {
                "owner": owner, "key": key, "text": entry["text"],
                "category": entry["category"], "updated": entry["updated"]})

    # -- vault notes ------------------------------------------------------
    def upsert_note(self, path, run_id, content, created_at):
        self._exec("DELETE FROM vault_notes WHERE path = ?", (path,))
        self.insert("vault_notes", {"path": path, "run_id": run_id,
                                    "content": content,
                                    "created_at": created_at})

    def list_notes(self, owner=None):
        """Published knowledge inherits its run's owner, including old notes.

        None is reserved for trusted operator callers. API requests supply
        their subject unless the principal has platform administration.
        Filtering in SQL keeps both note paths and contents out of another
        customer's response; the filesystem is never a read fallback.
        """
        if owner is None:
            return self._exec(
                "SELECT path, run_id, created_at FROM vault_notes "
                "ORDER BY created_at DESC")
        return self._exec(
            "SELECT n.path, n.run_id, n.created_at FROM vault_notes n "
            "JOIN runs r ON r.id = n.run_id WHERE r.owner = ? "
            "ORDER BY n.created_at DESC", (owner,))

    def get_note(self, path, owner=None):
        if owner is None:
            rows = self._exec("SELECT * FROM vault_notes WHERE path = ?", (path,))
        else:
            rows = self._exec(
                "SELECT n.* FROM vault_notes n JOIN runs r ON r.id = n.run_id "
                "WHERE n.path = ? AND r.owner = ?", (path, owner))
        return rows[0] if rows else None

    # -- datasets ---------------------------------------------------------
    def find_dataset(self, sha256, owner):
        rows = self._exec(
            "SELECT * FROM datasets WHERE sha256 = ? AND owner = ? LIMIT 1",
            (sha256, owner))
        return rows[0] if rows else None

    def get_dataset(self, dataset_id):
        rows = self._exec("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
        return rows[0] if rows else None

    # -- usage ------------------------------------------------------------
    # Usage is counted from the rows themselves rather than a parallel
    # tally, so it cannot drift away from what the tenant actually has.
    def count_runs_since(self, owner, since):
        rows = self._exec(
            "SELECT COUNT(*) AS n FROM runs WHERE owner = ? AND created_at >= ?",
            (owner, since))
        return int(rows[0]["n"]) if rows else 0

    def dataset_usage(self, owner):
        rows = self._exec(
            "SELECT COUNT(*) AS n, COALESCE(SUM(byte_size), 0) AS bytes "
            "FROM datasets WHERE owner = ?", (owner,))
        row = rows[0] if rows else {"n": 0, "bytes": 0}
        return {"datasets": int(row["n"]), "bytes": int(row["bytes"] or 0)}

    def list_datasets(self, owner):
        return self._exec(
            "SELECT id, sha256, name, byte_size, created_at, source_format, "
            "row_count, column_count, mapping_updated_at FROM datasets "
            "WHERE owner = ? ORDER BY created_at DESC LIMIT 50", (owner,))

    # -- backup and restore ----------------------------------------------
    def export_all(self):
        """Every durable row, as plain JSON-serialisable dicts."""
        return {table: self._exec(f"SELECT * FROM {table}") for table in TABLES}

    def table_columns(self, table):
        """The live column names of one table, migrations included."""
        if table not in TABLES:
            raise ValueError(f"unknown table {table!r}")
        return self._table_columns(table)

    def _prepare_restore(self, payload):
        """Every row of every table, checked against the live schema
        before anything is deleted: a dict whose keys are all columns of
        that table. Returns the rows to insert, in restore order."""
        prepared = []
        for table in RESTORE_ORDER:
            rows = payload.get(table, [])
            if not isinstance(rows, list):
                raise ValueError(f"backup table {table!r} is not a list of rows")
            known = set(self.table_columns(table))
            for index, row in enumerate(rows):
                if not isinstance(row, dict) or not row:
                    raise ValueError(f"backup table {table!r} row {index} is not a row")
                if table == "memory_kv" and not row.get("owner"):
                    # Written before memory had an owner: the same
                    # attribution the migration makes.
                    row = dict(row, owner="local-owner")
                unknown = sorted(str(c) for c in row if c not in known)
                if unknown:
                    raise ValueError(
                        f"backup table {table!r} row {index} has unknown columns: "
                        + ", ".join(unknown))
                prepared.append((table, row))
        return prepared

    def import_all(self, payload):
        """Replace all contents with a backup. Returns rows restored.

        All or nothing (assessment finding B5): every row is validated
        against the live schema before any delete, and the deletes and
        inserts run inside one transaction, so a failure part-way leaves
        the database exactly as it was. Children are deleted before
        parents and inserted after them, so foreign keys hold at every
        point."""
        prepared = self._prepare_restore(payload)
        with self.atomic("restore"):
            for table in reversed(RESTORE_ORDER):
                self._exec(f"DELETE FROM {table}")
            for table, row in prepared:
                self.insert(table, row)
        return len(prepared)


class DbMemoryBackend:
    """One owner's agent memory, in the store's memory_kv table.

    An instance is bound to an owner rather than shared, because the
    alternative — one backend for the process — is what let every tenant
    read and overwrite every other tenant's memory.
    """

    persistent = True

    def __init__(self, store, owner="local-owner"):
        self._store = store
        self._owner = owner or "local-owner"

    @property
    def owner(self):
        return self._owner

    def load(self):
        try:
            return self._store.memory_load(self._owner)
        except Exception:
            return {}

    def save(self, payload):
        try:
            self._store.memory_save(payload, self._owner)
            return True
        except Exception:
            return False


class SQLiteStore(SqlStore):
    placeholder = "?"

    def __init__(self, path):
        super().__init__()
        import os
        import sqlite3
        import tempfile
        from pathlib import Path

        path = Path(str(path))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Read-only deployment (e.g. a serverless bundle): fall back to
            # the writable temp directory. State is then per-instance and
            # ephemeral — configure DATABASE_URL for durable hosting.
            path = Path(tempfile.gettempdir()) / "agentic-os" / path.name
            path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(path.parent, os.W_OK):
            path = Path(tempfile.gettempdir()) / "agentic-os" / path.name
            path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        # A bounded local narration can take 60 seconds. Other writers wait
        # for that stage's atomic commit instead of failing after five seconds.
        self._conn = sqlite3.connect(str(path), check_same_thread=False, timeout=65)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _commit(self):
        if not self._transaction_depth:
            self._conn.commit()

    def _table_columns(self, table):
        return [row["name"] for row in self._exec(f"PRAGMA table_info({table})")]


class PostgresStore(SqlStore):
    placeholder = "%s"

    def __init__(self, database_url):
        super().__init__()
        import psycopg2  # lazy: only hosted mode needs the driver

        self._psycopg2 = psycopg2
        self._database_url = database_url
        self._conn = self._connect()
        self._create_schema()

    def _connect(self):
        conn = self._psycopg2.connect(self._database_url, connect_timeout=10)
        conn.autocommit = True
        return conn

    def _begin_transaction(self):
        # Reconnection is safe before the transaction has acquired any state.
        self._exec("BEGIN")

    def _lock_transaction(self, key):
        identifier = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],
                                    "big", signed=True)
        self._exec("SELECT pg_advisory_xact_lock(?)", (identifier,))

    def _retrying(self, statement, sql, params):
        """Run a statement, reconnecting once if the connection is gone.

        Two different failures land here and both are ordinary. A pooler
        or a server restart drops the socket, which surfaces as
        OperationalError on the next statement; a connection this process
        already closed surfaces as InterfaceError. Catching only the
        first meant a worker that had been idle — the normal state of a
        worker — could fail on the statement it woke up to run.

        Retrying is safe because autocommit means there is no transaction
        to rebuild: each statement stands alone. The one case where a
        blind repeat could mislead is a conditional UPDATE whose
        acknowledgement was lost, and `claim_run` checks for that
        directly rather than trusting the row count.
        """
        with self._operation_lock:
            try:
                return statement(sql, params)
            except (self._psycopg2.OperationalError,
                    self._psycopg2.InterfaceError):
                if self._transaction_depth:
                    raise  # The caller must retry the whole logical operation.
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = self._connect()
                return statement(sql, params)

    def _exec(self, sql, params=()):
        return self._retrying(super()._exec, sql, params)

    def _exec_rowcount(self, sql, params=()):
        # The lease statements run through here, which is to say the
        # worker's entire job does.
        return self._retrying(super()._exec_rowcount, sql, params)

    def _commit(self):
        pass  # autocommit

    def _table_columns(self, table):
        rows = self._exec(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = ? "
            "ORDER BY ordinal_position", (table,))
        return [row["column_name"] for row in rows]


def open_store(database_url=None, sqlite_path=None):
    """Hosted PostgreSQL when DATABASE_URL is configured; SQLite otherwise."""
    if database_url and str(database_url).startswith(("postgres://", "postgresql://")):
        return PostgresStore(str(database_url))
    return SQLiteStore(sqlite_path)
