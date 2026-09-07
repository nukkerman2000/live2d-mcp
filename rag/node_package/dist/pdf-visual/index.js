// `pdf-visual` package — orchestrator + intermediate barrel.
//
// `enrichPagesWithCaptions` glues `renderPdfPage` (T3.1) and the `Captioner`
// (T3.3) together for every page flagged as a visual candidate by
// `detectVisualCandidates` (T3.2). Per-page failure semantics — the heart of
// FR-3 / AC-004 — live HERE and ONLY here: the renderer and captioner each
// throw `VlmError` on their own failures; the orchestrator is the single
// site that catches those errors and continues with text-only output for the
// offending page.
//
// Captions are NOT mutated into `page.text`. Returning them as a separate
// `captions` array lets the ingest layer emit them as dedicated chunks
// (`src/ingest/visual.ts`), preserving the `Summary` + `Keywords` structure
// against the semantic chunker's sentence-boundary splits.
//
// Contract:
//   1. Build a Set of candidate page numbers from
//      `candidates.filter(c => c.isCandidate).map(c => c.pageNum)`.
//   2. Iterate `pages` in input order. For each page whose `pageNum` is in
//      the candidate Set:
//        - `pngBytes = await renderPdfPage(doc, page.pageNum, candidate.cropRect)`
//        - `caption  = await captioner.caption(pngBytes, page.pageNum)`
//        - `caption === null` → `console.warn` naming the page; no caption record.
//        - non-null → push `{ pageNum, text: caption }` into `captions`.
//        - thrown error → `console.warn` naming the page and including
//          `err.message`; no caption record. Per FR-3, a per-page captioner
//          failure is warning-level (the file ingest as a whole succeeds).
//   3. Return `{ pages, captions }`. The `pages` array is passed through
//      unchanged (no text mutation).
//
// DPI is NOT a parameter of this function. The renderer owns DPI as a
// module-private constant. If a future caller needs to override DPI it can
// be added then.
//
// Layer constraint (per task file): this module imports ONLY from
// `./renderer`, `./captioner`, `./detector`, `./types`. No external packages.
// (The `mupdf` type import is type-only and erased at compile.)
import { renderPdfPage } from './renderer.js';
// Public surface re-exports (T3.5). The Phase 4 dispatch sites in
// `src/cli/ingest.ts` and `src/server/index.ts` reach the visual-mode
// implementation exclusively through `await import('../pdf-visual/index.js')`
// (NFR-1 dynamic-import discipline). Keeping every public symbol re-exported
// here means those sites never need to know the internal module layout.
// Re-export ordering below is alphabetical by source module to match Biome's
// `organizeImports` rule (`./captioner` → `./detector` → `./renderer` → `./types`).
export { createCaptioner } from './captioner.js';
export { detectVisualCandidates } from './detector.js';
export { renderPdfPage } from './renderer.js';
export { VlmError } from './types.js';
/**
 * Generate VLM captions for each visual candidate page. Per-page failures are
 * tolerated: a thrown error or a `null` caption is logged and the page produces
 * no caption record. Other candidate pages are unaffected.
 *
 * @param pages - Per-page records from `parsePdfPages`. Passed through
 *                unchanged (no text mutation).
 * @param candidates - Per-page `{ pageNum, isCandidate }` records from
 *                     `detectVisualCandidates`. Pages whose `isCandidate` is
 *                     false are skipped.
 * @param doc - The open mupdf `Document`. The orchestrator does not own its
 *              lifecycle — the caller is responsible for `doc.destroy()`.
 * @param captioner - The VLM wrapper from `createCaptioner`.
 * @returns `{ pages, captions }`. `pages` is the same array reference, with
 *          text fields untouched. `captions` contains one entry per page that
 *          produced a non-empty caption.
 */
export async function enrichPagesWithCaptions(pages, candidates, doc, captioner) {
    const candidateByPage = new Map(candidates.filter((c) => c.isCandidate).map((c) => [c.pageNum, c]));
    const captions = [];
    for (const page of pages) {
        const candidate = candidateByPage.get(page.pageNum);
        if (!candidate)
            continue;
        try {
            const pngBytes = await renderPdfPage(doc, page.pageNum, candidate.cropRect);
            const caption = await captioner.caption(pngBytes, page.pageNum);
            if (caption === null) {
                // Empty / sanitized-empty caption is a documented non-failure (see
                // captioner contract step 7). Warn-log and emit no caption record.
                console.warn(`VLM caption empty for page ${page.pageNum}; proceeding text-only`);
                continue;
            }
            captions.push({ pageNum: page.pageNum, text: caption });
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            // Per FR-3 ("logs a warning"), a per-page captioner failure is
            // emitted at warn-level. The file ingest as a whole completes
            // successfully — only this single page degrades to text-only.
            console.warn(`VLM caption failed for page ${page.pageNum}: ${message}`);
            // No caption record for this page — AC-004 (text-only fallback).
        }
    }
    return { pages, captions };
}
//# sourceMappingURL=index.js.map