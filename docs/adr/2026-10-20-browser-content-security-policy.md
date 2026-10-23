# Browser content security policy

Date: 2026-10-20

Status: Accepted

## Context

The application and Miyaar shell previously supplied browser security headers
without a Content-Security-Policy (CSP). Executive HTML exports already had a
restrictive document policy. FastAPI serves the built shell locally; Vercel
serves it directly, bypassing FastAPI. Both serving paths need an enforced
policy that preserves the interface's existing resource requirements.

## Decision

Apply a default-deny CSP to shell responses, including SPA fallback paths and
the service-worker script. Permit scripts only from the same origin and the
SHA-256 hash of the fixed prepaint script in `frontend/index.html`. This script
restores the theme, reduced-motion preference and language before paint. A
test compares the hash against the source and built HTML; changing the script
requires reviewing and updating the hash in both server and static policy.
Inline event handlers, arbitrary inline scripts, eval, frames, objects and
base-URL overrides remain blocked. There are no external script hosts.

The shell permits same-origin images, fonts, styles, manifests and workers;
blob audio supports browser playback. Inline CSS remains permitted because
React controls chart/layout styles and print previews use a styled blob HTML
document, which inherits the opener's policy. This is a scoped compatibility
exception for CSS, not for JavaScript. Local model and speech services run
behind the API and require no browser connection exceptions.

Browser connections allow the same origin and the exact configured
`SUPABASE_URL` and `VITE_API_BASE` origins in FastAPI. The parser rejects
credentials, wildcard hosts and policy syntax, discards paths, and emits only
HTTP(S) origins. Set `VITE_API_BASE` in the shell-serving server environment as
well as at frontend build time when using an external API. The remote API must
separately allow the frontend origin through CORS.

Vercel's static shell policy allows same-origin connections plus
`https://*.supabase.co` for the standard managed-auth deployment. Its checked-in
header is not interpolated from runtime environment variables. Before deploying
with a custom auth domain or external API, edit only `connect-src` in the
non-API CSP rule in `vercel.json` to include each exact HTTPS origin (scheme,
host, optional port; no credentials or path). Prefer replacing the Supabase
wildcard with the exact project origin where known. Rebuild, then verify sign-in
and API access in the intended environment. Changing `SUPABASE_URL` or
`VITE_API_BASE` alone does not update the static header. Do not broaden
`script-src` or permit arbitrary HTTPS sources to solve a connection failure.

JSON/API responses, including validation, authentication and unexpected errors,
receive a deny-all resource policy. Existing executive export CSP headers remain
unchanged. Vercel's shell CSP excludes routed `/api/*` requests, preventing a
second policy from accidentally restricting the export document. Bare `/api`
remains covered because the existing Vercel rewrite serves it as a SPA fallback. Swagger, ReDoc and
the public OpenAPI endpoint remain disabled; no documentation-CDN exception is
introduced. If interactive docs are added later, they need a separately reviewed
policy and tests.

Vite production preview loads the static policy from `vercel.json`, so Miyaar
browser checks enforce the policy used by the static deployment. The Vite dev
server retains its development behavior for hot module replacement.

## Verification

`tests/test_content_policy.py` checks routes, errors, configured origins,
prepaint hashes, default static policy and API/export rule separation.
`tests/test_executive_exports.py` asserts the real export policy is preserved.
`frontend/e2e/csp.spec.ts` checks Chromium enforcement, saved prepaint settings,
managed sign-in through a synthetic provider response, service-worker startup,
blob audio and downloads. Existing executive-export and Miyaar browser suites
exercise their actual document and interface paths under the enforced policies.
These are local checks, not proof of an owner-approved hosted release.

## Sources

- [MDN CSP guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP):
  a hash can authorize fixed inline scripts without permitting arbitrary inline
  JavaScript; a deployed policy must cover the resources the page uses.
- [MDN CSP reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy):
  multiple policies intersect, and blob workers/documents can inherit policy
  rather than relaxing their creator's restrictions.
- [MDN worker-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/worker-src):
  worker sources have their own directive.
- [Vercel project configuration](https://vercel.com/docs/project-configuration):
  source-scoped response headers are configured in `vercel.json`.
