/**
 * Embedder configuration
 */
export interface EmbedderConfig {
    /** HuggingFace model path */
    modelPath: string;
    /** Batch size */
    batchSize: number;
    /** Model cache directory */
    cacheDir: string;
    /** Device type */
    device?: string;
}
/**
 * Embedding generation error
 */
export declare class EmbeddingError extends Error {
    readonly cause?: Error | undefined;
    constructor(message: string, cause?: Error | undefined);
}
/**
 * Embedding generation class using Transformers.js
 *
 * Responsibilities:
 * - Generate embedding vectors (dimension depends on model)
 * - Transformers.js wrapper
 * - Batch processing (size 8)
 */
export declare class Embedder {
    private model;
    private initPromise;
    private readonly config;
    constructor(config: EmbedderConfig);
    /**
     * Release resources held by the Embedder pipeline
     */
    dispose(): Promise<void>;
    /**
     * Initialize Transformers.js model
     */
    initialize(): Promise<void>;
    /**
     * Ensure model is initialized (lazy initialization)
     * This method is called automatically by embed() and embedBatch()
     */
    private ensureInitialized;
    /**
     * Convert single text to embedding vector
     *
     * @param text - Text
     * @returns Embedding vector (dimension depends on model)
     */
    embed(text: string): Promise<number[]>;
    /**
     * Convert multiple texts to embedding vectors with batch processing
     *
     * @param texts - Array of texts
     * @returns Array of embedding vectors (dimension depends on model)
     */
    embedBatch(texts: string[]): Promise<number[][]>;
}
//# sourceMappingURL=index.d.ts.map