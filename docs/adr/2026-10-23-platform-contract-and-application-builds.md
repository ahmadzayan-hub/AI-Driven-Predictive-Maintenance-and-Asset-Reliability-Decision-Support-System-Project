# Shared API contract, asset recovery and application build gates

Date: 2026-10-23 · Status: Accepted (owner: continue all development phases).

## Context

The next roadmap slice leaves the core/Operations/RMD APIs with different error
shapes, no authenticated schema and a web client that does not use the new run
idempotency key. Assets scans recent run payloads and silently drops failed KPI
requests. The Android app has a JVM-tested core but no recorded Compose/APK
build; inspection found multipart uploads against a raw-body API and approval
previews containing only a truncated report section.

## Decision

- Add a canonical `error` object (`code`, `message`, `problems`, `request_id`)
  across HTTP, validation, rate-limit and unexpected errors. Retain the previous
  `detail` value for installed clients. Validation never echoes input or context.
  Publish the machine-readable schema at authenticated `/api/openapi.json`;
  interactive/public documentation remains disabled.
- Run creation binds an owner/key to a digest of the exact request. Changed or
  legacy-unmatchable requests conflict. Web attempts retain only a digest/random
  key under the active session in tab storage; CSV and request bodies are never
  stored there. Without Web Crypto/storage, recovery is limited to the live form.
  Android retains the same key and known run during a live retry. Neither client
  automatically repeats a consequential POST after an uncertain response.
- CORS permits PATCH and the idempotency/request-id headers and exposes recovery
  and download headers. Existing allowed-origin restrictions remain in force.
- Assets uses a server query for the latest accessible completed maintenance
  screening across stored history, followed by the existing owned KPI endpoint.
  A KPI failure has an announced retry state; available screening remains usable.
  Evidence-check and analysis-update times are separately labelled. Obsolete reads
  are cancelled; no stale KPI from a different run/language is displayed.
- The relationship table contains every plotted point, within the existing
  bounded sample. No row is silently dropped from the numeric alternative.
- Cross-platform execution exposed WebKit's implicit button-focus policy:
  evidence activation explicitly focuses its invoking control, and the consent,
  Reject and Approve controls explicitly use tab index zero in DOM order. No
  positive index or automatic approval is introduced. WebKit's
  [form-control implementation](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/html/HTMLFormControlElement.cpp)
  confirms that an explicitly set index uses normal element keyboard focus
  rather than the platform's implicit-control preference (inspected 23 October).
- Android sends actual raw upload bytes with an encoded filename and unwraps
  `dataset`; recognizes canonical and legacy errors; queries the approval queue
  explicitly; displays the full exact artifact/version, destination and impact;
  and reports publication only from the confirmed state and returned path.
  Reads are bounded before allocation exceeds the upload cap.
- Add a read-only hosted Android job to compile Compose, run JVM/app tests and
  lint, and retain a debug APK. This is build evidence, not physical-device,
  accessibility, release-signing or store acceptance. No new runtime dependency
  is introduced. Windows/iOS continue through the existing installable PWA.

## Verification

Evidence and observed counts belong in `README.md#testing`. Synthetic HTTP
contracts, component recovery, run retry and chart alternatives are exercised;
the hosted Android build must actually pass before an APK is described as built.
Production deployment, live managed-provider acceptance, physical devices and
independent maintenance/model acceptance remain separate gates.

Integration retains main's workbook discovery, reviewer/evaluation improvements
and optional local Motion Studio sources. Remove its unused Overview import to
keep the repository's strict TypeScript build valid, and render its otherwise
unused bilingual draft-error state as an accessible alert. The retained local panel
does not become an enabled hosted capability merely through this merge.

A combined browser run lost its connection during model-card setup. That
synthetic creation request now carries one random idempotency key and permits
one Playwright transport retry for a connection reset. Stage advancement and
human decisions are not retried. Model cards in both languages also run in the
Windows/WebKit platform job. This is a bounded setup recovery, not a blanket
browser retry or a relaxed assertion.
