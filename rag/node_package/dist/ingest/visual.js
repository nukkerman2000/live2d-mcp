// Shared visual-PDF preparation for the ingest pipeline.
//
// `prepareVisualPdfChunks` lifts the inline `createCaptioner → parsePdfPages →
// detectVisualCandidates → enrichPagesWithCaptions → buildChunksAndEmbeddings
// → extractPdfTitle` flow out of the CLI's `ingestSingleFile`
// (src/cli/ingest.ts) and the MCP server's `handleIngestFile`
// (src/server/index.ts) into this single dispatch-agnostic helper. Each
// caller keeps ownership of its persistence semantics (delete + insert with
// the CLI's bulk-loop optimize() vs. the MCP server's backup/rollback/optimize
// per call); only the shared "produce chunks + embeddings + title from a PDF
// using VLM captions" computation lives here.
//
// NFR-1 dynamic-import discipline: this module lives under `src/ingest/`,
// which is safe to import statically from dispatch sites. The `pdf-visual`
// package is loaded HERE via a single dynamic `await import('../pdf-visual/index.js')`
// so the default (non-visual) path never pulls VLM code into the bundle.
// AC-001's Proxy sentinel (default-mode invariance witness) continues to
// observe `pdf-visual` untouched as long as the dispatch sites only call into
// `prepareVisualPdfChunks` when `visual === true && isPdf`.
import { basename } from 'node:path';
import { extractPdfTitle } from '../parser/title-extractor.js';
import { buildChunksAndEmbeddings } from './compute.js';
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
export async function prepareVisualPdfChunks(filePath, parser, chunker, embedder, captionerConfig) {
    // Dynamic import — load-bearing for NFR-1. The default (non-visual) path
    // must never reach a static `pdf-visual` reference; AC-001 Proxy sentinel
    // verifies this. Both former dispatch sites previously held their own
    // dynamic import; consolidating to a single one here preserves the
    // invariant while removing the duplication.
    const pdfVisual = await import('../pdf-visual/index.js');
    const captioner = pdfVisual.createCaptioner(captionerConfig);
    const { doc, metadataTitle, pages } = await parser.parsePdfPages(filePath, embedder);
    try {
        const candidates = pdfVisual.detectVisualCandidates(pages.map((p) => ({ pageNum: p.pageNum, stextJson: p.stextJson })), doc);
        const { pages: enrichedPages, captions } = await pdfVisual.enrichPagesWithCaptions(pages, candidates, 
        // The dynamic import widens the doc type at the boundary; the parser
        // returned a real mupdf `Document` (caller-typed) so this is safe.
        doc, captioner);
        const text = enrichedPages
            .map((p) => p.text)
            .filter((t) => t.length > 0)
            .join('\n\n');
        // Chunk + embed the page text WITHOUT captions inline. Captions are
        // emitted as dedicated chunks below so the semantic chunker cannot split
        // their internal Summary / Keywords structure on sentence-boundary
        // vocabulary shifts.
        const { chunks, embeddings } = await buildChunksAndEmbeddings(text, null, chunker, embedder);
        const titleResult = extractPdfTitle(metadataTitle, chunks[0]?.text, basename(filePath), pages[0]?.page1FontHint);
        const title = titleResult.title || null;
        // Append one dedicated chunk per caption. The `[Visual content on page N:
        // …]` wrapper is applied here (previously applied in the orchestrator)
        // so the caption chunk text matches the historical marker format used by
        // downstream search.
        if (captions.length > 0) {
            const captionChunks = captions.map((c, i) => ({
                text: `[Visual content on page ${c.pageNum}: ${c.text}]`,
                index: chunks.length + i,
            }));
            const captionEmbeddings = await embedder.embedBatch(captionChunks.map((c) => c.text));
            chunks.push(...captionChunks);
            embeddings.push(...captionEmbeddings);
        }
        return { chunks, embeddings, title, text };
    }
    finally {
        // Caller owns `doc` per `parsePdfPages` contract (AC-013) — release the
        // mupdf WASM handle on both success and error paths. Wrap so a destroy
        // failure cannot mask the original try-body error (finally-overrides-try).
        try {
            doc.destroy();
        }
        catch (destroyErr) {
            const message = destroyErr instanceof Error ? destroyErr.message : String(destroyErr);
            console.warn(`prepareVisualPdfChunks: doc.destroy() failed: ${message}`);
        }
    }
}
//# sourceMappingURL=visual.js.map