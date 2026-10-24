# Compatible undici security floor for the development DOM runtime

Status: accepted implementation; exact-head hosted acceptance is required before merge.

On 24 October, fresh PR51/52 CI correctly stopped at the unchanged high-severity npm audit gate. The locked undici 8.11.2 is a transitive development dependency of jsdom 30, not an application production dependency or a browser-bundled HTTP client. That distinction does not exempt development and CI processes from remediation.

## Decision

Replace only the undici lock entry with 8.12.2, the compatible patched floor documented by the upstream maintainers. The package manifest, jsdom range, Node engine requirement, all other lock entries, production runtime, audit severity threshold and UI budgets remain unchanged. The version, official registry URL and SHA-512 integrity were retrieved from the public npm registry; clean npm ci validates the package integrity. Unrelated lockfile regeneration changes are not retained.

Upstream references:
- https://github.com/nodejs/undici/releases/tag/v8.12.2
- https://github.com/advisories/GHSA-4qv8-2p9j-2685
- https://github.com/advisories/GHSA-f72v-6w45-q472
- https://github.com/advisories/GHSA-xjj6-f33q-929c

The earlier main 389ff968 acceptance was valid when performed, but its audit snapshot must not be presented as a current zero-vulnerability result after the advisory database changed.

## Verification and limits

A clean install with scripts disabled and a fresh registry audit reports zero vulnerabilities at the time of the repair. Two regression tests enforce the patched floor and development-only classification. Frontend unit/type/build and exact-head hosted browser/regression results are recorded in the PR rather than assumed from the old main run. No blanket dependency update, audit suppression, provider call, credential change or deployment is included.
