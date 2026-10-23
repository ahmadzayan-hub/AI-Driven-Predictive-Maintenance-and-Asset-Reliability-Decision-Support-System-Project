#!/usr/bin/env bash
# Build the Android app (apps/android) into an installable APK.
#
#   scripts/build-apk.sh                 # debug APK, installable on a phone with
#                                        # "install unknown apps" allowed
#   scripts/build-apk.sh release         # signed release APK; needs the four
#                                        # KEYSTORE_* variables below
#   SERVER_URL=https://your-host scripts/build-apk.sh
#
# Needs: JDK 17 or 21, the Android SDK (ANDROID_HOME or a local.properties
# with sdk.dir) and network access to dl.google.com and Maven Central. The
# core module alone needs neither the SDK nor Google's repository:
#   (cd apps/android && ./gradlew :core:test)
#
# Release signing is never in the repository: set KEYSTORE_PATH,
# KEYSTORE_PASSWORD, KEY_ALIAS and KEY_PASSWORD in the environment.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
project="$here/apps/android"
variant="${1:-debug}"
server="${SERVER_URL:-}"

if [ -z "${ANDROID_HOME:-}" ] && [ -z "${ANDROID_SDK_ROOT:-}" ] && [ ! -f "$project/local.properties" ]; then
  echo "The Android SDK was not found. Set ANDROID_HOME, or write sdk.dir=... to apps/android/local.properties." >&2
  echo "The core module can still be built and tested: (cd apps/android && ./gradlew :core:test)" >&2
  exit 2
fi

cd "$project"
args=()
[ -n "$server" ] && args+=("-PserverUrl=$server")

case "$variant" in
  debug)
    ./gradlew :core:test :app:testDebugUnitTest :app:lintDebug :app:assembleDebug "${args[@]}"
    out="app/build/outputs/apk/debug/app-debug.apk"
    ;;
  release)
    : "${KEYSTORE_PATH:?set KEYSTORE_PATH}" "${KEYSTORE_PASSWORD:?set KEYSTORE_PASSWORD}" \
      "${KEY_ALIAS:?set KEY_ALIAS}" "${KEY_PASSWORD:?set KEY_PASSWORD}"
    ./gradlew :core:test :app:testReleaseUnitTest :app:assembleRelease "${args[@]}"
    out="app/build/outputs/apk/release/app-release.apk"
    ;;
  *)
    echo "usage: $0 [debug|release]" >&2; exit 2 ;;
esac

echo
echo "APK: $project/$out"
echo "Install: adb install -r $project/$out   (or copy the file to the phone and open it)"
