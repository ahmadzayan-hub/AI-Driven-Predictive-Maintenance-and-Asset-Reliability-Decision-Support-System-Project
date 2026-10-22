package com.assetreliability.app.ui.screens

import android.content.Intent
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import com.assetreliability.app.data.PlatformRepository
import com.assetreliability.app.data.Settings
import com.assetreliability.app.ui.components.ErrorState
import com.assetreliability.app.ui.components.Loading
import com.assetreliability.app.ui.components.ToneBadge
import com.assetreliability.app.ui.t
import com.assetreliability.app.ui.theme.Tokens
import com.assetreliability.core.api.ExecutiveBrief
import com.assetreliability.core.decision.CommandCentre
import com.assetreliability.core.decision.DecisionSupport
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch
import java.io.File
import javax.inject.Inject

@HiltViewModel
class PresentationViewModel @Inject constructor(
    private val platform: PlatformRepository,
    private val settings: Settings,
) : ViewModel() {
    val state = MutableStateFlow<BriefState>(BriefState.Loading)
    val exporting = MutableStateFlow(false)
    val exported = MutableStateFlow<File?>(null)
    val error = MutableStateFlow<String?>(null)

    fun load(runId: String) = viewModelScope.launch {
        if (state.value is BriefState.Ready) return@launch
        try {
            val brief = platform.executive(runId)
            state.value = BriefState.Ready(brief, DecisionSupport.from(brief, settings.current().language))
        } catch (e: Exception) { state.value = BriefState.Failed(e.message ?: e.toString()) }
    }

    fun export(brief: ExecutiveBrief, format: String) = viewModelScope.launch {
        exporting.value = true; error.value = null
        try { exported.value = platform.exportExecutive(brief, format) }
        catch (e: Exception) { error.value = e.message ?: e.toString() }
        finally { exporting.value = false }
    }
}

/** A slide per question, on the navy ground, one message per slide, with
 *  a horizontal slide between them. The words are the brief's own. */
private fun slides(c: CommandCentre, tr: (String, Map<String, Any?>) -> String): List<Pair<String, List<String>>> = listOf(
    tr("command.latest", emptyMap()) to listOf(c.recommendation, tr("command.scope", mapOf("records" to c.records, "measures" to c.measureCount))),
    tr("command.decisions", emptyMap()) to c.decisions.map { "${it.title} · ${it.owner}" }.ifEmpty { listOf(tr("command.decisionsNone", emptyMap())) },
    tr("command.kpis", emptyMap()) to c.measures.map { "${it.title}: ${it.value ?: "—"} ${it.unit}".trim() }.ifEmpty { listOf(tr("command.kpisNone", emptyMap())) },
    tr("command.models", emptyMap()) to c.models.map { it.target + " · " + tr("command.model." + it.tone.name.lowercase(), emptyMap()) }.ifEmpty { listOf(tr("command.modelsNone", emptyMap())) },
    tr("command.action", emptyMap()) to listOfNotNull(c.recommendedAction ?: tr("command.actionNone", emptyMap()), c.assumption),
    tr("command.questions", emptyMap()) to c.questions,
)

@Composable
fun PresentationScreen(runId: String, onBack: () -> Unit, viewModel: PresentationViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val exporting by viewModel.exporting.collectAsStateWithLifecycle()
    val exported by viewModel.exported.collectAsStateWithLifecycle()
    val error by viewModel.error.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val translator = com.assetreliability.app.ui.LocalTranslator.current
    androidx.compose.runtime.LaunchedEffect(runId) { viewModel.load(runId) }
    androidx.compose.runtime.LaunchedEffect(exported) {
        exported?.let { file ->
            val uri = FileProvider.getUriForFile(context, context.packageName + ".files", file)
            val type = if (file.extension == "docx") "application/vnd.openxmlformats-officedocument.wordprocessingml.document" else "text/html"
            context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                this.type = type; putExtra(Intent.EXTRA_STREAM, uri); addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }, null))
        }
    }

    Box(Modifier.fillMaxSize().background(Tokens.Navy)) {
        when (val current = state) {
            BriefState.Loading, BriefState.NoRuns -> Loading()
            is BriefState.Failed -> ErrorState(current.message, onBack)
            is BriefState.Ready -> {
                val deck = remember(current) { slides(current.centre) { key, vars -> translator(key, vars) } }
                var index by remember { mutableIntStateOf(0) }
                Column(Modifier.fillMaxSize().padding(24.dp)) {
                    Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                        TextButton(onClick = onBack) { Text(t("common.back"), color = Tokens.DarkTeal) }
                        Text(t("present.slide", "n" to index + 1, "total" to deck.size), color = Color(0xFFA7B4C6))
                    }
                    AnimatedContent(targetState = index, label = "slide", transitionSpec = {
                        val forward = targetState > initialState
                        (slideInHorizontally(tween(320)) { if (forward) it / 3 else -it / 3 } + fadeIn(tween(260)))
                            .togetherWith(slideOutHorizontally(tween(260)) { if (forward) -it / 3 else it / 3 } + fadeOut(tween(200)))
                    }, modifier = Modifier.weight(1f)) { slide ->
                        val (title, lines) = deck[slide]
                        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(vertical = 24.dp), verticalArrangement = Arrangement.Center) {
                            Text(title.uppercase(), style = MaterialTheme.typography.labelSmall, color = Tokens.DarkTeal)
                            Spacer(Modifier.height(12.dp))
                            lines.forEachIndexed { i, line ->
                                Text(line, style = if (i == 0 && slide == 0) MaterialTheme.typography.headlineMedium else MaterialTheme.typography.titleLarge,
                                    color = Tokens.DarkText, modifier = Modifier.padding(vertical = 6.dp))
                            }
                            if (slide == 0) ToneBadge(when (current.centre.readiness) { "ready" -> com.assetreliability.core.decision.Tone.GOOD; "limited" -> com.assetreliability.core.decision.Tone.OKAY; else -> com.assetreliability.core.decision.Tone.UNAVAILABLE },
                                t("command.readiness." + current.centre.readiness))
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        OutlinedButton(onClick = { if (index > 0) index-- }, enabled = index > 0) { Text(t("present.previous")) }
                        Button(onClick = { if (index < deck.size - 1) index++ }, enabled = index < deck.size - 1) { Text(t("present.next")) }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
                        TextButton(onClick = { viewModel.export(current.brief, "html") }, enabled = !exporting) { Text(t("present.export.html"), color = Tokens.DarkTeal) }
                        TextButton(onClick = { viewModel.export(current.brief, "docx") }, enabled = !exporting) { Text(t("present.export.docx"), color = Tokens.DarkTeal) }
                    }
                    if (exporting) Text(t("present.exporting"), color = Color(0xFFA7B4C6))
                    error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    }
}
