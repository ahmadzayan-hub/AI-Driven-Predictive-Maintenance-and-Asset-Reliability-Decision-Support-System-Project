package com.assetreliability.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.assetreliability.app.data.MemoryRepository
import com.assetreliability.app.data.PlatformRepository
import com.assetreliability.app.data.Settings
import com.assetreliability.app.ui.components.ErrorState
import com.assetreliability.app.ui.components.Loading
import com.assetreliability.app.ui.components.Muted
import com.assetreliability.app.ui.components.RisingCard
import com.assetreliability.app.ui.components.SectionTitle
import com.assetreliability.app.ui.components.ToneBadge
import com.assetreliability.app.ui.t
import com.assetreliability.core.api.ExecutiveBrief
import com.assetreliability.core.decision.CommandCentre
import com.assetreliability.core.decision.DecisionSupport
import com.assetreliability.core.decision.Tone
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface BriefState {
    data object Loading : BriefState
    data object NoRuns : BriefState
    data class Failed(val message: String) : BriefState
    data class Ready(val brief: ExecutiveBrief, val centre: CommandCentre) : BriefState
}

/** Loads the latest analysis that has findings, then its decision brief.
 *  The same rule as the web Command Centre: finished or awaiting approval,
 *  most recently updated first. */
@HiltViewModel
class CommandCentreViewModel @Inject constructor(
    private val platform: PlatformRepository,
    private val memory: MemoryRepository,
    private val settings: Settings,
) : ViewModel() {
    val state = MutableStateFlow<BriefState>(BriefState.Loading)
    val remembered = MutableStateFlow(false)

    init { load() }

    fun load() = viewModelScope.launch {
        state.value = BriefState.Loading
        remembered.value = false
        try {
            val runs = platform.runs()
            val source = runs.filter { it.state in setOf("completed", "partially_completed", "awaiting_approval") }
                .maxByOrNull { it.updatedAt }
            if (source == null) { state.value = BriefState.NoRuns; return@launch }
            val brief = platform.executive(source.id)
            state.value = BriefState.Ready(brief, DecisionSupport.from(brief, settings.current().language))
        } catch (error: Exception) {
            state.value = BriefState.Failed(error.message ?: error.toString())
        }
    }

    /** Keeps the brief's words on the phone: the recommendation, the
     *  decisions and the questions, never a figure the server did not state. */
    fun remember() = viewModelScope.launch {
        val ready = state.value as? BriefState.Ready ?: return@launch
        val centre = ready.centre
        val text = buildString {
            append(centre.recommendation).append('\n')
            centre.decisions.forEach { append("- ").append(it.title).append(": ").append(it.owner).append('\n') }
            centre.questions.forEach { append("? ").append(it).append('\n') }
        }
        memory.remember(text, "brief", centre.runId, settings.current().language)
        remembered.value = true
    }
}

