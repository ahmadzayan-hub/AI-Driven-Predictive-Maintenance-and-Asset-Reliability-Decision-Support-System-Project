package com.assetreliability.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.assetreliability.app.data.MemoryRepository
import com.assetreliability.app.data.OkHttpTransport
import com.assetreliability.app.data.PlatformRepository
import com.assetreliability.app.data.Settings
import com.assetreliability.app.ui.components.Muted
import com.assetreliability.app.ui.t
import com.assetreliability.core.api.AssetReliabilityClient
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ChatLine(val mine: Boolean, val text: String, val source: String? = null)

/** The platform's assistant, through its session API, with the phone's
 *  own memory shown beside each question as context the person can see.
 *  Memory is never sent on its own: the person chooses what to ask. */
@HiltViewModel
class AssistantViewModel @Inject constructor(
    private val platform: PlatformRepository,
    private val transport: OkHttpTransport,
    private val settings: Settings,
    private val memory: MemoryRepository,
) : ViewModel() {
    val lines = MutableStateFlow<List<ChatLine>>(emptyList())
    val context = MutableStateFlow(0)
    val readOnly = MutableStateFlow(false)
    val busy = MutableStateFlow(false)
    private var sessionId: String? = null

    init { viewModelScope.launch { readOnly.value = runCatching { platform.isReadOnly() }.getOrDefault(false) } }

    private suspend fun client(): AssetReliabilityClient {
        val current = settings.current()
        return AssetReliabilityClient(transport, current.serverUrl) { current.token }
    }

    fun send(text: String) = viewModelScope.launch {
        if (text.isBlank() || busy.value) return@launch
        busy.value = true
        lines.value = lines.value + ChatLine(true, text)
        context.value = memory.recall(text, 3).size
        try {
            val api = client()
            val id = sessionId ?: api.createSession(settings.current().language).sessionId.also { sessionId = it }
            val reply = api.sendMessage(id, text).reply
            lines.value = lines.value + ChatLine(false, reply.text, reply.source)
        } catch (e: Exception) {
            lines.value = lines.value + ChatLine(false, e.message ?: e.toString(), "error")
        } finally { busy.value = false }
    }
}

@Composable
fun AssistantScreen(onBack: () -> Unit, viewModel: AssistantViewModel = hiltViewModel()) {
    val lines by viewModel.lines.collectAsStateWithLifecycle()
    val context by viewModel.context.collectAsStateWithLifecycle()
    val readOnly by viewModel.readOnly.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()
    var draft by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Row { TextButton(onClick = onBack) { Text(t("common.back")) }; Text(t("assistant.title"), style = MaterialTheme.typography.headlineMedium) }
        if (readOnly) Muted(t("assistant.demo"))
        if (context > 0) Muted(t("assistant.context", "n" to context))
        LazyColumn(Modifier.weight(1f).fillMaxWidth()) {
            items(lines) { line ->
                Text(line.text, style = if (line.mine) MaterialTheme.typography.titleMedium else MaterialTheme.typography.bodyLarge,
                    color = if (line.source == "error") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.padding(vertical = 6.dp))
                line.source?.takeIf { it != "error" }?.let { Muted(it) }
            }
        }
        OutlinedTextField(draft, { draft = it }, label = { Text(t("assistant.hint")) }, modifier = Modifier.fillMaxWidth(), enabled = !readOnly)
        Spacer(Modifier.height(8.dp))
        Button(onClick = { viewModel.send(draft); draft = "" }, enabled = !readOnly && !busy && draft.isNotBlank()) { Text(t("assistant.send")) }
    }
}
