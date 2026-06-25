// Embedder implementation with Transformers.js
import { env, pipeline } from '@huggingface/transformers';
// ============================================
// Error Classes
// ============================================
/**
 * Embedding generation error
 */
export class EmbeddingError extends Error {
    cause;
    constructor(message, cause) {
        super(message);
        this.cause = cause;
        this.name = 'EmbeddingError';
    }
}
// ============================================
// Embedder Class
// ============================================
/**
 * Embedding generation class using Transformers.js
 *
 * Responsibilities:
 * - Generate embedding vectors (dimension depends on model)
 * - Transformers.js wrapper
 * - Batch processing (size 8)
 */
export class Embedder {
    // Using unknown to avoid TS2590 (union type too complex with @types/jsdom)
    model = null;
    initPromise = null;
    config;
    constructor(config) {
        this.config = config;
    }
    /**
     * Release resources held by the Embedder pipeline
     */
    async dispose() {
        const model = this.model;
        if (model && typeof model.dispose === 'function') {
            try {
                await model.dispose();
            }
            catch (error) {
                console.error('Error disposing embedder model:', error);
            }
        }
        this.model = null;
        this.initPromise = null;
    }
    /**
     * Initialize Transformers.js model
     */
    async initialize() {
        // Skip if already initialized
        if (this.model) {
            return;
        }
        // Set cache directory BEFORE creating pipeline
        env.cacheDir = this.config.cacheDir;
        // No fallback — if the requested device fails, init throws.
        const device = this.config.device || 'cpu';
        console.error(`Embedder: Setting cache directory to "${this.config.cacheDir}"`);
        console.error(`Embedder: Loading model "${this.config.modelPath}" on device "${device}"...`);
        try {
            this.model = await pipeline('feature-extraction', this.config.modelPath, {
                dtype: 'fp32',
                device: device,
            });
            console.error(`Embedder: Model loaded successfully (device=${device})`);
        }
        catch (error) {
            // Don't prepend "device=X" — the prior stderr line already says which
            // device was attempted, and transformers.js' own errors typically
            // include the device name. Just re-type the error.
            throw new EmbeddingError(error.message, error);
        }
    }
    /**
     * Ensure model is initialized (lazy initialization)
     * This method is called automatically by embed() and embedBatch()
     */
    async ensureInitialized() {
        // Already initialized
        if (this.model) {
            return;
        }
        // Initialization already in progress, wait for it
        if (this.initPromise) {
            await this.initPromise;
            return;
        }
        console.error('Embedder: First use detected. Initializing model (downloading ~90MB, may take 1-2 minutes)...');
        this.initPromise = this.initialize().catch((error) => {
            // Clear initPromise on failure to allow retry on the next call.
            this.initPromise = null;
            throw error;
        });
        await this.initPromise;
    }
    /**
     * Convert single text to embedding vector
     *
     * @param text - Text
     * @returns Embedding vector (dimension depends on model)
     */
    async embed(text) {
        // Reject empty input before paying for model init.
        if (text.length === 0) {
            throw new EmbeddingError('Cannot generate embedding for empty text');
        }
        // Lazy initialization: initialize on first use if not already initialized
        await this.ensureInitialized();
        try {
            const options = { pooling: 'mean', normalize: true };
            const modelCall = this.model;
            const output = await modelCall(text, options);
            // Access raw data via .data property
            const embedding = Array.from(output.data);
            return embedding;
        }
        catch (error) {
            if (error instanceof EmbeddingError) {
                throw error;
            }
            throw new EmbeddingError(`Failed to generate embedding: ${error.message}`, error);
        }
    }
    /**
     * Convert multiple texts to embedding vectors with batch processing
     *
     * @param texts - Array of texts
     * @returns Array of embedding vectors (dimension depends on model)
     */
    async embedBatch(texts) {
        // Nothing to embed → skip model init entirely.
        if (texts.length === 0) {
            return [];
        }
        // Lazy initialization: initialize on first use if not already initialized
        await this.ensureInitialized();
        try {
            const embeddings = [];
            // Process in batches according to batch size
            for (let i = 0; i < texts.length; i += this.config.batchSize) {
                const batch = texts.slice(i, i + this.config.batchSize);
                const batchEmbeddings = await Promise.all(batch.map((text) => this.embed(text)));
                embeddings.push(...batchEmbeddings);
            }
            return embeddings;
        }
        catch (error) {
            if (error instanceof EmbeddingError) {
                throw error;
            }
            throw new EmbeddingError(`Failed to generate batch embeddings: ${error.message}`, error);
        }
    }
}
//# sourceMappingURL=index.js.map