import type { TextChunk } from './index.js';
/**
 * Semantic Chunker configuration
 * Based on paper recommendations: hardThreshold=0.6, initConst=1.5, c=0.9
 */
export interface SemanticChunkerConfig {
    /** Hard threshold for minimum similarity (default: 0.6) */
    hardThreshold: number;
    /** Initial constant for first sentence pair (default: 1.5) */
    initConst: number;
    /** Scaling constant for threshold calculation (default: 0.9) */
    c: number;
    /** Minimum chunk length in characters (default: 50) */
    minChunkLength: number;
}
/**
 * Embedder interface for generating embeddings
 */
export interface EmbedderInterface {
    embedBatch(texts: string[]): Promise<number[][]>;
}
/**
 * Check if a chunk is garbage (should be filtered out)
 *
 * Criteria (language-agnostic):
 * 1. Empty after trimming
 * 2. Contains alphanumeric -> valid content (keep)
 * 3. Only decoration characters (----, ====, etc.) -> garbage
 * 4. Single character repeated >80% of text -> garbage
 *
 * Note: Applied after minChunkLength filter
 *
 * @param text - Chunk text to check
 * @returns true if chunk is garbage and should be removed
 */
export declare function isGarbageChunk(text: string): boolean;
/** Default minimum chunk length in characters */
export declare const DEFAULT_MIN_CHUNK_LENGTH = 50;
/**
 * Semantic chunker using Max-Min algorithm
 *
 * The algorithm groups consecutive sentences based on semantic similarity:
 * 1. Split text into sentences
 * 2. Generate embeddings for all sentences
 * 3. For each sentence, decide whether to add to current chunk or start new chunk
 * 4. Decision is based on comparing max similarity with new sentence vs min similarity within chunk
 *
 * Key insight: A sentence belongs to a chunk if its maximum similarity to any chunk member
 * is greater than the minimum similarity between existing chunk members (with threshold adjustment)
 */
export declare class SemanticChunker {
    private readonly config;
    constructor(config?: Partial<SemanticChunkerConfig>);
    /**
     * Split text into semantically coherent chunks
     *
     * @param text - The text to chunk
     * @param embedder - Embedder to generate sentence embeddings
     * @returns Array of text chunks
     */
    chunkText(text: string, embedder: EmbedderInterface): Promise<TextChunk[]>;
    /**
     * Group sentences into chunks using Max-Min algorithm
     */
    private groupSentences;
    /**
     * Decide if a sentence should be added to the current chunk
     * Based on Max-Min algorithm from the paper
     */
    private shouldAddToChunk;
    /**
     * Get minimum pairwise similarity within a chunk.
     * Only compares the last WINDOW_SIZE sentences for O(1) complexity.
     * This approximation is valid because recent sentences are most relevant
     * for determining chunk coherence (per Max-Min paper's experimental setup).
     */
    private getMinSimilarity;
    /**
     * Get maximum similarity between a sentence and any sentence in the chunk
     */
    private getMaxSimilarity;
    /**
     * Calculate dynamic threshold based on chunk size
     * threshold = max(c * minSim * sigmoid(|C|), hardThreshold)
     */
    private calculateThreshold;
    /**
     * Sigmoid function
     */
    private sigmoid;
    /**
     * Calculate cosine similarity between two vectors
     * Public for testing
     */
    cosineSimilarity(vec1: number[], vec2: number[]): number;
}
//# sourceMappingURL=semantic-chunker.d.ts.map