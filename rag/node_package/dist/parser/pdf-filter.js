// PDF Header/Footer Filter
// - Detects and removes repeating patterns across pages
// - Semantic similarity-based header/footer detection (sentence-level)
import { splitIntoSentences } from '../chunker/sentence-splitter.js';
// ============================================
// Text Joining
// ============================================
/**
 * Join page items into text
 *
 * Groups items by Y coordinate (same Y = same line),
 * sorts each group by X coordinate (left to right),
 * then joins groups with newlines (top to bottom).
 */
function joinPageItems(items) {
    // Group by Y coordinate (rounded to handle minor variations)
    const yGroups = new Map();
    for (const item of items) {
        const y = Math.round(item.y);
        const group = yGroups.get(y) || [];
        group.push(item);
        yGroups.set(y, group);
    }
    // Sort groups by Y descending (top to bottom), items by X ascending (left to right)
    return [...yGroups.entries()]
        .sort((a, b) => b[0] - a[0])
        .map(([_, group]) => group
        .sort((a, b) => a.x - b.x)
        .map((i) => i.text)
        .join(' '))
        .join('\n')
        .trim();
}
/**
 * Join filtered pages into text
 *
 * @param pages - Filtered page data
 * @returns Joined text with proper line breaks
 */
export function joinFilteredPages(pages) {
    return pages
        .map((page) => joinPageItems(page.items))
        .filter((text) => text.length > 0)
        .join('\n\n');
}
/**
 * Split page items into sentences with Y coordinate
 *
 * 1. Join items into text (preserving item boundaries)
 * 2. Split into sentences using splitIntoSentences
 * 3. Map each sentence to the Y coordinate of its first item
 * 4. Merge sentences with same Y coordinate
 *
 * @param items - Text items with position
 * @returns Sentences with Y coordinate (merged by Y)
 */
function splitItemsIntoSentencesWithY(items) {
    if (items.length === 0)
        return [];
    // Sort items by Y descending, then X ascending (reading order)
    const sortedItems = [...items].sort((a, b) => {
        const yDiff = b.y - a.y;
        if (Math.abs(yDiff) > 1)
            return yDiff;
        return a.x - b.x;
    });
    // Build text and track character positions to item mapping
    const charToItem = [];
    let fullText = '';
    let prevY = null;
    for (const item of sortedItems) {
        // Insert newline when Y coordinate changes (different line)
        // This matches joinPageItems behavior: same Y = space, different Y = newline
        if (prevY !== null && Math.abs(prevY - item.y) > 1) {
            fullText = `${fullText.trimEnd()}\n`;
        }
        charToItem.push({ start: fullText.length, item });
        fullText += `${item.text} `;
        prevY = item.y;
    }
    // Split into sentences
    const sentences = splitIntoSentences(fullText);
    // Map each sentence to Y coordinate of its first character's item
    const sentencesWithY = [];
    let searchStart = 0;
    for (const sentence of sentences) {
        // Find where this sentence starts in fullText
        const sentenceStart = fullText.indexOf(sentence.trim(), searchStart);
        if (sentenceStart === -1)
            continue;
        // Find the item that contains this position
        let firstItemY = sortedItems[0]?.y ?? 0;
        for (let i = charToItem.length - 1; i >= 0; i--) {
            const entry = charToItem[i];
            if (entry && entry.start <= sentenceStart) {
                firstItemY = Math.round(entry.item.y);
                break;
            }
        }
        sentencesWithY.push({ text: sentence, y: firstItemY });
        searchStart = sentenceStart + sentence.length;
    }
    // Merge sentences with same Y coordinate
    return mergeSentencesByY(sentencesWithY);
}
/**
 * Merge sentences with same Y coordinate
 *
 * @param sentences - Sentences with Y coordinate
 * @returns Merged sentences (same Y = one sentence)
 */
function mergeSentencesByY(sentences) {
    if (sentences.length === 0)
        return [];
    const merged = [];
    let current = null;
    for (const sentence of sentences) {
        if (current === null) {
            current = { ...sentence };
        }
        else if (current.y === sentence.y) {
            // Same Y: merge text
            current.text += ` ${sentence.text}`;
        }
        else {
            // Different Y: push current and start new
            merged.push(current);
            current = { ...sentence };
        }
    }
    if (current !== null) {
        merged.push(current);
    }
    return merged;
}
// ============================================
// Sentence-Level Header/Footer Detection
// ============================================
/**
 * Calculate cosine similarity between two vectors
 */
