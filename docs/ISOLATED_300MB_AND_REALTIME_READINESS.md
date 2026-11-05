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
