// VectorDB type definitions, constants, type guards, and error classes
// ============================================
// Constants
// ============================================
/** Multiplier for candidate count in hybrid search (to allow reranking) */
export const HYBRID_SEARCH_CANDIDATE_MULTIPLIER = 2;
/** FTS index name (bump version when changing tokenizer settings) */
export const FTS_INDEX_NAME = 'fts_index_v2';
/** Threshold for cleaning up old index versions (1 minute) */
export const FTS_CLEANUP_THRESHOLD_MS = 60 * 1000;
// ============================================
// Type Guards
// ============================================
/**
 * Type guard for DocumentMetadata
 */
export function isDocumentMetadata(value) {
    if (typeof value !== 'object' || value === null)
        return false;
    const obj = value;
    return (typeof obj['fileName'] === 'string' &&
        typeof obj['fileSize'] === 'number' &&
        typeof obj['fileType'] === 'string');
}
/**
 * Type guard for LanceDB raw search result
 */
export function isLanceDBRawResult(value) {
    if (typeof value !== 'object' || value === null)
        return false;
    const obj = value;
    return (typeof obj['filePath'] === 'string' &&
        typeof obj['chunkIndex'] === 'number' &&
        typeof obj['text'] === 'string' &&
        isDocumentMetadata(obj['metadata']));
}
/**
 * Convert LanceDB raw result to SearchResult with type validation
 * @throws DatabaseError if the result is invalid
 */
export function toSearchResult(raw) {
    if (!isLanceDBRawResult(raw)) {
        throw new DatabaseError('Invalid search result format from LanceDB');
    }
    return {
        filePath: raw.filePath,
        chunkIndex: raw.chunkIndex,
        text: raw.text,
        score: raw._distance ?? raw._score ?? 0,
        metadata: raw.metadata,
        fileTitle: raw.fileTitle || null,
    };
}
/**
 * Convert LanceDB raw row to ChunkRow with type validation.
 * Mirrors toSearchResult but returns the minimal shape defined in
 * Design Doc §Contract Definitions: no score (not ranked) and no
 * metadata (not needed for index-adjacent retrieval).
 *
 * Uses a narrower shape check than isLanceDBRawResult: only
 * filePath/chunkIndex/text are required because getChunksByRange
 * does not project metadata. The empty-string-or-missing fileTitle
 * is normalized to null per §Field Propagation Map.
 *
 * @throws DatabaseError if the raw row is missing required fields
 */
export function toChunkRow(raw) {
    if (typeof raw !== 'object' || raw === null) {
        throw new DatabaseError('Invalid chunk row shape from LanceDB');
    }
    const obj = raw;
    if (typeof obj['filePath'] !== 'string' ||
        typeof obj['chunkIndex'] !== 'number' ||
        typeof obj['text'] !== 'string') {
        throw new DatabaseError('Invalid chunk row shape from LanceDB');
    }
    const rawFileTitle = obj['fileTitle'];
    const fileTitle = typeof rawFileTitle === 'string' && rawFileTitle.length > 0 ? rawFileTitle : null;
    return {
        filePath: obj['filePath'],
        chunkIndex: obj['chunkIndex'],
        text: obj['text'],
        fileTitle,
    };
}
// ============================================
// Error Classes
// ============================================
/**
 * Database error
 */
export class DatabaseError extends Error {
    cause;
    constructor(message, cause) {
        super(message);
        this.cause = cause;
        this.name = 'DatabaseError';
    }
}
//# sourceMappingURL=types.js.map