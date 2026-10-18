# ADR 0045: Bounded serverless event streams

Status: implementation for review. Date: 2026-10-18.

## Observed failure
After merging the UI and voice work, Vercel logs show recurring `GET /api/events` function timeouts at 30 seconds. The generic SSE stream defaults to `MAX_SECONDS = 55` and the Vercel function has `maxDuration: 30`. This is a time budget mismatch, not demonstrated proof that the whole API is broken.

## Decision
Keep the existing SSE event contract, owner scoping, cursor, and reconnect semantics. On runtimes with the Vercel `VERCEL` flag, cap each event stream at 20 seconds. Preserve 55 seconds for ordinary persistent Python servers and preserve explicit smaller requested waits.

Test a normal run, a Vercel-like runtime, and existing stream behavior. Do not disable authentication, remove headers or increase function duration to conceal the issue.

## Remaining limits
A reconnecting browser still consumes serverless function requests. A more scalable hosted production release should move to bounded polling for serverless deployments or persistent SSE on a dedicated service with durable auth and database access. No production readiness claim is made until runtime errors and authentication/tenancy behavior are checked after deployment.
