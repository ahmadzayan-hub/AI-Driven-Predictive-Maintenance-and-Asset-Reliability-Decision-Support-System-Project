// Plugin versions live in the module build files: the Android plugins
// resolve from Google's repository, which the core module never needs.
plugins {
    kotlin("jvm") version "2.1.20" apply false
    kotlin("plugin.serialization") version "2.1.20" apply false
}
