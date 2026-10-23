---
type: operation
aliases: []
tags: [operations]
status: active
updated: 2026-10-23
review_every_days: 30
sources: [scripts/verify.py, tests/test_verify.py, docs/UI_PLAN.md, README.md]
---

# Verification and budgets

Verification and budgets turn implementation claims into reproducible checks and measured delivery costs.

## Evidence rules

- The verifier coordinates dependency preflight, backend tests, brain checks, type checks, frontend tests, native contracts, build and size checks.
- Browser suites exercise actual interactions and accessibility; a screenshot alone does not establish correctness.
- Bundle limits distinguish first load, aggregate assets, lazy chunks and fonts. The allocations on 23 October 2026 are 100 KB of scripts on first load, 220 KB in total, 30 KB per chunk, 10.5 KB of CSS on first load and 30.5 KB in total, measured gzipped in exact bytes; every raise is recorded in a dated decision.
- A hosted run is the record for the browser suites when a change touches no interface code; a local run that cannot reproduce a hosted font difference says so rather than guessing.
- Record skipped or unavailable checks explicitly. Never reuse an older green run as proof of changed code.
- Test counts and measured sizes have one canonical home in README Testing.

## Related

- [[Release acceptance]] uses these results without treating them as deployment approval.
- [[Design system]] defines the interface constraints.
- [[Agent evaluation]] supplies a separate measure of specialist behavior.
- [[Session lifecycle]] records what actually ran.
- [[Home]] connects validation to the project.
