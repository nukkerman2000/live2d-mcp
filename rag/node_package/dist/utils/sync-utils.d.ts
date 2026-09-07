/**
 * Synchronization utilities for incremental updates
 */
/**
 * File metadata for sync diffing
 */
export interface SyncFileMetadata {
    contentHash: string;
}
/**
 * Batch sync plan
 */
export interface SyncPlan {
    upsertList: string[];
    pruneList: string[];
    skipList: string[];
}
/**
 * Compare disk state with database state to create a sync plan.
 *
 * @param diskFiles - Map of filePath to disk metadata
 * @param dbFiles - Map of filePath to database metadata
 * @returns SyncPlan categorized by action
 */
export declare function createSyncPlan(diskFiles: Map<string, SyncFileMetadata>, dbFiles: Map<string, SyncFileMetadata>): SyncPlan;
//# sourceMappingURL=sync-utils.d.ts.map