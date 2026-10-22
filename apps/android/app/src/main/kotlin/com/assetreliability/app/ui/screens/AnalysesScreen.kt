package com.assetreliability.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.item
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.assetreliability.app.data.PlatformRepository
import com.assetreliability.app.ui.components.ErrorState
import com.assetreliability.app.ui.components.Loading
import com.assetreliability.app.ui.components.Muted
import com.assetreliability.app.ui.components.RisingCard
import com.assetreliability.app.ui.components.SectionTitle
import com.assetreliability.app.ui.t
import com.assetreliability.core.api.RunDetail
import com.assetreliability.core.api.RunSummary
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface NewRunState {
    data object Idle : NewRunState
    data object Uploading : NewRunState
    data class Running(val done: Int, val total: Int, val stage: String) : NewRunState
    data class Finished(val run: RunDetail) : NewRunState
    data class Failed(val reason: String) : NewRunState
}

/** The upload and analysis journey: pick a file, upload it as a stored
 *  dataset, start a governed run, advance it stage by stage until it
 *  waits at the approval gate. The phone drives the run the way the
 *  browser does (client execution); a worker-backed server advances it
 *  on its own and the phone only polls. */
@HiltViewModel
class AnalysesViewModel @Inject constructor(private val platform: PlatformRepository) : ViewModel() {
    val runs = MutableStateFlow<List<RunSummary>?>(null)
    val error = MutableStateFlow<String?>(null)
    val readOnly = MutableStateFlow(false)
    val newRun = MutableStateFlow<NewRunState>(NewRunState.Idle)

    init { refresh() }

    fun refresh() = viewModelScope.launch {
        error.value = null
        try {
            readOnly.value = runCatching { platform.isReadOnly() }.getOrDefault(false)
            runs.value = platform.runs().sortedByDescending { it.updatedAt }
        } catch (e: Exception) { error.value = e.message ?: e.toString() }
    }

    fun start(uri: Uri, goal: String, maintenance: Boolean) = viewModelScope.launch {
        newRun.value = NewRunState.Uploading
        try {
            val dataset = platform.upload(uri)
            var run = platform.createRun(goal.ifBlank { "Analyse ${dataset.name}" }, dataset.id, if (maintenance) "maintenance" else null)
            var guard = 0
            while (run.state in setOf("queued", "running") && guard++ < 200) {
                val done = run.tasks.count { it.state == "succeeded" }
                val current = run.tasks.firstOrNull { it.state == "running" } ?: run.tasks.firstOrNull { it.state == "pending" }
                newRun.value = NewRunState.Running(done, run.tasks.size, current?.title ?: "")
                run = platform.advance(run.id)
                if (run.state in setOf("queued", "running")) delay(250)
            }
            newRun.value = if (run.state == "failed") NewRunState.Failed(run.error ?: run.state) else NewRunState.Finished(run)
            refresh()
        } catch (e: Exception) {
            newRun.value = NewRunState.Failed(e.message ?: e.toString())
        }
    }

    fun reset() { newRun.value = NewRunState.Idle }
}

@Composable
fun AnalysesScreen(viewModel: AnalysesViewModel = hiltViewModel()) {
    val runs by viewModel.runs.collectAsStateWithLifecycle()
    val error by viewModel.error.collectAsStateWithLifecycle()
    val readOnly by viewModel.readOnly.collectAsStateWithLifecycle()
    val newRun by viewModel.newRun.collectAsStateWithLifecycle()
    var picked by remember { mutableStateOf<Uri?>(null) }
    var pickedName by remember { mutableStateOf("") }
    var goal by remember { mutableStateOf("") }
    var maintenance by remember { mutableStateOf(true) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        picked = uri; pickedName = uri?.lastPathSegment?.substringAfterLast('/') ?: ""
    }

    LazyColumn(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        item {
            Spacer(Modifier.height(16.dp))
            Text(t("analyses.title"), style = MaterialTheme.typography.headlineMedium, modifier = Modifier.padding(bottom = 12.dp))
            RisingCard(0) {
                SectionTitle(t("analyses.new"))
                if (readOnly) Muted(t("analyses.demo")) else when (val state = newRun) {
                    NewRunState.Idle -> {
                        OutlinedButton(onClick = { picker.launch(arrayOf("text/*", "application/json", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream")) }) { Text(t("analyses.pick")) }
                        if (pickedName.isNotEmpty()) Muted(t("analyses.picked", "name" to pickedName))
                        OutlinedTextField(goal, { goal = it }, label = { Text(t("analyses.goal")) }, placeholder = { Text(t("analyses.goalHint")) },
                            modifier = Modifier.fillMaxWidth().padding(top = 8.dp), minLines = 2)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(maintenance, { maintenance = it }); Text(t("analyses.maintenance"))
                        }
                        Button(onClick = { picked?.let { viewModel.start(it, goal, maintenance) } }, enabled = picked != null) { Text(t("analyses.start")) }
                    }
                    NewRunState.Uploading -> Loading(t("analyses.uploading"))
                    is NewRunState.Running -> {
                        Text(t("analyses.running", "done" to state.done, "total" to state.total, "stage" to state.stage))
                        LinearProgressIndicator(progress = { if (state.total == 0) 0f else state.done.toFloat() / state.total }, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                    }
                    is NewRunState.Finished -> {
                        Text(if (state.run.state == "awaiting_approval") t("analyses.done") else t("analyses.completed"), style = MaterialTheme.typography.titleMedium)
                        state.run.reports.filter { it.headline.isNotBlank() }.forEach { Muted("• " + it.headline, Modifier.padding(top = 4.dp)) }
                        OutlinedButton(onClick = { viewModel.reset(); picked = null; pickedName = "" }, modifier = Modifier.padding(top = 8.dp)) { Text(t("analyses.new")) }
                    }
                    is NewRunState.Failed -> ErrorState(t("analyses.failed", "reason" to state.reason)) { viewModel.reset() }
                }
            }
        }
        when {
            error != null -> item { ErrorState(error!!) { viewModel.refresh() } }
            runs == null -> item { Loading() }
            runs!!.isEmpty() -> item { Muted(t("common.none")) }
            else -> items(runs!!, key = { it.id }) { run ->
                RisingCard(1) {
                    Text(run.goal, style = MaterialTheme.typography.titleMedium)
                    Muted(run.datasetName + " · " + t("analyses.state", "state" to run.state.replace('_', ' ')) + " · " + run.updatedAt.take(10))
                }
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}
