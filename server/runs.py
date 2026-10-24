"""Durable run engine: goal -> plan -> tasks -> approval -> artifact.

State is persisted through a storage adapter (SQLite locally, hosted
PostgreSQL via DATABASE_URL — see server/storage.py) after every
transition, so runs survive an application restart and can be resumed,
cancelled, or approved later. Client execution advances one bounded task
per call. Configured worker execution keeps model work out of HTTP and
uses a separate worker process; browser advances become snapshot reads.
Both modes preserve the same pause, cancel and recovery semantics.

The publish step writes the approved report into an Obsidian-compatible
vault folder (markdown + provenance frontmatter + [[wikilinks]]) and is
gated by a server-enforced approval bound to the exact artifact hash —
a manipulated client cannot publish unapproved or altered content.
"""

import copy
import hashlib
import json
import os
import re
import threading
import uuid
from collections import OrderedDict
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

from server import analytics, datasets, deadline, metrics, quota, model_privacy
from server import joins as joining
from server import query, tenant
from server import mapping as colmap
from server import stages as stage_registry

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_vault_dir(env=None, config=None, root=None):
    """The folder approved reports are published into.

    Sources, in order:

        AGENTIC_OS_VAULT_DIR    a folder, `~` expanded
        config["vault_dir"]     the same, from config.json
        <root>/vault            the repository's own folder

    The environment variable exists because an operator's own Obsidian
    vault is a machine path, usually holding a user name, and
    `config.json` is tracked in a public repository. This is how that
    path is given without committing it.

    A relative path resolves against `root`, the repository, not the
    working directory, so the API, the worker and the MCP server publish
    to one place however they were started. A blank or whitespace value
    is treated as unset rather than as the current directory.
    """
    env = os.environ if env is None else env
    root = Path(root) if root else PROJECT_ROOT
    for value in (env.get("AGENTIC_OS_VAULT_DIR"), (config or {}).get("vault_dir")):
        if value is not None and str(value).strip():
            path = Path(str(value).strip()).expanduser()
            return path if path.is_absolute() else root / path
    return root / "vault"


def resolve_publish_target(env=None, config=None):
    """Serverless publication is durable in SQL, without a writable vault."""
    env = os.environ if env is None else env
    selected = (env.get("AGENTIC_OS_PUBLISH_TARGET") or (config or {}).get("publish_target")
                or ("database" if env.get("VERCEL") == "1" else "vault"))
    if selected not in ("database", "vault"):
        raise ValueError("AGENTIC_OS_PUBLISH_TARGET must be database or vault.")
    return selected


RUN_STATES = {"queued", "running", "awaiting_approval", "verifying",
              "completed", "partially_completed", "failed", "cancelled"}
TASK_STATES = {"pending", "running", "succeeded", "failed", "skipped",
               "awaiting_approval", "cancelled"}

RUN_TRANSITIONS = {
    "queued": {"running", "cancelled"},
    "running": {"running", "awaiting_approval", "completed",
                "partially_completed", "failed", "cancelled"},
    "awaiting_approval": {"running", "completed", "partially_completed",
                          "cancelled"},
    "completed": set(), "partially_completed": set(), "failed": set(),
    "cancelled": set(),
}


DATASET_FIELDS = ("id", "sha256", "name", "byte_size", "created_at", "source_format",
                  "row_count", "column_count", "mapping_updated_at")

# Parsed analysis tables kept for the query endpoints (ADR 0031): a
# 50,000-row table is answered without parsing its stored result again.
TABLE_CACHE_SIZE = 3


class TableNotReady(Exception):
    """The run has not cleaned its data yet, so it has no table to read."""


def dataset_summary(dataset):
    """A dataset without its content, and whether it has a saved mapping."""
    summary = {key: dataset.get(key) for key in DATASET_FIELDS}
    summary["mapped"] = dataset.get("mapping_updated_at") is not None
    return summary


# A run of digits this long is read by the personal-data detector as a phone
# number (10+) or an account number (12+). Hex ids carry such runs about 1.5%
# of the time, and an id in a model's notes then made the assistant refuse the
# model as if a person's number were in it. Ids are drawn again instead.
DIGIT_RUN = re.compile(r"\d{8,}")


def personal_looking(value):
    return bool(DIGIT_RUN.search(value))


def random_id():
    while True:
        value = uuid.uuid4().hex[:12]
        if not personal_looking(value):
            return value


def _now():
    return datetime.now(timezone.utc).isoformat()


def _utcnow():
    return datetime.now(timezone.utc)


