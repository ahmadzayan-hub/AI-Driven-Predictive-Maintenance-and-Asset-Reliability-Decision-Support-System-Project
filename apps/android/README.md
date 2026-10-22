# Asset Reliability for Android

A Kotlin and Jetpack Compose phone app over the platform's API: upload data,
run a governed analysis, read the Executive Command Centre, approve or reject
at the human gate, present the brief as slides, share the executive report,
and keep notes in a local vector memory. English and Arabic, right-to-left.

Every figure on the phone is the server's. The app computes nothing from
rows, invents no KPI and claims no model accuracy the server did not record.

## State of the build (22 October 2026)

| Module | What it is | Built and tested |
| --- | --- | --- |
| `core` | Pure Kotlin: API client over a `Transport` seam, the executive brief models, the decision mapping shared with the web Command Centre, a local vector memory (HNSW index, lexical embedder, snapshots) | **Yes, on the JVM**: `./gradlew :core:test`, 14 tests, including HNSW recall of at least 0.9 against brute force on 1,500 vectors and parsing of the live demo brief |
| `app` | Android: Compose UI, Hilt, Room, DataStore, OkHttp, navigation; six screens | **Authored, not compiled here.** The development container cannot reach `dl.google.com`, which serves the Android SDK and Google's Maven repository. First build on a machine with Android Studio, or in this environment once that host is allowed |

The `app` module is only included in the Gradle build when an Android SDK
is present (`settings.gradle.kts`), so `core` builds anywhere.

## Build

```bash
# Core only, no SDK needed
cd apps/android && ./gradlew :core:test

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
| Approvals | Runs at the gate, oldest first. The report must be opened and "I have read this report" ticked before Approve is enabled | `GET /api/runs/{id}`, `POST /api/runs/{id}/approvals/{approval_id}` |
| Presentation | Six slides on the navy ground with a horizontal slide transition; share the executive report as HTML or Word through the system share sheet | `GET /api/runs/{id}/executive/export` |
| Memory | Notes and remembered briefs on the device (Room plus the HNSW index); recall by query; the screen names the embedder in use | none |
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
trusting old vectors. No language model runs on the phone; model roles run
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
