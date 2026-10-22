package com.assetreliability.app.data

import com.assetreliability.core.api.Transport
import com.assetreliability.core.api.TransportResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

/** The app's HTTP seam: OkHttp behind the core's Transport. Timeouts match
 *  the platform's own request limits; nothing is retried on its own. */
@Singleton
class OkHttpTransport @Inject constructor() : Transport {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    private suspend fun execute(request: Request): TransportResponse = withContext(Dispatchers.IO) {
        client.newCall(request).execute().use { response ->
            TransportResponse(response.code, response.body?.string() ?: "")
        }
    }

    private fun Request.Builder.headers(headers: Map<String, String>) = apply {
        headers.forEach { (k, v) -> header(k, v) }
    }

    override suspend fun get(url: String, headers: Map<String, String>) =
        execute(Request.Builder().url(url).headers(headers).get().build())

    override suspend fun postJson(url: String, body: String, headers: Map<String, String>) =
        execute(Request.Builder().url(url).headers(headers)
            .post(body.toRequestBody("application/json; charset=utf-8".toMediaType())).build())

    override suspend fun postMultipart(url: String, fileName: String, mediaType: String, bytes: ByteArray,
                                       fields: Map<String, String>, headers: Map<String, String>): TransportResponse {
        val form = MultipartBody.Builder().setType(MultipartBody.FORM)
        fields.forEach { (k, v) -> form.addFormDataPart(k, v) }
        form.addFormDataPart("file", fileName, bytes.toRequestBody(mediaType.toMediaType()))
        return execute(Request.Builder().url(url).headers(headers).post(form.build()).build())
    }

    override suspend fun delete(url: String, headers: Map<String, String>) =
        execute(Request.Builder().url(url).headers(headers).delete().build())

    /** Raw bytes for an export the person will share from the phone. */
    suspend fun download(url: String, headers: Map<String, String>): Pair<Int, ByteArray> = withContext(Dispatchers.IO) {
        client.newCall(Request.Builder().url(url).headers(headers).get().build()).execute().use { response ->
            response.code to (response.body?.bytes() ?: ByteArray(0))
        }
    }
}
