package com.assetreliability.app.data

import android.content.Context
import android.net.Uri
import com.assetreliability.core.api.ApiException
import com.assetreliability.core.api.AssetReliabilityClient
import com.assetreliability.core.api.DatasetSummary
import com.assetreliability.core.api.ExecutiveBrief
import com.assetreliability.core.api.Health
import com.assetreliability.core.api.RunDetail
import com.assetreliability.core.api.RunSummary
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.ByteArrayOutputStream
import javax.inject.Inject
import javax.inject.Singleton

/** The domain's one door to the platform. Every method returns the
 *  server's own objects; the app never derives a figure of its own. */
@Singleton
class PlatformRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val transport: OkHttpTransport,
    private val settings: Settings,
) {
    private suspend fun client(): AssetReliabilityClient {
        val current = settings.current()
        return AssetReliabilityClient(transport, current.serverUrl) { current.token }
    }

    suspend fun health(): Health = client().health()
    suspend fun identity() = client().identity()
    /** "demo", "local" or "jwt": what the server will let this phone do. */
    suspend fun authMode(): String = client().authConfig().mode
    suspend fun isReadOnly(): Boolean = settings.current().token == null && authMode() == "demo"
    suspend fun runs(state: String? = null): List<RunSummary> = client().runs(state)
    suspend fun run(id: String): RunDetail = client().run(id)
    suspend fun datasets(): List<DatasetSummary> = client().datasets()
    suspend fun executive(runId: String): ExecutiveBrief = client().executive(runId, settings.current().language)
    suspend fun advance(runId: String): RunDetail = client().advance(runId)
    suspend fun decide(runId: String, approvalId: String, approve: Boolean): RunDetail =
        client().decide(runId, approvalId, approve)

    /** Reads the picked file from the content resolver and uploads it. The
     *  platform caps uploads at 4 MB; a larger file is refused here with
     *  the same message rather than sent. */
    suspend fun upload(uri: Uri): DatasetSummary = withContext(Dispatchers.IO) {
        val resolver = context.contentResolver
        val name = resolver.query(uri, null, null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
            if (cursor.moveToFirst() && index >= 0) cursor.getString(index) else null
        } ?: "upload.csv"
        val bytes = resolver.openInputStream(uri)?.use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                if (output.size() + read > 4_000_000)
                    throw ApiException(413, "The file is larger than the 4 MB the platform accepts.")
                output.write(buffer, 0, read)
            }
            output.toByteArray()
        }
            ?: throw ApiException(0, "The file could not be read.")
        if (bytes.size > 4_000_000) throw ApiException(413, "The file is larger than the 4 MB the platform accepts.")
        val type = resolver.getType(uri) ?: when (name.substringAfterLast('.', "").lowercase()) {
            "csv" -> "text/csv"; "tsv" -> "text/tab-separated-values"
            "xlsx" -> "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            "json" -> "application/json"; "jsonl" -> "application/x-ndjson"
            else -> "application/octet-stream"
        }
        client().uploadDataset(name, type, bytes, settings.current().language)
    }

    suspend fun createRun(goal: String, datasetId: String, profile: String?, idempotencyKey: String): RunDetail =
        client().createRun(goal, datasetId, settings.current().language, profile, idempotencyKey)

    /** Downloads the executive report (HTML or DOCX) into the app cache for
     *  the share sheet. The server re-checks the snapshot; a 409 means the
     *  run changed and the brief must be re-read first. */
    suspend fun exportExecutive(brief: ExecutiveBrief, format: String): File = withContext(Dispatchers.IO) {
        val current = settings.current()
        val url = client().executiveExportUrl(brief.run.id, current.language,
            brief.run.updatedAt ?: "", brief.snapshotId ?: "", format)
        val headers = buildMap {
            put("Accept", if (format == "docx") "application/vnd.openxmlformats-officedocument.wordprocessingml.document" else "text/html")
            current.token?.let { put("Authorization", "Bearer $it") }
        }
        val (status, bytes) = transport.download(url, headers)
        if (status !in 200..299) throw ApiException(status, AssetReliabilityClient.detailOf(String(bytes)))
        val dir = File(context.cacheDir, "exports").apply { mkdirs() }
        File(dir, "executive-${brief.run.id}.${if (format == "docx") "docx" else "html"}").also { it.writeBytes(bytes) }
    }
}
