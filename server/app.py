"""FastAPI adapter that exposes the existing Agent class as a web API.

This layer contains no business logic. Every operation is mapped onto the
Agent's already-tested command surface (/remember, /forget, /set, /clear)
or reads the Agent's public state, and responses return fresh state
snapshots so the frontend never has to parse reply strings.

The command-line application (python main.py) is unaffected by this module.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from agent import Agent, language_code
from server.agent_runtime import build_runtime
from server import knowledge as knowledge_module
from server import analytics
from server import datasets as dataset_reader
from server import joins as joining
from server import live
from server import mapping as colmap
from server import query as table_query
from server.executive import ExecutiveDashboardAgent, parse_filters as executive_filters
from server import executive_export
from server.maintenance import kpis as kpi_register
from server.maintenance import performance
from server.assistant import Assistant, redact_reference_turns
from server.connectors import Busy, ConnectorError, Connectors, TooSoon
from server.model_gateway import ModelGateway
from server.orchestration import ModelRoles
from server.routing import RoutedGateway, build_router
from server.stages import describe, load_stages
from server.runs import (RunEngine, TableNotReady, dataset_summary,
                         resolve_vault_dir)
from server import demo
from server.auth import DEMO_PRINCIPAL, AuthError, build_identity, public_auth_config
from server.quota import ModelBudget, QuotaExceeded, load_limits
from server import tenant
from server.quota import usage as quota_usage
from server.rate_limit import WRITE_METHODS, RateLimiter, StoreRateLimiter
from server.storage import DbMemoryBackend, PostgresStore, open_store, is_database_error
from server.worker import worker_status
from server.operations_api import install_operations_api
from server.reliability_api import install_reliability_api
from server.pilot import install_pilot_api
from server.rmd_api import install_rmd_api
from server.rmd_workflow import authorize_run as authorize_evidence_run
from server.speech import LocalSpeech, SpeechError, MAX_BYTES as MAX_AUDIO_BYTES, content_format
from utils import load_config

# The only inline script is the fixed prepaint theme/language bootstrap in
# frontend/index.html. Pin its exact bytes, never authorize arbitrary inline JS.
PREPAINT_SCRIPT_HASH = "sha256-VPW7AEpPmugLy0qUATyKc9v5mNJnHZkoos20wLQ3uVI="
API_CONTENT_POLICY = (
    "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
)


def _browser_origin(value):
    """One configured HTTP(S) origin, never credentials or CSP syntax."""
    if not value or any(ord(c) < 33 or c in ";'\"<>" for c in value):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None
        host = parts.hostname.encode("idna").decode("ascii")
        if not re.fullmatch(r"[A-Za-z0-9.:-]+", host):
            return None
        host = f"[{host}]" if ":" in host else host
        port = f":{parts.port}" if parts.port else ""
        return f"{parts.scheme}://{host}{port}"
    except (ValueError, UnicodeError):
        return None


def application_content_policy(env):
    """Built shell policy; provider and optional API origins are operator-set.

    Inline styles are retained for React chart positioning and blob report
    previews, which inherit the opener's policy. Scripts never get that grant.
    The local model and speech services are contacted only by the server.
    """
    origins = sorted({origin for name in ("SUPABASE_URL", "VITE_API_BASE")
                      if (origin := _browser_origin(env.get(name, "")))})
    connect = " ".join(["'self'", *origins])
    return ("default-src 'none'; "
            f"script-src 'self' '{PREPAINT_SCRIPT_HASH}'; script-src-attr 'none'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; "
            f"connect-src {connect}; media-src 'self' blob:; "
            "worker-src 'self'; manifest-src 'self'; frame-src 'none'; "
            "object-src 'none'; base-uri 'none'; form-action 'self'; "
            "frame-ancestors 'none'")


MAX_SESSIONS = 32
MAX_TEXT_LENGTH = 4000
PREFERENCE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
# One JSON line per request (assessment finding B10). An incoming id is
# honoured only when it is short and safe to print; the subject is a
# hash prefix, never the raw subject, and never the token.
REQUEST_LOG = logging.getLogger("agentic_os.requests")
# Unexpected errors, one JSON line each with the request id and the
# traceback in the server log (assessment B9); never in a response.
ERROR_LOG = logging.getLogger("agentic_os.errors")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
# Per-session locks are dropped once this many sessions have been seen,
# keeping only the ones a request is holding at that moment.
MAX_SESSION_LOCKS = 4096


def request_id_for(header):
    """The caller's X-Request-ID when it is printable and bounded,
    otherwise a fresh one."""
    if header and REQUEST_ID_PATTERN.match(header):
        return header
    return uuid.uuid4().hex


def subject_hash(subject):
    """A 12-hex-character SHA-256 prefix: enough to group one caller's
    requests in a log, never enough to recover who they are."""
    return hashlib.sha256(str(subject).encode("utf-8")).hexdigest()[:12]

# Presentation metadata for the Agent's command surface, used by the UI for
# quick actions and the command palette. Behaviour lives in agent.py only.
COMMANDS = [
    {"command": "/help", "usage": "/help", "description": "Show available commands"},
    {"command": "/remember", "usage": "/remember <information>", "description": "Save information to memory"},
    {"command": "/recall", "usage": "/recall", "description": "Show saved memory"},
    {"command": "/forget", "usage": "/forget <key> | all", "description": "Remove saved memory"},
    {"command": "/set", "usage": "/set <setting> <value>", "description": "Update a preference"},
    {"command": "/preferences", "usage": "/preferences", "description": "Show current preferences"},
    {"command": "/history", "usage": "/history", "description": "Show conversation history"},
    {"command": "/clear", "usage": "/clear", "description": "Clear conversation history"},
    {"command": "/exit", "usage": "/exit", "description": "End the session"},
]

# The same commands, described in Arabic. A command's spelling is the
# same in either language — it is what the person types.
COMMANDS_ARABIC = [
    {"command": "/help", "usage": "/help", "description": "عرض الأوامر المتاحة"},
    {"command": "/remember", "usage": "/remember <information>", "description": "حفظ معلومة في الذاكرة"},
    {"command": "/recall", "usage": "/recall", "description": "عرض الذاكرة المحفوظة"},
    {"command": "/forget", "usage": "/forget <key> | all", "description": "إزالة ذاكرة محفوظة"},
    {"command": "/set", "usage": "/set <setting> <value>", "description": "تحديث تفضيل"},
    {"command": "/preferences", "usage": "/preferences", "description": "عرض التفضيلات الحالية"},
    {"command": "/history", "usage": "/history", "description": "عرض سجل المحادثة"},
    {"command": "/clear", "usage": "/clear", "description": "مسح سجل المحادثة"},
    {"command": "/exit", "usage": "/exit", "description": "إنهاء الجلسة"},
]


def commands_for(language):
    """The command catalogue in the language the session replies in."""
    return COMMANDS_ARABIC if language_code(language) == "ar" else COMMANDS


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Session:
    """One conversation: an Agent instance plus its visible transcript.

    Sessions are durable: every mutation is written back to the store, so
    conversations survive an application restart in both SQLite and
    hosted-PostgreSQL modes."""

    def __init__(self, config, memory_backend=None, row=None, owner="local-owner"):
        self.agent = Agent(config, memory_backend=memory_backend)
        self.owner = (row or {}).get("owner") or owner
        if row is None:
            self.id = uuid.uuid4().hex
            self.transcript = []
            self.ended = False
            self.created_at = now_iso()
            self._next_entry_id = 1
        else:
            self.id = row["id"]
            self.created_at = row["created_at"]
            self.ended = bool(row["ended"])
            self.transcript = redact_reference_turns(json.loads(row["transcript_json"]),
                                                    json.loads(row["preferences_json"]).get("language", "en"))
            self._next_entry_id = row["next_entry_id"]
            self.agent.preferences.update(json.loads(row["preferences_json"]))
            self.agent.history = json.loads(row["history_json"])

    def to_row(self):
        return {
            "id": self.id,
            "owner": self.owner,
            "created_at": self.created_at,
            "updated_at": now_iso(),
            "ended": 1 if self.ended else 0,
            "preferences_json": json.dumps(self.agent.preferences),
            "history_json": json.dumps(self.agent.history),
            "transcript_json": json.dumps(self.transcript),
            "next_entry_id": self._next_entry_id,
        }

    def add_entry(self, role, text, **extra):
        """Append a turn. `extra` carries what the assistant knows about an
        agent reply — who understood it (rules, model, command), what it
        did, and a pending confirmation — so the transcript is the record
        and survives a restart with it."""
        entry = {
            "id": self._next_entry_id,
            "role": role,
            "text": text,
            "time": now_iso(),
        }
        entry.update({key: value for key, value in extra.items() if value is not None})
        self._next_entry_id += 1
        self.transcript.append(entry)
        return entry

    def snapshot(self):
        return {
            "session_id": self.id,
            "agent_name": self.agent.name,
            "version": self.agent.version,
            "welcome": self.agent.get_welcome_message(),
            "ended": self.ended,
            "created_at": self.created_at,
            "transcript": self.transcript,
            "preferences": dict(self.agent.preferences),
            "memory": dict(self.agent.memory),
            "memory_entries": self.agent.memory_entries(),
            "history": list(self.agent.history),
            "memory_persisted": self.agent.memory_persistent,
            "commands": commands_for(self.agent.preferences.get("language")),
        }


class SessionIn(BaseModel):
    """Optional at creation: the language the interface is showing, so the
    agent's first words are already in it."""
    language: str | None = Field(default=None, max_length=64)


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class MemoryIn(BaseModel):
    information: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    category: str | None = Field(default=None, max_length=24)


