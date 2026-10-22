package com.assetreliability.core.api

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Records every call and answers from a map of path prefixes. */
class FakeTransport(private val answers: Map<String, String>) : Transport {
    val calls = mutableListOf<Triple<String, String, String?>>()

    private fun answer(method: String, url: String, body: String?): TransportResponse {
        calls.add(Triple(method, url, body))
        val path = url.substringAfter("http://server")
        val match = answers.entries.firstOrNull { path.startsWith(it.key) }
            ?: return TransportResponse(404, """{"detail":"Not found."}""")
        return TransportResponse(200, match.value)
    }

    override suspend fun get(url: String, headers: Map<String, String>) = answer("GET", url, null)
    override suspend fun postJson(url: String, body: String, headers: Map<String, String>) = answer("POST", url, body)
    override suspend fun postMultipart(url: String, fileName: String, mediaType: String, bytes: ByteArray,
                                       fields: Map<String, String>, headers: Map<String, String>) =
        answer("MULTIPART", url, "$fileName:$mediaType:${bytes.size}")
    override suspend fun delete(url: String, headers: Map<String, String>) = answer("DELETE", url, null)
}

class ClientTest {
    private val fixture = javaClass.getResource("/executive-demo.json")!!.readText()

    @Test
    fun `the live demo brief parses with every field the command centre needs`() = runBlocking {
        val transport = FakeTransport(mapOf("/api/runs/5fe5d44a8391/executive" to fixture))
        val client = AssetReliabilityClient(transport, "http://server/")
        val brief = client.executive("5fe5d44a8391", "en")
        assertEquals("demo-fleet-fictional.csv", brief.run.datasetName)
        assertEquals(240, brief.scope.records)
        assertEquals("limited", brief.readiness.status)
        assertEquals(7, brief.kpis.measures.size)
        assertEquals(4, brief.kpis.unavailable.size)
        assertEquals(5, brief.advisory!!.decisions.size)
        assertEquals("Maintenance planner", brief.advisory!!.decisions[0].owner)
        assertEquals(2, brief.models.size)
        assertNull(brief.kpis.measures.last().value)
        assertTrue(transport.calls.single().second.contains("language=en"))
        assertTrue(transport.calls.single().second.contains("filters=%5B%5D"))
    }

    @Test
    fun `a bearer token is sent only when a workspace is signed in`() = runBlocking {
        val transport = object : Transport by FakeTransport(mapOf("/api/health" to """{"status":"ok"}""")) {
            var seen: Map<String, String> = emptyMap()
            override suspend fun get(url: String, headers: Map<String, String>): TransportResponse {
                seen = headers; return TransportResponse(200, """{"status":"ok"}""")
            }
        }
        AssetReliabilityClient(transport, "http://server") { null }.health()
        assertNull(transport.seen["Authorization"])
        AssetReliabilityClient(transport, "http://server") { "t0k3n" }.health()
        assertEquals("Bearer t0k3n", transport.seen["Authorization"])
    }

    @Test
    fun `a run is created from a stored dataset with the goal quoted safely`() = runBlocking {
        val transport = FakeTransport(mapOf("/api/runs" to """{"id":"r1","goal":"g","state":"queued"}"""))
        val client = AssetReliabilityClient(transport, "http://server")
        val run = client.createRun("Review \"North\" downtime\nnow", "ds1", "ar", "maintenance")
        assertEquals("r1", run.id)
        val body = transport.calls.single().third!!
        assertEquals("""{"goal":"Review \"North\" downtime\nnow","dataset_id":"ds1","language":"ar","profile":"maintenance"}""", body)
    }

    @Test
    fun `an upload goes as multipart and a failure carries the server's detail`() = runBlocking {
        val transport = FakeTransport(mapOf("/api/datasets" to """{"id":"ds9","name":"fleet.csv"}"""))
        val client = AssetReliabilityClient(transport, "http://server")
        val dataset = client.uploadDataset("fleet.csv", "text/csv", "a,b\n1,2\n".toByteArray())
        assertEquals("ds9", dataset.id)
        assertEquals("MULTIPART", transport.calls.single().first)
        try {
            client.run("missing")
            throw AssertionError("expected a 404")
        } catch (error: ApiException) {
            assertEquals(404, error.status)
            assertEquals("Not found.", error.detail)
        }
    }

    @Test
    fun `the export url binds the report to its snapshot`() {
        val client = AssetReliabilityClient(FakeTransport(emptyMap()), "http://server")
        val url = client.executiveExportUrl("r1", "ar", "2026-10-22T09:00:00+00:00", "abc", "docx")
        assertTrue(url.startsWith("http://server/api/runs/r1/executive/export?"))
        assertTrue(url.contains("expected_snapshot_id=abc"))
        assertTrue(url.contains("format=docx"))
        assertTrue(url.contains("language=ar"))
    }
}
