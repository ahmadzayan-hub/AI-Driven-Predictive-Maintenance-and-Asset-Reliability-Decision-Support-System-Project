# P2 slice three: a corrective repair time, screened and versioned model cards, reversible cleaning, a shared rate limit with a model budget, one PostgreSQL connection per thread

Date: 2026-10-23 · Status: Accepted (assessment findings A7, A11, A14, A18,
B6 and B11 in `docs/audits/SAAS_PLATFORM_ASSESSMENT.md`; the third slice of
section 3 of `docs/implementation/DELIVERY_ROADMAP.md`, taken under the
owner's standing instruction to continue slice by slice).

## Decisions

1. **A corrective-work repair time beside the pooled one (A7).** The
   register's `mttr` pools every record's downtime over every failure, so
   where planned downtime is recorded it understates availability against
   an OEM's time-to-restore target. `mttr_corrective` is the same ratio
   over corrective work orders only (population `corrective_only`, read
   from `Work_Order_Type`), in the reliability family, undefined when no
   corrective failure was recorded. The pooled measure keeps its name and
   its edge-case note now says which basis to read against a target. The
   register holds 19 measures.
2. **Every model card is versioned and bound to its data (A14).** A card
   carries `version` (`CARD_VERSION`, bumped when the fitting or the
   evaluation changes), `fitted_at`, the run's `snapshot` hash from the
   collector, and `training_window` (the first and last period among the
   training rows when a date column exists; `null` otherwise). The same
   snapshot and the same version give the same scores; a card from an
   older version is identifiable and can be retired. Probabilities and
   calibration stay in the registered-window protocol
   (`reliability_validation.py`) and are not folded into the pipeline
   card; that half of A14 stays open and is listed as such.
3. **The screen is on the card (A11).** The maintenance targets already
   refuse identifiers, outcome and derived columns, columns the mapping
   ignores, detected personal data and the date; the card now carries
   `excluded_inputs` with each refused column and its reason, so a reader
   sees what the model was not allowed to use. The generic regression and
   classification stages take their inputs from the profiler's numeric
   columns and declare leakage rather than screen; they gain the version
   and snapshot fields but not the screen, which is noted on the row.
4. **Cleaning is recorded and reversible (A18).** The cleaner's output
   carries `dropped_indices` (`empty` and `duplicates`, by source row) and
   `unreadable_values` (row, column, value, capped at
   `MAX_UNREADABLE_RECORDED` = 200), and reports `c_coercion`
   (`values_not_read_as_numbers`, the uncapped count). When the count is
   not zero a limitation claim names the columns in both languages and
   cites it; a clean dataset makes no such claim. Exact duplicate rows
   are still removed, since a repeated identical record is more often a
   double export than two jobs; the indices make the choice reversible.
5. **The rate limit is counted in the store, with a daily model budget
   per tenant (B6).** `StoreRateLimiter` counts one fixed window per
   caller in `rate_windows` with one atomic read-modify-write per write
   request; windows two back are dropped as a caller's new window opens.
   The application uses it when the store is PostgreSQL (or
   `AGENTIC_OS_RATE_LIMIT_STORE=1`), so every instance of a hosted
   deployment counts the same requests; a single SQLite instance keeps the
   in-process bucket, which now evicts idle buckets once it holds 10,000.
   A refusal carries the error envelope (`rate_limited`). A store outage
   lets the request through rather than refusing every write while the
   database is down. `ModelBudget` counts provider attempts per owner per
   UTC day in `model_calls_daily`; the gateway makes no attempt once
   `model_calls_per_day` (default 500, `AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY`)
   is spent and the built-in writer answers, which the ledger shows as no
   call rather than a failed one. The owner comes from a context variable
   (`server/tenant.py`) set by the request middleware from the token and by
   the worker from the run; no owner means the local owner. `/api/usage`
   reports `model_calls` (used, limit, remaining). Both tables are in the
   Supabase snapshot under row-level security and in backups.
6. **One PostgreSQL connection per thread (B11).** `PostgresStore` keeps a
   connection, a statement lock and a transaction depth per thread, so a
   request thread's read never queues behind another thread's transaction
   and a transaction's statements all run on the connection that began it.
   Connections are tracked; `close()` releases every one, and the next
   statement on any thread opens a fresh one. There is no upper bound
   beyond the server's thread count (FastAPI's pool of 40 plus the worker),
   which is listed as a limitation; a connection pooler in front of the
   database remains the hosted recommendation.

## Consequences

- `tests/test_p2_slice_three.py` (19 tests, one PostgreSQL-only) covers
  each decision: the corrective basis, the recorded removals and the cap,
  the card fields with and without a context, the shared window across two
  store instances, the budget per owner in context and the gateway's
  refusal, the wiring at the API, and twenty reads completing while
  another thread holds a transaction.
- Model cards gain four fields; readers that compare cards should include
  `version`. Cleaner output gains two keys. The schema gains two tables, so
  `SCHEMA_VERSION` is unchanged (base statements create them) and the
  snapshot test holds them under RLS.
- Open after this slice: probabilities and calibration in the pipeline
  card (A14, second half); the screen for the generic stages (A11, second
  half); a bound on connections per process (B11); the standards lint
  blind score; the interface items and the G5 to G9 findings in the
  roadmap.