def _stamp(moment):
    """Lease timestamps are compared as text by the database, so they use
    a fixed width — `isoformat()` drops the fraction on a whole second."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")



def model_cards(result):
    """Both fitted and unsupported cards, without inventing missing scores.

    A maintenance stage returns several cards; generic stages retain their
    existing single-card contract. Invalid list members are not model cards.
    """
    output = (result or {}).get("output", {})
    candidates = [output["model_card"]] if isinstance(output.get("model_card"), dict) else []
    batch = output.get("models", [])
    if isinstance(batch, list):
        candidates.extend(card for card in batch if isinstance(card, dict)
                          and isinstance(card.get("kind"), str)
                          and isinstance(card.get("target"), str))
    return candidates[:12]


# The longest idempotency key a run creation accepts (B14).
MAX_IDEMPOTENCY_KEY = 200

# How many orchestration failures the engine remembers for the health detail.
MAX_ORCHESTRATION_PROBLEMS = 20


class IdempotencyConflict(ValueError):
    """The owner reused a creation key for a different request."""


class PublicationDestinationChanged(ValueError):
    """A pending review names a different destination from current settings."""

class RunEngine:
    def __init__(self, store, vault_dir, gateway, limits=None, glossary=None,
                 stages=None, profiles=None, execution_mode="client", roles=None,
                 stage_timeout=None, publish_target=None, specialist_driver=None,
                 specialist_limits=None):
        if execution_mode not in ("client", "worker"):
            raise ValueError("AGENTIC_OS_RUN_EXECUTION must be client or worker.")
        self.execution_mode = execution_mode
        self.store = store
        # The last reasons an orchestration note is missing (G12), shown
        # by /api/health to a signed-in reader.
        self.orchestration_problems = []
        # Every row id the engine makes comes from here. The public demo
        # swaps in a seeded generator while it seeds, so each serverless
        # instance builds its demo under the same ids (server/demo.py).
        self.new_id = random_id
        # Model roles (server/orchestration.py): None, the default, means
        # every run is exactly the deterministic pipeline.
        self.roles = roles
        # Custom stages (ADR 0020): role -> descriptor, in registration
        # order, and the named profiles that choose among them.
        self.stages = dict(stages or {})
        self.profiles = dict(profiles or {})
        # A custom stage's wall-clock limit (assessment G10); None reads
        # AGENTIC_OS_STAGE_TIMEOUT, seconds, default 120.
        self.stage_timeout = (float(stage_timeout) if stage_timeout else
                              deadline.seconds_from_env("AGENTIC_OS_STAGE_TIMEOUT",
                                                        deadline.DEFAULT_STAGE_SECONDS))
        self.vault_dir = Path(vault_dir)
        self.publish_target = publish_target or resolve_publish_target()
        if self.publish_target not in ("database", "vault"):
            raise ValueError("publish_target must be database or vault.")
        self.gateway = gateway
        # None disables quota enforcement entirely (the CLI and tests that
        # are not about quotas); the API always passes limits.
        self.limits = limits
        # The metric glossary is read once at startup rather than per run,
        # so every run in a process agrees about what a metric means and
        # editing the file mid-run cannot change a report halfway through.
        # None means "read the configured file"; pass a dict to override.
        if glossary is None:
            entries, problems = metrics.load_glossary()
            glossary = {"metrics": entries, "problems": problems}
        self.glossary = glossary
        self._tables = OrderedDict()
        self._tables_lock = threading.Lock()
        self.specialists = None
        if specialist_driver is not None:
            from server.specialists import SpecialistCoordinator
            self.specialists = SpecialistCoordinator(self, specialist_driver, specialist_limits)

    # -- state helpers ----------------------------------------------------
    def _set_run_state(self, run_id, new_state, error=None):
        run = self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        current = run["state"]
        if new_state != current and new_state not in RUN_TRANSITIONS[current]:
            raise ValueError(f"Illegal run transition {current} -> {new_state}")
        self.store.update(
            "runs", run_id,
            {"state": new_state, "error": error, "updated_at": _now()})

    def _set_task(self, task_id, state, summary=None, result=None):
        fields = {"state": state, "updated_at": _now()}
        if summary is not None:
            fields["summary"] = summary
        if result is not None:
            fields["result_json"] = json.dumps(result)
        self.store.update("tasks", task_id, fields)

    # -- API --------------------------------------------------------------
    def store_dataset(self, text, name, owner, source_format="csv"):
        """Content-addressed storage: identical uploads share one row."""
        return self._store(text, name, owner, source_format)[0]

    def store_upload(self, parsed, name, owner):
        """A file read by server.datasets (ADR 0024): its canonical CSV,
        stored like any other. Returns (dataset, created)."""
        return self._store(parsed.csv_text, name, owner, parsed.source_format,
                           (len(parsed.rows), len(parsed.columns)))

    def _store(self, text, name, owner, source_format, shape=None):
        with self.store.atomic("owner:" + owner):
            return self._store_atomic(text, name, owner, source_format, shape)

    def _store_atomic(self, text, name, owner, source_format, shape=None):
        rows, columns = shape or datasets.counts(text)
        digest = hashlib.sha256(text.encode()).hexdigest()
        existing = self.store.find_dataset(digest, owner)
        if existing:
            # Already stored: consumes no new space, so no quota applies.
            # A row from before the dataset API learns its shape now.
            if existing.get("row_count") is None and rows is not None:
                self.store.update("datasets", existing["id"], {
                    "source_format": existing.get("source_format") or source_format,
                    "row_count": rows, "column_count": columns})
                existing = self.store.get_dataset(existing["id"])
            return existing, False
        if self.limits:
            quota.check_dataset(self.store, owner, self.limits,
                                len(text.encode()))
        dataset_id = self.new_id()
        self.store.insert("datasets", {
            "id": dataset_id, "sha256": digest, "name": name,
            "content": text, "byte_size": len(text.encode()),
            "owner": owner, "created_at": _now(),
            "source_format": source_format, "row_count": rows,
            "column_count": columns})
        return self.store.get_dataset(dataset_id), True

    # -- column mapping (ADR 0025) -----------------------------------------
    def _owned_dataset(self, dataset_id, owner):
        dataset = self.store.get_dataset(dataset_id)
        if dataset is None or dataset["owner"] != owner:
            raise KeyError(dataset_id)
        return dataset

    def _metrics(self):
        return (self.glossary or {}).get("metrics", [])

    def dataset_detail(self, dataset_id, owner, language="en"):
        """A dataset as the mapping step needs it: the first rows, a
        profile of each column, the saved mapping and a suggested one."""
        dataset = self._owned_dataset(dataset_id, owner)
        columns, rows = colmap.table(dataset["content"])
        sampled = colmap.sample(rows)
        profiles = colmap.profile(columns, sampled)
        suggestion = colmap.suggest(columns, sampled, self._metrics(), profiles)
        reasons = suggestion.pop("reasons")
        for item in profiles:
            reason = reasons[item["name"]]
            item["suggested_role"] = suggestion["roles"][item["name"]]
            item["reason"] = reason["ar"] if language == "ar" else reason["en"]
        return {
            "dataset": dataset_summary(dataset),
            "columns": profiles,
            "preview": [[row.get(c) or "" for c in columns]
                        for row in rows[:colmap.PREVIEW_ROWS]],
            "row_count": len(rows), "profiled_rows": len(sampled),
            "mapping": (json.loads(dataset["mapping_json"])
                        if dataset.get("mapping_json") else None),
            "suggestion": suggestion,
        }

    def save_mapping(self, dataset_id, owner, mapping, language="en"):
        """Validate a mapping against every row and keep it with the
        dataset. Raises mapping.MappingError with every problem."""
        dataset = self._owned_dataset(dataset_id, owner)
        columns, rows = colmap.table(dataset["content"])
        clean = colmap.validate(mapping, columns, rows)
        self.store.update("datasets", dataset_id, {
            "mapping_json": json.dumps(clean, ensure_ascii=False),
            "mapping_updated_at": _now()})
        return self.dataset_detail(dataset_id, owner, language)

    def clear_mapping(self, dataset_id, owner, language="en"):
        """Back to automatic detection for runs made from now on."""
        self._owned_dataset(dataset_id, owner)
        self.store.update("datasets", dataset_id, {
            "mapping_json": None, "mapping_updated_at": None})
        return self.dataset_detail(dataset_id, owner, language)

    def custom_roles_for(self, profile=None):
        """Which registered stages a run includes. A profile names a
        subset; no profile means the "default" profile when one is
        configured, else every registered stage."""
        if profile is None:
            chosen = self.profiles.get("default")
            if chosen is None:
                return list(self.stages)
        else:
            chosen = self.profiles.get(profile)
            if chosen is None:
                available = ", ".join(sorted(self.profiles)) or "none"
                raise ValueError(f"Unknown pipeline profile “{profile}”. "
                                 f"Available: {available}.")
        unknown = [role for role in chosen if role not in self.stages]
        if unknown:
            raise ValueError(f"Profile “{profile or 'default'}” names stages "
                             f"that are not registered: {', '.join(unknown)}.")
        return list(chosen)

    def roles_for(self, profile=None, joined=False):
        """The run's stage order: the built-in pipeline with each custom
        stage inserted after the built-in stage it asked for. Custom
        stages can only be placed before the governed tail, so every
        one of them runs before provenance, validation and reporting.
        A run that joins datasets merges them right after cleaning, before
        anything else reads the cleaned rows (ADR 0030)."""
        if profile == "specialist_evidence":
            if self.specialists is None:
                raise ValueError("Specialist execution requires an explicit decision driver.")
            if joined:
                raise ValueError("The first specialist profile accepts one authorized source only.")
            from server.specialists import ROLE_NAMES
            return [*ROLE_NAMES, "publish"]
        custom = self.custom_roles_for(profile)
        roles = []
        for role, _ in analytics.PIPELINE:
            roles.append(role)
            if joined:
                roles.extend(optional for optional, after in analytics.OPTIONAL_AFTER.items()
                             if after == role)
            roles.extend(r for r in custom
                         if getattr(self.stages[r], "after",
                                    stage_registry.DEFAULT_AFTER) == role)
        return roles + ["publish"]

    # -- several datasets per run (ADR 0030) ------------------------------
    def _join_inputs(self, spec, owner):
        """Each joined dataset as the merge stage reads it. Another owner's
        dataset is missing (KeyError), never forbidden."""
        loaded = [self._owned_dataset(item["dataset_id"], owner) for item in spec["joins"]]
        joining.assign_aliases(spec["joins"], [d["name"] for d in loaded])
        return [{**item, "name": dataset["name"], "content": dataset["content"],
                 "snapshot": dataset["sha256"][:16],
                 "mapping": (json.loads(dataset["mapping_json"])
                             if dataset.get("mapping_json") else None)}
                for item, dataset in zip(spec["joins"], loaded)]

    def join_plan(self, owner, dataset_id, joins, breakdown=None):
        """Everything a merge needs, read from the store: the main
        dataset, the declaration and each joined dataset. Raises KeyError
        for a dataset that is not this owner's and JoinError for a
        declaration that cannot run."""
        if not dataset_id:
            raise joining.JoinError([joining.Problem(
                "dataset", None,
                "Joins start from a stored dataset: choose one or upload a file first.",
                "يبدأ الدمج من بيانات محفوظة: اختر مجموعة بيانات أو ارفع ملفاً أولاً.")])
        primary = self._owned_dataset(dataset_id, owner)
        spec = joining.normalise(joins, breakdown)
        inputs = self._join_inputs(spec, owner)
        mapping = json.loads(primary["mapping_json"]) if primary.get("mapping_json") else None
        return primary, mapping, spec, inputs

    def preview_joins(self, owner, dataset_id, joins, breakdown=None, language="en"):
        primary, mapping, spec, inputs = self.join_plan(owner, dataset_id, joins, breakdown)
        return analytics.preview_merge(primary["content"], mapping, inputs,
                                       spec["breakdown"], language)

    def create_run(self, goal, dataset_text=None, dataset_name=None,
                   owner="local-owner", dataset_id=None, profile=None,
                   language="en", joins=None, breakdown=None, assumptions=None,
                   idempotency_key=None):
        """Create a run; with an idempotency key, return the run this owner
        already created under it instead of a second one (assessment B14).
        A replayed run carries `idempotent_replay: True`."""
        if idempotency_key is not None:
            idempotency_key = str(idempotency_key).strip()
            if not idempotency_key or len(idempotency_key) > MAX_IDEMPOTENCY_KEY:
                raise ValueError("An idempotency key is 1 to 200 characters.")
        request_hash = hashlib.sha256(json.dumps({
            "goal": goal.strip(), "dataset_id": dataset_id,
            "dataset_text": None if dataset_id else dataset_text,
            "dataset_name": None if dataset_id else dataset_name,
            "profile": profile, "language": language, "joins": joins or None,
            "breakdown": breakdown, "assumptions": assumptions or None,
        }, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest() if idempotency_key else None
        with self.store.atomic("owner:" + owner):
            if idempotency_key:
                existing = self.store.find_run_by_key(owner, idempotency_key)
                if existing is not None:
                    if existing.get("request_hash") != request_hash:
                        raise IdempotencyConflict(
                            "تخص هوية المحاولة طلبًا مختلفًا أو سابقًا لا يمكن مطابقة مدخلاته. راجع التحليل السابق أو ابدأ محاولة جديدة."
                            if language == "ar" else
                            "This attempt key belongs to a different request, or an older request whose inputs cannot be matched. Review the earlier analysis or start a new attempt.")
                    detail = self.get_run(existing["id"])
                    detail["idempotent_replay"] = True
                    return detail
            return self._create_run_atomic(goal, dataset_text, dataset_name, owner,
                                           dataset_id, profile, language, joins, breakdown,
                                           assumptions, idempotency_key, request_hash)

    def _create_run_atomic(self, goal, dataset_text=None, dataset_name=None,
                           owner="local-owner", dataset_id=None, profile=None,
                           language="en", joins=None, breakdown=None, assumptions=None,
                           idempotency_key=None, request_hash=None):
        # An unknown profile, or a language reports are not written in, is
        # refused before anything is written.
        roles = self.roles_for(profile, joined=bool(joins))
        if language not in analytics.REPORT_LANGUAGES:
            raise ValueError(f"Reports are not written in “{language}”.")
        # The decision inputs (uplift, cost, uplift range) are checked here,
        # with every reason, and kept with the run (assessment A2, A13).
        assumptions = analytics.validate_assumptions(assumptions, language)
        if not joins and breakdown is not None and str(breakdown).strip():
            # ADR 0030 defines this override only for a merged table.
            # Refuse before admission rather than accept a grouping the
            # preparer will never read. A single table uses its mapping.
            raise ValueError(
                "خيار التقسيم يتطلب مجموعة بيانات مدمجة واحدة على الأقل. "
                "لمجموعة بيانات واحدة، اختر عمود التقسيم في تعيين الأعمدة المحفوظ."
                if language == "ar" else
                "The breakdown option requires at least one joined dataset. "
                "For a single dataset, choose its breakdown in the saved column mapping.")
        joins_json = None
        joined_names = []
        if joins:
            # Refused here, with every reason, rather than at the merge
            # stage halfway through the run: the preview runs the same code.
            primary, mapping, spec, inputs = self.join_plan(owner, dataset_id, joins,
                                                            breakdown)
            analytics.preview_merge(primary["content"], mapping, inputs,
                                    spec["breakdown"], language, rows_shown=0)
            # The run keeps its own copy of each joined mapping, as it does
            # of the main one, so a later change never reaches it.
            joins_json = json.dumps({
                "joins": [{key: item[key] for key in
                           ("dataset_id", "alias", "how", "keys", "mapping")}
                          for item in inputs],
                "breakdown": spec["breakdown"]}, ensure_ascii=False)
            joined_names = [item["name"] for item in inputs]
        # Checked before anything is written, so a refused run leaves no
        # half-created rows behind.
        if self.limits:
            quota.check_run(self.store, owner, self.limits)
        run_id = self.new_id()
        mapping_json = None
        if dataset_id:
            dataset = self._owned_dataset(dataset_id, owner)
            # The run keeps its own copy of the mapping, so changing the
            # mapping later never changes a run already made (ADR 0025).
            mapping_json = dataset.get("mapping_json")
        else:
            text = dataset_text or analytics.sample_dataset(language)
            name = dataset_name or (
                ("بيانات مرفوعة" if language == "ar" else "uploaded dataset") if dataset_text else
                ("بيانات مبيعات تجريبية" if language == "ar" else "sample sales dataset"))
            dataset = self.store_dataset(text, name, owner,
                                         "csv" if dataset_text else "sample")
        now = _now()
        self.store.insert("runs", {
            "id": run_id, "goal": goal.strip(),
            "dataset_name": " + ".join([dataset["name"], *joined_names]),
            # dataset_text stays populated for backward compatibility with
            # rows written before datasets were content-addressed.
            "dataset_text": "", "state": "queued",
            "created_at": now, "updated_at": now, "error": None,
            "owner": owner, "dataset_id": dataset["id"],
            # Fixed for the run's life: the approval gate binds to the hash
            # of one artifact, written in one language (ADR 0022).
            "report_language": language,
            "mapping_json": mapping_json, "joins_json": joins_json,
            "assumptions_json": (json.dumps(assumptions, ensure_ascii=False)
                                 if assumptions else None),
            "idempotency_key": idempotency_key or None, "request_hash": request_hash})
        titles = analytics.ROLE_TITLES_AR if language == "ar" else analytics.ROLE_TITLES
        for idx, role in enumerate(roles):
            # A plugin may name itself in Arabic too (ADR 0033).
            descriptor = self.stages.get(role)
            if profile == "specialist_evidence":
                from server.specialists import SPEC_BY_ROLE
                descriptor = SPEC_BY_ROLE.get(role) or descriptor
            title = (titles.get(role)
                     or (language == "ar" and getattr(descriptor, "title_ar", None))
                     or descriptor.title)
            self.store.insert("tasks", {
                "id": self.new_id(), "run_id": run_id, "idx": idx,
                "role": role, "title": title,
                "state": "pending", "summary": None, "result_json": None,
                "updated_at": now})
        if profile == "specialist_evidence":
            self.specialists.initialize(run_id)
        return self.get_run(run_id)

    def _dataset_text(self, run):
        dataset_id = run.get("dataset_id")
        if dataset_id:
            dataset = self.store.get_dataset(dataset_id)
            if dataset is not None:
                return dataset["content"]
        return run.get("dataset_text") or ""

    def _merge_inputs(self, run):
        declared = json.loads(run.get("joins_json") or "{}")
        inputs = []
        for item in declared.get("joins") or []:
            dataset = self.store.get_dataset(item["dataset_id"])
            if dataset is None:
                continue  # the merge then reports a join it cannot make
            inputs.append({**item, "name": dataset["name"], "content": dataset["content"],
                           "snapshot": dataset["sha256"][:16]})
        return {"joins": inputs, "join_breakdown": declared.get("breakdown")}

    def _context(self, run, tasks):
        ctx = {"goal": run["goal"], "dataset_text": self._dataset_text(run),
               "dataset_name": run["dataset_name"], "run_id": run["id"],
               "glossary": self.glossary,
               "report_language": run.get("report_language") or "en",
               "mapping": (json.loads(run["mapping_json"])
                           if run.get("mapping_json") else None),
               "assumptions": (json.loads(run["assumptions_json"])
                               if run.get("assumptions_json") else None)}
        for task in tasks:
            if task["state"] == "succeeded" and task["result_json"]:
                result = json.loads(task["result_json"])
                ctx[task["role"]] = result.get("output", {})
                ctx[task["role"] + "_result"] = result
        # The run declares its custom stages, and provenance, validation
        # and the report audit exactly that list (analytics.evidence_stages).
        custom = [t["role"] for t in tasks
                  if t["role"] not in analytics.ROLE_TITLES]
        ctx["custom_stages"] = custom
        ctx["custom_titles"] = {t["role"]: t["title"] for t in tasks
                                if t["role"] in custom}
        ctx["custom_failures"] = {t["role"]: t["summary"] for t in tasks
                                  if t["role"] in custom and t["state"] == "failed"}
        return ctx

    def _reclaim_orphaned_tasks(self, run_id):
        """Put back any task a crash left marked running.

        A worker killed between tasks leaves nothing behind; killed
        *during* one it leaves that task marked running forever, and the
        engine used to walk straight past it to the next pending task.
        The run then continued without a stage its successors depend on
        and failed several stages later, with an error naming the wrong
        thing entirely — a crash mid-stage silently producing a broken
        run, which is the failure durability was supposed to rule out.

        Reaching this point means nobody holds a live lease on the run
        (the caller's own, or none), so a task marked running is not
        being executed by anyone: it is debris. Re-running it is safe
        because a stage is a pure function of the results before it, and
        a task's result is written once, at the end.
        """
        tasks = self.store.get_tasks(run_id)
        orphans = [t for t in tasks if t["state"] == "running"]
        for task in orphans:
            self.store.update("tasks", task["id"],
                              {"state": "pending", "summary": None,
                               "result_json": None})
        return self.store.get_tasks(run_id) if orphans else tasks

    def advance(self, run_id, lease_owner=None):
        if self.execution_mode == "worker" and lease_owner is None:
            # An HTTP request never does model work in worker mode. In
            # particular, do not acquire the stage's write transaction: a
            # separate worker may be holding it for a slow bounded stage.
            # The queued run itself is the durable request, so repeated
            # advance calls do not enqueue additional work.
            return self.get_run(run_id)
        specialist_run = any(t["role"] == "evidence_steward" for t in self.store.get_tasks(run_id))
        if specialist_run:
            if self.specialists is None:
                raise ValueError("Specialist driver is unavailable; the checkpoint is preserved.")
            return self.specialists.advance(run_id, lease_owner)
        budget = getattr(self.gateway, "budget", None)
        owner_context = tenant.current_owner.set(self.owner_of(run_id))
        try:
            # Commit admission before taking the run transaction. The latter
            # preserves all existing state/CAS invariants, while rollback cannot
            # erase credits for provider work that has already happened.
            scope = (budget.reservation(self._model_attempt_bound())
                     if budget is not None else nullcontext())
            with scope:
                with self.store.atomic("run:" + run_id):
                    return self._advance_atomic(run_id, lease_owner)
        finally:
            tenant.current_owner.reset(owner_context)

    def _model_attempt_bound(self):
        """Conservative bound for one built-in stage, never the daily budget.

        Narration, Hermes and agent notes each use at most two attempts.
        Each external consultant may use two structured attempts, repeat
        once for compatibility, then two text fallback attempts. Reserve
        across configured roles so a concurrent advance changing the pending
        stage cannot invalidate admission. Unused credits are returned.
        Custom stages exceeding this bounded envelope degrade, never top up
        inside a state transaction.
        """
        from server.orchestration import BUILT_IN
        bound = 2  # the pipeline's narrated stage
        if self.roles is not None:
            bound += 2 * (self.roles.hermes not in (None, BUILT_IN))
            bound += 2 * (self.roles.agents not in (None, BUILT_IN))
            bound += 6 * sum(name != BUILT_IN for name in self.roles.consultants)
        return bound

    def _advance_atomic(self, run_id, lease_owner=None):
        """Execute exactly one bounded task; every transition is durable.

        If a background worker holds a live lease on this run, a client's
        advance is a no-op that simply returns the current state: the two
        never execute the same task. In client mode, an expired lease
        permits clients to resume. Worker mode leaves recovery to another
        worker and never falls back to request-thread computation.
        """
        run = self._row(run_id)
        if run.get("paused"):
            raise ValueError("Run is paused — resume it before advancing.")
        holder = run.get("lease_owner")
        if (holder and holder != lease_owner
                and (run.get("lease_expires_at") or "") > _stamp(_utcnow())):
            return self.get_run(run_id)
        if run["state"] in ("completed", "partially_completed", "failed", "cancelled"):
            raise ValueError(f"Run is {run['state']} and cannot advance.")
        if run["state"] == "awaiting_approval":
            raise ValueError("Run is awaiting approval — decide the approval first.")
        tasks = self._reclaim_orphaned_tasks(run_id)
        task = next((t for t in tasks if t["state"] == "pending"), None)
        if task is None:
            return self.get_run(run_id)
        self._set_run_state(run_id, "running")

        if task["role"] == "publish":
            return self._request_publish_approval(run_id, task)

        stage = (dict(analytics.PIPELINE).get(task["role"])
                 or analytics.OPTIONAL_STAGES.get(task["role"]))
        custom = self.stages.get(task["role"])
        if stage is None and custom is None:
            # A run created by an earlier pipeline version, or with a
            # custom stage that is no longer registered. Say so plainly
            # rather than failing with an unrelated error later.
            message = (f"This run was created with a pipeline this server does "
                       f"not have (stage “{task['role']}” is not built in and not "
                       "registered) and cannot be resumed. Its stored results "
                       "remain readable; start a new run to analyze the same "
                       "data with the current pipeline.")
            self._set_task(task["id"], "failed", summary=message)
            self._set_run_state(run_id, "failed", error=message)
            return self.get_run(run_id)

        self._set_task(task["id"], "running")
        ctx = self._context(run, tasks)
        if task["role"] == "merge":
            # Read only for the stage that needs them: joined datasets can
            # be large, and no other stage reads them raw.
            ctx.update(self._merge_inputs(run))
        if custom is not None:
            return self._advance_custom(run_id, task, custom, ctx)
        if task["role"] == "reporter":
            ctx["orchestration"] = self._consult(run, ctx)
        try:
            result = (stage(ctx, gateway=self.gateway)
                      if task["role"] in analytics.NARRATED_STAGES else stage(ctx))
        except Exception as error:  # defensive: a stage bug must not hang the run
            self._set_task(task["id"], "failed", summary=f"Stage error: {error}")
            self._set_run_state(run_id, "failed", error=str(error))
            return self.get_run(run_id)

        if result["status"] == "failed" and task["role"] != "validator":
            self._set_task(task["id"], "failed", summary=result["summary"], result=result)
            self._set_run_state(run_id, "failed", error=result["summary"])
            return self.get_run(run_id)

        self._annotate(run, task, tasks, result, ctx)
        if ctx.get("orchestration"):
            result["orchestration"] = ctx["orchestration"]
        if ctx.get("orchestration_problem"):
            result["orchestration_problem"] = ctx["orchestration_problem"]
        self._set_task(task["id"], "succeeded", summary=result["summary"], result=result)

        if task["role"] == "validator" and not result["output"]["passed"]:
            # Rejected work: skip publishing, finish as partially completed.
            for t in self.store.get_tasks(run_id):
                if t["state"] == "pending":
                    self._set_task(t["id"], "skipped",
                                   summary="Skipped: validation rejected the work.")
            self._set_run_state(run_id, "partially_completed",
                                error="Validation checks failed.")
            return self.get_run(run_id)

        if task["role"] == "reporter":
            self.store.insert("artifacts", {
                "id": self.new_id(), "run_id": run_id,
                "name": "analytics-report", "kind": "markdown", "version": 1,
                "content": result["output"]["report_markdown"],
                "published_path": None, "created_at": _now()})
        return self.get_run(run_id)

    def _roles_for(self, run, ctx, texts):
        """The roles a run may use. The same personal-data boundary the
        narrator keeps (server/model_privacy.py) applies here: when the
        run's privacy scan or the outgoing sentences carry personal data,
        every model role is played by the built-in writer instead."""
        roles = self.roles
        if roles is None or roles.all_built_in:
            return roles
        if model_privacy.run_blocks_model(self.store, run["id"]) or model_privacy.blocks_model(
                privacy=ctx.get("privacy"), merged=ctx.get("merge"),
                texts=[run.get("goal") or "", *texts]):
            return roles.restricted()
        return roles

    def _annotate(self, run, task, tasks, result, ctx):
        """Model notes on a finished stage: Hermes' plan on the planner, the
        agent's note on every stage with findings. Words only, grounded in
        the stage's own verified claims; a model failure never fails a run."""
        if self.roles is None:
            return
        language = run.get("report_language") or "en"
        try:
            facts = [claim.get("text") or "" for claim in result.get("claims", [])]
            # Include the just-completed privacy/merge result before persistence.
            current = {**ctx, task["role"]: result.get("output", {})}
            roles = self._roles_for(run, current, facts + [t["title"] for t in tasks])
            if roles is None:
                return
            if task["role"] == "planner":
                plan = roles.plan(run["goal"], [t["title"] for t in tasks], language)
                if plan:
                    result["hermes_plan"] = plan
            note = roles.agent_note(run["goal"], task["role"], result, language)
            if note:
                result["agent_note"] = note
        except Exception as error:
            # A model failure never fails a run, but it is not silent
            # (assessment G12): the task result and the engine both say why.
            problem = f"{task['role']}: {type(error).__name__}: {str(error)[:200]}"
            result["orchestration_problem"] = problem
            self.orchestration_problems.append(problem)
            del self.orchestration_problems[:-MAX_ORCHESTRATION_PROBLEMS]

    def _consult(self, run, ctx):
        """The consultants and Hermes' brief, read by the reporter."""
        if self.roles is None:
            return None
        facts = [claim["text"] for stage in analytics.evidence_stages(ctx)
                 for claim in ctx.get(stage + "_result", {}).get("claims", [])
                 if claim.get("text")]
        try:
            roles = self._roles_for(run, ctx, facts)
            if roles is None:
                return None
            return roles.consult(run["goal"], facts, run.get("report_language") or "en")
        except Exception as error:
            problem = f"consult: {type(error).__name__}: {str(error)[:200]}"
            ctx["orchestration_problem"] = problem
            self.orchestration_problems.append(problem)
            del self.orchestration_problems[:-MAX_ORCHESTRATION_PROBLEMS]
            return None

    def _advance_custom(self, run_id, task, descriptor, ctx):
        """Run a registered stage under the contract (ADR 0020).

        What the built-in stages found is safe from it because every
        stage's context is rebuilt from the stored results (a write to
        this dict reaches no later stage). The copy is for the one live
        object in the context: the glossary, read once per process and
        shared by every run — a stage must not be able to certify its
        own definition of revenue for everyone who runs after it. Its
        result is checked against the contract before anything is
        recorded. A failure is the stage's, not the run's, unless the
        stage declared otherwise — and the report then says the stage
        failed rather than silently lacking it.
        """
        try:
            result = deadline.call_with_deadline(descriptor.run, self.stage_timeout,
                                                 copy.deepcopy(ctx))
            result = stage_registry.validate_result(task["role"], result)
        except deadline.Timeout:
            # The stage keeps running on its abandoned thread; its result,
            # if it ever comes, is never recorded (G10).
            message = (f"Custom stage “{task['role']}” timed out after "
                       f"{self.stage_timeout:g} s and was abandoned.")
            return self._custom_failed(run_id, task, descriptor, message)
        except Exception as error:
            message = f"Custom stage “{task['role']}” failed: {error}"
            return self._custom_failed(run_id, task, descriptor, message)
        if result["status"] == "failed":
            return self._custom_failed(run_id, task, descriptor,
                                       result["summary"], result)
        self._set_task(task["id"], "succeeded", summary=result["summary"],
                       result=result)
        return self.get_run(run_id)

    def _custom_failed(self, run_id, task, descriptor, message, result=None):
        self._set_task(task["id"], "failed", summary=message, result=result)
        if getattr(descriptor, "can_fail_run", False):
            self._set_run_state(run_id, "failed", error=message)
        return self.get_run(run_id)

    def _request_publish_approval(self, run_id, task):
        self._verify_specialist_publication(run_id)
        # The approval is read by the same person who reads the report, so
        # it is in the report's language. `risk` stays an enum (ADR 0022).
        arabic = (self._row(run_id).get("report_language") or "en") == "ar"
        artifact = self.store.latest_artifact(run_id)
        if artifact is None:
            self._set_task(task["id"], "skipped",
                           summary="لا يوجد ما يُنشر." if arabic
                           else "No artifact to publish.")
            self._set_run_state(run_id, "completed")
            return self.get_run(run_id)
        if self.store.pending_approval(run_id) is None:
            content_hash = hashlib.sha256(artifact["content"].encode()).hexdigest()
            self.store.insert("approvals", {
                "id": self.new_id(), "run_id": run_id,
                "action": (("نشر تقرير التحليل في المخزن الدائم" if arabic else
                            "Publish the analytics report to the durable vault")
                           if self.publish_target == "database" else
                           ("نشر تقرير التحليل في مخزن Obsidian" if arabic else
                            "Publish the analytics report to the Obsidian vault")),
                "target": self.publication_destination(), "risk": "high",
                "impact": (("يحفظ ملاحظتي Markdown (التقرير وسجل التشغيل) في قاعدة البيانات بصلاحيات مساحة العمل." if arabic else
                            "Stores two Markdown notes (report + run log) in the database under workspace permissions.")
                           if self.publish_target == "database" else
                           ("يكتب ملاحظتين بصيغة Markdown (التقرير وسجل التشغيل) في المخزن المحلي." if arabic else
                            "Writes two markdown notes (report + run log) to the local vault.")),
                "reversibility": ("قابل للتراجع: احذف الملاحظتين المنشأتين." if arabic
                                  else "Reversible: delete the created notes."),
                "content_hash": content_hash, "state": "pending",
                "created_at": _now(), "decided_at": None})
        self._set_task(task["id"], "awaiting_approval",
                       summary="بانتظار موافقة بشرية على النشر." if arabic
                       else "Waiting for human approval to publish.")
        self._set_run_state(run_id, "awaiting_approval")
        return self.get_run(run_id)

    def decide_approval(self, run_id, approval_id, decision, approver=None):
        with self.store.atomic("run:" + run_id):
            return self._decide_approval_atomic(run_id, approval_id, decision, approver)

    def refresh_publication_review(self, run_id):
        """Request fresh consent for a changed destination, never publish.

        A changed report cannot use this shortcut: its evidence must go through
        a new governed analysis. Repeating this request at the same destination
        returns the current pending review without another history entry.
        """
        with self.store.atomic("run:" + run_id):
            run = self._row(run_id)
            arabic = (run.get("report_language") or "en") == "ar"
            if run["state"] != "awaiting_approval":
                raise ValueError("تتطلب مراجعة النشر الجديدة تحليلًا بانتظار الموافقة." if arabic
                                 else "A new publication review requires a run awaiting approval.")
            pending = self.store.pending_approval(run_id)
            artifact = self.store.latest_artifact(run_id)
            if not pending or not artifact:
                raise ValueError("مراجعة التقرير المعلّقة غير متاحة." if arabic
                                 else "The pending report review is unavailable.")
            current_hash = hashlib.sha256(artifact["content"].encode()).hexdigest()
            if current_hash != pending["content_hash"]:
                raise ValueError("تغيّر التقرير؛ ابدأ تحليلًا جديدًا خاضعًا للضوابط قبل طلب الموافقة." if arabic
                                 else "The report changed; start a new governed analysis before requesting approval.")
            if pending["target"] == self.publication_destination():
                return self.get_run(run_id)
            self.store.update("approvals", pending["id"], {"state": "superseded"})
            task = next(task for task in self.store.get_tasks(run_id) if task["role"] == "publish")
            return self._request_publish_approval(run_id, task)

    def _decision_record(self, tasks):
        """The run's decision record, as the sensitivity stage completed it
        or as the prescriptive stage wrote it; None when neither ran. The
        record carries the recommendation claim's id when there is one."""
        results = {}
        for t in tasks:
            if t["state"] == "succeeded" and t.get("result_json"):
                results[t["role"]] = json.loads(t["result_json"])
        for role in ("sensitivity", "prescriptive"):
            record = (results.get(role) or {}).get("output", {}).get("decision")
            if record:
                return dict(record)
        return None

    def _recommends(self, tasks):
        for t in tasks:
            if t["role"] == "prescriptive" and t["state"] == "succeeded" and t.get("result_json"):
                claims = json.loads(t["result_json"]).get("claims") or []
                return any(c.get("id") == "cl_recommendation" for c in claims)
        return False

    def _verify_specialist_publication(self, run_id):
        if any(t["role"] == "evidence_steward" for t in self.store.get_tasks(run_id)):
            if self.specialists is None:
                raise ValueError("Specialist verification is unavailable; publication is blocked.")
            self.specialists.ensure_verified(run_id)

    def _decide_approval_atomic(self, run_id, approval_id, decision, approver=None):
        approval = self.store.get_approval(approval_id, run_id)
        if approval is None:
            raise KeyError(approval_id)
        if approval["state"] != "pending":
            raise ValueError(f"Approval already {approval['state']}.")
        tasks = self.store.get_tasks(run_id)
        if decision == "approve" and self._recommends(tasks) and not self._decision_record(tasks):
            # A recommendation without its decision record cannot be
            # published: there would be no audit trail from advice to
            # action (assessment A13).
            raise ValueError("The run recommends an action but carries no decision "
                             "record; publishing is refused.")
        task = next(t for t in self.store.get_tasks(run_id)
                    if t["role"] == "publish")
        artifact = self.store.latest_artifact(run_id)
        # Approval binds to the exact content hash: altered content invalidates it.
        current_hash = hashlib.sha256(artifact["content"].encode()).hexdigest()
        if current_hash != approval["content_hash"]:
            raise ValueError("Artifact changed after approval was requested.")
        if decision == "approve":
            self._verify_specialist_publication(run_id)
            if approval["target"] != self.publication_destination():
                raise PublicationDestinationChanged(
                    "تغيرت وجهة النشر بعد المراجعة. حدّث طلب المراجعة ثم اقرأ التقرير والوجهة الجديدة قبل الموافقة."
                    if (self._row(run_id).get("report_language") or "en") == "ar" else
                    "The publication destination changed after review. Update the review request, then read the report and new destination before approving.")
            path, where = self._publish(run_id, artifact)
            self.store.update("approvals", approval_id,
                              {"state": "approved_once", "decided_at": _now(),
                               "decided_by": approver})
            # The path a reader sees is relative to the vault folder
            # (assessment B19): never the server's absolute layout.
            self.store.update("artifacts", artifact["id"],
                              {"published_path": self._relative(path)})
            self._set_task(task["id"], "succeeded",
                           summary=(f"Published to {self._relative(path)}." if where == "vault" else
                                    f"Published to the database store as {self._relative(path)}."
                                    if where == "database" else
                                    f"Published to the database store as {path}; the vault "
                                    "folder is not writable on this host."))
            self._set_run_state(run_id, "completed")
        else:
            self.store.update("approvals", approval_id,
                              {"state": "rejected", "decided_at": _now(),
                               "decided_by": approver})
            self._set_task(task["id"], "skipped",
                           summary="Publishing rejected by the user; no note was written.")
            self._set_run_state(run_id, "completed")
        return self.get_run(run_id)

    def _relative(self, path):
        """A published path as the vault sees it: `Reports/<note>.md`, or
        the `store:` form when the vault folder was not writable."""
        text = str(path)
        if text.startswith("store:") or not Path(path).is_absolute():
            return Path(text).as_posix()
        try:
            return Path(path).resolve().relative_to(Path(self.vault_dir).resolve()).as_posix()
        except ValueError:
            return Path(path).name

    def publication_destination(self):
        return "database:Reports" if self.publish_target == "database" else str(self.vault_dir / "Reports")

    def _publish(self, run_id, artifact):
        """Publish the approved report and its run log.

        The database store is the publish target: both notes are written
        there first, inside the approval's transaction, so a hosted host
        with a read-only filesystem publishes completely or not at all
        (assessment B13). The vault folder is then written as a courtesy
        for Obsidian; when it cannot be, the published path names the
        store and the approval says so. Returns (path, where), with where
        one of "vault", "database" or "fallback"."""
        run = self._row(run_id)
        slug = re.sub(r"[^a-z0-9]+", "-", run["goal"].lower()).strip("-")[:48] or "report"
        note_name = f"{slug}-{run_id}.md"
        note_stem = note_name[:-3]
        frontmatter = (
            "---\n"
            f"type: analytics-report\nrun: {run_id}\n"
            f"generated: {_now()}\nstatus: approved\n"
            f"dataset: {json.dumps(run['dataset_name'], ensure_ascii=False)}\n"
            f"lang: {run.get('report_language') or 'en'}\n---\n\n"
        )
        report_text = frontmatter + artifact["content"] + f"\n\nRun log: [[{run_id}]]\n"
        log_lines = [f"---\ntype: run-log\nrun: {run_id}\ngenerated: {_now()}\n---",
                     f"# Run {run_id}", "", f"**Goal:** {run['goal']}", "",
                     "| Stage | Outcome |", "| --- | --- |"]
        for t in self.store.get_tasks(run_id):
            log_lines.append(f"| {t['title']} | {t['state']}: {t['summary'] or ''} |")
        log_lines.append(f"\nReport: [[{note_stem}]]\n")
        log_text = "\n".join(log_lines)
        # The store writes share the approval/state transaction. Database
        # mode never touches a filesystem, including a read-only serverless
        # root; vault mode writes the folder too and falls back to the store
        # alone when the folder cannot be written (B13).
        now = _now()
        self.store.upsert_note(f"Reports/{note_name}", run_id, report_text, now)
        self.store.upsert_note(f"Runs/{run_id}.md", run_id, log_text, now)
        if self.publish_target == "database":
            return Path("Reports") / note_name, "database"
        try:
            reports = self.vault_dir / "Reports"
            logs = self.vault_dir / "Runs"
            reports.mkdir(parents=True, exist_ok=True)
            logs.mkdir(parents=True, exist_ok=True)
            note = reports / note_name
            note.write_text(report_text, encoding="utf-8")
            (logs / f"{run_id}.md").write_text(log_text, encoding="utf-8")
        except OSError:
            return f"store:Reports/{note_name}", "fallback"
        return note, "vault"

    def set_paused(self, run_id, paused):
        with self.store.atomic("run:" + run_id):
            return self._set_paused_atomic(run_id, paused)

    def _set_paused_atomic(self, run_id, paused):
        """Pause is durable, not a client-side toggle: a background worker
        must honour it too, or the button would stop meaning anything."""
        run = self._row(run_id)
        if run["state"] not in ("queued", "running"):
            raise ValueError(f"Run is {run['state']} and cannot be paused.")
        self.store.update("runs", run_id,
                          {"paused": 1 if paused else 0, "updated_at": _now()})
        return self.get_run(run_id)

    def cancel(self, run_id):
        with self.store.atomic("run:" + run_id):
            return self._cancel_atomic(run_id)

    def _cancel_atomic(self, run_id):
        self._set_run_state(run_id, "cancelled")
        for t in self.store.get_tasks(run_id):
            if t["state"] in ("pending", "awaiting_approval"):
                self._set_task(t["id"], "cancelled")
        pending = self.store.pending_approval(run_id)
        if pending is not None:
            self.store.update("approvals", pending["id"],
                              {"state": "cancelled", "decided_at": _now()})
        return self.get_run(run_id)

    # -- the analysis table (ADR 0031) ------------------------------------
    TABLE_ROLES = ("profiler", "cleaner", "merge", "governance", "preparer")

    def table_source(self, run_id):
        """What reading a run's analysis table needs, taken from the store:
        a cache key and the stored results. Cheap, so it can run under the
        server's lock; `load_table` does the parsing outside it."""
        run = self._row(run_id)
        tasks = {t["role"]: t for t in self.store.get_tasks(run_id)}
        source = tasks.get("merge") or tasks.get("cleaner")
        if source is None or source["state"] != "succeeded" or not source["result_json"]:
            raise TableNotReady(run_id)
        stored = {role: tasks[role]["result_json"] for role in self.TABLE_ROLES
                  if role in tasks and tasks[role]["state"] == "succeeded"
                  and tasks[role]["result_json"]}
        if "collector" in tasks and tasks["collector"]["result_json"]:
            stored["collector"] = tasks["collector"]["result_json"]
        return (run_id, source["id"], source["updated_at"]), stored, run

    def load_table(self, key, stored):
        """The analysis table as a query.Table, parsed once per key."""
        with self._tables_lock:
            if key in self._tables:
                self._tables.move_to_end(key)
                return self._tables[key]
        outputs = {role: json.loads(text)["output"] for role, text in stored.items()
                   if role != "collector"}
        merged = outputs.get("merge")
        if merged:
            rows, columns = merged["rows"], merged["columns"]
            numeric = merged["numeric_columns"]
        else:
            rows = outputs["cleaner"]["rows"]
            # The cleaner keeps the CSV's column order in each row; an empty
            # table has none, so only then is the larger collector result read.
            columns = (list(rows[0].keys()) if rows else
                       json.loads(stored["collector"])["output"]["columns"])
            numeric = outputs["profiler"]["numeric_columns"]
        roles = {}
        for column in numeric:
            roles[column] = "measure"
        # A mapped date is read by the cleaner; an unmapped one is found by
        # name by the preparer. Either way it is the run's time axis.
        date_col = ((outputs.get("cleaner") or {}).get("date_col")
                    or (outputs.get("preparer") or {}).get("date_col"))
        if date_col:
            roles[date_col] = "date"
        for record in (merged or {}).get("joins", []):
            for column in record["added_columns"]:
                roles.setdefault(column, "joined")
        group_col = (outputs.get("preparer") or {}).get("group_col")
        if group_col:
            roles[group_col] = "breakdown"
        measure = (outputs.get("governance") or {}).get("measure")
        if measure:
            roles[measure] = "analysed"
        table = query.table_from(columns, numeric, rows, roles)
        with self._tables_lock:
            self._tables[key] = table
            while len(self._tables) > TABLE_CACHE_SIZE:
                self._tables.popitem(last=False)
        return table

    def analysis_table(self, run_id):
        key, stored, _ = self.table_source(run_id)
        return self.load_table(key, stored)

    # -- reads ------------------------------------------------------------
    def _row(self, run_id):
        run = self.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def list_runs(self, owner=None, state=None):
        return self.store.list_runs(owner=owner, state=state)

    def owner_of(self, run_id):
        return self._row(run_id).get("owner") or "local-owner"

    def get_run(self, run_id):
        run = self._row(run_id)
        tasks = []
        charts, report, reports, models = [], None, [], []
        questions = dict(analytics.REPORT_SECTIONS)
        for t in self.store.get_tasks(run_id):
            result = json.loads(t["result_json"]) if t["result_json"] else None
            tasks.append({"id": t["id"], "role": t["role"], "title": t["title"],
                          "state": t["state"], "summary": t["summary"],
                          "quality_checks": (result or {}).get("quality_checks", []),
                          "claims": (result or {}).get("claims", [])})
            if result and t["role"] == "visuals":
                charts = result["output"].get("charts", [])
            # One report per analytics type, readable on its own.
            if result and t["role"] in questions:
                content = result["output"].get("report_markdown")
                if content:
                    reports.append({"type": t["role"], "question": questions[t["role"]],
                                    # As stored at creation: in the run's language.
                                    "title": t["title"],
                                    # The one sentence a business reader needs,
                                    # surfaced rather than left inside the markdown.
                                    "headline": result["output"].get("headline", ""),
                                    "content": content})
            # A model reports its card, baseline included (ADR 0033).
            if t["state"] == "succeeded":
                models.extend({**card, "role": t["role"], "title": t["title"]}
                              for card in model_cards(result))
            # A custom stage that wrote a section gets its own tab too.
            if result and t["role"] not in analytics.ROLE_TITLES:
                content = result["output"].get("report_markdown")
                if content:
                    reports.append({"type": t["role"],
                                    "question": result["output"].get("question") or "",
                                    "title": t["title"],
                                    "headline": result["output"].get("headline", ""),
                                    "content": content})
        artifact = self.store.latest_artifact(run_id)
        if artifact:
            report = {"id": artifact["id"], "name": artifact["name"],
                      "version": artifact["version"], "content": artifact["content"],
                      "published_path": artifact["published_path"]}
        approvals = [
            {key: a.get(key) for key in ("id", "action", "target", "risk", "impact",
                                         "reversibility", "state", "created_at",
                                         "decided_at", "decided_by")}
            for a in self.store.approvals_for_run(run_id)
        ]
        # The decision record, completed by the gate: who decided, what and
        # when, from the approval row itself (A13). No stage writes this part.
        decision = self._decision_record(self.store.get_tasks(run_id))
        if decision is not None:
            gate = next((a for a in approvals if a["state"] in ("approved_once", "rejected")), None)
            decision["approval"] = ({"state": gate["state"], "decided_at": gate["decided_at"],
                                     "decided_by": gate.get("decided_by")} if gate else None)
        declared = json.loads(run.get("joins_json") or "{}")
        joins = [{key: item.get(key) for key in ("dataset_id", "alias", "how", "keys")}
                 for item in declared.get("joins") or []]
        return {"id": run["id"], "goal": run["goal"],
                "execution": {"mode": self.execution_mode, "poll_after_ms": 2500},
                "dataset_name": run["dataset_name"], "state": run["state"],
                "joins": joins, "breakdown": declared.get("breakdown"),
                "report_language": run.get("report_language") or "en",
                "error": run["error"], "created_at": run["created_at"],
                "updated_at": run["updated_at"], "tasks": tasks,
                "paused": bool(run.get("paused")),
                "approvals": approvals, "charts": charts, "report": report,
                "reports": reports, "models": models, "decision": decision,
                "assumptions": (json.loads(run["assumptions_json"])
                                if run.get("assumptions_json") else None),
                # The live source a refresh made this run from (ADR 0034).
                "connector_id": run.get("connector_id")}
