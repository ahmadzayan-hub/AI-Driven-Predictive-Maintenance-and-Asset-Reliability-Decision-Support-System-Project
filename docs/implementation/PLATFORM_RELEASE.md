# Platform and application delivery

Updated: 23 October 2026. Integration branch: `codex/rmd-evidence-insights-20261022`.
Measured verification and test counts are maintained in [README](../../README.md#testing).

## Delivered journeys

The existing React/FastAPI/Hermes platform remains the application. English,
Arabic RTL, semantic tokens, permission checks and artifact-bound human approval
are reused. No parallel dashboard or replacement analytics engine was added. Incoming main's workbook discovery, reviewer improvements and optional local Motion Studio
sources are preserved. Their separate media/reviewer release gates remain in
[the Motion Studio handoff](../MOTION_STUDIO_RELEASE_HANDOFF.md).

1. Select sample, uploaded or stored data and state the question.
2. Follow actual server stages; inspect the available finding and evidence.
3. Review the exact report, approve or reject, and await server confirmation.
4. Reopen the durable result, download a permitted export or ask a follow-up.
5. For RMD, import a private pack, review mappings/extraction coverage, calculate
   a snapshot and investigate its records or cited clauses before publication.

The unavailable real RMD inputs were omitted at the owner's instruction.
Synthetic verification is not a study or validation of those original sources.

## Implementation mapping

| User need | Implementation and API | Failure/recovery and boundary |
| --- | --- | --- |
| Recover a run creation after an uncertain response | `CreationAttempt`, `POST /api/runs`, owner/key/request digest | Same exact request replays; changed input conflicts. Tab storage contains only a digest/key. Draft text stays in the existing scoped draft flow; CSV is not persisted there |
| Read a stable machine contract | Authenticated `GET /api/openapi.json`, `server/api_contract.py` | Canonical error code/message/problems/request ID; old `detail` retained. No public interactive schema or validation-input echo |
| Find older maintenance evidence | `GET /api/assets/evidence`, `runs_with_completed_stage` | Queries stored history, rechecks authorization, returns an explicit empty result; no browser scan of recent run payloads |
| Recover missing KPI cards | Existing owned `/api/runs/{id}/kpis`, `AssetIntelligenceView` | Announced loading/failure, retry only the measures, retain screening; cancel obsolete reads and hide another run/language's figures |
| Understand freshness | Separate analysis-update and evidence-check timestamps | Viewer-local formatting; no unrecorded reporting period or Dubai-time claim |
| Read every chart value | Relationship table matches the complete plotted sample | Existing sampling disclosure remains. Scrollable chart tables are labelled and keyboard focusable |
| Return from evidence | Existing shared `Dialog` and explicit invoking-button focus | WebKit pointer activation is supported; Escape restores the evidence control |
| Publish on a read-only host | `AGENTIC_OS_PUBLISH_TARGET=database`, existing SQL notes and approval transaction | No filesystem access. Failed note/state writes roll back. Changed destination refuses the old approval. Local `vault` mode remains available |
| Recover a changed publication destination | `POST /api/runs/{id}/approvals/refresh`, `ApprovalCard`, Android Approvals | An authorized approver requests a new review of unchanged content; the previous request is superseded without a human decision. Repeating refresh is idempotent. The preview and read confirmation reset; changed content requires a new governed analysis |
| Use Android | Existing Kotlin core, Compose app and same API | Raw upload contract, readable errors, live retry key/known run, worker polling, complete report review and server-confirmed publication |
| Separate phone workspaces | Atomic connection settings, identity-bound Room databases, keyed navigation | Server verifies identity before note operations; old unscoped `memory.db` is retained without assigning it to a new person. Access failure prevents recall |
| Use Windows/iPhone/iPad | Existing installable PWA plus Edge/Windows and WebKit/macOS browser jobs | Browser-engine checks are distinct from physical installation, VoiceOver and actual iOS acceptance |

## Obtain and run the applications

**Web/PWA:** build with `npm --prefix frontend ci` and
`npm --prefix frontend run build`; run `python scripts/serve.py`. Analyses and
private data require the backend. Use Preferences for installation instructions.
Windows uses Edge/Chrome's Install app control; iPhone/iPad uses Safari → Share →
Add to Home Screen. HTTPS is required outside localhost.

**Android:** open the successful **Android build** run on GitHub and download
`asset-reliability-android-debug`. Its ZIP contains
`app/build/outputs/apk/debug/app-debug.apk`, test reports and build evidence.
Unzip it and install on an authorized test phone with `adb install -r <apk>`.
The debug application is separate from a signed production release. Configure
the actual HTTPS API and, where required, a managed-provider token in Settings.
A Vercel-protected website alone is not a managed-provider API credential.

For a local Android build, follow [the app guide](../../apps/android/README.md)
and `scripts/build-apk.sh`. Release keystores and credentials remain outside Git.
Windows and iOS currently use the PWA; no native Windows or Swift application is
claimed by this release.

## Verification and acceptance

Synthetic backend checks cover ownership, request replay/conflicts, error
redaction, private schema access, old-stage selection, transactional publication,
read-only hosts, changed destinations and YAML source-name fidelity. Scoped web
journeys cover reload recovery, evidence, charts, RTL, keyboard review and
confirmed publication. Hosted Android compiles Compose and runs JVM/app tests,
lint, APK assembly and signature verification. Platform jobs run the actual API
journeys in Edge on Windows and WebKit on macOS, including model cards in
both languages. Synthetic model setup permits one connection-reset retry bound
to one exact-request idempotency key; stages and human decisions are not retried.

| Review | Current evidence | Acceptance boundary |
| --- | --- | --- |
| UX-01/02 stack and tokens | Existing architecture and component source; bundle gate | No framework or design-system migration |
| UX-03/04/05 authorization and evidence | Synthetic separate-user API checks; immutable report/destination gate | Authentication alone is not collection isolation; existing RMD grants remain authoritative |
| UX-06 recovery | Fault-injected committed/lost response, KPI component failure, failed publication write | No automatic publish retry; a returned path is required for success |
| UX-07/08/12 language, layout and charts | Bilingual desktop/phone journeys, exact plotted-value tables, automated accessibility | Browser/viewport details and observed results are in README and CI artifacts |
| UX-09/11 keyboard and touch | Evidence focus, keyboard approval and phone-size journey | Physical assistive technology and native touch remain NOT TESTED |
| UX-10/15 zoom and production performance | Existing token/bundle gates | Manual zoom and fresh production Web Vitals remain NOT TESTED |
| UX-14 session continuity | Scoped web attempts, requester tests and implemented native identity separation | Native account-switch/revocation behavior requires device acceptance |
| UX-16 regression | Hosted source-specific run links in README | A successful debug build is not store or production approval |

## Remaining gates

The [roadmap](DELIVERY_ROADMAP.md) remains authoritative for subsequent product
work, including model quotas, storage pooling/versioned migrations, advanced
model/consultant contracts and independent evaluations. This release does not
claim those future items completed.

Production sign-in/storage/provider acceptance, direct-egress connector refresh,
responsive controls under real model load, prospective maintenance outcomes,
timed manager review, device installation, assistive technology, native secure
credential-storage review, release signing and store submission require their
recorded acceptance. No production deployment or external publication was made.
The repository stays private. Real source ingestion remains outside this delivery
because the owner explicitly omitted its unavailable inputs.
