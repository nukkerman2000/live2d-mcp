import type { EmbedderInterface } from '../chunker/semantic-chunker.js';
export type { EmbedderInterface };
/**
 * Text item with position information from PDF
 */
interface TextItemWithPosition {
    text: string;
    x: number;
    y: number;
    fontSize: number;
    hasEOL: boolean;
    fontName?: string;
    fontWeight?: string;
}
/**
 * Page data containing positioned text items
 */
export interface PageData {
    pageNum: number;
    items: TextItemWithPosition[];
    pageHeight?: number;
}
/**
 * Join filtered pages into text
 *
 * @param pages - Filtered page data
 * @returns Joined text with proper line breaks
 */
export declare function joinFilteredPages(pages: PageData[]): string;
/**
 * Configuration for sentence-level pattern detection
 */
interface SentencePatternConfig {
    /** Similarity threshold for pattern detection (default: 0.85) */
    similarityThreshold: number;
    /** Minimum pages required for pattern detection (default: 3) */
    minPages: number;
    /** Number of pages to sample from center for pattern detection (default: 5) */
    samplePages: number;
    /** Block attribute hints for boosted threshold (from detectBlockAttributeCandidates) */
    blockHints?: BlockAttributeHints;
    /** Boosted similarity threshold when block hints match (default: 0.75) */
    boostedThreshold?: number;
}
/**
 * Hints for block-level header/footer detection based on font attributes
 */
export interface BlockAttributeHints {
    medianFontSize: number;
    headerCandidateYs: Set<number>;
    footerCandidateYs: Set<number>;
}
/**
 * Detect candidate header/footer lines based on font size and Y position
 *
 * Stage 1 of the 2-stage header/footer detection:
 * 1. Sample center pages (same logic as detectSentencePatterns)
 * 2. Calculate median font size from all items across sampled pages
 * 3. Identify header candidates: fontSize < medianFontSize * 0.7 AND y > pageHeight * 0.9
 * 4. Identify footer candidates: fontSize < medianFontSize * 0.7 AND y < pageHeight * 0.1
 *
 * @param pages - Array of page data
 * @param config - Configuration options (minPages, samplePages)
 * @returns Block attribute hints with candidate Y positions
 */
export declare function detectBlockAttributeCandidates(pages: PageData[], config?: Partial<Pick<SentencePatternConfig, 'minPages' | 'samplePages'>>): BlockAttributeHints;
/**
 * Result of sentence-level pattern detection
 */
interface SentencePatternResult {
    /** Whether first sentences should be removed (detected as header) */
    removeFirstSentence: boolean;
    /** Whether last sentences should be removed (detected as footer) */
    removeLastSentence: boolean;
    /** Median similarity of first sentences */
    headerSimilarity: number;
    /** Median similarity of last sentences */
    footerSimilarity: number;
}
/**
 * Detect header/footer patterns at sentence level
 *
 * Algorithm:
 * 1. Sample pages from the CENTER of the document (guaranteed to be content pages)
 * 2. Split each page into sentences with Y coordinate
 * 3. Collect first/last sentences from sampled pages
 * 4. Embed and calculate median pairwise similarity
 * 5. If similarity > threshold, mark as header/footer
 *
 * Key insight: Middle pages are always content pages (cover, TOC, index are at edges).
 * Using median instead of mean provides robustness against outliers.
 *
 * This approach handles variable content like page numbers ("7 of 75")
 * by using semantic similarity instead of exact text matching.
 *
 * @param pages - Array of page data
 * @param embedder - Embedder for generating embeddings
 * @param config - Configuration options
 * @returns Detection result
 */
export declare function detectSentencePatterns(pages: PageData[], embedder: EmbedderInterface, config?: Partial<SentencePatternConfig>): Promise<SentencePatternResult>;
/**
 * Filter page boundary sentences and return per-page filtered text
 *
 * This is the main entry point for sentence-level header/footer filtering.
 * It detects and removes repeating sentence patterns at page boundaries.
 * Returns an array of filtered text per page, preserving page boundaries.
 *
 * Use this instead of joinFilteredPages when embedder is available.
 *
 * @param pages - Array of page data
 * @param embedder - Embedder for generating embeddings
 * @param config - Configuration options
 * @returns Array of filtered text strings, one per page
 */
export declare function filterPageBoundarySentences(pages: PageData[], embedder: EmbedderInterface, config?: Partial<SentencePatternConfig>): Promise<string[]>;
//# sourceMappingURL=pdf-filter.d.ts.map