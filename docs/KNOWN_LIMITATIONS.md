# Known Limitations

Honest boundaries of the current release. None of these are hidden behind
placeholder controls — absent capabilities have no UI.

## Maintenance pilot boundaries (21 October 2026)

The Operations workspace, organization permissions, maintenance audit, worker
execution and prospective validation ledger are implemented. Their local
verification is recorded in [README](../README.md#testing). The
[pilot runbook](PILOT_RUNBOOK.md) describes the proposed MaintainX integration
for selected pumps/motors at one site. Its adapter reads assets/work orders
into private snapshots and prepares reviewed initial asset imports; it does
not yet reconcile bidirectional CMMS work orders or prove a live vendor contract.

No account credential, hosted deployment acceptance, independent maintenance
outcomes, customer purchase or service agreement has been supplied. Ledger
scores describe adjudicated registered windows only. Pending outcomes,
correlated asset windows, declared training cutoff and external evidence
require explicit interpretation. Worker heartbeat is not an availability SLA.
Offline technician execution and enterprise provisioning remain conditional.
The two documented confidential course artifacts are untracked from future
source trees; historical copies still require remediation before public release.

## Intelligence

Local role acceptance is recorded in [README testing](../README.md#testing).
The selected CPU profile shares one Qwen model across separate role prompts;
it is not an independent multi-provider review. Optional notes are omitted when
inference fails or grounding rejects the response. Successful numeric grounding
does not certify the model's domain interpretation. Human review remains required.

A live pause request during the earlier long-running SQLite model analysis
returned a server error while the worker held its stage transaction; the analysis
then completed. Responsive pause/cancel under model load remains unverified
after the main integration. Do not infer it from idle API health.

1. The chat understands and acts on plain language — save, recall,
   change a preference, start an analysis, report its status, explain a
   report, in English or Arabic — through a **rules-based vocabulary**
   that works with no model (ADR 0019). A configured model widens what
   is understood, not what can be done: it picks from the same ten
   actions, and only its `chat` phrasing is ever shown. Boundaries: a
   sentence outside the vocabulary gets an honest "not understood, here
   is what you can ask"; one action per sentence; "explain" quotes the
   report's verified headlines rather than reasoning over the report;
   and bounded local Qwen/Whisper acceptance is recorded in
   [README testing](../README.md#testing). That conversational smoke does
   not establish maintenance-domain or hosted-production acceptance.
2. The analytics pipeline covers all four types (descriptive,
   diagnostic, predictive, prescriptive) deterministically, and each has
   a boundary worth knowing:
   - **Diagnostic** decomposes change by segment (exact arithmetic) and
     measures which columns move together. It does **not** establish
     cause. The separate Experiment and Causal Inference agent
     (ADR 0010) decides whether a causal claim is available at all: it
     compares recorded control/treatment groups and refuses the claim
     otherwise. It estimates nothing from observational data — no
     propensity scores, difference-in-differences, instrumental
     variables, or synthetic control. Where an experiment *is* recorded,
     the range carrying the verdict is always-valid (ADR 0016), so
     checking a running test repeatedly does not inflate the error rate;
     it is about 1.55× wider than the fixed-horizon reading, which is
     printed beside it. Small samples now decline to conclude — eight
     observations are eight observations.
   - **Predictive** fits a straight-line trend to the historical periods
     and extends it, with accuracy measured by backtesting against
     held-out periods. There is no probabilistic interval — the stated
     range comes from measured backtest error. A seasonal model, a
     regression, a classifier and a clustering are available as optional
     stages on the `models` profile (ADR 0033; see item 28). Fewer than 4 periods produces no
     forecast; fewer than 6 produces a forecast explicitly marked as
     having unmeasured accuracy. With 6 or more, the trend is also
     backtested against repeating the last period, and a trend that does
     not beat that by 5% is reported as no better than it. A measure that
     is a rate (by contract, glossary unit or name) gets no forecast at
     all, because its period sums are not rates.
   - **Prescriptive** ranks options the dataset itself supplies, scoring
     each with an assumed 10% improvement unless the run states an uplift
     or a cost per target (API `assumptions`, collected by the Analytics
     form under "Improvement and cost"). It is not an optimizer and knows nothing about
     capacity or feasibility; it writes a decision record per
     recommendation and the sensitivity stage says whether the ranking
     survives independent uplift ranges. It also does not know which way is good
     news unless the glossary says so: a metric entry may declare
     `better` as `higher` or `lower`, and only then does the stage speak
     of protecting and growing, or of reducing and curbing. With no
     declaration it ranks options by the size of the change they would
     make and says so in the report — the number is the same, the verb
     is withheld. A measure where less is better and no glossary to say
     so therefore gets no advice about direction from this product, which
     is the honest state and not a silent default.
   - Comparison between recorded experiment groups reports a range and
     whether it includes no-change (ADR 0010, 0016). No test is applied
     anywhere else: the descriptive, diagnostic, predictive and
     prescriptive stages are arithmetic, not inference. Nothing
     recommends when to stop a test — that is a decision about cost and
     risk, not a statistic.
3. The optional narrator (Ollama, Anthropic, or Groq) only phrases
   already-verified facts and never receives the dataset. Detected personal
   data in the main or joined datasets, or in outgoing fact text, now keeps
   narration and related assistant/runtime handoffs deterministic (ADR
   2026-10-20-personal-data-model-boundary). Reports explain that choice in
   their language. This is pattern-based screening, not exhaustive detection
   or anonymization; human-readable evidence remains unchanged. The wire
   contract for each provider is tested against a local HTTP server —
   including a reasoning model's `<think>` scratchpad, which is stripped
   and never reaches a report. Bounded local Qwen acceptance is recorded in
   [README testing](../README.md#testing); the 20 October corrective review
   used synthetic provider probes and made no live model call. Hosted provider
   acceptance remains unconfirmed. A local Ollama must be reachable from the
   machine running the server: a model on a laptop is invisible to a
   hosted deployment. Any failure falls
   back to the deterministic narrator, and the report always names which
   one wrote the summary.
4. Which model narrates can be decided per report by an optional router
   (ADR 0017), and that too has edges. **LLMRouter is not installed by
   default** and is not in `requirements.txt`: its routers bring torch,
   transformers and CUDA wheels — 5.3 GB measured — so five tests skip on
   an ordinary install and in CI, which is the expected result rather
   than a gap. Importing one costs about **11 seconds of start-up**
   (torch, once); the routing decision itself is free for the heuristic
   routers. Only those two heuristic routers (`SmallestLLM`,
   `LargestLLM`) have been exercised here — LLMRouter's **KNN, MLP and
   graph routers need embedding models and checkpoints this environment's
   egress policy blocks**, so they are untested, and "it works with
   SmallestLLM" is not "it works with the MLP router". Nothing measures
   what a choice cost and nothing feeds that back: there is no online
   learning and no billing relationship to learn against (ADR 0008).
   There is one router per process, fixed at start-up, so a hosted
   install cannot give each tenant its own — the same limitation, for the
   same reason, as the metric glossary below. A choice the deployment
   cannot reach is refused rather than substituted, which means a router
   trained on a catalogue this install does not hold contributes nothing
   but a line in the report saying so.
5. There is no autonomous "improve forever" loop. Runs are bounded;
   lessons accumulate as vault run logs for human review. Permanent 100%
   accuracy cannot honestly be promised by any AI system; deterministic
   calculations are exact for the operations implemented.
   The agents are measured on a schedule and the result is kept
   (`scripts/agent_loop.py`, `AGENTIC_OS_EVAL_INTERVAL_SECONDS`, the
   [dated decision](adr/2026-10-20-agent-measurement-loop.md)), but the loop
   stops at `needs_person`: it never edits a rule, a floor or a holdout case.
   `done` means no floor is broken and nothing regressed, not that an agent
   is accurate.
6. Every classifying agent is measured on labelled **synthetic** cases
   (ADR 0027), and the numbers are only as good as those cases. On the
   intent holdout the rules reach 72% macro recall; jargon recall is 92%.
   Causal wording originally reached 69% recall on v4 (precision 92%).
   After fixes informed by that set, its measured recall and precision are
   100%; it is no longer independent evidence. The newer adversarial
   `probe_v5` reports only 6% recall and is not comparable with those sets
   (ADR 0056). On a fresh independent set (`blind_v6`) causal wording first
   scored 45% recall and 69% precision, against 100% on its holdout, which was
   fitted to; intent scored 68.5% and jargon 85%. After the rules were fixed
   against it, a second independent set (`blind_v7`) measured causal wording
   at 60% recall and 88% precision (28% and 70% for the old rules on the same
   sentences) and intent at 61% correct (56% before), a gain within noise (the
   [decision](adr/2026-10-20-labelled-cases-from-real-use.md)). On 23 October `blind_v7` moved into dev and the
   rules were fixed against it (causal 96% recall at 100% precision and intent 100% on those sentences, which are
   now dev numbers, not blind ones), so causal and intent have no independent score until `blind_v8` is added
   ([decision](adr/2026-10-23-blind-v7-into-dev-causal-and-intent-fix.md)). Hand-written rules generalise only so far: intent
   scored 80% on the previous blind set and 68% on this one before any
   change. A sentence the causal check passes may still claim a
   cause, and a chat sentence outside the vocabulary is answered as chat. The seeded reviewer memos were nearly too easy for the
   reviewer subagents: both scored at or near 100% with either prompt.
   So the prompt changes are justified on the dev memo, not proven on the
   held-out ones, and the subagents' run-to-run variation (zero to three
   false alarms on the same memo) is measured on one run per condition.
   The local conversational smoke does not measure maintenance-domain
   prediction or general narrator accuracy. Hosted narrators remain
   unvalidated against an independently labelled task set. The
   figures checker reads counts written in English and Arabic words
   ("twenty-four", "خمسة وعشرون") but not ratios ("one in five"),
   fractions or ordinals; the figures-auditor reads the text for those.

## Resolved since the first release

Sessions, transcripts, preferences, memory, and published knowledge are
now durable in the storage layer: a server restart no longer loses a
conversation, and in hosted mode (`DATABASE_URL`) the backend keeps no
required local files. Both behaviors are covered by tests
(`test_sessions_survive_an_application_restart`,
`test_hosted_mode_keeps_memory_in_the_database`).

## Platform

6. Authentication ships as an adapter (ADR 0002/0003): local mode is
   single-owner with no login; hosted mode verifies managed-provider
   JWTs with server-side roles, per-owner isolation, a sign-in screen,
   and per-caller rate limiting. Caveats: the live provider round-trip
   was never executed (this environment blocks HTTPS to the provider),
   so first-deployment sign-in must be confirmed once by hand; tokens
   are stored in browser storage without refresh rotation; and the rate
   limiter is per process, so multi-instance deployments need a shared
   store. There is no admin UI for granting roles — roles come from
   token claims or `AGENTIC_OS_DEFAULT_ROLE`. Agent memory is scoped to
   its owner as of ADR 0014 — before that commit a hosted deployment
   shared one memory store between every tenant, so an upgrade
   attributes all existing memory to `local-owner` and **nothing
   reassigns it**; that is a SQL `UPDATE` by someone who knows whose
   data it was. The application enforces the owner boundary; the
   database's row-level security is deny-by-default rather than
   owner-aware, so there is no second line of defence underneath it, and
   erasing one owner is an operator command (`scripts/erase.py`,
   ADR 0015), not an endpoint: it deletes the rows and the published
   files but cannot reach backups, and it names them in every report
   rather than implying completeness. A consequence worth
   stating plainly: `python scripts/serve.py` binds to the local network
   so a phone can reach it, and because local mode has no login, every
   device on that network can read and change the saved memory. The
   launcher binds to this computer alone unless `--lan` is given, and prints the consequence when it is, but
   nothing enforces it — a laptop on café Wi-Fi is an open app.
7. The metric glossary (ADR 0011) is a file, not a table: it is
   process-wide, so a hosted install cannot give each tenant its own,
   and it is read once at server start, so an edit does not reach a
   running process until it restarts. Its formula language is one
   operation over column names — deliberately less than a metric layer,
   so a definition stays checkable by hand. No glossary ships with the
   repository; an unconfigured install analyses an undefined column and
   says so in every report.
8. Crash recovery is drilled, not assumed (ADR 0012): connection loss,
   a worker killed with SIGKILL mid-stage, and the engine rebuilt
   mid-run are automated against PostgreSQL in CI. A **full database
   outage** is not — CI's database is a service container the test
   process cannot stop — so that drill was executed by hand once, with
   its measurements recorded in the ADR. Not covered anywhere: network
   partition, failover (there is one database and no standby), and
   corruption as opposed to unavailability.
9. Supply-chain evidence stops at composition (ADR 0013): the SBOM
   says what this software is made of, and nothing signs it or attests
   to how it was built. Signed artifacts and SLSA provenance need a
   release process this project does not have. The licence gate blocks
   only strong copyleft in a **shipped** dependency; weak copyleft and
   undeclared licences are reported, not blocked. `pip-audit` remains
   advisory. The repository also has no LICENSE file of its own — what
   this project grants is the owner's decision.
10. Execution is client-stepped by default: runs advance while the Runs
    view is open. A background worker (`python scripts/worker.py`) can
    advance them server-side with no browser, using database leases with
    heartbeats (ADR 0006), but **nothing starts it automatically** and
    Vercel's serverless runtime has no process to run it in — hosted
    deployments there keep the client-stepped path. One worker advances
    one run at a time; parallelism means running more workers. A
    paused or interrupted run resumes from its durable state either way.
11. The repository is deployed to Vercel as a full-stack project (static
    frontend + Python function) at `agentic-os-final-project.vercel.app`,
    and `/api/health`, `/api/pipelines` and the interface were verified
    there by HTTP on 2026-10-02. What was **not** verified from the
    implementation environment: that the domain is reachable without a
    Vercel login (the project has Standard Protection on), a full run and
    approval in a browser there, and whether `DATABASE_URL` is set —
    without it a deployment keeps per-instance storage that a cold start
    wipes. The historical deployment reported single-owner mode; current
    identity and storage configuration were not established by the 20 October
    metadata review. That review identifies older production commit `42e53d00`
    and Vercel Authentication protection. Main-branch Git deployment is now
    disabled; releasing a corrected commit requires explicit approval and
    hosted acceptance. On 21 October `dcde343` was deployed to production
    with approval; it runs in `local` mode until the owner adds
    `AGENTIC_OS_DEMO=1` in Vercel. See `docs/VERCEL_DEPLOYMENT.md`.
12. Android support is a verified installable PWA; a native Capacitor
    project is documented but not shipped (no Android SDK available to
    build or test one honestly).
13. Obsidian integration is approval-gated write-back into a vault
    folder; reading/sync/retrieval from a vault is not implemented. Since
    23 October the database store is the publish target and the folder a
    courtesy: on a host where it cannot be written, the published path
    names the store and `/api/vault` still serves both notes (B13).
14. The interface is Arabic or English (ADR 0018), right-to-left in
    Arabic, and the agent's own replies follow the chosen language.
    Reports are written in the language a run was started in (ADR 0022),
    with the same figures, verified by the validator claim by claim.
    Boundaries: a report's language is fixed when its run starts, so the
    other language means a new run and a new approval; calculation names
    and methods, column and group names and period labels stay as the
    data and the evidence wrote them; a custom stage's text appears as its
    author wrote it; the choice is per browser and per session, so a
    hosted install has no organisation-wide default; and Arabic uses
    system fonts, so the face varies by operating system (no font is
    downloaded, because the app works offline). Digits are Western in
    both languages so a figure on screen matches the same figure in any
    report.
15. Backups are on-demand: `scripts/backup.py` produces a verified,
    restorable backup (the drill in `tests/test_backup.py` destroys the
    database and rebuilds it on every push), but **nothing schedules
    it**, so the recovery point objective is "whenever it was last run".
    A nightly GitHub Actions job is deliberately not shipped — this
    repository is public and workflow artifacts would expose user data
    (ADR 0005). Supabase's automated daily backups cover Pro plans and
    above, not the free plan this project uses. Backup files are
    unencrypted JSON, the whole database is held in memory while one is
    written (fine at the 10 MB dataset limit, not at hundreds of
    megabytes), and in local mode `data/memory.json` lives outside the
    database and must be backed up separately.
16. Usage is bounded per owner (runs/day, dataset count, dataset bytes)
    but **no cost in currency is tracked**: there is no billing
    relationship, model tokens are counted per process rather than per
    tenant, and serverless execution time is not measured. `/api/usage`
    names those gaps rather than hiding them. The gateway's in-process
    ledger (`GET /api/health`, `model_calls`) records every provider
    attempt with its latency and the token counts the provider reported,
    never an estimate; it is lost on restart and summed across tenants.
    Since 23 October the store counts model calls per owner per UTC day
    and the gateway stops attempting at `model_calls_per_day` (B6), but
    that is a count of calls, not of tokens: a per-tenant token budget is
    still out of scope. The daily window is calendar-based (midnight UTC), so a
    burst either side of midnight can exceed the intended daily rate.
    The request rate limit is counted in the store when it is PostgreSQL,
    so every instance shares one window; a store outage lets writes
    through to fail on their own data access rather than refusing them.
17. Datasets come from a file (CSV, TSV, Excel `.xlsx`, JSON or JSON
    Lines) or pasted CSV (ADR 0024): up to 4 MB as uploaded, the limit
    of the platform the app is deployed to, 50,000 rows, and 10 MB once
    converted to CSV. They are held in the database rather than object
    storage. Not read: old `.xls` workbooks, OpenDocument, Parquet, CSV
    in any encoding but UTF-8 or UTF-16, and database connectors. A
    workbook gives one sheet per upload. After a successful upload, the
    interface lets you choose another sheet (ADR 0038). A cover sheet is
    skipped for the first sheet that looks like a table, judged from a
    sample of each sheet's first rows; a table whose header sits below a
    title row is not detected (2026-10-23 workbook sheet discovery). A formula with no saved result
    arrives empty, with a warning. Analysis is in-memory (no
    DuckDB/Polars), so larger-than-memory datasets are out of scope, and
    a dataset cannot yet be deleted from the interface.
18. Custom stages (ADR 0020) are **trusted Python in this process**, not
    a sandbox. A stage that overruns `AGENTIC_OS_STAGE_TIMEOUT` (default
    120 s) is abandoned on its thread and its task fails, which keeps a
    hung stage from hanging a run but stops nothing it does meanwhile
    (G10, 23 October): the contract catches a malformed result, a mis-cited
    claim or a mutated context, and a plugin that wants to misbehave
    can still import anything. The operator decides what to register.
    The registry is per process and read at start-up — no per-tenant
    stages in a hosted install, and a new stage needs a restart, as
    with the glossary and the router. A custom stage cannot narrate (it
    gets no model gateway) and cannot chart; its figures are tables.
19. An agent runtime (ADR 0021) is optional and bounded, and both
    halves have edges. **No live model has driven either example
    runtime from this environment** — the LangGraph and Pydantic AI
    examples were exercised with scripted models, so the first real
    provider is unverified, and the rules path is what makes that safe.
    A runtime may call at most eight tools for one sentence, may never
    delete, and cannot approve or publish; its closing line is model
    text and is labelled as such. The MCP server is **stdio and local
    mode only** — no HTTP transport, no authentication, no resources or
    prompts — so a hosted deployment has no MCP surface. The frameworks
    are not in `requirements.txt` and CI does not install them; their
    tests skip there, and the versions verified are the ones in the
    ADR's table.
20. The Overview and Datasets views (ADR 0023) read existing endpoints
    and nothing more. The Overview's counts cover the 50 most recent
    analyses that `GET /api/runs` returns, and the view says so when
    the list is full; the Datasets view lists the 50 most recent
    datasets. Hash addresses now restore these views and an individual
    run (ADR 0029); browser back preserves the destination. On a phone the header has
    room for only the first letters of the agent's name.
21. Column mapping (ADR 0025) gives each column one role and analyses
    one measure, broken down by at most one dimension. The other
    measures are drivers, not subjects. There is no week grain, no
    fiscal year, no derived or computed column, and no unit per
    measure. A decimal comma is refused rather than read, and
    two-digit years follow the POSIX rule, so `70` is 1970. The
    suggestion reads an even sample of 10,000 rows of a larger table,
    while saving checks every row. A mapping belongs to one dataset:
    a changed file is new content, so it starts unmapped. Pasted CSV
    and the sample always use automatic detection. Unmapped data is
    still typed from column names, and its periods still sort as text.
    Its breakdown is chosen by this product, not by a reader: the first
    repeated non-numeric column in the file's own column order, with at
    most 200 distinct values and at least two records per value on
    average, excluding identifier-like, date-like and detected-personal
    columns (dated decision
    `2026-10-20-domain-models-and-automatic-grouping.md`). A file with
    no such column gets a report with no breakdown at all. Either way a
    bilingual limitation claim says the product chose it, names the
    other columns that could have been used, or says why there is none
    (dated decision `2026-10-20-who-chose-the-breakdown.md`); the
    candidates are not ranked, because nothing here measures which
    breakdown a reader wants. A run-level `breakdown` remains a
    merged-table option only: declared without joins it is refused
    rather than ignored, and a single dataset chooses its breakdown by
    saving a column mapping (dated decision
    `2026-10-20-reject-unsupported-single-dataset-breakdown.md`).
22. Uneven periods are read per record (ADR 0026) only in the
    descriptive stage: its headline and a limitation claim give the
    per-record change when the quietest period holds under three
    quarters of the busiest's records. The predictive and anomaly
    stages leave a partial last period out of the trend and say so
    (A12, 23 October); the segment, diagnostic and prescriptive stages
    still work on totals, so "protect the leading group"
    can name the group with the most records rather than the largest
    loss per record. The dashboards skill shows per-record charts beside
    the totals; the app's report does not yet.
23. The agent team (`docs/AGENT_TEAM.md`) is tooling for this
    repository and its deliverables, not part of the app.
    - **Local models:** provider and framework tests normally use stubs.
      Local Ollama and Whisper are now installed through the opt-in profile
      (ADR 0055). See README for actual live probes; those do not validate
      every model or turn the separate reviewer tooling into an app feature.
    - **Reviewers:** they are Claude subagents. Their findings are
      checked by recomputation before they are acted on, but a reviewer
      can miss what it was not asked about.
    - **Scores:** the loop's percentage counts gates, not findings.
    - **Claude Dashboards:** this is a hosted claude.ai feature. The
      skill reaches it only in a claude.ai session, and elsewhere writes
      an offline page. A new agent file loads at the next session start.
24. Views load on demand (ADR 0028). A reader who goes offline before
    the idle prefetch finishes, or whose browser asks to save data, can
    reach a view whose chunk was never fetched. That view says it could
    not be shown and offers a reload, which works once the reader is
    back online. The split did not make today's app measurably faster:
    Lighthouse mobile scored 98 against 99 before, with the same largest
    paint (2.13 s). What it saves is the unused script, which halved.
    Both dictionaries still ship on the first load.
25. Several datasets per run (ADR 0030) are joined, not stacked: up to
    four lookups, each on one to three key columns, onto one main
    dataset of the same owner. Keys match as trimmed text, as numbers
    when the main key is numeric, or as periods when it is the mapped
    date; there is no case-insensitive or fuzzy matching, so `north`
    and `North` do not match and the coverage figure is how the owner
    finds out. A lookup whose key repeats is refused rather than
    aggregated. The stages before cleaning (contract, profiling,
    quality, privacy) describe the main dataset only; joined datasets
    are screened for personal data by the merge stage itself.
26. A run's cleaned table (ADR 0031) downloads as CSV only, not Excel or
    Parquet, and is read-only. Its query language is deliberately small:
    named aggregates, eleven filter operators, at most two groupings and
    no expressions or joins at query time. A table is parsed into memory
    on first use and three are kept, so the first question asked of a
    50,000-row run is slower than the ones after it, and a server with
    several processes parses once per process.
27. Dashboards (ADR 0032) are one run's table, read-only, with a fixed
    set of pages chosen from its fields: no saved layouts, no choice of
    chart per page and no cross-filtering by dragging. The relationship
    page reads an even sample of at most 500 records, and a filter list
    offers a column only when it has at most 200 values, so an ID or
    free-text column cannot be filtered from the bar.
28. The modelling stages (ADR 0033) are four fixed, standard-library
    models: least squares, naive Bayes, k-means and an additive trend
    and season. There are no trees, ensembles or tuning, and nothing
    beyond the documented settings. The models are associations, not
    causes. A model cannot know which inputs were recorded after the
    outcome, so an input like that makes it look better than it is; every
    model says so, but none of the four can check it. Only the
    `maintenance` profile can: its risk models read the domain contract's
    per-column timing and withhold outcome, derived and
    unestablished-timing columns (ADR 0040). Where the classifier derives
    its own label from the measure, the quartile that defines the label is
    now taken from the training rows alone (ADR 0041). Fewer than 30
    records, or fewer than three seasons for the seasonal forecast, is
    reported as a limitation and shows no card.
29. Live sources fetch HTTPS snapshots, with optional operator-held credential
    aliases scoped to an owner and exact host/port (the 21 October durable-worker
    decision). They do not offer a browser secret store, arbitrary database
    connections or a proxy; a server that reaches the internet only through a
    proxy cannot refresh. The dedicated read-only MaintainX adapter is described
    in the pilot runbook and has not been exercised against a customer account.
    Each refresh is a whole snapshot of at most 4 MB; ten sources per
    account, and "Refresh now" once a minute per source. Addresses that
    carry a credential in their query are refused. The cap of five event
    streams per owner is per server process. Scheduled refreshes need the
    background worker
    (`python scripts/worker.py`); a serverless deployment refreshes only
    when someone presses **Refresh now**. The event stream ends every 55
    seconds and the page reconnects, so a hosting platform that limits a
    request's length is fine; one that buffers responses delays events
    until the stream ends. A connector's error is stored in the
    language it was created in.

20. On PostgreSQL one process holds a pool of at most 20 connections
    (23 October, B11): a thread at the bound waits up to 30 seconds for a
    released one and then fails as a database error (503). A pooler in
    front of the database stays the hosted recommendation; the bound is
    what one instance asks of it. The classification card carries
    probabilities with a Brier score and reliability bins (A14); the
    regression card does not quote prediction intervals. The generic
    stages refuse mapping-ignored, personal and target-derived columns
    (A11), but a measure recorded after the outcome that is none of those
    is still declared rather than detected. A hosted model's structured
    answer is checked against its schema on the server (G5); Anthropic has
    no JSON mode, so it is asked in text and checked the same way.

30. The maintenance KPI register (`server/maintenance/kpis.py`) is bound
    to cleaned runs through the KPI endpoint and Asset Intelligence view
    (ADRs 0049 and 0051). The separate `?design=maintenance` preview still
    uses explicitly fictional fixtures (ADR 0037). The register
    excludes a record from a measure when any column that measure's
    arithmetic reads is missing, and reports the count as
    `records_unmeasured` (ADR 0042); a view that binds these KPIs must
    show that count, or it re-creates the defect one layer up. Whether a
    blank in a particular source means "none happened" is a question for
    that source's owner and is declared per KPI.

31. The process-wide lock in `server/app.py` now covers only in-memory
    session state; the assistant's model call and a run's pipeline stage
    run outside it, so one slow model call no longer stalls every tenant
    (assessment finding B4). On SQLite a stage's `store.atomic("run:...")`
    transaction still serialises every store access for its duration,
    model call included, because the store has one connection; only
    PostgreSQL locks the one run. In local mode the memory file is
    written by the assistant outside that lock, so two conversations
    saving a memory at the same instant can lose one write; the memory
    endpoints themselves are still serialised.
32. Request logging (finding B10) is one JSON line per request on the
    `agentic_os.requests` logger at INFO, with a request id (an incoming
    `X-Request-ID` of up to 64 safe characters is honoured, otherwise one
    is generated and echoed), method, path, status, duration and a
    12-character SHA-256 prefix of the token subject or `anonymous`.
    Nothing ships the lines anywhere: the handler is whatever the
    process's Python logging is configured with, the id is not
    propagated to the worker or to model providers, and bodies, query
    strings, tokens and raw subjects are never logged.
33. A restore (finding B5) validates every row of every table against
    the live schema before any delete and runs the deletes and inserts in
    one transaction on both SQLite and PostgreSQL, so a failure part-way
    leaves the database as it was. The whole backup is still held in
    memory, and a backup written by a build with more columns is refused
    rather than trimmed.

-   **A child interpreter can fail to start under full-suite load on
    Windows.** `tests/test_backup.test_a_destroyed_database_is_rebuilt_from_a_backup`
    runs `backup.py` as a subprocess, and on this workspace that child
    sometimes dies before any of its code executes:
    `Fatal Python error: _Py_HashRandomization_Init: failed to get random
    numbers to initialize Python`. The interpreter is asking the operating
    system for entropy to seed hash randomisation and not getting it. No
    change to `backup.py` can address this, because `backup.py` never runs;
    a child Python launched from an idle shell starts normally, so it is
    resource pressure during the full suite rather than a defect in the
    script or the test. The assertion was deliberately left strict: relaxing
    it would turn a red run green without making anything work. CI on Linux
    is the authority for this test. Verified 19 October 2026.

-   **Initial CSS and fonts have little budget headroom.** Current measured
    values are maintained in [README testing](../README.md#testing). ADRs
    0054, 0055 and 0058 record the explicit allowances for the visual, local voice
    and scoped executive features; initial ceilings remain unchanged. Further features need
    measurement and trimming or a justified design decision, not an unexplained
    gate increase.


## Executive decision support

The executive agent (ADR 0058) is a deterministic, read-only briefing over an
authorized cleaned run. Filters recompute controlled measures and priorities;
model evaluations and historical findings retain their whole-run scope. The
brief can be inspected and exported, but it does not issue work orders, retrain
models, approve publication or prove a future-failure prediction. Missing
evidence and unsupported targets stay visible. Claude dashboard skills are
development instructions; hosted Artifact availability is account-dependent
and was not activated by this implementation.

## KPI register: what it cannot measure yet

The register ([decision](adr/2026-10-21-register-availability-and-pooled-reliability-measures.md))
holds 19 controlled measures, each a ratio of sums over a declared population
(the corrective-only repair time, `mttr_corrective`, was added on 23 October;
the pooled `mttr` still includes planned downtime and says so).
These common asset-management measures are **not** in it, because the exports
this product reads do not carry the fields, and a stand-in would be a guess:

- planned-maintenance percentage **in hours**, wrench time, PM compliance and
  schedule compliance (need hours by work type, hands-on time, and
  scheduled-versus-done counts);
- backlog in crew-weeks (needs outstanding hours and weekly craft capacity;
  the register's overdue rate is a count share and is named as one);
- maintenance cost as a share of replacement value (needs replacement values
  for a defined asset base).

Three more limits on what the figures mean:

- **Availability scope.** It is operational availability on planned time from
  the downtime recorded. Where no preventive downtime is recorded it is not
  technical availability, and logistic delay cannot be separated.
- **MTBF assumes exposure.** The pooled MTBF and any interval around it assume
  a constant failure rate and independent records. Records that are not unique
  assets (the course data repeats every `Asset_ID` across all asset classes)
  make per-asset reliability impossible.
- **Stored targets are held, not migrated.** A target saved against
  `availability` before 21 October 2026 was set against utilisation. It now
  gives no verdict until someone saves it again in the target editor
  ([decision](adr/2026-10-21-targets-held-when-a-measure-is-redefined.md));
  it is never rewritten. The same holds for MTTR, first-time fix and repeat
  repair, redefined the same day to match the team's Power BI report
  ([decision](adr/2026-10-21-kpi-register-aligned-with-power-bi.md)).
- **MTTR counts all downtime.** It follows the Power BI report: all recorded
  downtime over all failures. Where planned downtime is recorded on records
  with no failure, it overstates time to restore a failure.
- **The view-only demo keeps some write controls.** With `AGENTIC_OS_DEMO=1`
  there is no sign-in and the landing views hide their start buttons, but the
  Analytics run form, adding a dataset, approving, saving a target and the
  Operations administration still show theirs; using one gets the server's
  refusal and writes nothing
  ([decision](adr/2026-10-21-view-only-demo-mode.md)).
