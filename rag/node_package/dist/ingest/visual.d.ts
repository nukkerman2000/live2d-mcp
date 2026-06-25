import type { SemanticChunker, TextChunk } from '../chunker/index.js';
import type { EmbedderInterface } from '../chunker/semantic-chunker.js';
import type { DocumentParser } from '../parser/index.js';
import type { QualityProfile } from '../pdf-visual/types.js';
/**
 * Minimal parser surface consumed by `prepareVisualPdfChunks`. Only the
 * `parsePdfPages` method is required; we reuse `DocumentParser`'s type so the
 * shape stays in sync automatically when the parser contract evolves (e.g.,
 * a new optional field on `pages[]`). `import type` keeps this a type-only
 * dependency — no runtime import of the parser class and no bundle/NFR-1
 * impact. Both `DocumentParser` (production) and parser mocks satisfy this.
 */
export interface VisualPdfParser {
    parsePdfPages: DocumentParser['parsePdfPages'];
}
/**
 * Captioner configuration forwarded to `pdf-visual.createCaptioner`. The
 * `profile` selects the underlying VLM family (`fast` = SmolVLM-256M,
 * `quality` = Qwen2.5-VL-3B); the actual model identifier lives inside the
 * profile module.
 */
export interface CaptionerConfig {
    profile: QualityProfile;
    cacheDir: string;
    /** Execution device passed through to the captioner model. */
    device?: string | undefined;
}
/**
 * Result of the shared visual-PDF computation.
 *
 * - `chunks` and `embeddings` come from `buildChunksAndEmbeddings(...)` on
 *   the joined enriched-page text. They have the same length.
 * - `title` is the resolved display title from `extractPdfTitle(...)`, or
 *   `null` when no title can be derived (matches the existing inline-flow
 *   semantics).
 */
export interface PrepareVisualPdfChunksResult {
    chunks: TextChunk[];
    embeddings: number[][];
    title: string | null;
    /**
     * The joined enriched-page text that was fed into the chunker. Exposed so
     * callers can use its length for `metadata.fileSize` (the existing
     * inline-flow contract — the joined text length is the post-enrichment,
     * pre-chunking size, not the on-disk PDF byte size).
     */
    text: string;
}
/**
 * Run the visual-PDF enrichment flow end-to-end and return the chunks +
 * embeddings + title for the caller to persist.
 *
 * Steps (matches the inline flow in `ingestSingleFile` and `handleIngestFile`):
 *   1. Dynamic-import `pdf-visual` (NFR-1 discipline — loaded only here).
 *   2. `createCaptioner(captionerConfig)`.
 *   3. `parser.parsePdfPages(filePath, embedder)` → `{ doc, metadataTitle, pages }`.
 *   4. `detectVisualCandidates(pages)`.
 *   5. `enrichPagesWithCaptions(pages, candidates, doc, captioner)`.
 *   6. Join enriched page texts with `\n\n` (DD-documented join).
 *   7. `buildChunksAndEmbeddings(text, null, chunker, embedder)`.
 *   8. `extractPdfTitle(metadataTitle, chunks[0]?.text, basename(filePath),
 *      pages[0]?.page1FontHint)` (matches DD §Title resolution).
 *   9. `doc.destroy()` in `finally` so the mupdf WASM handle is released on
 *      both success and error paths.
 *
 * Empty-chunks case is propagated verbatim: when `chunks.length === 0`, this
 * function returns `{ chunks: [], embeddings: [], title }` and the caller
 * handles the warning/error (CLI: log + skip; MCP: throw McpError).
 *
 * @param filePath        Absolute path to the PDF (caller has already validated).
 * @param parser          Parser instance with `parsePdfPages` (mockable).
 * @param chunker         Semantic chunker instance (owned by the caller).
 * @param embedder        Embedder implementing `EmbedderInterface`.
 * @param captionerConfig modelName + cacheDir + dtype (resolved by the caller).
 */
export declare function prepareVisualPdfChunks(filePath: string, parser: VisualPdfParser, chunker: SemanticChunker, embedder: EmbedderInterface, captionerConfig: CaptionerConfig): Promise<PrepareVisualPdfChunksResult>;
//# sourceMappingURL=visual.d.ts.map