class PreferenceIn(BaseModel):
    key: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=200)


class KeyPairIn(BaseModel):
    """One key of a join: a column of the table so far and the column of
    the joined dataset that holds the same values (ADR 0030)."""
    left: str = Field(min_length=1, max_length=200)
    right: str = Field(min_length=1, max_length=200)


class JoinIn(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=32)
    keys: list[KeyPairIn] = Field(min_length=1, max_length=joining.MAX_KEYS)
    how: str = Field(default="left", pattern="^(left|inner)$")
    alias: str | None = Field(default=None, max_length=24)


class JoinPreviewIn(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=32)
    joins: list[JoinIn] = Field(min_length=1, max_length=joining.MAX_JOINS)
    breakdown: str | None = Field(default=None, max_length=200)


class RunIn(BaseModel):
    goal: str = Field(min_length=3, max_length=500)
    profile: str | None = Field(default=None, max_length=64)
    # Pasted CSV. A file goes through POST /api/datasets (ADR 0024).
    dataset_text: str | None = Field(default=None, max_length=dataset_reader.MAX_UPLOAD_BYTES)
    dataset_id: str | None = Field(default=None, max_length=32)
    dataset_name: str | None = Field(default=None, max_length=100)
    # The language the report is written in (ADR 0022). The interface
    # sends the reader's language.
    language: str = Field(default="en", pattern="^(en|ar)$")
    # Other stored datasets joined onto this one, and an optional
    # breakdown from the merged table (ADR 0030).
    joins: list[JoinIn] | None = Field(default=None, max_length=joining.MAX_JOINS)
    breakdown: str | None = Field(default=None, max_length=200)
    # Decision inputs: an uplift per target, a cost per target and the
    # uplift range the sensitivity stage explores (slice three, A2, A13).
    # Validated in full by analytics.validate_assumptions.
    assumptions: dict | None = None
    # A caller's key for this creation; the Idempotency-Key header wins
    # when both are given (B14).
    idempotency_key: str | None = Field(default=None, max_length=200)


class MappingIn(BaseModel):
    """A column mapping (ADR 0025). Roles, orders and grains are checked
    by server.mapping, which explains a refusal in the reader's language."""
    roles: dict[str, str] = Field(default_factory=dict, max_length=500)
    measure: str | None = Field(default=None, max_length=200)
    dimension: str | None = Field(default=None, max_length=200)
    date_order: str = Field(default="auto", max_length=20)
    grain: str = Field(default="auto", max_length=20)
    # The currency of the money columns, an ISO 4217 code; absent means
    # not stated (slice three, U4). Checked by server.mapping.
    currency: str | None = Field(default=None, max_length=8)


class QueryIn(BaseModel):
    """Totals by group under filters (ADR 0031). The shapes are checked by
    server.query, which explains a refusal in the reader's language."""
    group_by: list = Field(default_factory=list, max_length=table_query.MAX_GROUP_BY)
    measures: list = Field(default_factory=list, max_length=table_query.MAX_MEASURES)
    filters: list = Field(default_factory=list, max_length=table_query.MAX_FILTERS)
    sort: dict | None = None
    limit: int = 100


class RecordsIn(BaseModel):
    filters: list = Field(default_factory=list, max_length=table_query.MAX_FILTERS)
    sort: dict | None = None
    offset: int = 0
    limit: int = 50
    sample: int | None = None


class ApprovalIn(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")


class ConnectorIn(BaseModel):
    """A live source (ADR 0034). The address is checked by server.connectors,
    which explains a refusal in the reader's language."""
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=2000)
    goal: str = Field(min_length=1, max_length=500)
    format: str | None = Field(default=None, pattern="^(csv|tsv|xlsx|json|jsonl)$")
    sheet: str | None = Field(default=None, max_length=31)
    every_minutes: int | None = None
    language: str = Field(default="en", pattern="^(en|ar)$")
    profile: str | None = Field(default=None, max_length=64)
    credential_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class ConnectorUpdateIn(BaseModel):
    """Pause or resume, or change the interval. An interval that is not
    sent is kept; `null` means "only when asked"."""
    enabled: bool | None = None
    every_minutes: int | None = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Vite names every file under /assets by a hash of its content, so a cached
# copy can never be stale. The page, the service worker and the manifest
# point at the current hashes, so the browser revalidates them each visit.
# vercel.json sets the same headers in production (ADR 0023, amendment).
IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"


class InterfaceGZip:
    """Compress the built interface, never the API.

    API responses can carry a token beside text the caller chose, which is
    the shape a compression side channel (BREACH) needs, and they are small
    JSON anyway. The interface is public, static and most of the bytes.
    """

    def __init__(self, app):
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=1024)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not scope["path"].startswith("/api/"):
            await self.gzip(scope, receive, send)
        else:
            await self.app(scope, receive, send)


