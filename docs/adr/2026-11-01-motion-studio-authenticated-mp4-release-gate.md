# Motion Studio authenticated MP4 with a human release gate

Date: 2026-11-01. Status: proposed (Tier 2 item 2).

## Decision

Motion Studio produces an MP4 that is only ever served to an authenticated
user, and its release is gated on a named human approval. No anonymous or
unauthenticated access to a generated MP4.

Concretely:

- The MP4 route requires an authenticated session; unauthenticated requests
  return 401 and are never redirected to a public URL.
- Generation runs behind a release gate: a named approver records approval
  against the evidence version that produced the MP4. Changed evidence
  supersedes the approval automatically (per the existing approval rule).
- The "responsive pause/cancel under model load" gap is handled by writing the
  failing test first, then fixing transaction handling in the analysis step.
  No claim of pause/cancel safety is made until that test passes.
- A real Arabic RTL frame and MP4 audio integration regression test (PR #29)
  is the minimum evidence that the Arabic path is not broken.

## Why

KNOWN_LIMITATIONS and the Motion Studio release handoff treat authenticated
MP4 plus a human release gate as a P0. An unauthenticated MP4 is a data
exposure; an unapproved release is a governance failure. Both are worse than
not shipping.

## Validation and reversibility

- An integration test requests the MP4 without a session and expects 401.
- An integration test approves a release, regenerates with changed evidence,
  and expects the approval to be superseded.
- Reversible: if the gate blocks a legitimate release, the approver records a
  new approval against the new evidence version; no history rewrite.
