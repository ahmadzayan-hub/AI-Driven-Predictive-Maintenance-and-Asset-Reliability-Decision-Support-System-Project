package com.assetreliability.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.assetreliability.app.BuildConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.store: DataStore<Preferences> by preferencesDataStore("settings")

data class AppSettings(
    val serverUrl: String,
    val language: String,
    /** A bearer token for a signed-in workspace; null for the demo. Stored
     *  on the device only, never logged. */
    val token: String?,
)

/** Server address, language and the sign-in token, on the device. */
@Singleton
class Settings @Inject constructor(@ApplicationContext private val context: Context) {
    private val serverKey = stringPreferencesKey("server_url")
    private val languageKey = stringPreferencesKey("language")
    private val tokenKey = stringPreferencesKey("token")

    val flow: Flow<AppSettings> = context.store.data.map { prefs ->
        AppSettings(
            serverUrl = prefs[serverKey] ?: BuildConfig.DEFAULT_SERVER_URL,
            language = prefs[languageKey] ?: "en",
            token = prefs[tokenKey],
        )
    }

    suspend fun current(): AppSettings = flow.first()

    /** One connection revision: never expose a new host with the old token. */
    suspend fun save(server: String, language: String, token: String?) = context.store.edit {
        it[serverKey] = server.trim().trimEnd('/')
        it[languageKey] = if (language == "ar") "ar" else "en"
        if (token.isNullOrBlank()) it.remove(tokenKey) else it[tokenKey] = token.trim()
    }

    suspend fun setServerUrl(url: String) = context.store.edit { it[serverKey] = url.trim().trimEnd('/') }
    suspend fun setLanguage(language: String) = context.store.edit { it[languageKey] = language }
    suspend fun setToken(token: String?) = context.store.edit {
        if (token.isNullOrBlank()) it.remove(tokenKey) else it[tokenKey] = token.trim()
    }
}
