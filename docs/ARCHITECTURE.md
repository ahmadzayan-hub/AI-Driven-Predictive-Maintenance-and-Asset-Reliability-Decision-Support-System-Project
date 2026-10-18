# Architecture

**Last checked against the code:** 2026-10-18. Where a decision was
later revised, the record names the ADR that revised it rather than
pretending the first choice was never made.

```
Browser (React 19 + TS SPA, PWA)  ──HTTP/JSON──►  FastAPI adapter (server/app.py)
   Chat · Overview · Runs · Datasets                │ sessions, validation, policy,
   Dashboard · Approvals · Memory · Activity        │ security headers, no-store
   Live · Maintenance · Preferences                 │
                                                    ▼
                       ┌──────────────┬──────────────────────┬──────────────────┐
                       │ Agent core   │ Run engine           │ Model gateway    │
                       │ agent.py     │ server/runs.py       │ server/model_    │
                       │ (commands,   │ SQLite WAL or        │ gateway.py       │
                       │ preferences, │ PostgreSQL; state    │ deterministic ▸  │
                       │ memory)      │ machines, approvals  │ Groq (env-only)  │
                       └──────┬───────┴──────────┬───────────┴──────────────────┘
                              │                  │
                     data/memory.json    server/analytics.py (specialists)
                     (per-user, un-      └─ publish (approved) ─► vault/  ◄─ open
                      tracked by git)                              in Obsidian
```

## Boundaries

- **Domain core** (`agent.py`, `server/analytics.py`) is framework-free and
  fully testable without a network, browser, or credentials.
- **Run engine** (`server/runs.py`): durable persistence for runs, tasks,
  approvals and artifacts; explicit state machines with a central
  legal-transition table; bounded execution, where `advance` runs exactly
  one task, which is what makes pause, cancel and restart recovery honest.
  A run advances while a view is open, and an **optional worker**
  (`server/worker.py`, `scripts/worker.py`) advances it with no browser
  open, claiming a run with a database lease it renews after every task so
  two workers cannot take the same run (ADR 0034). Stepping one task at a
  time is unchanged; only who asks for the step is.
- **Storage** (`server/storage.py`): one dialect-neutral `SqlStore` with two
  subclasses — `SQLiteStore` (WAL) for local-first use, and `PostgresStore`
  when `DATABASE_URL` is set, for hosted multi-tenant use (ADR 0001). The
  swap the earlier design anticipated has been made; SQLite remains the
  default and the one the tests run on unless `PG_TEST_URL` is given.
- **Model gateway** (`server/model_gateway.py`): provider-neutral; the
  deterministic narrator is the default and the only provider used in
  tests/CI. Groq is configured exclusively via server-side env vars and can
  only phrase already-verified facts — every number comes from
  deterministic code.
- **API adapter** (`server/app.py`): validation (Pydantic), security
  headers, `Cache-Control: no-store` on `/api/*`, restricted CORS,
  path-aware static containment, safe errors.
- **Frontend** (`frontend/src/`): fourteen feature folders — activity,
  approvals, auth, chat, commands, dashboard, datasets, live, maintenance,
  memory, onboarding, overview, preferences, runs — beside `shared/`
  (api, types, components, styles), `app/` (shell, routing, lazy views) and
  `i18n/` (English and Arabic). No state library: one provider-scoped store.
  Every view but the chat and the shell loads on demand (ADR 0028), and a
  view's strings ship with its chunk (ADR 0035).

## Data at rest

| Data | Location | Tracked by git |
| --- | --- | --- |
| Memory | `data/memory.json` | No (example file only) |
| Runs/tasks/approvals/artifacts | `data/agentic.db` (SQLite), or PostgreSQL when `DATABASE_URL` is set | No |
| Published reports & run logs | `vault/` (Obsidian-compatible) | No |
| Settings | `config.json` | Yes (no secrets) |

## Key decisions

1. **One task per step** instead of a worker queue: honest progress,
   pause, cancel and restart recovery with zero infrastructure; the engine
   API would keep the same shape over a real queue. It did: ADR 0034 added
   a lease-based worker for runs that must advance with no browser open,
   and the step contract did not change to accommodate it.
2. **Deterministic analytics** instead of LLM-calculated numbers: claims
   trace to calculation ids and are independently re-verified by the
   Validation Expert stage.
3. **Approval bound to content hash**: publishing re-hashes the artifact
   and refuses if it changed after the approval was requested.
