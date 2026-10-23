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

## Native Android: built in hosted CI, 23 October 2026

`apps/android` is the existing Kotlin/Compose client over the same platform API.
The hosted [Android build](https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/39935735248)
compiles Compose, runs core/app tests and lint, and assembles a debug APK.
The artifact is `asset-reliability-android-debug`; unzip it and locate
`app/build/outputs/apk/debug/app-debug.apk`. Source, screens and build commands
are in [the app guide](../apps/android/README.md). Exact verification counts
are maintained in [README](../README.md#testing).

The raw upload and response contracts match FastAPI. The approval screen shows
the complete report artifact/version, destination and impact. Publication needs
server confirmation and a returned path. Changed destinations require a fresh
review and a new read confirmation; refresh never publishes. Worker-backed runs poll the server;
client-backed runs retain the existing bounded stepping behavior.

## Device and release acceptance

The successful debug APK is a build artifact. Physical installation, TalkBack,
large text, rotation, background/process recovery, account switching and live
managed sign-in remain device checks. Production needs reviewed secure token
storage, an actual HTTPS API, release signing outside Git and the applicable
store target-SDK/privacy review. No production keystore, store submission or
production deployment is performed here.

Windows and iOS use the existing PWA. Platform browser jobs exercise Edge on
Windows and WebKit on macOS; they do not establish physical iPhone/iPad or
installed-PWA acceptance. See [the platform handoff](implementation/PLATFORM_RELEASE.md).
