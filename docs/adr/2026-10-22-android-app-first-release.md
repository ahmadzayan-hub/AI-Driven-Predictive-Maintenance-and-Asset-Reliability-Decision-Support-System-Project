# The Android app: first release, authored with a tested core

Date: 2026-10-22 · Status: Accepted (owner request, 22 October: a Kotlin and
Compose app to upload data, run the analytics and read executive dashboards
and presentations on a phone, with local memory; "recommend and proceed")

## Context

`docs/ANDROID_BUILD_AND_RELEASE.md` recorded that a native project would not
be committed unbuilt and untested, because the development environment has no
Android SDK. That is still true, and the owner asked for the app now. The
container has JDK 21 and Gradle, reaches Maven Central and the Gradle plugin
portal, and cannot reach `dl.google.com`, which serves the SDK, the Android
Gradle plugin and every AndroidX and Compose artifact.

## Decision

1. The app is two modules under `apps/android`. **`core`** is pure Kotlin
   (API client over a `Transport` seam, brief models, the decision mapping
   the web Command Centre uses, a local vector memory with an HNSW index) and
   is **built and tested here** on the JVM. **`app`** is the Android module
   (Compose, Hilt, Room, DataStore, OkHttp) and is **authored, not compiled
   here**; `settings.gradle.kts` includes it only when an SDK is present. The
   README and this record say so plainly; the owner chose this path over
   waiting for the network change.
2. The app shows only the server's figures. No KPI, verdict or model
   score is computed or invented on the phone; the brief is mapped, never
   recalculated. The platform has no transit, traffic or revenue data, so the
   app has no such dashboards.
3. The human gate is stricter on the phone than on the web today: Approve
   needs the report opened and a read confirmation (assessment finding U3).
4. Local memory is lexical (a hashing embedder) and says so on screen. A
   semantic on-device model is a later release; snapshots carry the
   embedder's name so a change re-embeds rather than trusting old vectors.
5. Release signing comes from the environment only. The server address is a
   build property, never a secret.
6. The build script `scripts/build-apk.sh` runs the core tests, the app unit
   tests, lint and the assembly; it refuses with a clear message when no SDK
   is present.

## Consequences

- The first APK is built on a machine with Android Studio, or here once
  `dl.google.com` is allowed. Until then the app module's compile status is
  unknown and is reported as such.
- The core's behaviour (paths, bodies, parsing, decision mapping, rounding
  identical to the browser, recall quality) is already verified and will not
  change when the UI compiles.

## Verification

`apps/android/core`: 14 JVM tests (`ClientTest` 5, `DecisionSupportTest` 4,
`HnswIndexTest` 3, `LocalMemoryTest` 2) pass with `./gradlew :core:test`.
`apps/android/app/src/test`: a string-parity test, to run with the SDK.
