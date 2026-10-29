# Assistant focus and composer context

Status: isolated review candidate; browser acceptance blocked, not activated.
Base: `1dd392c26a2f3c5107081faf1e5e917a62b1a90a`.

The owner requested implementation of the screenshot review recommendations.
GitHub main, open PRs and Claude branches were checked before editing. The
latest visual-layer work remains intact; no remote changes are authorized here.

## Decision

- Remove the permanently allocated empty context rail. Keep the existing native
  report disclosure beside the composer, initially closed. Its summary always
  names the selected dataset (or explicitly says no report); opening and closing
  it does not unmount selection state or trigger API requests. Existing load,
  explicit selection, clear, failure and disabled behavior remain unchanged.
- Keep the server-provided assistant status message visible. It is a preflight
  statement, not proof of inference. Scope the existing session badge explicitly
  as session connection; remove its duplicate in the assistant. No new health
  source, polling, model calls or availability inference is added.
- Reduce welcome artwork/headline/spacing and repeated toolbar branding. Give
  Analyze data one primary button treatment; preserve all existing destinations.
- Increase small helper text to existing readable type tokens. Retain RTL,
  ASCII numbers, native disclosure keyboard behavior and reduced-motion rules.
  Expanded context scrolls within a bounded composer-adjacent area on phones.

## Verification boundary

Component coverage exercises both languages, disclosure toggles without
selection reset, explicit selection and clearing, failed saves, unavailable
controls and unchanged action dispatch. The browser matrix adds keyboard
opening/closing and overflow checks, but is not claimed executed: local Chromium
cannot create its sandbox socket, and the environment's escalation fails during
mount setup. The supported CUA browser cannot reach this isolated localhost.
Fresh before/after screenshots, axe, phone geometry and actual desktop/mobile
visual acceptance remain required before integration. No old screenshot is
presented as new evidence. Existing dependencies only; no live data or runtime
checkout, installs, pushes, PRs, merges or deployments.
