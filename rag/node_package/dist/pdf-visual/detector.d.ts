import type { Document as MupdfDocument } from 'mupdf';
/**
 * Input page record consumed by the detector. `stextJson` is typed `unknown`
 * because mupdf's `StructuredText.asJSON()` shape is not statically declared
 * by `mupdf.d.ts` (DD §Risks → "mupdf JSON block.type taxonomy"). The
 * implementation narrows it locally.
 */
interface DetectorPage {
    pageNum: number;
    stextJson: unknown;
}
/**
 * Output record. Separate from the input page record (not joined back) so
 * the detector stays dispatch-agnostic; the orchestrator (T3.4) joins via
 * `pageNum`.
 */
interface DetectorResult {
    pageNum: number;
    isCandidate: boolean;
    cropRect?: Rect;
}
/**
 * Rectangle tuple in mupdf page coordinates: [x0, y0, x1, y1].
 */
type Rect = [number, number, number, number];
/**
 * Decide which pages are visual candidates.
 *
 * @param pages - Per-page records from `parsePdfPages`, each carrying the
 *                raw mupdf StructuredText JSON.
 * @returns Per-page `{ pageNum, isCandidate }` records in the same order as
 *          the input.
 */
export declare function detectVisualCandidates(pages: DetectorPage[], doc: MupdfDocument): DetectorResult[];
export {};
//# sourceMappingURL=detector.d.ts.map