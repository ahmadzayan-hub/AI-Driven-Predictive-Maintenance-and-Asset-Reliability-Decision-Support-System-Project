# Large Data + Live Monitoring + Video Worker: Isolated Feasibility Branch

This is a **non-production foundation**, not a declaration that the MIYAAR UI/API already accepts 300 MB.

## Verified from main source (5 Nov 2026)
- server/datasets.py: 4,000,000-byte upload; 500 columns; byte-based in-memory reader.
- docs/DATASET_ANALYTICS.md: 50,000 rows, 10 MB canonical CSV; PDF/images/PBIX outside analytic upload.
- server/connectors.py: HTTPS allowlisted snapshot polling; not push streaming.
- PR #92 film rendering requires Chromium and ffmpeg on a non-Vercel host.
- Three hosted schema tables for video/reviews/layouts have not been evidenced as migrated.

## Implemented on this branch
- Isolated disk-based byte-chunk spool, limit 300,000,000 bytes and SHA-256.
- Disk-based CSV indexing with JSON-array record storage, supporting 501+ input columns.
- Cursor paging and tests without altering main upload/analytics safety contracts.

## Results in separate standalone lab
- 6/6 standalone tests pass.
- Synthetic 7,500-row, 501-column, and 50,001-row ingestion preflights pass.
- 34 challenge scenarios inventoried, **zero passed against actual MIYAAR runtime**.

## Required before promotion
1. Signed, authenticated multipart uploads direct to private object storage, resumability, antivirus, quotas and no public bucket.
2. Separate ingestion worker using projected/partitioned Arrow/Parquet/DuckDB and analytics with bounded memory; explicit quotas for column width and concurrency.
3. PDF/image isolated extraction with positional citations, OCR confidence and approval; PBIX metadata only until Microsoft-supported semantic-model/API integration validates DAX and dataset compatibility.
4. Reuse existing connector SSRF fencing for cloud/API polling; add broker for event-time true streaming, lag metrics, dedup, backpressure, reconnection and fail-closed credential scoping.
5. Independent Chromium/ffmpeg worker: queue, job-scoped authorization, private MP4 storage, manifests, RTL visual QA, synthetic narration, voice provider approval.
6. Run the challenge set on authenticated isolated MIYAAR clone, compare KPI ground truth and capture logs/screenshots. Do not call preflight a platform test.
7. Review current migrations, backups, rollback and stakeholder approval before ANY production changes.

No deployment, hosted database migration, external voice request or secret rotation is authorized by this branch.

## Development checkpoint, 5 Nov 2026 23:00 Gulf time

Additional experimental modules on PR #93:
- `server/experimental_jobs.py`: SQLite lease/heartbeat, per-owner task visibility, dedupe and "awaiting_review" artifact gate. No real renderer or HTTP adapter.
- `server/experimental_assets.py`: signature and ZIP-member path inspection only; **not PDF OCR or PBIX model parsing**.
- `server/experimental_stream.py`: synthetic event-time ingestion, duplicate IDs, lateness, skew and staleness measurements. **Not connected to an external API/message broker**.
- `tests/test_miyaar_challenge_contract.py`: regression coverage of the actual current 4 MB/500-column reader and refusal of masquerading PDF/image/Parquet content.

Historical CI 42076975901 failed because a disguised PDF was previously accepted as CSV. New `server/datasets.py` signature guard and tests aim to close that issue. Some later CI runs are queued/in progress at this checkpoint; no overall green result is claimed.

**Release verdict: NOT READY.** Required missing deliveries: private multipart browser upload, partitioned analytics equivalence, secure live API/cloud connector, verified Power BI semantic-model APIs, extraction of PDF/image evidence with citations, hosted video worker with Chromium/FFmpeg, live voice evaluation, isolated integrated challenge execution, migration checks, cost/load/security tests, and documented owner approval. The goal "unlimited rows and columns" must be operationalized as storage/compute scaling with enforceable budget and time limits, not unbounded RAM.

## 6 November 2026 development continuation

- Latest prior head `6fa89f89` had successful CI, application platform journeys, RMD evidence and UI budget checks. New commits must be evaluated independently.
- Hardened experimental PBIX archive inspection against symbolic links, encrypted entries, unsupported compression and extreme expansion ratios. This is metadata screening, **not** safe general extraction or verified Power BI integration.
- Introduced `server/experimental_worker.py` to exercise a trusted callback, atomic private artifact write, SHA-256 digest, owner-linked job completion and an awaiting-review gate. Synthetic bytes are not a rendered video; no public endpoint, deployment, real TTS, voiceover review, or production side effects occur.
- Remaining P0 release gates: secure authenticated upload/storage, complete 300 MB UI/worker journey, external streaming connector security, scalable business analytics/KPI parity, real Chromium/FFmpeg worker, verified hosted data migration/permissions and independent 34-case application challenge. P1: OCR positional provenance, Power BI semantic-model connector, live voice acceptance, visual RTL QA and cost measurement.
- No merge to main, Vercel changes, external audio transmission, database changes or secret changes in this phase.
