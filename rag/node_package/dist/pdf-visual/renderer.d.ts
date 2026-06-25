import type { Document as MupdfDocument } from 'mupdf';
import { VlmError } from './types.js';
export { VlmError };
type Rect = [number, number, number, number];
/**
 * Render a single PDF page to a PNG byte array.
 *
 * @param doc - An already-open mupdf `Document`. The renderer does NOT own the
 *              document lifecycle.
 * @param pageNum - 1-based page index. Translated to 0-based for mupdf.
 * @returns PNG bytes (`Uint8Array`, NOT `Buffer`).
 * @throws {VlmError} When mupdf rejects the page (out-of-range, render
 *                    failure, etc.). `cause` carries the original mupdf error;
 *                    `pageNum` carries the requested 1-based page.
 */
export declare function renderPdfPage(doc: MupdfDocument, pageNum: number, cropRect?: Rect): Promise<Uint8Array>;
//# sourceMappingURL=renderer.d.ts.map