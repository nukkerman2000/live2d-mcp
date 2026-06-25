import type { SemanticChunker } from '../chunker/index.js';
import type { Embedder } from '../embedder/index.js';
import type { DocumentParser } from '../parser/index.js';
import type { VectorStore } from '../vectordb/index.js';
import { type SyncFileMetadata, type SyncPlan } from './sync-utils.js';
export type SyncEvent = {
    type: 'prune_start';
    count: number;
} | {
    type: 'file_start';
    filePath: string;
    index: number;
    total: number;
} | {
    type: 'file_ok';
    filePath: string;
    index: number;
    total: number;
    chunkCount: number;
} | {
    type: 'file_empty';
    filePath: string;
    index: number;
    total: number;
} | {
    type: 'file_failed';
    filePath: string;
    index: number;
    total: number;
    error: string;
} | {
    type: 'aborted';
    completed: number;
    total: number;
} | {
    type: 'complete';
    stats: SyncStats;
};
export interface SyncStats {
    upsertCount: number;
    pruneCount: number;
    skipCount: number;
    skippedEmpty: number;
    failedCount: number;
    totalChunks: number;
}
export interface SyncDeps {
    vectorStore: VectorStore;
    parser: DocumentParser;
    chunker: SemanticChunker;
    embedder: Embedder;
}
/**
 * Scan disk and DB in parallel and produce a sync plan.
 */
export declare function planSync(targetPath: string, excludePaths: string[], vectorStore: VectorStore): Promise<{
    plan: SyncPlan;
    diskFiles: Map<string, SyncFileMetadata>;
}>;
/**
 * Execute a sync plan: prune deleted files, upsert changed files, optimize once.
 * Continues past per-file failures; honors signal between files.
 */
export declare function executeSyncPlan(plan: SyncPlan, diskFiles: Map<string, SyncFileMetadata>, deps: SyncDeps, options?: {
    signal?: AbortSignal | undefined;
    onEvent?: ((event: SyncEvent) => void) | undefined;
}): Promise<SyncStats>;
//# sourceMappingURL=sync-runner.d.ts.map