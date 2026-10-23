package com.assetreliability.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.assetreliability.app.data.AppSettings
import com.assetreliability.app.data.PlatformRepository
import com.assetreliability.app.data.Settings
import com.assetreliability.app.ui.components.Muted
import com.assetreliability.app.ui.t
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val store: Settings,
    private val platform: PlatformRepository,
) : ViewModel() {
    val settings: StateFlow<AppSettings?> = store.flow.stateIn(viewModelScope, SharingStarted.Eagerly, null)
    val check = MutableStateFlow<Pair<Boolean, Map<String, String>>?>(null)

    fun save(server: String, language: String, token: String) = viewModelScope.launch {
        store.setServerUrl(server); store.setLanguage(language); store.setToken(token)
    }

    fun checkConnection() = viewModelScope.launch {
        check.value = try {
            val health = platform.health()
            val mode = runCatching { platform.authMode() }.getOrDefault("unknown")
            true to mapOf("name" to health.agentName, "version" to health.version, "mode" to mode)
        } catch (error: Exception) {
            false to mapOf("reason" to (error.message ?: error.toString()))
        }
    }
}

@Composable
fun SettingsScreen(viewModel: SettingsViewModel = hiltViewModel()) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val check by viewModel.check.collectAsStateWithLifecycle()
    var server by remember { mutableStateOf("") }
    var language by remember { mutableStateOf("en") }
    var token by remember { mutableStateOf("") }
    LaunchedEffect(settings) { settings?.let { server = it.serverUrl; language = it.language; token = it.token ?: "" } }

    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(t("settings.title"), style = MaterialTheme.typography.headlineMedium)
        OutlinedTextField(server, { server = it }, label = { Text(t("settings.server")) }, singleLine = true, modifier = Modifier.fillMaxWidth())
        Text(t("settings.language"), style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = language == "en", onClick = { language = "en" }, label = { Text(t("settings.english")) })
            FilterChip(selected = language == "ar", onClick = { language = "ar" }, label = { Text(t("settings.arabic")) })
        }
        OutlinedTextField(token, { token = it }, label = { Text(t("settings.token")) }, singleLine = true,
            visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
        Muted(t("settings.tokenHelp"))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { viewModel.save(server, language, token) }) { Text(t("settings.save")) }
            OutlinedButton(onClick = { viewModel.checkConnection() }) { Text(t("settings.check")) }
        }
        check?.let { (ok, vars) ->
            Text(if (ok) t("settings.ok", *vars.toList().toTypedArray()) else t("settings.failed", *vars.toList().toTypedArray()),
                color = if (ok) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error)
        }
    }
}
