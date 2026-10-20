---
type: operation
aliases: []
tags: [operations]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [scripts/verify.py, tests/test_verify.py, docs/UI_PLAN.md, README.md]
---

# Verification and budgets

Verification and budgets turn implementation claims into reproducible checks and measured delivery costs.

## Evidence rules

- The verifier coordinates dependency preflight, backend tests, brain checks, type checks, frontend tests, native contracts, build and size checks.
- Browser suites exercise actual interactions and accessibility; a screenshot alone does not establish correctness.
- Bundle limits distinguish first load, aggregate assets, lazy chunks and fonts.
- Record skipped or unavailable checks explicitly. Never reuse an older green run as proof of changed code.
- Test counts and measured sizes have one canonical home in README Testing.

## Related

- [[Release acceptance]] uses these results without treating them as deployment approval.
- [[Design system]] defines the interface constraints.
- [[Agent evaluation]] supplies a separate measure of specialist behavior.
- [[Session lifecycle]] records what actually ran.
- [[Home]] connects validation to the project.
