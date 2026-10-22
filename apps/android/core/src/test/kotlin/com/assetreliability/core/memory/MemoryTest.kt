package com.assetreliability.core.memory

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

class HnswIndexTest {
    private fun unit(random: Random, dim: Int): FloatArray =
        HashingEmbedder.normalise(FloatArray(dim) { (random.nextFloat() * 2f - 1f) })

    @Test
    fun `nearest neighbours match brute force on at least nine queries in ten`() {
        val dim = 32
        val random = Random(7)
        val vectors = (0 until 1500).associate { "v$it" to unit(random, dim) }
        val index = HnswIndex(dim, m = 16, efConstruction = 200, efSearch = 100, seed = 1)
        vectors.forEach { (id, v) -> index.add(id, v) }
        assertEquals(1500, index.size)
        var hits = 0
        val queries = 50
        val k = 10
        repeat(queries) {
            val q = unit(random, dim)
            val exact = vectors.entries.sortedByDescending { HnswIndex.dot(q, it.value) }.take(k).map { it.key }.toSet()
            val found = index.search(q, k).map { it.id }.toSet()
            hits += found.intersect(exact).size
        }
        val recall = hits.toDouble() / (queries * k)
        assertTrue("recall was $recall", recall >= 0.9)
    }

    @Test
    fun `a removed vector is never returned and a snapshot searches the same`() {
        val dim = 16
        val random = Random(3)
        val index = HnswIndex(dim, seed = 9)
        val kept = (0 until 200).associate { "n$it" to unit(random, dim) }
        kept.forEach { (id, v) -> index.add(id, v) }
        val q = kept["n17"]!!
        assertEquals("n17", index.search(q, 1).single().id)
        assertTrue(index.remove("n17"))
        assertTrue(index.search(q, 5).none { it.id == "n17" })
        assertEquals(199, index.size)
        val json = Json.encodeToString(HnswIndex.Snapshot.serializer(), index.snapshot())
        val restored = HnswIndex.restore(Json.decodeFromString(HnswIndex.Snapshot.serializer(), json))
        assertEquals(index.search(q, 5).map { it.id }, restored.search(q, 5).map { it.id })
        assertEquals(199, restored.size)
    }

    @Test
    fun `re-adding an id replaces its vector`() {
        val index = HnswIndex(4)
        index.add("a", floatArrayOf(1f, 0f, 0f, 0f))
        index.add("a", floatArrayOf(0f, 1f, 0f, 0f))
        assertEquals(1, index.size)
        assertEquals("a", index.search(floatArrayOf(0f, 1f, 0f, 0f), 1).single().id)
        assertTrue(index.search(floatArrayOf(1f, 0f, 0f, 0f), 1).single().score < 0.5f)
    }
}

class LocalMemoryTest {
    private fun record(id: String, text: String) = MemoryRecord(id, text, "note", "2026-10-22T00:00:00Z")

    @Test
    fun `recall finds the note that shares the words and says which embedder made it`() {
        val memory = LocalMemory(HashingEmbedder(128))
        memory.remember(record("1", "Overdue work orders at the North site need a planner review"))
        memory.remember(record("2", "The approver asked for the loss valuation basis"))
        memory.remember(record("3", "Availability is reported on planned hours"))
        val hits = memory.recall("overdue work at North", k = 2)
        assertEquals("1", hits.first().record.id)
        assertEquals("hashing-lexical-128", memory.embedder.name)
        assertEquals(3, memory.size)
    }

    @Test
    fun `a snapshot restores exactly and a different embedder re-embeds instead of trusting it`() {
        val memory = LocalMemory(HashingEmbedder(64))
        memory.remember(record("a", "approve the maintenance intervention at East"))
        memory.remember(record("b", "repeat repairs on pumps"))
        val json = Json.encodeToString(LocalMemory.Snapshot.serializer(), memory.snapshot())
        val same = LocalMemory.restore(Json.decodeFromString(LocalMemory.Snapshot.serializer(), json), HashingEmbedder(64))
        assertEquals("a", same.recall("intervention at East", 1).single().record.id)
        val other = LocalMemory.restore(Json.decodeFromString(LocalMemory.Snapshot.serializer(), json), HashingEmbedder(32))
        assertEquals(2, other.size)
        assertEquals("b", other.recall("repeat repairs", 1).single().record.id)
        assertTrue(memory.forget("a"))
        assertTrue(memory.recall("intervention at East", 3).none { it.record.id == "a" })
    }
}
