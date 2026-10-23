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
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.security.MessageDigest
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
class MemoryRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val settings: Settings,
    private val platform: PlatformRepository,
) {
    private val embedder = HashingEmbedder(256)
    private val lock = Mutex()
    private var database: MemoryDatabase? = null
    private var activeScope: String? = null
    private var memory: LocalMemory? = null

    val embedderName: String get() = embedder.name

    /** Recheck access before reading metadata, recall or saved excerpts. A
     *  disconnected/expired workspace does not expose its cached brief. The
     *  server-verified subject, not decoded JWT claims, selects the database.
     *  Legacy unscoped memory.db is retained without guessing its owner.
     */
    private suspend fun <T> authorized(operation: suspend (LocalMemory, MemoryDao) -> T): T =
        withContext(Dispatchers.IO) {
            val before = settings.current()
            val identity = platform.identity()
            val after = settings.current()
            if (before.serverUrl != after.serverUrl || before.token != after.token)
                throw CancellationException("Workspace changed")
            val scope = MessageDigest.getInstance("SHA-256")
                .digest((before.serverUrl + "\u0000" + identity.principal.subject).toByteArray(Charsets.UTF_8))
                .joinToString("") { "%02x".format(it.toInt() and 255) }
            lock.withLock {
                if (activeScope != scope) {
                    database?.close()
                    database = Room.databaseBuilder(context, MemoryDatabase::class.java, "memory-$scope.db").build()
                    activeScope = scope
                    memory = null
                }
                val dao = database!!.memory()
                val current = memory ?: run {
                    val saved = dao.snapshot()
                    val restored = saved?.let {
                        runCatching { LocalMemory.restore(Json.decodeFromString(LocalMemory.Snapshot.serializer(), it.json), embedder) }.getOrNull()
                    }
                    (restored ?: LocalMemory(embedder).also { fresh ->
                        dao.all().forEach { fresh.remember(MemoryRecord(it.id, it.text, it.kind, it.createdAt, it.runId, it.language)) }
                    }).also { memory = it }
                }
                operation(current, dao)
            }
        }

    private suspend fun persist(current: LocalMemory, dao: MemoryDao) {
        dao.saveSnapshot(IndexSnapshotEntity("hnsw", Json.encodeToString(LocalMemory.Snapshot.serializer(), current.snapshot())))
    }

    suspend fun remember(text: String, kind: String, runId: String? = null, language: String = "en"): MemoryRecord =
        authorized { current, dao ->
            val record = MemoryRecord(UUID.randomUUID().toString(), text.trim(), kind, Instant.now().toString(), runId, language)
            dao.upsert(MemoryEntity(record.id, record.text, record.kind, record.createdAt, record.runId, record.language))
            current.remember(record)
            persist(current, dao)
            record
        }

    suspend fun forget(id: String) = authorized { current, dao ->
        dao.delete(id); current.forget(id); persist(current, dao)
    }

    suspend fun recall(query: String, k: Int = 5): List<Recall> = authorized { current, _ -> current.recall(query, k) }
    suspend fun all(): List<MemoryRecord> = authorized { current, _ -> current.all().sortedByDescending { it.createdAt } }
}
