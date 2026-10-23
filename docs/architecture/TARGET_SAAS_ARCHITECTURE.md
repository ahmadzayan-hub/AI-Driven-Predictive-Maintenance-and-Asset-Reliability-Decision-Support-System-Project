# Target SaaS architecture

Date: 22 October 2026 · Principle: incremental, backward compatible, no
rebuild. What exists stays; the target names what changes around it and why.

## 1. As implemented today

```
Browser (React 19, Vite, TypeScript; English and Arabic; lazy views)
   │  /api/*  JSON, bearer token or demo
   ▼
FastAPI app  (server/app.py)  ── identity: Local | Demo | JWT (server/auth.py)
   │                            ── quotas, rate limit, owner scoping, CSP
   ├─ Run engine "Hermes" (server/runs.py): state machine, stages in fixed
   │    order, approval gate, recovery; client-advanced or worker-advanced
   │    ├─ Stages (server/analytics.py, server/maintenance/*, server/stages.py)
   │    │    deterministic; every claim cites a calculation; validator;
   │    │    provenance; reporter
   │    ├─ Model gateway (server/model_gateway.py): Ollama local or hosted,
   │    │    Claude, OpenAI, Groq, OpenRouter, NVIDIA, Mistral, Cerebras,
   │    │    Vercel; one failover; task map; words only
   │    └─ Model roles (server/orchestration.py): Hermes plan and brief,
   │         agent notes, consultants; built-in writer when no model;
   │         grounded; behind the privacy boundary
   ├─ Executive brief (server/executive.py, executive_advisory.py): KPIs
   │    from the register, decisions with owner and gate, model cards,
   │    findings, evidence, drill-downs, export
   ├─ Operations (server/operations*.py): organisations, sites, assets,
   │    work orders, authorisation and audit; MaintainX read-only adapter
   ├─ Reliability validation (server/reliability_validation.py): registered
   │    prediction windows, adjudicated outcomes, Brier and calibration
   └─ Storage (server/storage.py): PostgreSQL or SQLite; one schema
Worker (server/worker.py): lease-based stage execution, heartbeat
```

Hosting: Vercel serverless (`api/index.py`, 30 s functions), static
frontend, PostgreSQL via Supabase when `DATABASE_URL` is set; the view-only
demo otherwise.

## 2. Target: what changes, in order

| Layer | Change | Why (finding) | Compatibility |
| --- | --- | --- | --- |
| API | Request-id middleware and JSON logging with hashed subject | B10, B9 | additive |
| API | `GET /api/runs?state=awaiting_approval` with pagination; `GET /api/approvals` | U1 | additive; `GET /api/runs` unchanged |
| API | Idempotency keys on `POST /api/runs` and `POST /api/datasets` | B14 | optional header |
| API | OpenAPI enabled behind auth; one error envelope `{code, message}` | B14 | envelope change is a versioned step |
| API | `/api/health` split: public liveness, authenticated detail | B18 | additive route |
| Run engine | Per-run and per-session locks; model and stage work outside the global lock | B4 | internal |
| Run engine | A `decision` record persisted with the run and bound to the approval | A13 | additive table |
| Run engine | Expose orchestrator and consultant notes on `GET /api/runs/{id}` | Command Centre gap | additive field |
| Analytics | Measure kind from the contract: rates through the KPI register; forecast baselines; figure-match validation; illustrative gain with cost input | A2 to A6 | report content changes; ADR per change |
| Models | Card version, snapshot hash, split kind on the verdict; probabilities and Brier | A10, A14 | additive card fields |
| Storage | `schema_migrations` table; migrations run once; connection pool; transactional restore | B5, B11, B12 | one-time migration step |
| Identity | Audience and issuer required with a provider | B7 | configuration |
| Model calls | Ledger of provider, model, latency, tokens, failover; per-tenant daily budget | G4, B6 | additive |
| Frontend | Land on the Command Centre; Approvals in the phone bar; shared `Loading`; one KPI component; currency formatting | U12, U9, U18, U4 | view-level |
| Evaluation | Blind-set floors; router aliases removed; optional-runtime CI job | G1, G7, G11 | CI |

## 3. Boundaries that do not move

1. A model never sees a dataset row, and never produces a figure.
2. Every number in a report cites a calculation the validator can check.
3. Publishing, maintenance authorisation and any outward write wait for a
   person with the permission.
4. Tenant data is owner-scoped on every read and write; a missing scope is a
   404, not a 403.
5. English and Arabic ship together, with the same figures.
6. The interface size gate stays, with each allocation recorded in a decision.