function cosineSimilarity(vec1, vec2) {
    if (vec1.length !== vec2.length || vec1.length === 0) {
        return 0;
    }
    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;
    for (let i = 0; i < vec1.length; i++) {
        const v1 = vec1[i] ?? 0;
        const v2 = vec2[i] ?? 0;
        dotProduct += v1 * v2;
        norm1 += v1 * v1;
        norm2 += v2 * v2;
    }
    const denominator = Math.sqrt(norm1) * Math.sqrt(norm2);
    if (denominator === 0)
        return 0;
    return dotProduct / denominator;
}
/**
 * Calculate median pairwise similarity for a list of embeddings
 *
 * Uses median instead of mean for robustness against outliers.
 * This handles cases where some pages have different header content
 * (e.g., chapter title changes) that would otherwise drag down the average.
 */
function medianPairwiseSimilarity(embeddings) {
    if (embeddings.length < 2)
        return 1.0;
    const similarities = [];
    for (let i = 0; i < embeddings.length; i++) {
        for (let j = i + 1; j < embeddings.length; j++) {
            const embI = embeddings[i];
            const embJ = embeddings[j];
            if (embI && embJ) {
                similarities.push(cosineSimilarity(embI, embJ));
            }
        }
    }
    if (similarities.length === 0)
        return 0;
    // Sort and find median
    similarities.sort((a, b) => a - b);
    const mid = Math.floor(similarities.length / 2);
    if (similarities.length % 2 === 0) {
        // Even: average of two middle values
        return ((similarities[mid - 1] ?? 0) + (similarities[mid] ?? 0)) / 2;
    }
    // Odd: middle value
    return similarities[mid] ?? 0;
}
/**
 * Sample pages from the center of the document
 *
 * Center pages are guaranteed to be content (not cover, TOC, or index).
 */
