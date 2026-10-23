# Android Build and Release

## What ships today: an installable PWA

The web app is a mobile-first Progressive Web App:

- `manifest.webmanifest` with 192/512 px standard and maskable icons,
  standalone display, and theme colors.
- A service worker (`sw.js`) caching the app shell and immutable assets;
  `/api/*` is never cached (session data stays live and private).
- Verified layouts from 320 px up, a bottom tab bar, 44 px touch targets,
  and safe-area padding.

On Android (Chrome): open the app → menu → **Add to Home screen /
Install app**. It launches standalone with the Agentic OS icon and splash
colors.

## Native Android (Kotlin, Jetpack Compose): authored 22 October 2026

`apps/android` holds a Kotlin and Compose app over the platform API: upload,
analyse, the Command Centre, approvals, a presentation view with report
sharing, and a local vector memory. Its pure-Kotlin `core` module is built
and tested on the JVM in this repository (14 tests); the Android `app`
module is authored and waits for a machine with the Android SDK, or for
`dl.google.com` to be allowed in the cloud environment, to compile and
produce the APK (`scripts/build-apk.sh`). The decision and its honesty
boundary are in
[the Android record](adr/2026-10-22-android-app-first-release.md); the
screens and build steps are in [apps/android/README.md](../apps/android/README.md).

## Capacitor wrapper (earlier documented path, superseded)

A real `apps/android` Capacitor project requires the Android SDK and
Gradle to build and an emulator/device to test. Neither exists in the
implementation environment, and committing an unbuilt, untested native
project would violate the no-placeholder rule. The exact path:

```bash
cd frontend
npm i @capacitor/core @capacitor/cli @capacitor/android
npx cap init "Agentic OS" com.agenticos.app --web-dir=dist
npm run build && npx cap add android && npx cap sync android
cd android && ./gradlew lintDebug testDebugUnitTest assembleDebug
# artifact: android/app/build/outputs/apk/debug/app-debug.apk
```

Release requirements (per Android core app quality + V2 §18): HTTPS-only
API origin, tokens in platform secure storage (not WebView localStorage),
deep-link allowlist, minimal permissions requested at point of use, back/
keyboard/safe-area handling (the PWA layout already handles safe areas),
adaptive icons (the maskable icons ship already), and CI jobs for lint,
unit tests, and `assembleDebug` with the APK as an artifact. Never commit
keystores or signing credentials.

Do not claim device validation until it has actually run on hardware.
