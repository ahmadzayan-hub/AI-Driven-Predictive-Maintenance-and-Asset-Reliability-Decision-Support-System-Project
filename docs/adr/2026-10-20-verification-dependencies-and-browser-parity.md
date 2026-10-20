# Full verification requires the server dependencies and both browser suites

Date: 2026-10-20 · Status: Accepted

## Problem

Several server test modules intentionally skip when their optional server
imports fail, allowing the standard-library CLI to be tested independently.
During this review, an incomplete dependency installation caused those skips.
Dependency metadata alone reported compatibility despite missing package files.
The full-release verifier must not interpret this as a functioning server.

The verifier also omitted the native run-logic check and the separate Miyaar
browser suite that CI runs.

## Decision

Before Python tests, import the declared server and test dependencies in a
separate process. A failure blocks the Python test step and fails verification.
Direct `unittest` discovery keeps its existing optional-dependency behavior.
Run the native logic check in all verifier modes; `--e2e` runs both the main
API-backed Playwright suite and the Miyaar browser suite.

Use one Vitest worker by default on Windows. The full run reproduced
timeouts in unrelated interactive tests while concurrent jsdom environments
consumed the machine's headroom. Earlier repository sessions independently
recorded the same failure family. Limiting concurrency keeps the assertions
and their existing deadlines; other platforms retain their default workers.
The bounded Windows run still timed out in some interactive tests on this
resource-constrained host. This setting bounds worker memory; it is not a
claim that every Windows run is now green. Complete Linux CI passed the
integrated source. Keep the local failures and isolated follow-up results in
README's verification record, without increasing assertion deadlines.

## Validation

A regression supplies a deliberately broken server import and verifies that
the preflight fails. The step contracts require the preflight before Python
tests and include both browser suites in end-to-end verification.

Missing PostgreSQL remains an explicit conditional skip unless `REQUIRE_PG=1`
is set. Live identity-provider, hosted database, and real-model acceptance
remain separate deployment checks.
