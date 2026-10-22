package com.assetreliability.core.memory

import kotlinx.serialization.Serializable
import java.util.PriorityQueue
import kotlin.math.ln
import kotlin.random.Random

data class Hit(val id: String, val score: Float)

/** A vector index over unit-length vectors: cosine similarity is the dot
 *  product. Scores are higher-is-closer. */
interface VectorIndex {
    val dimension: Int
    val size: Int
    fun add(id: String, vector: FloatArray)
    fun remove(id: String): Boolean
    fun search(query: FloatArray, k: Int): List<Hit>
}

/** Hierarchical Navigable Small World graph (Malkov and Yashunin, 2016),
 *  in plain Kotlin, for an on-device memory of at most a few tens of
 *  thousands of notes. Deterministic for a given seed, so a snapshot
 *  restored on the phone searches exactly as it did before. */
class HnswIndex(
    override val dimension: Int,
    private val m: Int = 16,
    private val efConstruction: Int = 200,
    var efSearch: Int = 64,
    seed: Long = 42L,
) : VectorIndex {
    private val random = Random(seed)
    private val levelMult = 1.0 / ln(m.toDouble())
    private val maxM0 = m * 2

    private class Node(val id: String, val vector: FloatArray, val level: Int) {
        val neighbours: Array<MutableList<Int>> = Array(level + 1) { mutableListOf() }
        var deleted = false
    }

    private val nodes = ArrayList<Node>()
    private val byId = HashMap<String, Int>()
    private var entryPoint = -1
    private var topLevel = -1

    override val size: Int get() = byId.size

    override fun add(id: String, vector: FloatArray) {
        require(vector.size == dimension) { "vector has ${vector.size} dimensions, index has $dimension" }
        byId[id]?.let { remove(id) }
        val level = randomLevel()
        val node = Node(id, vector.copyOf(), level)
        val index = nodes.size
        nodes.add(node)
        byId[id] = index
        if (entryPoint < 0) {
            entryPoint = index; topLevel = level; return
        }
        var current = entryPoint
        for (layer in topLevel downTo level + 1) current = greedyClosest(vector, current, layer)
        for (layer in minOf(level, topLevel) downTo 0) {
            val candidates = searchLayer(vector, current, efConstruction, layer)
            val selected = candidates.take(if (layer == 0) maxM0 else m)
            node.neighbours[layer].addAll(selected.map { it.index })
            for (neighbour in selected) {
                val list = nodes[neighbour.index].neighbours[layer]
                list.add(index)
                val cap = if (layer == 0) maxM0 else m
                if (list.size > cap) prune(nodes[neighbour.index], layer, cap)
            }
            if (candidates.isNotEmpty()) current = candidates.first().index
        }
        if (level > topLevel) { entryPoint = index; topLevel = level }
    }

    override fun remove(id: String): Boolean {
        val index = byId.remove(id) ?: return false
        nodes[index].deleted = true
        if (index == entryPoint) {
            val next = nodes.indices.filter { !nodes[it].deleted }.maxByOrNull { nodes[it].level }
            entryPoint = next ?: -1
            topLevel = next?.let { nodes[it].level } ?: -1
        }
        return true
    }

    override fun search(query: FloatArray, k: Int): List<Hit> {
        if (entryPoint < 0 || k <= 0) return emptyList()
        var current = entryPoint
        for (layer in topLevel downTo 1) current = greedyClosest(query, current, layer)
        return searchLayer(query, current, maxOf(efSearch, k), 0)
            .filter { !nodes[it.index].deleted }
            .take(k)
            .map { Hit(nodes[it.index].id, it.score) }
    }

    private class Candidate(val index: Int, val score: Float)

    private fun greedyClosest(query: FloatArray, start: Int, layer: Int): Int {
        var current = start
        var best = dot(query, nodes[current].vector)
        var improved = true
        while (improved) {
            improved = false
            for (neighbour in nodes[current].neighbours[layer]) {
                val score = dot(query, nodes[neighbour].vector)
                if (score > best) { best = score; current = neighbour; improved = true }
            }
        }
        return current
    }

    /** Beam search on one layer; returns candidates best first. */
    private fun searchLayer(query: FloatArray, start: Int, ef: Int, layer: Int): List<Candidate> {
        val visited = HashSet<Int>()
        val toVisit = PriorityQueue<Candidate>(compareByDescending { it.score })
        val results = PriorityQueue<Candidate>(compareBy { it.score })
        val first = Candidate(start, dot(query, nodes[start].vector))
        visited.add(start); toVisit.add(first); results.add(first)
        while (toVisit.isNotEmpty()) {
            val candidate = toVisit.poll()
            if (results.size >= ef && candidate.score < results.peek().score) break
            for (neighbour in nodes[candidate.index].neighbours[layer]) {
                if (!visited.add(neighbour)) continue
                val score = dot(query, nodes[neighbour].vector)
                if (results.size < ef || score > results.peek().score) {
                    val next = Candidate(neighbour, score)
                    toVisit.add(next); results.add(next)
                    if (results.size > ef) results.poll()
                }
            }
        }
        return results.sortedByDescending { it.score }
    }

    private fun prune(node: Node, layer: Int, cap: Int) {
        val kept = node.neighbours[layer]
            .map { Candidate(it, dot(node.vector, nodes[it].vector)) }
            .sortedByDescending { it.score }
            .take(cap)
            .map { it.index }
        node.neighbours[layer].clear(); node.neighbours[layer].addAll(kept)
    }

    private fun randomLevel(): Int {
        val r = random.nextDouble().coerceAtLeast(1e-12)
        return (-ln(r) * levelMult).toInt()
    }

    // -- persistence -------------------------------------------------------

    @Serializable
    data class SnapshotNode(val id: String, val vector: List<Float>, val level: Int, val neighbours: List<List<Int>>, val deleted: Boolean)

    @Serializable
    data class Snapshot(val dimension: Int, val m: Int, val efConstruction: Int, val entryPoint: Int, val topLevel: Int, val nodes: List<SnapshotNode>)

    fun snapshot(): Snapshot = Snapshot(dimension, m, efConstruction, entryPoint, topLevel,
        nodes.map { SnapshotNode(it.id, it.vector.toList(), it.level, it.neighbours.map { n -> n.toList() }, it.deleted) })

    companion object {
        fun restore(snapshot: Snapshot, efSearch: Int = 64, seed: Long = 42L): HnswIndex {
            val index = HnswIndex(snapshot.dimension, snapshot.m, snapshot.efConstruction, efSearch, seed)
            for ((position, saved) in snapshot.nodes.withIndex()) {
                val node = Node(saved.id, saved.vector.toFloatArray(), saved.level)
                for ((layer, list) in saved.neighbours.withIndex()) node.neighbours[layer].addAll(list)
                node.deleted = saved.deleted
                index.nodes.add(node)
                if (!saved.deleted) index.byId[saved.id] = position
            }
            index.entryPoint = snapshot.entryPoint
            index.topLevel = snapshot.topLevel
            return index
        }

        fun dot(a: FloatArray, b: FloatArray): Float {
            var sum = 0f
            for (i in a.indices) sum += a[i] * b[i]
            return sum
        }
    }
}
