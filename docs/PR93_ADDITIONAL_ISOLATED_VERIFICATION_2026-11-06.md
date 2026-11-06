# PR93 additional isolated verification, 6 November 2026

**Release verdict: BLOCKED.** These results are not production or MIYAAR application acceptance.

## Independent disk-spool boundary probe

Ran a standalone Python copy of the reviewed `experimental_ingest.spool` implementation in an isolated temporary directory, using synthetic byte chunks.

| Case | Observed | Evidence |
| --- | --- | --- |
| 300,000,000 bytes | accepted; file of exactly 300,000,000 bytes | SHA-256 `f5995fd3ee39ef8fe8ebea12cd5d74432981f071920cdf5917a465f46fd39eaf` |
| 300,000,001 bytes | rejected; previous file unchanged | `LargeIntakeError` |
| Empty upload | rejected | `LargeIntakeError` |
| Non-byte chunk | rejected | `LargeIntakeError` |

Observed max process RSS: 96,780 KiB. This is not hosted-worker or HTTP-request memory, and no network was used. The source transcription is not equivalent to executing the checked-out module inside the MIYAAR application.

For repeatable execution against the **actual branch module**, this branch includes `tests/test_pr93_300mb_boundary.py` with explicit opt-in:
```bash
MIYAAR_LARGE_STRESS=1 python -m unittest tests.test_pr93_300mb_boundary -v
```
Reserve at least ~600 MB temporary writes. Ordinary CI skips this test deliberately.

## Security and correctness finding

`server.datasets.read(body,name,fmt=...)` formerly skipped `detect_format` when a caller passed `fmt`. This may bypass magic-signature blocking for disguised PDFs and images, depending on the caller; no exploitability claim is made without an HTTP route audit. The separate branch now performs signature detection unconditionally and adds forced-format regression tests. Run full dataset parser regression CI before adoption.

## Remaining P0 acceptance gaps

* Authenticated multipart 300 MB private object-storage upload, resumability, quota, malware check, encrypted artifacts, tenant separation
* Partitioned analytics with independent KPI parity and bounded resident memory, not only disk indexing
* Running all 34 synthetic challenge scenarios end-to-end against a deployed isolated MIYAAR app with screen/API/log proof
* Tenant-scoped live connector and stream controls; job worker and video artifact access validation

Do not merge PR #93, migrate databases, deploy new versions, or authorize production credentials without written owner approval.
