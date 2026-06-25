// Shared sync runner — planning and execution used by both CLI and MCP server
import { collectFiles, ingestSingleFile } from '../cli/ingest.js';
import { createSyncPlan } from './sync-utils.js';
/**
 * Scan disk and DB in parallel and produce a sync plan.
 */
export async function planSync(targetPath, excludePaths, vectorStore) {
    const [diskFileInfos, dbFiles] = await Promise.all([
        collectFiles(targetPath, excludePaths),
        vectorStore.getFileManifest(),
    ]);
    const diskFiles = new Map(diskFileInfos.map((f) => [f.filePath, { contentHash: f.contentHash }]));
    const plan = createSyncPlan(diskFiles, dbFiles);
    return { plan, diskFiles };
}
/**
 * Execute a sync plan: prune deleted files, upsert changed files, optimize once.
 * Continues past per-file failures; honors signal between files.
 */
export async function executeSyncPlan(plan, diskFiles, deps, options = {}) {
    const { vectorStore, parser, chunker, embedder } = deps;
    const { signal, onEvent } = options;
    const stats = {
        upsertCount: 0,
        pruneCount: 0,
        skipCount: plan.skipList.length,
        skippedEmpty: 0,
        failedCount: 0,
        totalChunks: 0,
    };
    if (plan.pruneList.length > 0) {
        if (signal?.aborted) {
            onEvent?.({ type: 'aborted', completed: 0, total: plan.upsertList.length });
            return stats;
        }
        onEvent?.({ type: 'prune_start', count: plan.pruneList.length });
        await vectorStore.deleteFiles(plan.pruneList);
        stats.pruneCount = plan.pruneList.length;
    }
    for (let i = 0; i < plan.upsertList.length; i++) {
        if (signal?.aborted) {
            onEvent?.({ type: 'aborted', completed: stats.upsertCount, total: plan.upsertList.length });
            return stats;
        }
        const filePath = plan.upsertList[i];
        const index = i + 1;
        const total = plan.upsertList.length;
        onEvent?.({ type: 'file_start', filePath, index, total });
        try {
            const result = await ingestSingleFile(filePath, parser, chunker, embedder, vectorStore, diskFiles.get(filePath)?.contentHash, signal);
            if (result.status === 'empty') {
                stats.skippedEmpty++;
                onEvent?.({ type: 'file_empty', filePath, index, total });
            }
            else {
                stats.upsertCount++;
                stats.totalChunks += result.chunkCount;
                onEvent?.({ type: 'file_ok', filePath, index, total, chunkCount: result.chunkCount });
            }
        }
        catch (error) {
            stats.failedCount++;
            const message = error instanceof Error ? error.message : String(error);
            onEvent?.({ type: 'file_failed', filePath, index, total, error: message });
        }
    }
    if (plan.upsertList.length > 0 || plan.pruneList.length > 0) {
        await vectorStore.optimize();
    }
    onEvent?.({ type: 'complete', stats });
    return stats;
}
//# sourceMappingURL=sync-runner.js.map