import { type ChunkRow, type SearchResult, type VectorChunk, type VectorStoreConfig } from './types.js';
export type { GroupingMode, SearchResult, VectorChunk } from './types.js';
/**
 * Vector storage class using LanceDB
 *
 * Responsibilities:
 * - LanceDB operations (insert, delete, search)
 * - Transaction handling (atomicity of delete→insert)
 * - Metadata management
 */
export declare class VectorStore {
    private db;
    private table;
    private readonly config;
    private ftsEnabled;
    constructor(config: VectorStoreConfig);
    /**
     * Initialize LanceDB and create table
     */
    initialize(): Promise<void>;
    /**
     * Delete all chunks for specified file path
     *
     * @param filePath - File path (absolute)
     */
    deleteChunks(filePath: string): Promise<void>;
    /**
     * Return chunk rows for a single file whose chunkIndex is within the
     * inclusive [minIdx, maxIdx] range, sorted ascending by chunkIndex.
     *
     * This is a feature-agnostic primitive (ADR-0001 D5): it knows nothing
     * about before/after/isTarget semantics — those live in the handler.
     * Ascending sort by chunkIndex is a contract, not incidental storage
     * order (AC-018).
     *
     * Lazy-table null returns [] (mirrors search, listFiles, deleteChunks).
     * LanceDB errors are wrapped as DatabaseError with the original error
     * preserved as cause.
     *
     * Note: LanceDB numeric predicates (>=, <=) on chunkIndex are not
     * exercised elsewhere in the repo today. Task 1.3 unit tests act as
     * the probe for this SQL shape; see Design Doc §Main Components →
     * VectorStore Limitation note for the fetch-all + in-memory-filter
     * fallback plan if the probe fails.
     *
     * @param filePath - File path (absolute)
     * @param minIdx - Minimum chunk index (inclusive)
     * @param maxIdx - Maximum chunk index (inclusive)
     * @returns Array of chunk rows sorted ascending by chunkIndex
     */
    getChunksByRange(filePath: string, minIdx: number, maxIdx: number): Promise<ChunkRow[]>;
    /**
     * Batch insert vector chunks
     *
     * @param chunks - Array of vector chunks
     */
    insertChunks(chunks: VectorChunk[]): Promise<void>;
    /**
     * Ensure FTS index exists for hybrid search
     * Creates ngram-based index if it doesn't exist, drops old versions
     * @throws DatabaseError if index creation fails (Fail-Fast principle)
     */
    private ensureFtsIndex;
    /**
     * Ensure schema is up to date by adding missing columns.
     * Uses table.addColumns() API for top-level column additions.
     * Idempotent: checks for column existence before adding.
     */
    private ensureSchemaVersion;
    /**
     * Optimize table: compact fragments, update FTS index, and clean up old versions.
     * LanceDB OSS requires explicit optimize() call to update FTS index.
     *
     * Callers are responsible for deciding when to invoke this (e.g., once per
     * ingest rather than after every insert/delete) to avoid O(n²) overhead
     * during bulk operations.
     */
    optimize(): Promise<void>;
    /**
     * Execute vector search with quality filtering
     * Architecture: Semantic search → Filter (maxDistance, grouping) → Keyword boost → File filter (maxFiles)
     *
     * This "prefetch then rerank" approach ensures:
     * - maxDistance and grouping work on meaningful vector distances
     * - Keyword matching acts as a boost, not a replacement for semantic similarity
     *
     * @param queryVector - Query vector (dimension depends on model)
     * @param queryText - Optional query text for keyword boost (BM25)
     * @param limit - Number of results to retrieve (default 10)
     * @returns Array of search results (sorted by distance ascending, filtered by quality settings)
     */
    search(queryVector: number[], queryText?: string, limit?: number): Promise<SearchResult[]>;
    /**
     * Get list of ingested files
     *
     * @returns Array of file information
     */
    listFiles(): Promise<{
        filePath: string;
        chunkCount: number;
        timestamp: string;
    }[]>;
    /**
     * Get system status
     *
     * @returns System status information
     */
    getStatus(): Promise<{
        documentCount: number;
        chunkCount: number;
        memoryUsage: number;
        uptime: number;
        ftsIndexEnabled: boolean;
        searchMode: 'hybrid' | 'vector-only';
    }>;
    /**
     * Close the database connection
     */
    close(): Promise<void>;
}
//# sourceMappingURL=index.d.ts.map