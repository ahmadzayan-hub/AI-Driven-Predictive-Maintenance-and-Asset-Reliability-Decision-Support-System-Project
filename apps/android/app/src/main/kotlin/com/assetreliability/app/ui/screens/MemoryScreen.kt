package com.assetreliability.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.item
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import com.assetreliability.app.data.Settings
import com.assetreliability.app.ui.components.Muted
import com.assetreliability.app.ui.components.RisingCard
import com.assetreliability.app.ui.components.SectionTitle
import com.assetreliability.app.ui.t
import com.assetreliability.core.memory.MemoryRecord
import com.assetreliability.core.memory.Recall
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class MemoryViewModel @Inject constructor(
    private val memory: MemoryRepository,
    private val settings: Settings,
) : ViewModel() {
    val notes = MutableStateFlow<List<MemoryRecord>>(emptyList())
    val recalled = MutableStateFlow<List<Recall>?>(null)
    val embedder: String get() = memory.embedderName

    init { refresh() }

    fun refresh() = viewModelScope.launch { notes.value = memory.all() }
    fun add(text: String) = viewModelScope.launch {
        if (text.isBlank()) return@launch
        memory.remember(text, "note", null, settings.current().language); refresh()
    }
    fun forget(id: String) = viewModelScope.launch { memory.forget(id); refresh(); recalled.value = null }
    fun recall(query: String) = viewModelScope.launch { recalled.value = if (query.isBlank()) null else memory.recall(query, 5) }
}

@Composable
fun MemoryScreen(onAssistant: () -> Unit, viewModel: MemoryViewModel = hiltViewModel()) {
    val notes by viewModel.notes.collectAsStateWithLifecycle()
    val recalled by viewModel.recalled.collectAsStateWithLifecycle()
    var draft by remember { mutableStateOf("") }
    var query by remember { mutableStateOf("") }

    LazyColumn(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        item {
            Spacer(Modifier.height(16.dp))
            Text(t("memory.title"), style = MaterialTheme.typography.headlineMedium)
            Muted(t("memory.subtitle", "embedder" to viewModel.embedder), Modifier.padding(bottom = 12.dp))
            RisingCard(0) {
                SectionTitle(t("memory.search"))
                OutlinedTextField(query, { query = it }, label = { Text(t("memory.query")) }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
                    Button(onClick = { viewModel.recall(query) }) { Text(t("memory.search")) }
                    OutlinedButton(onClick = onAssistant) { Text(t("assistant.title")) }
                }
                recalled?.forEach { hit ->
                    Text(hit.record.text, modifier = Modifier.padding(top = 8.dp))
                    Muted(t("memory.score", "score" to "%.2f".format(hit.score)) + " · " + hit.record.createdAt.take(10))
                }
            }
            RisingCard(1) {
                SectionTitle(t("memory.add"))
                OutlinedTextField(draft, { draft = it }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                Button(onClick = { viewModel.add(draft); draft = "" }, enabled = draft.isNotBlank(), modifier = Modifier.padding(top = 8.dp)) { Text(t("memory.save")) }
            }
        }
        if (notes.isEmpty()) item { Muted(t("memory.none")) }
        items(notes, key = { it.id }) { note ->
            RisingCard(2) {
                Text(note.text)
                Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                    Muted(note.kind + " · " + note.createdAt.take(10))
                    TextButton(onClick = { viewModel.forget(note.id) }) { Text(t("memory.forget")) }
                }
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}
