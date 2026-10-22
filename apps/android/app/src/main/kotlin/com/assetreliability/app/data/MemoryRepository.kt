package com.assetreliability.app.data

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase
import com.assetreliability.core.memory.HashingEmbedder
import com.assetreliability.core.memory.LocalMemory
import com.assetreliability.core.memory.MemoryRecord
import com.assetreliability.core.memory.Recall
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.time.Instant
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/** A note the phone remembers. Room holds the records; the HNSW index is
 *  held as one serialised snapshot so it restores in one read. */
@Entity(tableName = "memory")
data class MemoryEntity(
    @PrimaryKey val id: String,
    val text: String,
    val kind: String,
    val createdAt: String,
    val runId: String?,
    val language: String,
)

@Entity(tableName = "index_snapshot")
data class IndexSnapshotEntity(@PrimaryKey val name: String, val json: String)

@Dao
interface MemoryDao {
    @Query("SELECT * FROM memory ORDER BY createdAt DESC") suspend fun all(): List<MemoryEntity>
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(entity: MemoryEntity)
    @Query("DELETE FROM memory WHERE id = :id") suspend fun delete(id: String)
    @Query("SELECT * FROM index_snapshot WHERE name = 'hnsw'") suspend fun snapshot(): IndexSnapshotEntity?
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun saveSnapshot(entity: IndexSnapshotEntity)
}

@Database(entities = [MemoryEntity::class, IndexSnapshotEntity::class], version = 1, exportSchema = false)
abstract class MemoryDatabase : RoomDatabase() {
    abstract fun memory(): MemoryDao
}

/** Local vector memory: SQLite (Room) for the records, the core's HNSW
 *  index for recall. The embedder is lexical until an on-device semantic
 *  model is installed, and the UI says which one is in use. */
@Singleton
class MemoryRepository @Inject constructor(@ApplicationContext context: Context) {
    private val db = Room.databaseBuilder(context, MemoryDatabase::class.java, "memory.db").build()
    private val embedder = HashingEmbedder(256)
    private val lock = Mutex()
    private var memory: LocalMemory? = null

    val embedderName: String get() = embedder.name

    private suspend fun load(): LocalMemory = lock.withLock {
        memory ?: run {
            val dao = db.memory()
            val saved = dao.snapshot()
            val restored = if (saved != null) {
                runCatching { LocalMemory.restore(Json.decodeFromString(LocalMemory.Snapshot.serializer(), saved.json), embedder) }.getOrNull()
            } else null
            val built = restored ?: LocalMemory(embedder).also { fresh ->
                dao.all().forEach { fresh.remember(MemoryRecord(it.id, it.text, it.kind, it.createdAt, it.runId, it.language)) }
            }
            memory = built
            built
        }
    }

    private suspend fun persist(current: LocalMemory) {
        db.memory().saveSnapshot(IndexSnapshotEntity("hnsw", Json.encodeToString(LocalMemory.Snapshot.serializer(), current.snapshot())))
    }

    suspend fun remember(text: String, kind: String, runId: String? = null, language: String = "en"): MemoryRecord =
        withContext(Dispatchers.IO) {
            val record = MemoryRecord(UUID.randomUUID().toString(), text.trim(), kind, Instant.now().toString(), runId, language)
            val current = load()
            lock.withLock {
                current.remember(record)
                db.memory().upsert(MemoryEntity(record.id, record.text, record.kind, record.createdAt, record.runId, record.language))
                persist(current)
            }
            record
        }

    suspend fun forget(id: String) = withContext(Dispatchers.IO) {
        val current = load()
        lock.withLock { current.forget(id); db.memory().delete(id); persist(current) }
    }

    suspend fun recall(query: String, k: Int = 5): List<Recall> = withContext(Dispatchers.IO) { load().recall(query, k) }
    suspend fun all(): List<MemoryRecord> = withContext(Dispatchers.IO) { load().all().sortedByDescending { it.createdAt } }
}
