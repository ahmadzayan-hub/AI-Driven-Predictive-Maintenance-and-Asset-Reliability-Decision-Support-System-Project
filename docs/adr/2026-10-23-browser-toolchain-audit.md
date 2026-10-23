# Browser-toolchain Zod advisory repair

Status: code-only dependency remediation; no production activation.

The frontend audit on model-resilience PR #39 reported high-severity
[GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5),
updated 23 October 2026. The affected Zod dependency was transitive through
Lighthouse's Puppeteer / Chromium BiDi development toolchain, not a direct
application runtime dependency. The audit remains blocking; no exception or
severity threshold was changed.

Refresh the existing compatible Puppeteer dependency chain in the lockfile:
Puppeteer Core 25.16.0 and Chromium BiDi 157.0.8090-0 use Zod 4.6.7, above
the advisory's patched 4.6.6 floor. Keep package.json ranges, application
runtime dependencies and unrelated platform-binding metadata unchanged.
No override forces a new Zod major onto an incompatible old consumer.

Local validation: npm clean install with lifecycle scripts disabled, npm audit
at the existing high threshold (zero reported vulnerabilities), frontend unit
tests, typecheck/build and unchanged interface budgets. Hosted CI must also
exercise the browser suite against the final commit before release acceptance.
Audit results are time-dependent and are not a guarantee of no future advisories.
