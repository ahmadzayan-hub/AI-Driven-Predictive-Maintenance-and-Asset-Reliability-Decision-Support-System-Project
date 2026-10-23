pluginManagement {
    plugins {
        id("org.jetbrains.kotlin.jvm") version "2.1.20"
        id("org.jetbrains.kotlin.android") version "2.1.20"
        id("org.jetbrains.kotlin.plugin.serialization") version "2.1.20"
        id("org.jetbrains.kotlin.plugin.compose") version "2.1.20"
        id("com.android.application") version "8.9.1"
        id("com.google.devtools.ksp") version "2.1.20-1.0.32"
        id("com.google.dagger.hilt.android") version "2.56.1"
    }
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
