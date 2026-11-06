# PR #93 image inspection and CI reliability

## Context

PR #93 at `e888ad6c` rejects actual PNG, JPEG and TIFF headers because the
experimental inspector compares bytes with literal backslash escapes. The
separate acceptance branch already carries a binary-signature correction and
cross-module tests (`11a0103f`, `abfc8159`). Reuse that work instead of creating
a second independent implementation. Recognition remains header inspection,
not image decoding, OCR, or approval of an asset.

The same PR head passed complete CI in run `42099704191`, but run
`42103130390` failed while creating a mobile dashboard fixture: the POST to
`/api/runs` encountered `ECONNRESET` before any filter assertion. The server
cause is not established. Run `42099716713` spent most of the job downloading
OS packages and was cancelled around the configured job limit. The independent
acceptance branch likewise ran out of time after a slow package download.

## Decision

- Incorporate the existing binary-signature fix and acceptance tests. Cover
  JPEG aliases, both TIFF byte orders, and reject textual escape sequences.
- Retry dashboard fixture creation at most once, only through Playwright's
  request-level `maxRetries` handling of `ECONNRESET`. Allocate one unique
  `Idempotency-Key` before the request so an uncertain first response replays
  the same run. The API already verifies the request hash and scopes the key
  to its owner. Accept only HTTP creation/replay success statuses.
- Do not retry advancing, approving or publishing a run. Do not relax a UI
  assertion, use blanket test retries, or call the transport cause resolved.
- Keep every CI stage, reduce apt's optional recommended packages, and allow
  bounded job time for the observed slow setup followed by the full suites.
  This provides headroom, not a guarantee of faster package mirrors. The
  separate Arabic-media job also needs setup headroom: on repair head
  `856008b1`, its PR job hit the former 10-minute limit downloading 66.4 MB
  before tests, while the push job fetched the same packages in four seconds
  and passed. Allow 45 minutes there without skipping any media assertions.
- Retain browser/server output, Python output, HTML reports and failure traces
  with failure exit codes preserved through `pipefail`. Fixtures are synthetic.

## Verification and limits

Real loopback HTTP fault tests cover response loss after creation, replay with
one stored identity, bounded repeated resets, ordinary HTTP failures, unique
keys between fixtures and malformed success responses. The existing real API
test verifies its idempotency contract. Measured counts and execution limits
are recorded in README Testing, not inferred from source inspection.

No production configuration, deployed database, permission, model call or
voice provider changes. Claude's separate feature branch is not incorporated
or overwritten. The large-upload platform integration and production release
gates remain open; isolated module tests are not end-to-end acceptance.

## Evidence

- [Failed mobile fixture setup](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/42103130390/job/127510863021)
- [Passing same-head CI](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/42099704191)
- [Cancelled PR run after slow package download](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/42099716713/job/127499011735)
- [Original image correction](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/commit/abfc81593864d8f5255c94c8b8e0fed13998622e)

- [Arabic-media PR download timeout](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/42169555544/job/127733903767)
- [Passing same-head Arabic-media job](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/42169550671/job/127733888799)
