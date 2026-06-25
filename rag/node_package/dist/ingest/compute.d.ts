import type { SemanticChunker, TextChunk } from '../chunker/index.js';
import type { EmbedderInterface } from '../chunker/semantic-chunker.js';
/**
 * Result of the shared chunk + embed computation.
 *
 * - `chunks` is the result of a single `chunker.chunkText` call.
 * - `embeddings` is the result of `embedder.embedBatch(chunks.map(c => c.text))`
 *   and has the same length as `chunks`.
 * - `title` is passed through unchanged when non-null. When the caller
 *   passes `null`, the caller is responsible for deriving the title from
 *   `chunks[0]?.text` after this function returns (used by the visual
 *   PDF path in later phases).
 */
export interface BuildChunksAndEmbeddingsResult {
    chunks: TextChunk[];
    embeddings: number[][];
    title: string | null;
}
/**
 * Compute semantic chunks and their embeddings for already-extracted text.
 *
 * Calls `chunker.chunkText` exactly once and then
 * `embedder.embedBatch` on the resulting chunk texts. Does NOT touch
 * `vectorStore`. Does NOT fail-fast on zero chunks — callers decide
 * how to handle an empty result (the MCP handler throws `McpError`;
 * the CLI logs a warning and returns 0).
 *
 * Errors from the chunker or embedder propagate verbatim.
 *
 * @param text  Already-extracted document text (parser output, raw-data
 *              payload, or joined visual-enriched per-page text).
 * @param title Display-only document title. Pass-through when non-null;
 *              `null` signals that the caller will derive the title
 *              from `chunks[0]?.text` after this function returns.
 * @param chunker  Semantic chunker instance (owned by the caller).
 * @param embedder Embedder implementing the structural `EmbedderInterface`
 *                 (only `embedBatch` is required).
 */
export declare function buildChunksAndEmbeddings(text: string, title: string | null, chunker: SemanticChunker, embedder: EmbedderInterface): Promise<BuildChunksAndEmbeddingsResult>;
//# sourceMappingURL=compute.d.ts.map