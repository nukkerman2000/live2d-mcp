import type { Document as MupdfDocument } from 'mupdf';
import { type EmbedderInterface } from './pdf-filter.js';
/**
 * File extensions supported by the parser module (parseFile + parsePdf).
 * Exported so other modules (e.g. list_files) stay in sync automatically
 * when new formats are added here.
 */
export declare const SUPPORTED_EXTENSIONS: Set<string>;
/**
 * Result from parsing a document, containing both content and extracted title.
 * Title is display-only metadata (NOT used for search scoring).
 */
export interface ParseResult {
    content: string;
    title: string;
}
/**
 * DocumentParser configuration.
 *
 * Accepts either a single `baseDir` (legacy single-root shape — preserved for
 * backward compatibility with downstream callers that have not yet migrated
 * to the multi-root model) or a `baseDirs` array (multi-root shape produced
 * by `resolveBaseDirs`). Exactly one of the two MUST be supplied; supplying
 * both is rejected by the constructor so misconfiguration cannot silently
 * pick one source over the other.
 *
 * Behavior under a single allowed root (`{ baseDir }` or
 * `{ baseDirs: [oneRoot] }`) is byte-identical to the previous single-root
 * implementation — see `validateFilePath` for the iteration contract under
 * multiple roots.
 */
export type ParserConfig = {
    /** Security: single allowed base directory (legacy shape). */
    baseDir: string;
    baseDirs?: undefined;
    /** Maximum file size (100MB). */
    maxFileSize: number;
} | {
    /** Security: one or more allowed base directories (multi-root shape). */
    baseDirs: readonly string[];
    baseDir?: undefined;
    /** Maximum file size (100MB). */
    maxFileSize: number;
};
/**
 * Validation error (equivalent to 400)
 */
export declare class ValidationError extends Error {
    readonly cause?: Error | undefined;
    constructor(message: string, cause?: Error | undefined);
}
/**
 * File operation error (equivalent to 500)
 */
export declare class FileOperationError extends Error {
    readonly cause?: Error | undefined;
    constructor(message: string, cause?: Error | undefined);
}
/**
 * Document parser class (PDF/DOCX/TXT/MD support)
 *
 * Responsibilities:
 * - File path validation (path traversal prevention)
 * - File size validation (100MB limit)
 * - Parse 4 formats (PDF/DOCX/TXT/MD)
 */