@Composable
fun CommandCentreScreen(onPresent: (String) -> Unit, viewModel: CommandCentreViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val remembered by viewModel.remembered.collectAsStateWithLifecycle()
    LazyColumn(Modifier.fillMaxWidth().padding(horizontal = 16.dp)) {
        item {
            Spacer(Modifier.height(16.dp))
            Text(t("command.title"), style = MaterialTheme.typography.headlineMedium)
            Muted(t("command.subtitle"), Modifier.padding(bottom = 12.dp))
        }
        when (val current = state) {
            BriefState.Loading -> item { Loading() }
            BriefState.NoRuns -> item { Muted(t("command.noRuns")) }
            is BriefState.Failed -> item { ErrorState(t("command.failed") + " " + current.message) { viewModel.load() } }
            is BriefState.Ready -> {
                val c = current.centre
                item {
                    RisingCard(0) {
                        Text(t("command.latest") + " · " + c.datasetName, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                        Text(c.recommendation, style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(vertical = 8.dp))
                        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            ToneBadge(when (c.readiness) { "ready" -> Tone.GOOD; "limited" -> Tone.OKAY; else -> Tone.UNAVAILABLE }, t("command.readiness." + c.readiness))
                            Muted(t("command.scope", "records" to c.records, "measures" to c.measureCount))
                        }
                        c.asOf?.let { Muted(t("command.asOf", "date" to it.take(10))) }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 12.dp)) {
                            Button(onClick = { onPresent(c.runId) }) { Text(t("command.present")) }
                            OutlinedButton(onClick = { viewModel.remember() }, enabled = !remembered) {
                                Text(if (remembered) t("command.remembered") else t("command.remember"))
                            }
                        }
                    }
                }
                item {
                    RisingCard(1) {
                        SectionTitle(t("command.decisions"), c.decisions.size)
                        if (c.decisions.isEmpty()) Muted(t("command.decisionsNone"))
                        c.decisions.forEachIndexed { index, decision ->
                            if (index > 0) HorizontalDivider(Modifier.padding(vertical = 8.dp))
                            Text("${index + 1}. ${decision.title}", style = MaterialTheme.typography.titleMedium)
                            Muted(decision.detail)
                            if (decision.owner.isNotBlank()) Muted(t("command.owner") + ": " + decision.owner + " · " + t("command.gate") + ": " + decision.gate)
                        }
                    }
                }
                item {
                    RisingCard(2) {
                        SectionTitle(t("command.kpis"))
                        if (c.measures.isEmpty()) Muted(t("command.kpisNone"))
                        c.measures.forEach { tile ->
                            Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Muted(tile.title)
                                    Text((tile.value ?: "—") + if (tile.value != null && tile.unit.isNotEmpty()) " " + tile.unit else "",
                                        style = MaterialTheme.typography.titleLarge)
                                    tile.reason?.let { Muted(it) }
                                }
                                ToneBadge(tile.tone)
                            }
                        }
                        if (c.unavailableMeasures > 0) Muted(t("command.unavailable", "n" to c.unavailableMeasures), Modifier.padding(top = 8.dp))
                    }
                }
                item {
                    RisingCard(3) {
                        SectionTitle(t("command.models"))
                        if (c.models.isEmpty()) Muted(t("command.modelsNone"))
                        c.models.forEach { model ->
                            Column(Modifier.padding(vertical = 4.dp)) {
                                Text(model.target, style = MaterialTheme.typography.bodyMedium)
                                ToneBadge(model.tone, t("command.model." + model.tone.name.lowercase()))
                                model.reason?.let { Muted(it) }
                            }
                        }
                        c.prediction?.let { Muted(it, Modifier.padding(top = 8.dp)) }
                    }
                }
                item {
                    RisingCard(4) {
                        SectionTitle(t("command.action"))
                        if (c.recommendedAction == null) Muted(t("command.actionNone")) else {
                            Text(c.recommendedAction)
                            c.assumption?.let { Muted(it, Modifier.padding(top = 6.dp)) }
                            Muted(t("command.actionNote"), Modifier.padding(top = 8.dp))
                        }
                    }
                }
                item {
                    RisingCard(5) {
                        SectionTitle(t("command.quality"))
                        Text(c.dataQuality ?: t("command.qualityNone"))
                        if (c.failedChecks > 0) Text(t("command.failedChecks", "n" to c.failedChecks), color = MaterialTheme.colorScheme.tertiary, modifier = Modifier.padding(top = 6.dp))
                        if (c.limitations.isNotEmpty()) {
                            Text(t("command.limitations", "n" to c.limitations.size), style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 8.dp))
                            c.limitations.forEach { Muted("• $it") }
                        }
                    }
                }
                item {
                    RisingCard(6) {
                        SectionTitle(t("command.questions"))
                        c.questions.forEach { Text("• $it", modifier = Modifier.padding(vertical = 2.dp)) }
                    }
                    Spacer(Modifier.height(24.dp))
                }
            }
        }
    }
}
