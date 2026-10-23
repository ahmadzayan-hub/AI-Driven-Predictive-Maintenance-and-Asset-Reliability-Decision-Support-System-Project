---
type: operation
aliases: []
tags: [operations]
status: active
updated: 2026-10-23
review_every_days: 30
sources: [docs/adr/2026-10-20-production-release-approval.md, docs/assessments/2026-10-20-project-review.md, docs/implementation/DELIVERY_ROADMAP.md, README.md, vercel.json, .github/workflows/ci.yml]
---

# Release acceptance

Release acceptance is the owner's decision to deploy a reviewed source revision after its hosted and domain checks are satisfied.

## Separate decisions

- Synchronizing source to main has standing permission; production deployment requires explicit owner approval.
- Main-branch automatic Git deployment is disabled in the checked-in Vercel configuration.
- Local tests, hosted identity and storage checks, operational recovery and independent domain acceptance are different evidence.
- CI that never starts is not a failed source assertion or a passing verification result. Current run evidence and infrastructure limits live in README.
- Repository privacy containment does not erase historical copies or authorize a later public release.
- The platform assessment's P1 list was closed in three slices on 22 October 2026; the P2 list is worked slice by slice, the first on 23 October. Each slice is a dated decision record, tests and a pull request merged under the owner's standing permission once hosted CI is green.
- Hosted CI assigns runners again since 22 October: the job runs under a 45-minute limit with the Playwright browser cached by version. The full browser suite on the merged head passed 139 with 5 skipped; the one-pixel Arabic phone overflow was the skip link's 9999 px offset and a header running 1 px over, both fixed in CSS.

## Related

- [[Verification and budgets]] records reproducible source checks.
- [[Managed identity]] needs a real hosted acceptance path.
- [[Backup and restore]] supports operational recovery.
- [[Soul]] defines authority and honesty.
- [[Home]] connects release work to the platform.