export declare class DocumentParser {
    private readonly config;
    /** Raw allowed roots in input order (pre-realpath). Always non-empty. */
    private readonly rawBaseDirs;
    /**
     * Lazily cached realpath-normalized allowed roots, each with a trailing
     * path separator so the `startsWith` check is sibling-prefix safe (e.g.
     * `/foo/bar/` must not match `/foo/barista/x.txt`). Order is preserved
     * from `rawBaseDirs` so the legacy single-root rejection message keeps
     * referencing the user-configured first root. Assumes the allowed roots
     * are stable for the process lifetime.
     */
    private resolvedBaseDirs;
    constructor(config: ParserConfig);
    /**
     * File path validation (Absolute path requirement + Path traversal prevention).
     *
     * Multi-root semantics: a file is accepted iff its realpath (or, for a
     * non-symlink path that does not yet exist, its `resolve()`-normalized
     * absolute path) is under ANY realpath-normalized allowed root using a
     * trailing-separator prefix check. Broken symlinks are still rejected
     * outright — the lstat-based detection mirrors the previous single-root
     * behavior.
     *
     * Under a single allowed root the behavior is identical to the previous
     * single-root implementation.
     *
     * @param filePath - File path to validate (must be absolute)
     * @throws ValidationError - When path is not absolute or outside all allowed roots
     */
    validateFilePath(filePath: string): Promise<void>;
    /**
     * File size validation (100MB limit)
     *
     * @param filePath - File path to validate
     * @throws ValidationError - When file size exceeds limit
     * @throws FileOperationError - When file read fails
     */
    validateFileSize(filePath: string): void;
    /**
     * File parsing (auto format detection)
     *
     * @param filePath - File path to parse
     * @returns ParseResult with content and extracted title
     * @throws ValidationError - Path traversal, size exceeded, unsupported format
     * @throws FileOperationError - File read failed, parse failed
     */
    parseFile(filePath: string): Promise<ParseResult>;
    /**
     * PDF parsing with header/footer filtering
     *
     * Features:
     * - Extracts text with position information (x, y, fontSize)
     * - Semantic header/footer detection using embedding similarity
     * - Uses hasEOL for proper line break handling
     * - Extracts document title from PDF metadata and first page font heuristic
     *
     * @param filePath - PDF file path
     * @param embedder - Embedder for semantic header/footer detection
     * @returns ParseResult with content and extracted title
     * @throws FileOperationError - File read failed, parse failed
     */
    parsePdf(filePath: string, embedder: EmbedderInterface): Promise<ParseResult>;
    /**
     * Per-page PDF parsing for the visual-enrichment path.
     *
     * Opens a mupdf `Document`, delegates per-page extraction to the shared
     * `extractPdfPages` helper with the `'preserve-whitespace,preserve-images'`
     * stext option string so mupdf emits `block.type === 'image'` blocks for
     * the downstream visual-candidate detector (Phase 1 probe finding).
     *
     * Returns the open `Document` handle alongside the per-page records and
     * title-resolution materials so the caller can:
     *   - run the renderer (`page.toPixmap()`) on the same handle,
     *   - feed `metadataTitle` + `pages[0].page1FontHint` into `extractPdfTitle`
     *     after `buildChunksAndEmbeddings` returns.
     *
     * Disposal contract (asymmetric — read carefully):
     *   - SUCCESS path: this method returns the open `doc` handle. The caller
     *     owns disposal and MUST wrap the call site in
     *     `try { ... } finally { doc.destroy() }`.
     *   - ERROR path: when this method throws, `doc` has already been destroyed
     *     internally before the exception propagates (so the caller never
     *     receives a handle it would not know to clean up). Callers MUST NOT
     *     call `doc.destroy()` on an error from this method.
     * See DD § `parser.parsePdfPages` contract.
     *
     * This method does NOT compute the final title and does NOT decide visual
     * candidates — those are the dispatch site's and `pdf-visual/detector`'s
     * responsibilities, respectively.
     *
     * @param filePath - PDF file path (validated against BASE_DIR and size limit)
     * @param embedder - Embedder for semantic header/footer detection
     * @returns Open mupdf `Document`, `metadataTitle`, and per-page records.
     *          `page1FontHint` (largest-font line on page 1) is present only on `pages[0]`.
     * @throws ValidationError - Path traversal, size exceeded
     * @throws FileOperationError - File read or parse failed (after destroying `doc` internally)
     */
    parsePdfPages(filePath: string, embedder: EmbedderInterface): Promise<{
        doc: MupdfDocument;
        metadataTitle: string | undefined;
        pages: Array<{
            pageNum: number;
            text: string;
            stextJson: unknown;
            page1FontHint?: {
                text: string;
                fontSize: number;
            };
        }>;
    }>;
    /**
     * DOCX parsing (using mammoth)
     *
     * Uses extractRawText for content and convertToHtml additionally for title detection.
     *
     * @param filePath - DOCX file path
     * @returns ParseResult with content and extracted title
     * @throws FileOperationError - File read failed, parse failed
     */
    private parseDocx;
    /**
     * TXT parsing (using fs.readFile)
     *
     * @param filePath - TXT file path
     * @returns ParseResult with content and extracted title
     * @throws FileOperationError - File read failed
     */
    private parseTxt;
    /**
     * MD parsing (using fs.readFile)
     *
     * @param filePath - MD file path
     * @returns ParseResult with content and extracted title
     * @throws FileOperationError - File read failed
     */
    private parseMd;
}
//# sourceMappingURL=index.d.ts.map