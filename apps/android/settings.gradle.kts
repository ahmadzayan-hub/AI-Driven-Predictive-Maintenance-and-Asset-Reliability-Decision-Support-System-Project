pluginManagement {
    repositories {
        gradlePluginPortal()
        google()
        mavenCentral()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "asset-reliability-android"
include(":core")
// The Android module needs Google's repository (dl.google.com). It is
// included only when the Android SDK is present, so the pure-Kotlin core
// builds and tests anywhere; see README.md.
if (System.getenv("ANDROID_HOME") != null || System.getenv("ANDROID_SDK_ROOT") != null || File(rootDir, "local.properties").exists()) {
    include(":app")
}
