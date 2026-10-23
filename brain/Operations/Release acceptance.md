---
type: operation
aliases: []
tags: [operations]
status: active
updated: 2026-10-20
review_every_days: 30
sources: [docs/adr/2026-10-20-production-release-approval.md, docs/assessments/2026-10-20-project-review.md, README.md, vercel.json]
---

# Release acceptance

Release acceptance is the owner's decision to deploy a reviewed source revision after its hosted and domain checks are satisfied.

## Separate decisions

- Synchronizing source to main has standing permission; production deployment requires explicit owner approval.
- Main-branch automatic Git deployment is disabled in the checked-in Vercel configuration.
- Local tests, hosted identity and storage checks, operational recovery and independent domain acceptance are different evidence.
- CI that never starts is not a failed source assertion or a passing verification result. Current run evidence and infrastructure limits live in README.
- Repository privacy containment does not erase historical copies or authorize a later public release.

## Related

- [[Verification and budgets]] records reproducible source checks.
- [[Managed identity]] needs a real hosted acceptance path.
- [[Backup and restore]] supports operational recovery.
- [[Soul]] defines authority and honesty.
- [[Home]] connects release work to the platform.