def create_app(config_path=None, env=None, dist_dir=None):
    config = load_config(config_path or PROJECT_ROOT / "config.json")
    # Fails closed: declaring production without a managed identity
    # provider raises here rather than serving data unauthenticated.
    identity = build_identity(env)
    app = FastAPI(
        title=config.get("agent_name", "Agentic OS"),
        version=str(config.get("version", "1.0.0")),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Protects the in-memory state the store does not: the read-modify-
    # write of a session row and, in local mode, the memory file. Model
    # calls and pipeline stages run outside it (assessment finding B4):
    # the engine's durable mutations are serialised by store.atomic().
    lock = threading.Lock()
    app.state.request_lock = lock  # observed by tests, never taken by them
    # One lock per conversation, so two messages to the same session are
    # answered in turn while other sessions, and every read, go on.
    session_locks = {}

    def session_lock_for(session_id):
        with lock:
            if session_id not in session_locks and len(session_locks) >= MAX_SESSION_LOCKS:
                for stale in [k for k, v in session_locks.items() if not v.locked()]:
                    del session_locks[stale]
            return session_locks.setdefault(session_id, threading.Lock())

    gateway = ModelGateway()
    # The unwrapped gateway keeps the model call ledger (finding G4);
    # a router wraps it without replacing it.
    base_gateway = gateway
    # Which model plays Hermes, the agents and the consultants (ADR
    # 2026-10-21 model roles). Built on the plain gateway, which can be
    # asked for a named provider; nothing configured means no model role.
    model_roles = ModelRoles(gateway, os.environ if env is None else env)
    # Optional: something that chooses which model narrates each report
    # (ADR 0017). Absent — the default, and always in tests and CI — this
    # wraps nothing and changes nothing.
    router, router_name, router_problem = build_router(env, config)
    if router is not None:
        gateway = RoutedGateway(gateway, router, router_name)
    app.state.router_problem = router_problem
    # Hosted PostgreSQL (DATABASE_URL / config "database_url") when
    # configured; local SQLite otherwise. See docs/adr/0001-database.md.
    store = open_store(
        os.environ.get("DATABASE_URL") or config.get("database_url"),
        config.get("database_file") or PROJECT_ROOT / "data" / "agentic.db",
    )
    limits = load_limits(env)
    # Custom stages (ADR 0020). A stage that fails to load leaves the
    # pipeline as it was; the problem is reported, not raised.
    stage_registry, stage_problems = load_stages(env, config)
    app.state.stage_problems = stage_problems
    engine = RunEngine(
        store,
        resolve_vault_dir(env, config),
        gateway,
        limits=limits,
        stages=stage_registry,
        profiles=config.get("profiles") or {},
        execution_mode=(os.environ if env is None else env).get("AGENTIC_OS_RUN_EXECUTION", "client"),
        roles=model_roles if model_roles.active else None,
    )
    app.state.engine = engine
    app.state.store = store
    # The public demo reads one fictional analysis that no visitor could
    # have made, so the server makes it (server/demo.py). Once per store.
    if identity.mode == "demo":
        demo.seed(engine, DEMO_PRINCIPAL.subject)
    # Free text in the chat goes here; slash commands go to the Agent.
    # An agent runtime (ADR 0021) is optional and, like the router and
    # the stages, a load failure is reported rather than raised.
    runtime, runtime_name, runtime_problem = build_runtime(env, config)
    app.state.runtime_name = runtime_name
    app.state.runtime_problem = runtime_problem
    assistant = Assistant(gateway, engine, runtime=runtime, runtime_name=runtime_name,
                          identity_mode=identity.mode, env=env)
    app.state.assistant = assistant
    # Where memory lives, and whose it is.
    #
    # Local mode is one person on one machine, and keeps the documented
    # data/memory.json contract. The moment an identity provider is
    # configured the install is multi-tenant, and memory has to be
    # scoped like sessions and runs are — otherwise one tenant reads and
    # overwrites another's, which is what happened until ADR 0014. That
    # is a property of authentication, not of the database: a small
    # deployment with JWTs and SQLite is just as multi-tenant as one
    # with PostgreSQL, and used to share one memory file between
    # everybody.
    # Two independent reasons to keep memory in the database, and either
    # is enough: a PostgreSQL store means the backend must not depend on
    # local files (a serverless filesystem is read-only, ADR 0001), and
    # an identity provider means more than one owner exists. With a
    # single owner the scoping is a no-op; with several it is the whole
    # point.
    multi_tenant = identity.mode != "local"
    memory_in_database = multi_tenant or isinstance(store, PostgresStore)

    def memory_for(owner):
        if not memory_in_database:
            return None  # the Agent's own data/memory.json backend
        return DbMemoryBackend(store, owner or "local-owner")

    allowed_origins = [
        origin.strip()
        for origin in os.environ.get(
            "AGENTIC_OS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    environ = os.environ if env is None else env
    app.state.speech = LocalSpeech(environ)
    # Live sources (ADR 0034). The fence reads its host list and the test
    # fixture folder from the same environment as everything else.
    connectors = Connectors(engine, env=environ)
    app.state.connectors = connectors
    # Open event streams per owner in this process (ADR 0034): each polls
    # the database every second, so one owner cannot open hundreds.
    open_streams = {}
    # Content and collection grants are read together for each request.
    def knowledge_store(principal):
        # Authorization is never cached. A manifest edit or membership removal
        # must take effect on the next request, including a formerly warm index.
        root = Path(environ.get("AGENTIC_OS_KNOWLEDGE_DIR")
                    or knowledge_module.DEFAULT_ROOT).expanduser()
        return knowledge_module.load(root).for_principal(
            principal, store, local=identity.mode == "local")

    streams_lock = threading.Lock()
    # The default must exceed the application's own legitimate write
    # cadence: a client-stepped analytics run issues ~3 advance calls per
    # second, so a 120/min budget (2/s) would throttle a normal run.
    # 600/min leaves headroom while still stopping runaway loops.
    # A shared store counts every instance's requests in one window (B6);
    # a single SQLite instance keeps the in-process bucket.
    shared_store = isinstance(store, PostgresStore) or environ.get("AGENTIC_OS_RATE_LIMIT_STORE") == "1"
    limiter = (StoreRateLimiter if shared_store else RateLimiter)(
        *([store] if shared_store else []),
        limit=int(environ.get("AGENTIC_OS_RATE_LIMIT", "600")),
        window_seconds=int(environ.get("AGENTIC_OS_RATE_WINDOW", "60")),
    )
    # The owner's daily model budget, charged through the tenant context.
    base_gateway.budget = ModelBudget(store, limits)
    app.state.gateway = base_gateway

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if request.method in WRITE_METHODS and request.url.path.startswith("/api/"):
            # Key on the caller: the token subject when present, the
            # client address otherwise. Tokens are never used as keys.
            header = request.headers.get("authorization")
            try:
                key = identity.authenticate(header).subject
            except AuthError:
                key = request.client.host if request.client else "anonymous"
            allowed, remaining, retry_after = limiter.check(key)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content=error_envelope(429, "Too many requests. Please slow down.",
                                           "rate_limited"),
                    headers={"Retry-After": str(retry_after)},
                )
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
        return await call_next(request)

    shell_content_policy = application_content_policy(environ)

    def apply_security_headers(response, path):
        # Export routes already set a more restrictive document-specific CSP.
        # JSON/errors cannot load subresources; shell/SW responses retain only
        # the resources this interface actually uses.
        api_response = (path == "/api" or path.startswith("/api/")
                        or response.headers.get("Content-Type", "").startswith("application/json"))
        response.headers.setdefault("Content-Security-Policy",
                                    API_CONTENT_POLICY if api_response else shell_content_policy)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(self), geolocation=()"
        )
        if path.startswith("/api/"):
            # Session, memory, and export payloads are private.
            response.headers.setdefault("Cache-Control", "no-store")
        elif path.startswith("/assets/") and response.status_code == 200:
            response.headers.setdefault("Cache-Control", IMMUTABLE)
        else:
            response.headers.setdefault("Cache-Control", REVALIDATE)
        return response

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        return apply_security_headers(await call_next(request), request.url.path)

    def log_subject(request):
        """The hashed token subject when a bearer token authenticates,
        otherwise "anonymous". The token itself is never logged."""
        header = request.headers.get("authorization")
        if not header:
            return "anonymous"
        try:
            return subject_hash(identity.authenticate(header).subject)
        except AuthError:
            return "anonymous"

    def log_request(request, status, started):
        REQUEST_LOG.info(json.dumps({
            "request_id": request.state.request_id,
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "duration_ms": round((time.monotonic() - started) * 1000, 1),
            "subject": log_subject(request),
        }, separators=(",", ":")))

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        """Every request gets an id, echoed back, and one JSON log line:
        id, method, path without the query string, status, duration and
        a hashed subject. No token, body, query string or raw subject."""
        request.state.request_id = request_id_for(request.headers.get("x-request-id"))
        started = time.monotonic()
        # The owner this request works for, for the model budget (B6).
        try:
            subject = identity.authenticate(request.headers.get("authorization")).subject
        except AuthError:
            subject = None
        tenant.current_owner.set(subject)
        try:
            response = await call_next(request)
        except Exception:
            # The generic handler answers with 500 outside this middleware.
            log_request(request, 500, started)
            raise
        response.headers["X-Request-ID"] = request.state.request_id
        log_request(request, response.status_code, started)
        return response

    app.add_middleware(InterfaceGZip)

    def error_envelope(status, detail, code=None):
        """One shape for every error (assessment B14): `detail` as before,
        for existing clients, and `error` with a code and a message."""
        if isinstance(detail, dict):
            message = detail.get("message") if isinstance(detail.get("message"), str) else None
            code = code or detail.get("code") or f"http_{status}"
        elif isinstance(detail, list):
            message = "The request is not valid."
            code = code or "request_invalid"
        else:
            message = str(detail)
            code = code or f"http_{status}"
        return {"detail": detail, "error": {"code": code, "message": message or str(detail)}}

    def error_response(request, status, detail, code=None):
        request_id = getattr(request.state, "request_id", None)
        return apply_security_headers(JSONResponse(
            status_code=status, content=error_envelope(status, detail, code),
            headers={"X-Request-ID": request_id} if request_id else None,
        ), request.url.path)

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException):
        response = error_response(request, exc.status_code, exc.detail)
        for key, value in (exc.headers or {}).items():
            response.headers[key] = value
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return error_response(request, 422, jsonable_encoder(exc.errors()), "request_invalid")

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        # Never leak stack traces or internal details to the browser; the
        # server log gets the type and the request id for triage (B9).
        request_id = getattr(request.state, "request_id", None)
        ERROR_LOG.error(json.dumps({"request_id": request_id, "path": request.url.path,
                                    "error": type(exc).__name__}, separators=(",", ":")),
                        exc_info=exc)
        if is_database_error(exc):
            return error_response(request, 503,
                                  "The database is unavailable. Please try again shortly.",
                                  "database_unavailable")
        return error_response(request, 500,
                              "Something went wrong on the server. Please try again.",
                              "server_error")

    # ------------------------------------------------------------------
    # Identity and authorization
    # ------------------------------------------------------------------
    def current_principal(authorization: str = Header(default=None)):
        try:
            return identity.authenticate(authorization)
        except AuthError as error:
            raise HTTPException(status_code=401, detail=str(error))

    def requires(permission):
        def dependency(principal=Depends(current_principal)):
            if not principal.can(permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Your role ({principal.role}) cannot {permission} here.",
                )
            return principal
        return dependency

    def owns(principal, owner):
        """Objects belong to their creator; admins may act across owners."""
        return owner == principal.subject or principal.can("admin")

    install_operations_api(app, store, current_principal)
    install_reliability_api(app, store, current_principal)
    install_pilot_api(app, store, engine, current_principal, identity.mode)
    rmd = install_rmd_api(app, store, current_principal, identity.mode, env=env, engine=engine)

    def owns_run(principal, run_id, permission="read"):
        scoped = authorize_evidence_run(rmd, principal, run_id, permission)
        return (scoped if scoped is not None else owns(principal, engine.owner_of(run_id)))

    @app.get("/api/auth/config")
    def auth_config():
        """Public: the browser needs this before it can sign in. Contains
        no secret — only the mode and the provider's publishable key."""
        return public_auth_config(identity, env)

    @app.get("/api/identity")
    def whoami(principal=Depends(current_principal)):
        return {"mode": identity.mode, "principal": principal.as_dict()}

    def get_session(session_id, principal=None):
        row = store.get_session(session_id)
        if row is None or (principal is not None
                           and not owns(principal, row.get("owner") or "local-owner")):
            # Same response for missing and forbidden: no existence oracle.
            raise HTTPException(
                status_code=404,
                detail="Session not found. It may have expired — start a new session.",
            )
        return Session(config,
                       memory_for(row.get("owner") or "local-owner"),
                       row=row)

    def save_session(session):
        store.upsert_session(session.to_row())

    def clean_single_line(value, field_name):
        value = value.strip()
        if not value or "\n" in value or "\r" in value:
            raise HTTPException(
                status_code=422,
                detail=f"{field_name} must be a single non-empty line.",
            )
        return value

    # ------------------------------------------------------------------
    # Health and sessions
    # ------------------------------------------------------------------
    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "agent_name": config.get("agent_name", "Agentic OS"),
            "version": str(config.get("version", "1.0.0")),
            "model_provider": gateway.status(),
            "model_roles": model_roles.status(),
            "model_map": model_roles.model_map(),
            # A misconfigured router is the operator's to fix, and they
            # will not find it unless something says so.
            "router_problem": app.state.router_problem,
            "stage_problems": app.state.stage_problems,
            "agent_runtime": app.state.runtime_name,
            "runtime_problem": app.state.runtime_problem,
            "execution": worker_status(store, engine.execution_mode),
            # Model calls this process has made: totals per provider,
            # never prompts or replies (finding G4).
            "model_calls": base_gateway.ledger(),
        }

    @app.post("/api/sessions", status_code=201)
    def create_session(body: SessionIn | None = None,
                       principal=Depends(requires("write"))):
        with lock:
            session = Session(config, memory_for(principal.subject),
                              owner=principal.subject)
            if body is not None and body.language:
                session.agent.set_preference("language", body.language)
            save_session(session)
            store.trim_sessions(MAX_SESSIONS, principal.subject)
            return session.snapshot()

    @app.get("/api/sessions/{session_id}")
    def read_session(session_id: str, principal=Depends(requires("read"))):
        with lock:
            return get_session(session_id, principal).snapshot()

    @app.delete("/api/sessions/{session_id}")
    def end_session(session_id: str, principal=Depends(requires("write"))):
        with lock:
            session = get_session(session_id, principal)
            session.ended = True
            reply = session.agent.process_input("/exit")
            session.add_entry("agent", reply)
            save_session(session)
            return session.snapshot()

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------
    @app.get("/api/voice/status")
    def voice_status(principal=Depends(requires("read"))):
        return app.state.speech.status()

    @app.post("/api/sessions/{session_id}/transcriptions")
    async def transcribe_recording(session_id: str, request: Request,
                                  language: str = Query(default="en"),
                                  principal=Depends(requires("write"))):
        # Validate ownership before reading or decoding an untrusted body.
        with lock:
            session = get_session(session_id, principal)
            if session.ended:
                raise HTTPException(status_code=409, detail=(
                    "انتهت الجلسة. ابدأ جلسة جديدة للمتابعة." if language == "ar" else
                    "This session has ended. Start a new session to continue."))
        try:
            if language not in ("en", "ar"):
                raise SpeechError("language")
            service = app.state.speech
            service.ensure_available()
            content_type = request.headers.get("content-type", "")
            if not content_format(content_type):
                raise SpeechError("unsupported")
            length = request.headers.get("content-length")
            if length:
                try:
                    declared_length = int(length)
                except ValueError:
                    raise SpeechError("invalid") from None
                if declared_length < 0:
                    raise SpeechError("invalid")
                if declared_length > MAX_AUDIO_BYTES:
                    raise SpeechError("too_large")
            audio = bytearray()
            async for chunk in request.stream():
                if len(audio) + len(chunk) > MAX_AUDIO_BYTES:
                    raise SpeechError("too_large")
                audio.extend(chunk)
            result = await run_in_threadpool(service.transcribe, bytes(audio), content_type, language)
            # A session can end while the CPU job runs. Do not return its
            # late transcript into a now-closed conversation.
            with lock:
                if get_session(session_id, principal).ended:
                    raise HTTPException(status_code=409, detail=(
                        "انتهت الجلسة. ابدأ جلسة جديدة للمتابعة." if language == "ar" else
                        "This session has ended. Start a new session to continue."))
            return result
        except SpeechError as error:
            headers = {"Retry-After": "2"} if error.code == "busy" else None
            raise HTTPException(status_code=error.status, detail=error.message(language),
                                headers=headers) from None

    @app.post("/api/sessions/{session_id}/messages")
    def send_message(session_id: str, message: MessageIn, principal=Depends(requires("write"))):
        text = message.text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="Message text is empty.")
        # The session lock orders this conversation's turns; the global
        # lock covers only the load and the save, so the assistant's
        # model call holds up nobody else (finding B4).
        with session_lock_for(session_id):
            with lock:
                session = get_session(session_id, principal)
                if session.ended:
                    raise HTTPException(
                        status_code=409,
                        detail="This session has ended. Start a new session to continue.",
                    )
                session.add_entry("user", text)
                if text.startswith("/"):
                    # A command is exact and deterministic; it does not need
                    # understanding.
                    entry = session.add_entry("agent", session.agent.process_input(text),
                                              source="command", action="command")
                    if text.split()[0].lower() == "/exit":
                        session.ended = True
                    save_session(session)
                    return {"reply": entry, "state": session.snapshot()}
                session.agent.record_request(text)
            outcome = assistant.handle(text, session, principal=principal)
            with lock:
                entry = session.add_entry(
                    "agent", outcome["text"], source=outcome.get("source"),
                    provider=outcome.get("provider"), action=outcome.get("action"),
                    result=outcome.get("result"), pending=outcome.get("pending"),
                    steps=outcome.get("steps"), why=outcome.get("why"))
                save_session(session)
                return {"reply": entry, "state": session.snapshot()}

    @app.delete("/api/sessions/{session_id}/history")
    def clear_history(session_id: str, principal=Depends(requires("write"))):
        with lock:
            session = get_session(session_id, principal)
            session.agent.history.clear()
            save_session(session)
            return {
                "reply_text": "Conversation history cleared.",
                "state": session.snapshot(),
            }

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    @app.put("/api/sessions/{session_id}/preferences")
    def update_preference(session_id: str, preference: PreferenceIn, principal=Depends(requires("write"))):
        key = preference.key.strip().lower()
        if not PREFERENCE_KEY_PATTERN.match(key):
            raise HTTPException(
                status_code=422,
                detail="Preference names may use lowercase letters, digits, and underscores.",
            )
        value = clean_single_line(preference.value, "Preference value")
        with lock:
            session = get_session(session_id, principal)
            reply = session.agent.set_preference(key, value)
            save_session(session)
            return {"reply_text": reply, "state": session.snapshot()}

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------
    @app.post("/api/sessions/{session_id}/memory", status_code=201)
    def add_memory(session_id: str, memory: MemoryIn, principal=Depends(requires("write"))):
        information = clean_single_line(memory.information, "Memory text")
        with lock:
            session = get_session(session_id, principal)
            # Reload the shared file first so a concurrent session's saves
            # are never overwritten (lost-update prevention).
            session.agent.reload_memory()
            reply = session.agent.add_memory(information, memory.category)
            save_session(session)
            return {"reply_text": reply, "state": session.snapshot()}

    @app.put("/api/sessions/{session_id}/memory/{key}")
    def update_memory(session_id: str, key: str, memory: MemoryIn, principal=Depends(requires("write"))):
        information = clean_single_line(memory.information, "Memory text")
        with lock:
            session = get_session(session_id, principal)
            session.agent.reload_memory()
            if key not in session.agent.memory:
                raise HTTPException(status_code=404, detail=f"No memory named {key}.")
            reply = session.agent.update_memory(key, information, memory.category)
            save_session(session)
            return {"reply_text": reply, "state": session.snapshot()}

    @app.get("/api/sessions/{session_id}/export")
    def export_data(session_id: str, principal=Depends(requires("read"))):
        with lock:
            session = get_session(session_id, principal)
            return JSONResponse(
                content={
                    "exported_at": now_iso(),
                    "agent_name": session.agent.name,
                    "preferences": dict(session.agent.preferences),
                    "memory": dict(session.agent.memory),
                    "memory_entries": session.agent.memory_entries(),
                    "history": list(session.agent.history),
                    "transcript": session.transcript,
                },
                headers={
                    "Content-Disposition": 'attachment; filename="agentic-os-export.json"'
                },
            )

    @app.delete("/api/sessions/{session_id}/memory/{key}")
    def delete_memory(session_id: str, key: str, principal=Depends(requires("write"))):
        with lock:
            session = get_session(session_id, principal)
            session.agent.reload_memory()
            if key not in session.agent.memory:
                raise HTTPException(status_code=404, detail=f"No memory named {key}.")
            reply = session.agent.remove_memory(key)
            save_session(session)
            return {"reply_text": reply, "state": session.snapshot()}

    @app.delete("/api/sessions/{session_id}/memory")
    def clear_memory(session_id: str, principal=Depends(requires("write"))):
        with lock:
            session = get_session(session_id, principal)
            session.agent.reload_memory()
            reply = session.agent.clear_all_memory()
            save_session(session)
            return {"reply_text": reply, "state": session.snapshot()}

    # ------------------------------------------------------------------
    # Vault: durable record of approved, published knowledge
    # ------------------------------------------------------------------
    @app.get("/api/openapi.json")
    def openapi_schema(principal=Depends(requires("read"))):
        """The API contract, to a signed-in reader (assessment B14); the
        public /openapi.json and /docs stay off."""
        return app.openapi()

    @app.get("/api/vault")
    def list_vault_notes(principal=Depends(requires("read"))):
        with lock:
            return {"notes": [note for note in store.list_notes(owner=None)
                              if owns_run(principal, note["run_id"])]}

    @app.get("/api/vault/note")
    def get_vault_note(path: str, principal=Depends(requires("read"))):
        with lock:
            note = store.get_note(path, owner=None)
            if note is None or not owns_run(principal, note["run_id"]):
                raise HTTPException(status_code=404, detail="Note not found.")
            return note

    # ------------------------------------------------------------------
    # Knowledge: Markdown collections, searched and cited (ADR 0057)
    # ------------------------------------------------------------------
    @app.get("/api/knowledge")
    def list_knowledge(principal=Depends(requires("read"))):
        """What is indexed, from where, and at which version."""
        return {"collections": knowledge_store(principal).describe()}

    @app.get("/api/knowledge/search")
    def search_knowledge(q: str = Query(..., min_length=2, max_length=400),
                         collection: str = Query(None, max_length=120),
                         limit: int = Query(5, ge=1, le=20),
                         principal=Depends(requires("read"))):
        """Passages for a question, each carrying the citation to its section.

        The text returned is reference material. It is quoted to a reader
        or handed to a model as evidence; it never instructs the system.
        """
        hits = knowledge_store(principal).search(q, collection=collection, limit=limit)
        return {"query": q,
                "results": [dict(h.passage.as_dict(score=h.score),
                                 matched=list(h.matched)) for h in hits]}

    # ------------------------------------------------------------------
    # Runs: goal -> plan -> tasks -> approval -> artifact
    # ------------------------------------------------------------------
    def _run_or_404(action, principal=None, run_id=None, permission="read"):
        try:
            if principal is not None and run_id is not None:
                # Ownership is checked before any state change, and a run
                # owned by someone else is indistinguishable from missing.
                if not owns_run(principal, run_id, permission):
                    raise KeyError(run_id)
            return action()
        except KeyError:
            raise HTTPException(status_code=404, detail="Run not found.")
        except QuotaExceeded as error:
            raise HTTPException(status_code=429, detail=error.message)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error))

    @app.post("/api/runs", status_code=201)
    def create_run(run: RunIn, response: Response, principal=Depends(requires("write")),
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key",
                                                        max_length=200)):
        # A retried POST with the same Idempotency-Key (header, or the
        # body's idempotency_key) returns the run already made, as 200
        # rather than 201, instead of creating a second one (B14).
        with lock:
            try:
                detail = engine.create_run(run.goal, run.dataset_text,
                                           run.dataset_name,
                                           owner=principal.subject,
                                           dataset_id=run.dataset_id,
                                           profile=run.profile,
                                           language=run.language,
                                           joins=([j.model_dump() for j in run.joins]
                                                  if run.joins else None),
                                           breakdown=run.breakdown,
                                           assumptions=run.assumptions,
                                           idempotency_key=idempotency_key or run.idempotency_key)
                if detail.get("idempotent_replay"):
                    response.status_code = 200
                return detail
            except KeyError:
                raise HTTPException(status_code=404, detail='Dataset not found.')
            except joining.JoinError as error:
                raise HTTPException(status_code=422, detail=error.detail(run.language))
            except ValueError as error:
                # An unknown profile, or one naming an unregistered stage.
                raise HTTPException(status_code=422, detail=str(error))
            except QuotaExceeded as error:
                # 429: the request is well formed and the caller is
                # entitled to make it — just not right now, or not this
                # much. The message says which and when it clears.
                raise HTTPException(status_code=429, detail=error.message)

    @app.post("/api/joins/preview")
    async def preview_joins(body: JoinPreviewIn,
                            language: str = Query(default="en", pattern="^(en|ar)$"),
                            principal=Depends(requires("read"))):
        """What a run with these joins would merge, without making the run
        (ADR 0030). Reads under the lock; merges outside it, because a
        merge of large tables takes long enough to hold up everyone."""
        def plan():
            with lock:
                return engine.join_plan(principal.subject, body.dataset_id,
                                        [j.model_dump() for j in body.joins],
                                        body.breakdown)
        try:
            primary, mapping, spec, inputs = await run_in_threadpool(plan)
            return await run_in_threadpool(
                analytics.preview_merge, primary["content"], mapping, inputs,
                spec["breakdown"], language)
        except KeyError:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        except joining.JoinError as error:
            raise HTTPException(status_code=422, detail=error.detail(language))

    @app.get("/api/pipelines")
    def read_pipelines(principal=Depends(requires("read"))):
        """The registered custom stages, the profiles that choose among
        them, what a run gets by default, and why any stage could not
        be loaded."""
        return {"stages": [describe(d) for d in engine.stages.values()],
                "profiles": engine.profiles,
                "default": engine.custom_roles_for(None),
                "problems": app.state.stage_problems}

    @app.get("/api/usage")
    def read_usage(principal=Depends(requires("read"))):
        with lock:
            return quota_usage(store, principal.subject, limits)

    @app.post("/api/datasets", status_code=201)
    async def upload_dataset(
        request: Request,
        name: str = Query(min_length=1, max_length=100),
        format: str | None = Query(default=None, pattern="^(csv|tsv|xlsx|json|jsonl)$"),
        sheet: str | None = Query(default=None, max_length=31),
        language: str = Query(default="en", pattern="^(en|ar)$"),
        principal=Depends(requires("write")),
    ):
        """One file as the request body, read into a canonical table and
        stored content-addressed (ADR 0024). 201 when it is new; 200 when
        the same data was already stored, which costs nothing."""
        limit = dataset_reader.MAX_UPLOAD_BYTES
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > limit:
            raise HTTPException(413, detail=dataset_reader.too_large().message(language))
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, detail=dataset_reader.too_large().message(language))
            chunks.append(chunk)
        # Only the file's own name: a browser sends no path, a script might.
        filename = re.split(r"[\\/]", name)[-1].strip() or "dataset"
        try:
            parsed = await run_in_threadpool(
                dataset_reader.read, b"".join(chunks), filename, format, sheet)
        except dataset_reader.DatasetError as error:
            raise HTTPException(error.status, detail=error.message(language))

        def store_it():
            with lock:
                return engine.store_upload(parsed, filename, principal.subject)
        try:
            dataset, created = await run_in_threadpool(store_it)
        except QuotaExceeded as error:
            raise HTTPException(status_code=429, detail=error.message)
        return JSONResponse(status_code=201 if created else 200, content={
            "dataset": dataset_summary(dataset), "created": created,
            "columns": parsed.columns, "preview": parsed.preview(),
            "warnings": parsed.warning_texts(language), "sheets": parsed.sheets,
            "selected_sheet": parsed.selected_sheet})

    @app.get("/api/datasets")
    def list_datasets(principal=Depends(requires("read"))):
        with lock:
            return {"datasets": [
                {**row, "mapped": row.get("mapping_updated_at") is not None}
                for row in store.list_datasets(principal.subject)]}

    # Column mapping (ADR 0025). Another owner's dataset is a 404, never a
    # 403: whether it exists is not theirs to learn.
    @app.get("/api/datasets/{dataset_id}")
    def read_dataset(dataset_id: str,
                     language: str = Query(default="en", pattern="^(en|ar)$"),
                     principal=Depends(requires("read"))):
        with lock:
            try:
                return engine.dataset_detail(dataset_id, principal.subject, language)
            except KeyError:
                raise HTTPException(status_code=404, detail="Dataset not found.")

    @app.put("/api/datasets/{dataset_id}/mapping")
    def save_mapping(dataset_id: str, mapping: MappingIn,
                     language: str = Query(default="en", pattern="^(en|ar)$"),
                     principal=Depends(requires("write"))):
        with lock:
            try:
                return engine.save_mapping(dataset_id, principal.subject,
                                           mapping.model_dump(), language)
            except KeyError:
                raise HTTPException(status_code=404, detail="Dataset not found.")
            except colmap.MappingError as error:
                raise HTTPException(status_code=422, detail=error.detail(language))

    @app.delete("/api/datasets/{dataset_id}/mapping")
    def clear_mapping(dataset_id: str,
                      language: str = Query(default="en", pattern="^(en|ar)$"),
                      principal=Depends(requires("write"))):
        with lock:
            try:
                return engine.clear_mapping(dataset_id, principal.subject, language)
            except KeyError:
                raise HTTPException(status_code=404, detail="Dataset not found.")

    @app.get("/api/runs")
    def list_runs(state: str | None = Query(default=None, pattern="^[a-z_]{1,40}$"),
                  principal=Depends(requires("read"))):
        with lock:
            owner = None if principal.can("admin") else principal.subject
            candidates = {r["id"]: r for r in engine.list_runs(owner=owner, state=state)}
            # Organization colleagues can see their governed reports; creator
            # ownership does not preserve access after membership revocation.
            for row in store._exec("SELECT id FROM rmd_runs"):
                run = store.get_run(row["id"])
                if run is not None and (state is None or run["state"] == state):
                    candidates[row["id"]] = {key: run.get(key) for key in
                        ("id", "goal", "dataset_name", "state", "created_at", "updated_at")}
            runs = [r for r in candidates.values() if owns_run(principal, r["id"])]
            return {"runs": sorted(runs, key=lambda r: (r["created_at"], r["id"]), reverse=True)}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, principal=Depends(requires("read"))):
        with lock:
            return _run_or_404(lambda: engine.get_run(run_id), principal, run_id)

    @app.post("/api/runs/{run_id}/advance")
    def advance_run(run_id: str, principal=Depends(requires("write"))):
        if engine.execution_mode == "worker":
            detail = _run_or_404(lambda: engine.advance(run_id), principal, run_id, permission="write")
            return JSONResponse(detail, status_code=202)
        # A stage may call a model for most of a minute. The engine holds
        # store.atomic("run:...") for the run it advances, so the global
        # lock is not needed here and would stall every tenant (finding B4).
        return _run_or_404(lambda: engine.advance(run_id), principal, run_id, permission="write")

    @app.post("/api/runs/{run_id}/pause")
    def pause_run(run_id: str, principal=Depends(requires("write"))):
        with lock:
            return _run_or_404(lambda: engine.set_paused(run_id, True),
                               principal, run_id, permission="write")

    @app.post("/api/runs/{run_id}/resume")
    def resume_run(run_id: str, principal=Depends(requires("write"))):
        with lock:
            return _run_or_404(lambda: engine.set_paused(run_id, False),
                               principal, run_id, permission="write")

    @app.post("/api/runs/{run_id}/cancel")
    def cancel_run(run_id: str, principal=Depends(requires("write"))):
        with lock:
            return _run_or_404(lambda: engine.cancel(run_id), principal, run_id, permission="write")

    # ------------------------------------------------------------------
    # A run's cleaned table (ADR 0031): download, fields, totals, records
    # ------------------------------------------------------------------
    async def run_table(run_id, principal, language):
        """The run's analysis table, for its owner. Ownership and the store
        are read under the lock; the table is parsed and queried outside
        it, so a large table does not hold up everyone else."""
        def source():
            with lock:
                if not owns_run(principal, run_id):
                    raise KeyError(run_id)
                return engine.table_source(run_id)
        try:
            key, stored, run = await run_in_threadpool(source)
        except KeyError:
            raise HTTPException(status_code=404, detail="Run not found.")
        except TableNotReady:
            raise HTTPException(status_code=409, detail=(
                "الجدول المنظَّف غير جاهز بعد: لم ينتهِ التشغيل من تنظيف بياناته."
                if language == "ar" else
                "The cleaned table is not ready yet: the run has not finished cleaning its data."))
        return await run_in_threadpool(engine.load_table, key, stored), run

    @app.get("/api/runs/{run_id}/data.csv")
    async def download_table(run_id: str,
                             language: str = Query(default="en", pattern="^(en|ar)$"),
                             principal=Depends(requires("read"))):
        table, run = await run_table(run_id, principal, language)
        name = table_query.download_name(run["goal"], run_id)
        text = await run_in_threadpool(table_query.to_csv, table)
        return Response(content=text.encode("utf-8"), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition":
                                 f'attachment; filename="{name}"; filename*=UTF-8\'\'{name}'})

    @app.get("/api/runs/{run_id}/fields")
    async def table_fields(run_id: str,
                           language: str = Query(default="en", pattern="^(en|ar)$"),
                           principal=Depends(requires("read"))):
        table, _ = await run_table(run_id, principal, language)
        return {"fields": await run_in_threadpool(table_query.fields, table),
                "records": len(table.rows)}

    @app.get("/api/runs/{run_id}/kpi-policy")
    async def read_kpi_policy(run_id: str,
                              language: str = Query(default="en", pattern="^(en|ar)$"),
                              principal=Depends(requires("read"))):
        await run_table(run_id, principal, language)
        with lock:
            if not owns_run(principal, run_id):
                raise HTTPException(status_code=404, detail="Run not found.")
            return performance.load_policy(store, run_id)

    @app.put("/api/runs/{run_id}/kpi-policy")
    async def write_kpi_policy(run_id: str, request: Request,
                               language: str = Query(default="en", pattern="^(en|ar)$"),
                               principal=Depends(requires("write"))):
        await run_table(run_id, principal, language)
        try:
            content = bytearray()
            async for part in request.stream():
                if len(content) + len(part) > performance.MAX_POLICY_BYTES:
                    raise performance.PolicyError("The target policy exceeds the 16 KB limit.",
                                                  "تتجاوز سياسة الأهداف الحد البالغ 16 كيلوبايت.")
                content.extend(part)
            try:
                body = performance.parse_json(content)
            except (ValueError, UnicodeError, RecursionError):
                raise performance.PolicyError("Supply a JSON target-policy object.",
                                              "حدد كائن سياسة الأهداف بصيغة JSON.") from None
            expected, selected = performance.parse_update(body)
        except performance.PolicyError as error:
            raise HTTPException(status_code=422, detail=error.detail(language))
        with lock:
            if not owns_run(principal, run_id, "write"):
                raise HTTPException(status_code=404, detail="Run not found.")
            current = performance.load_policy(store, run_id)
            if current["revision"] != expected:
                raise HTTPException(status_code=409, detail=(
                    "تغيرت أهداف العرض. أعد تحميلها قبل الحفظ." if language == "ar" else
                    "The display targets changed. Reload them before saving."))
            if current["revision"] == selected["revision"]:
                return current
            saved = store.save_kpi_policy(uuid.uuid4().hex, run_id, expected,
                selected["revision"], performance.canonical(selected["rules"]),
                principal.subject, now_iso(), performance.policy()["revision"])
            if not saved:
                raise HTTPException(status_code=409, detail=(
                    "تغيرت أهداف العرض. أعد تحميلها قبل الحفظ." if language == "ar" else
                    "The display targets changed. Reload them before saving."))
            return selected

    @app.get("/api/runs/{run_id}/kpis")
    async def maintenance_kpis(run_id: str,
                               language: str = Query(default="en", pattern="^(en|ar)$"),
                               principal=Depends(requires("read"))):
        """The maintenance KPI register, computed on this run's cleaned table.

        Every measure is a ratio of sums over a named population, never a
        mean of row rates, and each one travels with the counts that make
        it auditable: `records` is what it was computed on, so dividing the
        numerator by it reproduces the printed value by hand.

        `records_unmeasured` is the one a caller must not drop. ADR 0042
        made an unmeasured cell stop counting as a measured zero, and said
        that a card hiding the exclusions re-creates the defect one layer
        up. It is returned for every measure, and it is non-zero exactly
        when the figure rests on less than its whole population.
        """
        table, _ = await run_table(run_id, principal, language)
        with lock:
            selected_policy = performance.load_policy(store, run_id)

        def compute():
            # The register reads rows by column name; the analysis table
            # holds them as tuples in column order.
            rows = [dict(zip(table.columns, row)) for row in table.rows]
            return kpi_register.compute_all(table.columns, rows)

        computed = await run_in_threadpool(compute)
        arabic = language == "ar"
        measures = []
        for result in computed["results"]:
            measure = dict(result)
            if arabic and measure.get("title_ar"):
                measure["title"] = measure["title_ar"]
            measure.pop("title_ar", None)
            # `population` stays the code; the label is what a reader sees.
            measure["population_label"] = measure.pop("population_ar") if arabic else measure["population"]
            measure["assessment"] = performance.assessment(measure, selected_policy["rules"], language)
            measures.append(measure)
        return {
            "run": run_id,
            "language": language,
            "records": len(table.rows),
            "measures": measures,
            "kpi_policy": selected_policy,
            # Why a register entry produced nothing, named rather than
            # left as an absent card.
            "unavailable": computed["unavailable"],
        }

    @app.get("/api/runs/{run_id}/executive")
    async def executive_brief(run_id: str,
                              language: str = Query(default="en", pattern="^(en|ar)$"),
                              filters: str = Query(default="[]"),
                              principal=Depends(requires("read"))):
        # Ownership and table readiness are checked before parsing a request.
        table, _ = await run_table(run_id, principal, language)
        try:
            chosen = executive_filters(filters)
            with lock:
                # Cleaning may have been followed by more stages while the
                # table loaded. Capture their stored metadata with the tasks.
                run = engine.store.get_run(run_id)
                if run is None or not owns_run(principal, run_id):
                    raise HTTPException(status_code=404, detail="Run not found.")
                tasks = engine.store.get_tasks(run_id)
                selected_policy = performance.load_policy(store, run_id)
            return await run_in_threadpool(ExecutiveDashboardAgent().brief,
                                           table, run, tasks, chosen, language, selected_policy)
        except table_query.QueryError as error:
            raise HTTPException(status_code=422, detail=error.detail(language))

    @app.get("/api/runs/{run_id}/executive/export")
    async def export_executive_brief(run_id: str,
                                    expected_updated_at: str = Query(min_length=1, max_length=160),
                                    expected_snapshot_id: str = Query(min_length=64, max_length=64, pattern="^[a-f0-9]{64}$"),
                                    format: str = Query(default="html", pattern="^(html|docx)$"),
                                    language: str = Query(default="en", pattern="^(en|ar)$"),
                                    filters: str = Query(default="[]"),
                                    principal=Depends(requires("read"))):
        # Reuse the complete ownership, readiness, filter and evidence boundary.
        # No client-supplied metric or report body is ever trusted.
        brief = await executive_brief(run_id, language, filters, principal)
        if (brief["run"]["updated_at"] != expected_updated_at
                or brief["snapshot_id"] != expected_snapshot_id):
            raise HTTPException(status_code=409, detail=(
                "تغير التشغيل منذ إعداد الموجز. حدّث الموجز ثم أعد التصدير."
                if language == "ar" else
                "The run changed after this brief was prepared. Refresh the brief before exporting."))
        render = executive_export.render_docx if format == "docx" else executive_export.render_html
        content = await run_in_threadpool(render, brief)
        mime = executive_export.DOCX_MIME if format == "docx" else executive_export.HTML_MIME
        return Response(content, media_type=mime, headers={
            "Content-Disposition": 'attachment; filename="' + executive_export.attachment_name(run_id, language, format) + '"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": executive_export.CONTENT_POLICY,
        })

    @app.post("/api/runs/{run_id}/query")
    async def query_table(run_id: str, body: QueryIn,
                          language: str = Query(default="en", pattern="^(en|ar)$"),
                          principal=Depends(requires("read"))):
        table, _ = await run_table(run_id, principal, language)
        try:
            return await run_in_threadpool(table_query.aggregate, table, body.model_dump())
        except table_query.QueryError as error:
            raise HTTPException(status_code=422, detail=error.detail(language))

    @app.post("/api/runs/{run_id}/records")
    async def table_records(run_id: str, body: RecordsIn,
                            language: str = Query(default="en", pattern="^(en|ar)$"),
                            principal=Depends(requires("read"))):
        table, _ = await run_table(run_id, principal, language)
        try:
            return await run_in_threadpool(table_query.records, table, body.model_dump())
        except table_query.QueryError as error:
            raise HTTPException(status_code=422, detail=error.detail(language))

    @app.post("/api/runs/{run_id}/approvals/{approval_id}")
    def decide_approval(run_id: str, approval_id: str, decision: ApprovalIn, principal=Depends(requires("approve"))):
        with lock:
            return _run_or_404(
                lambda: engine.decide_approval(run_id, approval_id, decision.decision,
                                                       approver=principal.subject),
                principal, run_id, permission="authorize",
            )

    # ------------------------------------------------------------------
    # Live data (ADR 0034): connectors and the event stream. A connector
    # is its owner's alone; another owner's is a 404, never a 403.
    # ------------------------------------------------------------------
    def _no_connector():
        raise HTTPException(status_code=404, detail="Live source not found.")

    @app.get("/api/connectors")
    def list_connectors(principal=Depends(requires("read"))):
        with lock:
            return {"connectors": connectors.list(principal.subject)}

    @app.post("/api/connectors", status_code=201)
    def create_connector(body: ConnectorIn,
                         language: str = Query(default="en", pattern="^(en|ar)$"),
                         principal=Depends(requires("write"))):
        with lock:
            try:
                return connectors.create(
                    principal.subject, body.name, body.url, body.goal, language=body.language,
                    format=body.format, sheet=body.sheet, every_minutes=body.every_minutes,
                    profile=body.profile, credential_id=body.credential_id)
            except ConnectorError as error:
                raise HTTPException(status_code=error.status, detail=error.message(language))
            except ValueError as error:  # an unknown pipeline profile
                raise HTTPException(status_code=422, detail=str(error))

    @app.put("/api/connectors/{connector_id}")
    def update_connector(connector_id: str, body: ConnectorUpdateIn,
                         language: str = Query(default="en", pattern="^(en|ar)$"),
                         principal=Depends(requires("write"))):
        every = body.every_minutes if "every_minutes" in body.model_fields_set else "keep"
        with lock:
            try:
                return connectors.update(connector_id, principal.subject,
                                         enabled=body.enabled, every_minutes=every)
            except KeyError:
                _no_connector()
            except ConnectorError as error:
                raise HTTPException(status_code=error.status, detail=error.message(language))

    @app.delete("/api/connectors/{connector_id}", status_code=204)
    def delete_connector(connector_id: str, principal=Depends(requires("write"))):
        with lock:
            try:
                connectors.delete(connector_id, principal.subject)
            except KeyError:
                _no_connector()
        return Response(status_code=204)

    @app.post("/api/connectors/{connector_id}/refresh")
    async def refresh_connector(connector_id: str,
                                language: str = Query(default="en", pattern="^(en|ar)$"),
                                principal=Depends(requires("write"))):
        """Fetch now. The fetch and the parse run outside the lock; the
        connector's lease keeps a worker from fetching it at the same time."""
        try:
            return await run_in_threadpool(
                connectors.refresh_now, connector_id, principal.subject, lock)
        except KeyError:
            _no_connector()
        except Busy:
            raise HTTPException(status_code=409, detail=(
                "يجري تحديث هذا المصدر الآن. حاول بعد قليل." if language == "ar" else
                "This source is being refreshed already. Try again in a moment."))
        except TooSoon as wait:
            raise HTTPException(status_code=429, headers={"Retry-After": str(wait.seconds)},
                                detail=(f"حُدّث هذا المصدر للتو. حاول بعد {wait.seconds} ثانية."
                                        if language == "ar" else
                                        f"This source was fetched moments ago. Try again in "
                                        f"{wait.seconds} seconds."))

    @app.get("/api/events")
    async def events(request: Request,
                     wait: float = Query(default=live.MAX_SECONDS, ge=0, le=live.MAX_SECONDS),
                     last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
                     principal=Depends(requires("read"))):
        """The owner's runs and connectors as they change, as server-sent
        events. Each stream ends within `wait` seconds; the client resumes
        with Last-Event-ID. An unreadable one starts from now."""
        owner = principal.subject
        with streams_lock:
            if open_streams.get(owner, 0) >= live.MAX_STREAMS_PER_OWNER:
                raise HTTPException(status_code=429, headers={"Retry-After": "30"},
                                    detail="Too many open update streams. Close a tab.")
            open_streams[owner] = open_streams.get(owner, 0) + 1
        reader = live.Reader(store, owner,
                             live.parse_cursor(last_event_id) or live.cursor_now())

        def poll_locked():
            with lock:
                return [event for event in reader.poll()
                        if event[1] != "run" or owns_run(principal, event[2]["id"])]

        async def poll():
            return await run_in_threadpool(poll_locked)

        async def body():
            try:
                async for part in live.stream(reader, poll, asyncio.sleep, time.monotonic,
                                              request.is_disconnected, max_seconds=live.stream_budget(wait)):
                    yield part
            finally:
                with streams_lock:
                    open_streams[owner] -= 1

        return StreamingResponse(body(), media_type="text/event-stream", headers={
            "Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    # ------------------------------------------------------------------
    # Static frontend (production build), if present
    # ------------------------------------------------------------------
    dist = Path(dist_dir) if dist_dir else PROJECT_ROOT / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            # An API path no route matched is a missing endpoint, not a page.
            if full_path == "api" or full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found.")
            candidate = (dist / full_path).resolve()
            # Serve real files inside dist; anything else falls back to the
            # SPA entry point. Path-aware containment (is_relative_to on the
            # resolved path) blocks traversal — a string prefix check would
            # not, e.g. a sibling directory named "dist-evil".
            if (
                full_path
                and candidate.is_relative_to(dist.resolve())
                and candidate.is_file()
            ):
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


# AGENTIC_OS_CONFIG lets tests and tools point the server at an alternative
# configuration file (and therefore an alternative memory file).
app = create_app(os.environ.get("AGENTIC_OS_CONFIG"))
