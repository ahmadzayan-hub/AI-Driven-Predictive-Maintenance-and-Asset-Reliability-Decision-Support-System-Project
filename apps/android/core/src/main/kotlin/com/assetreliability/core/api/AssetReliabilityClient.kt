package com.assetreliability.core.api

import java.net.URLEncoder

/** The one HTTP seam. The Android app supplies OkHttp; tests supply a
 *  fake. The client never sees a socket, so every path and body it builds
 *  is testable on the JVM. */
interface Transport {
    suspend fun get(url: String, headers: Map<String, String>): TransportResponse
    suspend fun postJson(url: String, body: String, headers: Map<String, String>): TransportResponse
    suspend fun postBytes(url: String, mediaType: String, bytes: ByteArray,
                          headers: Map<String, String>): TransportResponse
    suspend fun delete(url: String, headers: Map<String, String>): TransportResponse
}

data class TransportResponse(val status: Int, val body: String) {
    val ok: Boolean get() = status in 200..299
}

class ApiException(val status: Int, val detail: String) : Exception("HTTP $status: $detail")

/** Reads the platform's API. `tokenProvider` returns a bearer token for a
 *  signed-in workspace, or null for the view-only demo. */
class AssetReliabilityClient(
    private val transport: Transport,
    baseUrl: String,
    private val tokenProvider: () -> String? = { null },
) {
    val baseUrl: String = baseUrl.trimEnd('/')

    private fun headers(language: String? = null): Map<String, String> {
        val out = mutableMapOf("Accept" to "application/json")
        tokenProvider()?.let { out["Authorization"] = "Bearer $it" }
        language?.let { out["Accept-Language"] = it }
        return out
    }

    private fun url(path: String, query: Map<String, String> = emptyMap()): String {
        val q = query.entries.joinToString("&") { (k, v) ->
            URLEncoder.encode(k, "UTF-8") + "=" + URLEncoder.encode(v, "UTF-8")
        }
        return baseUrl + path + if (q.isEmpty()) "" else "?$q"
    }

    private inline fun <reified T> parse(response: TransportResponse): T {
        if (!response.ok) throw ApiException(response.status, detailOf(response.body))
        return ApiJson.decodeFromString(response.body)
    }

    suspend fun health(): Health = parse(transport.get(url("/api/health"), headers()))
    suspend fun authConfig(): AuthConfig = parse(transport.get(url("/api/auth/config"), headers()))
    suspend fun identity(): WorkspaceIdentity = parse(transport.get(url("/api/identity"), headers()))
    suspend fun runs(state: String? = null): List<RunSummary> = parse<RunsPage>(transport.get(
        url("/api/runs", if (state == null) emptyMap() else mapOf("state" to state)), headers())).runs
    suspend fun run(id: String): RunDetail = parse(transport.get(url("/api/runs/${enc(id)}"), headers()))
    suspend fun datasets(): List<DatasetSummary> =
        parse<DatasetsPage>(transport.get(url("/api/datasets"), headers())).datasets

    suspend fun executive(runId: String, language: String = "en"): ExecutiveBrief = parse(
        transport.get(url("/api/runs/${enc(runId)}/executive",
            mapOf("language" to language, "filters" to "[]")), headers(language)))

    /** Uploads a CSV, TSV, XLSX, JSON or JSONL file as a stored dataset. */
    suspend fun uploadDataset(fileName: String, mediaType: String, bytes: ByteArray,
                              language: String = "en"): DatasetSummary = parse<DatasetUpload>(
        transport.postBytes(url("/api/datasets", mapOf("name" to fileName, "language" to language)),
            mediaType, bytes, headers(language))).dataset

    /** Starts a governed analysis on a stored dataset. */
    suspend fun createRun(goal: String, datasetId: String, language: String = "en",
                          profile: String? = null, idempotencyKey: String? = null): RunDetail {
        val body = buildString {
            append("{\"goal\":").append(quote(goal))
            append(",\"dataset_id\":").append(quote(datasetId))
            append(",\"language\":").append(quote(language))
            if (profile != null) append(",\"profile\":").append(quote(profile))
            append("}")
        }
        val sentHeaders = headers(language).toMutableMap()
        idempotencyKey?.let { sentHeaders["Idempotency-Key"] = it }
        return parse(transport.postJson(url("/api/runs"), body, sentHeaders))
    }

    suspend fun advance(runId: String): RunDetail =
        parse(transport.postJson(url("/api/runs/${enc(runId)}/advance"), "{}", headers()))

    suspend fun decide(runId: String, approvalId: String, approve: Boolean): RunDetail = parse(
        transport.postJson(url("/api/runs/${enc(runId)}/approvals/${enc(approvalId)}"),
            "{\"decision\":\"${if (approve) "approve" else "reject"}\"}", headers()))

    suspend fun createSession(language: String = "en"): SessionState =
        parse(transport.postJson(url("/api/sessions"), "{\"language\":${quote(language)}}", headers()))

    suspend fun sendMessage(sessionId: String, text: String): MessageReply = parse(
        transport.postJson(url("/api/sessions/${enc(sessionId)}/messages"),
            "{\"text\":${quote(text)}}", headers()))

    /** The executive report as HTML or DOCX bytes, for sharing from the phone. */
    fun executiveExportUrl(runId: String, language: String, expectedUpdatedAt: String,
                           snapshotId: String, format: String = "html"): String =
        url("/api/runs/${enc(runId)}/executive/export", mapOf(
            "language" to language, "filters" to "[]", "expected_updated_at" to expectedUpdatedAt,
            "expected_snapshot_id" to snapshotId, "format" to format))

    private fun enc(value: String) = URLEncoder.encode(value, "UTF-8")

    companion object {
        fun quote(text: String): String = buildString {
            append('"')
            for (c in text) when (c) {
                '"' -> append("\\\"")
                '\\' -> append("\\\\")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> if (c < ' ') append(String.format("\\u%04x", c.code)) else append(c)
            }
            append('"')
        }

        fun detailOf(body: String): String = try {
            val element = ApiJson.parseToJsonElement(body)
            val root = element as? kotlinx.serialization.json.JsonObject
            val error = root?.get("error") as? kotlinx.serialization.json.JsonObject
            val detail = root?.get("detail")
            val structured = detail as? kotlinx.serialization.json.JsonObject
            ((error?.get("message") ?: structured?.get("message") ?: detail)
                as? kotlinx.serialization.json.JsonPrimitive)?.content ?: body.take(200)
        } catch (_: Exception) {
            body.take(200)
        }
    }
}
