package com.assetreliability.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
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
import com.assetreliability.app.ui.t
import com.assetreliability.core.api.RunDetail
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/** The human gate, on the phone. Approve is enabled only after the report
 *  has been opened and the person has said they read it (assessment
 *  finding U3, applied here first). */
@HiltViewModel
class ApprovalsViewModel @Inject constructor(private val platform: PlatformRepository) : ViewModel() {
    val waiting = MutableStateFlow<List<RunDetail>?>(null)
    val error = MutableStateFlow<String?>(null)
    val readOnly = MutableStateFlow(false)
    val opened = MutableStateFlow<String?>(null)
    val read = MutableStateFlow(false)
    val busy = MutableStateFlow(false)
    val result = MutableStateFlow<RunDetail?>(null)

    init { refresh() }

    fun refresh() = viewModelScope.launch {
        error.value = null
        try {
            readOnly.value = runCatching { platform.isReadOnly() }.getOrDefault(false)
            val summaries = platform.runs("awaiting_approval").sortedBy { it.createdAt }
            waiting.value = summaries.map { platform.run(it.id) }
        } catch (e: Exception) { error.value = e.message ?: e.toString() }
    }

    fun open(runId: String) { opened.value = if (opened.value == runId) null else runId; read.value = false }

    fun decide(run: RunDetail, approve: Boolean) = viewModelScope.launch {
        if (busy.value || readOnly.value || (approve && (!read.value || opened.value != run.id || run.report == null))) return@launch
        val approval = run.approvals.firstOrNull { it.state == "pending" } ?: return@launch
        busy.value = true
        try { result.value = platform.decide(run.id, approval.id, approve); opened.value = null; read.value = false; refresh() }
        catch (e: Exception) { error.value = e.message ?: e.toString() }
        finally { busy.value = false }
    }
}

@Composable
fun ApprovalsScreen(viewModel: ApprovalsViewModel = hiltViewModel()) {
    val waiting by viewModel.waiting.collectAsStateWithLifecycle()
    val error by viewModel.error.collectAsStateWithLifecycle()
    val readOnly by viewModel.readOnly.collectAsStateWithLifecycle()
    val opened by viewModel.opened.collectAsStateWithLifecycle()
    val read by viewModel.read.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()
    val result by viewModel.result.collectAsStateWithLifecycle()

    LazyColumn(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        item {
            Spacer(Modifier.height(16.dp))
            Text(t("approvals.title"), style = MaterialTheme.typography.headlineMedium)
            Muted(t("approvals.gate"), Modifier.padding(bottom = 12.dp))
            if (readOnly) Muted(t("approvals.demo"), Modifier.padding(bottom = 12.dp))
            result?.let { decided ->
                val path = decided.report?.publishedPath
                Text(if (decided.state == "completed" && !path.isNullOrBlank())
                    t("approvals.published", "path" to path) else t("approvals.recorded"))
            }
        }
        when {
            error != null -> item { ErrorState(error!!) { viewModel.refresh() } }
            waiting == null -> item { Loading() }
            waiting!!.isEmpty() -> item { Muted(t("approvals.none")) }
            else -> items(waiting!!, key = { it.id }) { run ->
                RisingCard(0) {
                    Text(run.goal, style = MaterialTheme.typography.titleMedium)
                    Muted(run.datasetName + " · " + run.updatedAt.take(10))
                    val report = run.report
                    val approval = run.approvals.firstOrNull { it.state == "pending" }
                    OutlinedButton(onClick = { viewModel.open(run.id) }, modifier = Modifier.padding(top = 8.dp)) { Text(t("approvals.open")) }
                    if (opened == run.id) {
                        Column(Modifier.padding(top = 8.dp)) {
                            run.reports.filter { it.headline.isNotBlank() }.forEach { Text("• " + it.headline, modifier = Modifier.padding(vertical = 2.dp)) }
                            report?.let {
                                Text(t("approvals.artifact", "name" to it.name, "version" to it.version))
                                Text(it.content, modifier = Modifier.padding(top = 8.dp))
                            } ?: Muted(t("approvals.reportMissing"))
                            approval?.let {
                                Muted(t("approvals.destination", "target" to it.target))
                                Muted(t("approvals.impact", "risk" to it.risk, "impact" to it.impact, "reversibility" to it.reversibility))
                            }
                        }
                        if (!readOnly) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Checkbox(read, { viewModel.read.value = it }); Text(t("approvals.read"))
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(onClick = { viewModel.decide(run, true) }, enabled = read && !busy && report != null && approval != null) { Text(t("approvals.approve")) }
                                OutlinedButton(onClick = { viewModel.decide(run, false) }, enabled = !busy) { Text(t("approvals.reject")) }
                            }
                        }
                    }
                }
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }
}
