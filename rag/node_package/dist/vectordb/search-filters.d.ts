import type { GroupingMode, SearchResult } from './types.js';
/**
 * Standard deviation multiplier for detecting group boundaries.
 * A gap is considered a "boundary" if it exceeds mean + k*std.
 * Value of 1.5 means gaps > 1.5 standard deviations above mean are boundaries.
 */
export declare const GROUPING_BOUNDARY_STD_MULTIPLIER = 1.5;
/**
 * Apply grouping algorithm to filter results by detecting group boundaries.
 *
 * Uses statistical threshold (mean + k*std) to identify significant gaps (group boundaries).
 * - 'similar': Returns only the first group (cuts at first boundary)
 * - 'related': Returns up to 2 groups (cuts at second boundary)
 *
 * @param results - Search results sorted by distance (ascending)
 * @param mode - Grouping mode ('similar' = 1 group, 'related' = 2 groups)
 * @returns Filtered results
 */
export declare function applyGrouping(results: SearchResult[], mode: GroupingMode): SearchResult[];
/**
 * Apply file-based filter to limit results to chunks from the top N files.
 *
 * Ranks files by their best (lowest distance) chunk score and keeps only
 * chunks belonging to the top `maxFiles` files.
 *
 * @param results - Search results sorted by distance (ascending)
 * @param maxFiles - Maximum number of files to keep
 * @returns Filtered results preserving original order
 */
export declare function applyFileFilter(results: SearchResult[], maxFiles: number): SearchResult[];
/**
 * Apply keyword boost to rerank vector search results
 * Uses multiplicative formula: final_distance = distance / (1 + keyword_normalized * weight)
 *
 * This proportional boost ensures:
 * - Keyword matches improve ranking without dominating semantic similarity
 * - Documents without keyword matches keep their original vector distance
 * - Higher weight = stronger influence of keyword matching
 *
 * @param vectorResults - Results from vector search (already filtered by maxDistance/grouping)
 * @param ftsResults - Raw FTS results with BM25 scores
 * @param weight - Boost weight (0-1, from hybridWeight config)
 */
export declare function applyKeywordBoost(vectorResults: SearchResult[], ftsResults: Record<string, unknown>[], weight: number): SearchResult[];
//# sourceMappingURL=search-filters.d.ts.map