// Versions are declared lazily in settings.pluginManagement. Loading Kotlin
// alone into the root classloader prevents the Android target from seeing
// AGP's BaseVariant. Each module resolves its own coherent plugin classpath;
// SDK-less core builds still do not resolve Google's Android plugins.
