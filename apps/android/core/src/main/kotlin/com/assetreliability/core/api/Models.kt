package com.assetreliability.core.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement

/** The platform's JSON, read leniently: a field the app does not know is
 *  ignored, so an older app keeps working against a newer server. */
val ApiJson: Json = Json {
    ignoreUnknownKeys = true
    isLenient = true
    explicitNulls = false
    coerceInputValues = true
}

@Serializable
data class Health(
    val status: String,
    @SerialName("agent_name") val agentName: String = "",
    val version: String = "",
    @SerialName("model_map") val modelMap: Map<String, JsonElement> = emptyMap(),
)

@Serializable
data class AuthConfig(val mode: String = "local")

@Serializable
data class WorkspacePrincipal(val subject: String, val role: String)

@Serializable
data class WorkspaceIdentity(val mode: String, val principal: WorkspacePrincipal)

@Serializable
data class RunSummary(
    val id: String,
    val goal: String,
    @SerialName("dataset_name") val datasetName: String = "",
    val state: String,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
)

@Serializable
data class RunsPage(val runs: List<RunSummary> = emptyList())

@Serializable
data class RunApproval(
    val id: String,
    val action: String = "",
    val target: String = "",
    val risk: String = "",
    val impact: String = "",
    val reversibility: String = "",
    val state: String = "",
)

@Serializable
data class RunArtifact(
    val id: String, val name: String, val version: Int, val content: String,
    @SerialName("published_path") val publishedPath: String? = null,
)

@Serializable
data class RunTask(
    val id: String,
    val role: String,
    val title: String = "",
    val state: String = "",
    val summary: String? = null,
)

@Serializable
data class RunReport(
    val type: String,
    val question: String = "",
    val title: String = "",
    val headline: String = "",
    val content: String = "",
)

@Serializable
data class RunExecution(val mode: String = "client", @SerialName("poll_after_ms") val pollAfterMs: Long = 2500)

@Serializable
data class RunDetail(
    val id: String,
    val goal: String,
    @SerialName("dataset_name") val datasetName: String = "",
    val state: String,
    val error: String? = null,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
    @SerialName("report_language") val reportLanguage: String = "en",
    val tasks: List<RunTask> = emptyList(),
    val reports: List<RunReport> = emptyList(),
    val approvals: List<RunApproval> = emptyList(),
    val report: RunArtifact? = null,
    val execution: RunExecution = RunExecution(),
)

@Serializable
data class DatasetSummary(
    val id: String,
    val name: String,
    @SerialName("byte_size") val byteSize: Long = 0,
    @SerialName("row_count") val rowCount: Int? = null,
    @SerialName("column_count") val columnCount: Int? = null,
    @SerialName("created_at") val createdAt: String = "",
    val mapped: Boolean = false,
)

@Serializable
data class DatasetsPage(val datasets: List<DatasetSummary> = emptyList())

@Serializable
data class DatasetUpload(val dataset: DatasetSummary, val created: Boolean = false)

@Serializable
data class Assessment(
    val status: String = "unassessed",
    @SerialName("reason_code") val reasonCode: String? = null,
    val reason: String? = null,
    val direction: String? = null,
)

@Serializable
data class KpiMeasure(
    val key: String,
    val title: String,
    val value: Double? = null,
    val scale: String = "count",
    val numerator: Double? = null,
    val denominator: Double? = null,
    val formula: String = "",
    val population: String = "",
    val records: Int = 0,
    @SerialName("records_excluded") val recordsExcluded: Int = 0,
    @SerialName("records_unmeasured") val recordsUnmeasured: Int = 0,
    val family: String = "other",
    @SerialName("undefined_reason") val undefinedReason: String? = null,
    val assessment: Assessment? = null,
)

@Serializable
data class Kpis(
    val measures: List<KpiMeasure> = emptyList(),
    val unavailable: Map<String, String> = emptyMap(),
)

@Serializable
data class Readiness(val status: String = "empty", val limitations: List<String> = emptyList())

@Serializable
data class Priority(
    val id: String,
    val title: String,
    val detail: String = "",
    @SerialName("evidence_refs") val evidenceRefs: List<String> = emptyList(),
)

@Serializable
data class Question(val id: String, val text: String)

@Serializable
data class Finding(
    val id: String,
    val text: String,
    val stage: String = "",
    val kind: String = "",
    @SerialName("evidence_refs") val evidenceRefs: List<String> = emptyList(),
)

@Serializable
data class ModelMetric(val name: String = "", val model: Double? = null, val baseline: Double? = null)

@Serializable
data class ModelCard(
    val kind: String = "",
    val target: String = "",
    val fitted: Boolean? = null,
    @SerialName("beats_baseline") val beatsBaseline: Boolean? = null,
    val metric: ModelMetric? = null,
    val details: Map<String, JsonElement> = emptyMap(),
    val role: String = "",
    val title: String = "",
)

@Serializable
data class Evidence(
    val id: String,
    val kind: String = "",
    val label: String = "",
    val value: Double? = null,
    val method: String = "",
)

@Serializable
data class Decision(
    val id: String,
    val title: String,
    val action: String = "",
    val owner: String = "",
    val gate: String = "",
    @SerialName("evidence_refs") val evidenceRefs: List<String> = emptyList(),
)

@Serializable
data class Advisory(
    val title: String = "",
    val subtitle: String = "",
    val role: String = "",
    val recommendation: String = "",
    val prediction: String = "",
    val decisions: List<Decision> = emptyList(),
)

@Serializable
data class BriefRun(
    val id: String,
    @SerialName("dataset_name") val datasetName: String = "",
    val state: String = "",
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class BriefScope(val records: Int = 0, @SerialName("total_records") val totalRecords: Int = 0)

/** GET /api/runs/{id}/executive: the decision brief the Command Centre
 *  shows. Every number in it is the server's. */
@Serializable
data class ExecutiveBrief(
    val run: BriefRun,
    val language: String = "en",
    val source: String = "engine",
    val scope: BriefScope = BriefScope(),
    val headline: String = "",
    val readiness: Readiness = Readiness(),
    val kpis: Kpis = Kpis(),
    val priorities: List<Priority> = emptyList(),
    val questions: List<Question> = emptyList(),
    val findings: List<Finding> = emptyList(),
    val models: List<ModelCard> = emptyList(),
    val evidence: List<Evidence> = emptyList(),
    val advisory: Advisory? = null,
    @SerialName("snapshot_id") val snapshotId: String? = null,
)

@Serializable
data class SessionState(
    @SerialName("session_id") val sessionId: String,
)

@Serializable
data class TranscriptEntry(val role: String = "", val text: String = "", val source: String? = null)

@Serializable
data class MessageReply(val reply: TranscriptEntry = TranscriptEntry())
