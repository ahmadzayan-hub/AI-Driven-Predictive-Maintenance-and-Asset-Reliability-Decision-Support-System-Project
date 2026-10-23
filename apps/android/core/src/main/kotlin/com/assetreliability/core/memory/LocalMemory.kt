package com.assetreliability.core.memory

import kotlinx.serialization.Serializable
import kotlin.math.sqrt

/** Turns text into a unit vector. */
interface Embedder {
    val dimension: Int
    val name: String
    fun embed(text: String): FloatArray
}

/** A lexical embedding: tokens hashed into a fixed number of dimensions
 *  with a sign, then normalised. It finds notes that share words, not
 *  notes that share meaning; it is the fallback when no on-device
 *  semantic model is installed, and it says so in `name`. */
class HashingEmbedder(override val dimension: Int = 256) : Embedder {
    override val name = "hashing-lexical-$dimension"

    override fun embed(text: String): FloatArray {
        val vector = FloatArray(dimension)
        val tokens = tokenise(text)
        for (token in tokens) {
            val hash = token.hashCode()
            val slot = Math.floorMod(hash, dimension)
            val sign = if ((hash ushr 31) == 0) 1f else -1f
            vector[slot] += sign
        }
        // Bigrams keep a little word order ("not overdue" vs "overdue").
        for (i in 0 until tokens.size - 1) {
            val hash = (tokens[i] + " " + tokens[i + 1]).hashCode()
            vector[Math.floorMod(hash, dimension)] += if ((hash ushr 31) == 0) 0.5f else -0.5f
        }
        return normalise(vector)
    }

    companion object {
        private val SPLIT = Regex("[^\\p{L}\\p{N}]+")

        fun tokenise(text: String): List<String> =
            text.lowercase().split(SPLIT).filter { it.length > 1 }

        fun normalise(vector: FloatArray): FloatArray {
            var sum = 0f
            for (v in vector) sum += v * v
            val norm = sqrt(sum)
            if (norm > 0f) for (i in vector.indices) vector[i] /= norm
            return vector
        }
    }
}

@Serializable
data class MemoryRecord(
    val id: String,
    val text: String,
    val kind: String,
    val createdAt: String,
    val runId: String? = null,
    val language: String = "en",
)

data class Recall(val record: MemoryRecord, val score: Float)

/** What the phone remembers: briefs read, decisions taken, notes typed,
 *  each embedded and indexed on the device. Nothing here leaves the phone
 *  unless the person sends it to the assistant. */
class LocalMemory(
    val embedder: Embedder,
    private val index: HnswIndex = HnswIndex(embedder.dimension),
    records: Map<String, MemoryRecord> = emptyMap(),
) {
    private val records = LinkedHashMap(records)

    val size: Int get() = records.size

    fun remember(record: MemoryRecord) {
        records[record.id] = record
        index.add(record.id, embedder.embed(record.text))
    }

    fun forget(id: String): Boolean {
        records.remove(id) ?: return false
        return index.remove(id)
    }

    fun recall(query: String, k: Int = 5, minScore: Float = 0.1f): List<Recall> =
        index.search(embedder.embed(query), k)
            .filter { it.score >= minScore }
            .mapNotNull { hit -> records[hit.id]?.let { Recall(it, hit.score) } }

    fun all(): List<MemoryRecord> = records.values.toList()

    @Serializable
    data class Snapshot(val embedder: String, val index: HnswIndex.Snapshot, val records: List<MemoryRecord>)

    fun snapshot(): Snapshot = Snapshot(embedder.name, index.snapshot(), records.values.toList())

    companion object {
        /** A snapshot made with a different embedder cannot be searched by
         *  this one: the caller re-embeds instead of trusting it. */
        fun restore(snapshot: Snapshot, embedder: Embedder): LocalMemory {
            if (snapshot.embedder != embedder.name) {
                val memory = LocalMemory(embedder)
                snapshot.records.forEach { memory.remember(it) }
                return memory
            }
            return LocalMemory(embedder, HnswIndex.restore(snapshot.index), snapshot.records.associateBy { it.id })
        }
    }
}
