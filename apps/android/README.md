# Asset Reliability for Android

A Kotlin and Jetpack Compose phone app over the platform's API: upload data,
run a governed analysis, read the Executive Command Centre, approve or reject
at the human gate, present the brief as slides, share the executive report,
and keep notes in a local vector memory. English and Arabic, right-to-left.

Every figure on the phone is the server's. The app computes nothing from
rows, invents no KPI and claims no model accuracy the server did not record.

## State of the build (23 October 2026)

| Module | What it is | Built and tested |
| --- | --- | --- |
| `core` | Pure Kotlin: API client over a `Transport` seam, the executive brief models, the decision mapping shared with the web Command Centre, a local vector memory (HNSW index, lexical embedder, snapshots) | **Built and tested on the JVM**: `./gradlew :core:test`; actual counts and CI evidence are in [README testing](../../README.md#testing), including the bounded HNSW comparison and synthetic executive-brief contract |
| `app` | Android: Compose UI, Hilt, Room, DataStore, OkHttp and navigation | **Built in hosted CI:** Compose compilation, app unit tests, lint and actual debug APK assembly. [Successful build and artifact](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/39935735248). Physical devices and store release remain separate |

The `app` module is only included in the Gradle build when an Android SDK
is present (`settings.gradle.kts`), so `core` builds anywhere.

## Build

```bash
# Core only, no SDK needed
bash apps/android/gradlew -p apps/android :core:test

# Debug APK (needs JDK 17+, Android SDK, network)
scripts/build-apk.sh
# Against your own server
SERVER_URL=https://your-host scripts/build-apk.sh
# Signed release
KEYSTORE_PATH=... KEYSTORE_PASSWORD=... KEY_ALIAS=... KEY_PASSWORD=... scripts/build-apk.sh release
```

In Android Studio: open `apps/android`, let it sync, run `app`.

## Screens

| Screen | What it does | API |
| --- | --- | --- |
| Command Centre | The latest analysis's decision brief: recommendation and readiness, decisions with owner and gate, six controlled measures with the server's verdict, predictive readiness, recommended action with its assumption, data quality and limitations, approver's questions. "Remember this brief" stores its words on the phone | `GET /api/runs`, `GET /api/runs/{id}/executive` |
| Analyses | Pick a CSV, TSV, XLSX, JSON or JSONL file (4 MB cap, the platform's), upload it, start a run (maintenance profile by default), advance it stage by stage with a progress bar until it waits for approval | `POST /api/datasets`, `POST /api/runs`, `POST /api/runs/{id}/advance` |
| Approvals | Runs at the gate, oldest first. The complete report and destination must be opened and "I have read this report" ticked before Approve is enabled. A changed destination can request a fresh review without publishing | `GET /api/runs/{id}`, `POST /api/runs/{id}/approvals/{approval_id}`, `POST /api/runs/{id}/approvals/refresh` |
| Presentation | Six slides on the navy ground with a horizontal slide transition; share the executive report as HTML or Word through the system share sheet | `GET /api/runs/{id}/executive/export` |
| Memory | Notes and remembered briefs in an identity-bound device database; recall by query; a connection verifies the workspace first | `GET /api/identity` |
| Assistant | The platform's assistant through its session API; the phone shows how many of its own notes relate to each question | `POST /api/sessions`, `POST /api/sessions/{id}/messages` |
| Settings | Server address, language, optional sign-in token (device only), connection check | `GET /api/health`, `GET /api/auth/config` |

In the view-only demo (no token, server in demo mode) the upload, approval
and assistant controls say so instead of failing.

## Memory and models

The local memory uses a lexical hashing embedder (256 dimensions): recall is
by shared words, not meaning, and the Memory screen says which embedder is in
use. A semantic on-device model (for example through ML Kit or an ONNX
runtime) is a later release; the `Embedder` interface and the snapshot
format already carry the embedder's name so a change re-embeds instead of
trusting old vectors. Old unscoped `memory.db` is retained without assigning its contents to another account.
Connection changes save server and credential together and reset navigation.
Notes require an authorized connection before recall; this is not an offline
technician workflow. Native credential-storage hardening and real account-switch
acceptance remain release gates.

No language model runs on the phone; model roles run
on the server under the platform's grounding and privacy rules.

## Architecture

Clean architecture in two layers: `core` (domain and API, no Android) and
`app` (data: OkHttp transport, DataStore settings, Room memory; UI: MVVM
with Hilt ViewModels, `StateFlow`, Compose screens). Coroutines throughout.
Retrofit is on the classpath for the next release's typed services; the
first release uses the core client over OkHttp directly, which the JVM
tests cover.

## What is not in this release

- No transit, traffic or revenue KPIs: the platform has no such data, and
  the app shows only what the server computes from uploaded data.
- No on-device language model or semantic embeddings.
- No push notifications or background sync (WorkManager is on the
  classpath for the next release).
- No instrumentation tests have been run; the JVM tests are the evidence.
