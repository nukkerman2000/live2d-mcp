/**
 * Split text into sentences using Intl.Segmenter
 *
 * Uses the Unicode Text Segmentation standard (UAX #29) via Intl.Segmenter.
 * This provides multilingual support for sentence boundary detection.
 *
 * Note: Intl.Segmenter may split on abbreviations like "Mr." or "e.g."
 * These edge cases are acceptable for semantic chunking as:
 * 1. Short fragments will be grouped with adjacent sentences by similarity
 * 2. Fragments below minChunkLength are filtered out
 *
 * @param text - The text to split into sentences
 * @returns Array of sentences
 */
export declare function splitIntoSentences(text: string): string[];
//# sourceMappingURL=sentence-splitter.d.ts.map