function sampleCenterPages(pages, sampleSize) {
    const centerIndex = Math.floor(pages.length / 2);
    const halfSample = Math.floor(sampleSize / 2);
    const startIndex = Math.max(0, centerIndex - halfSample);
    const endIndex = Math.min(pages.length, startIndex + sampleSize);
    return pages.slice(startIndex, endIndex);
}
/** Default configuration for sentence-level pattern detection */
const DEFAULT_SENTENCE_PATTERN_CONFIG = {
    similarityThreshold: 0.85,
    minPages: 3,
    samplePages: 5,
    boostedThreshold: 0.75,
};
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
export function detectBlockAttributeCandidates(pages, config = {}) {
    const cfg = { ...DEFAULT_SENTENCE_PATTERN_CONFIG, ...config };
    const emptyResult = {
        medianFontSize: 0,
        headerCandidateYs: new Set(),
        footerCandidateYs: new Set(),
    };
    if (pages.length < cfg.minPages)
        return emptyResult;
    const samplePages = sampleCenterPages(pages, cfg.samplePages);
    // Collect all font sizes
    const fontSizes = [];
    for (const page of samplePages) {
        for (const item of page.items) {
            if (item.fontSize > 0)
                fontSizes.push(item.fontSize);
        }
    }
    if (fontSizes.length === 0)
        return emptyResult;
    // Calculate median font size
    fontSizes.sort((a, b) => a - b);
    const mid = Math.floor(fontSizes.length / 2);
    const medianFontSize = fontSizes.length % 2 === 0 ? (fontSizes[mid - 1] + fontSizes[mid]) / 2 : fontSizes[mid];
    if (medianFontSize === 0)
        return { ...emptyResult, medianFontSize };
    // Use actual page height if available, otherwise estimate from max Y
    const firstPageWithHeight = samplePages.find((p) => p.pageHeight != null);
    let pageHeight;
    if (firstPageWithHeight?.pageHeight) {
        pageHeight = firstPageWithHeight.pageHeight;
    }
    else {
        let maxY = 0;
        for (const page of samplePages) {
            for (const item of page.items) {
                if (item.y > maxY)
                    maxY = item.y;
            }
        }
        pageHeight = maxY;
    }
    if (pageHeight === 0)
        return { ...emptyResult, medianFontSize };
    const fontSizeThreshold = medianFontSize * 0.7;
    const headerCandidateYs = new Set();
    const footerCandidateYs = new Set();
    // Scan items: small font + extreme Y position = candidate
    for (const page of samplePages) {
        for (const item of page.items) {
            if (item.fontSize >= fontSizeThreshold)
                continue;
            const roundedY = Math.round(item.y);
            // Header: top 10% of page (large Y values, since Y is inverted)
            if (item.y > pageHeight * 0.9) {
                headerCandidateYs.add(roundedY);
            }
            // Footer: bottom 10% of page (small Y values)
            if (item.y < pageHeight * 0.1) {
                footerCandidateYs.add(roundedY);
            }
        }
    }
    return { medianFontSize, headerCandidateYs, footerCandidateYs };
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
export async function detectSentencePatterns(pages, embedder, config = {}) {
    const cfg = { ...DEFAULT_SENTENCE_PATTERN_CONFIG, ...config };
    const result = {
        removeFirstSentence: false,
        removeLastSentence: false,
        headerSimilarity: 0,
        footerSimilarity: 0,
    };
    // Need minimum pages to detect patterns reliably
    if (pages.length < cfg.minPages) {
        return result;
    }
    // 1. Sample pages from the CENTER of the document
    const samplePages = sampleCenterPages(pages, cfg.samplePages);
    const startIndex = pages.indexOf(samplePages[0]);
    const endIndex = startIndex + samplePages.length;
    // 2. Split each page into sentences with Y coordinate (merged by Y)
    const pageSentences = samplePages.map((page) => splitItemsIntoSentencesWithY(page.items));
    // 3. Collect first and last sentences from sampled pages
    const firstSentences = [];
    const lastSentences = [];
    for (const sentences of pageSentences) {
        if (sentences.length > 0) {
            firstSentences.push(sentences[0].text);
            if (sentences.length > 1) {
                lastSentences.push(sentences[sentences.length - 1].text);
            }
        }
    }
    // 5. Detect header pattern (sampled first sentences are semantically similar)
    if (firstSentences.length >= cfg.minPages) {
        const embeddings = await embedder.embedBatch(firstSentences);
        const medianSim = medianPairwiseSimilarity(embeddings);
        result.headerSimilarity = medianSim;
        // Determine effective threshold (boosted if block hints match)
        let headerThreshold = cfg.similarityThreshold;
        if (cfg.blockHints) {
            const firstSentenceYs = pageSentences
                .filter((s) => s.length > 0)
                .map((s) => Math.round(s[0].y));
            const hasBlockHintMatch = firstSentenceYs.some((y) => cfg.blockHints.headerCandidateYs.has(y));
            if (hasBlockHintMatch) {
                headerThreshold = cfg.boostedThreshold ?? 0.75;
            }
        }
        if (medianSim >= headerThreshold) {
            result.removeFirstSentence = true;
            console.error(`Sentence header detected: sampled ${firstSentences.length} center pages (${startIndex + 1}-${endIndex}), median similarity: ${medianSim.toFixed(3)}`);
        }
    }
    // 6. Detect footer pattern (sampled last sentences are semantically similar)
    if (lastSentences.length >= cfg.minPages) {
        const embeddings = await embedder.embedBatch(lastSentences);
        const medianSim = medianPairwiseSimilarity(embeddings);
        result.footerSimilarity = medianSim;
        // Determine effective threshold (boosted if block hints match)
        let footerThreshold = cfg.similarityThreshold;
        if (cfg.blockHints) {
            const lastSentenceYs = pageSentences
                .filter((s) => s.length > 1)
                .map((s) => Math.round(s[s.length - 1].y));
            const hasBlockHintMatch = lastSentenceYs.some((y) => cfg.blockHints.footerCandidateYs.has(y));
            if (hasBlockHintMatch) {
                footerThreshold = cfg.boostedThreshold ?? 0.75;
            }
        }
        if (medianSim >= footerThreshold) {
            result.removeLastSentence = true;
            console.error(`Sentence footer detected: sampled ${lastSentences.length} center pages (${startIndex + 1}-${endIndex}), median similarity: ${medianSim.toFixed(3)}`);
        }
    }
    return result;
}
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
export async function filterPageBoundarySentences(pages, embedder, config = {}) {
    const cfg = { ...DEFAULT_SENTENCE_PATTERN_CONFIG, ...config };
    // Need minimum pages to detect patterns
    if (pages.length < cfg.minPages) {
        return pages.map((page) => joinFilteredPages([page]));
    }
    // Detect block attribute candidates for boosted threshold
    const blockHints = detectBlockAttributeCandidates(pages, cfg);
    // Detect patterns (with block hints for boosted threshold)
    const patterns = await detectSentencePatterns(pages, embedder, { ...cfg, blockHints });
    // If no patterns detected, return normally joined text per page
    if (!patterns.removeFirstSentence && !patterns.removeLastSentence) {
        return pages.map((page) => joinFilteredPages([page]));
    }
    // Split each page into sentences with Y coordinate (merged by Y)
    const pageSentences = pages.map((page) => splitItemsIntoSentencesWithY(page.items));
    // Remove detected patterns from page sentences
    const cleanedPageSentences = pageSentences.map((sentences) => {
        let cleaned = [...sentences];
        if (patterns.removeFirstSentence && cleaned.length > 0) {
            cleaned = cleaned.slice(1);
        }
        if (patterns.removeLastSentence && cleaned.length > 0) {
            cleaned = cleaned.slice(0, -1);
        }
        return cleaned;
    });
    // Return per-page filtered text
    return cleanedPageSentences.map((sentences) => sentences.map((s) => s.text).join(' '));
}
//# sourceMappingURL=pdf-filter.js.map