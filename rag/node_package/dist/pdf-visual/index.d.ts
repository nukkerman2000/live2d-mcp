import type { Document as MupdfDocument } from 'mupdf';
import type { Captioner } from './types.js';
export { createCaptioner } from './captioner.js';
export { detectVisualCandidates } from './detector.js';
export { renderPdfPage } from './renderer.js';
export { VlmError } from './types.js';
/**
 * Per-page record consumed and (selectively) mutated by the orchestrator.
 * `stextJson` is passed through verbatim — the orchestrator does not inspect
 * it. The structural type is duplicated here (not imported from `parser/`)
 * to preserve the layer boundary documented in the task file.
 */
interface OrchestratorPage {
    pageNum: number;
    text: string;
    stextJson: unknown;
}
/**
 * Per-page detector record. Mirrors the shape returned by
 * `detectVisualCandidates` in `./detector.ts`.
 */
interface OrchestratorCandidate {
    pageNum: number;
    isCandidate: boolean;
    cropRect?: [number, number, number, number];
}
/**
 * Per-page caption record emitted by `enrichPagesWithCaptions`.
 *
 * `text` is the raw caption string returned by the captioner (without the
 * `[Visual content on page N: …]` wrapper — wrapping happens at the ingest
 * layer where the dedicated caption chunks are built).
 */
export interface VisualCaption {
    pageNum: number;
    text: string;
}
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
export declare function enrichPagesWithCaptions(pages: OrchestratorPage[], candidates: OrchestratorCandidate[], doc: MupdfDocument, captioner: Captioner): Promise<{
    pages: OrchestratorPage[];
    captions: VisualCaption[];
}>;
//# sourceMappingURL=index.d.ts.map