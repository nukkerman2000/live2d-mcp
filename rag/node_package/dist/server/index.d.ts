import { type BaseDirsConfigError } from '../utils/base-dirs.js';
import { type RagContentBlock } from './error-utils.js';
import type { DeleteFileInput, IngestDataInput, IngestFileInput, QueryDocumentsInput, RAGServerConfig, ReadChunkNeighborsInput } from './types.js';
/** RAG server compliant with MCP Protocol */
export declare class RAGServer {
    private readonly server;
    private readonly vectorStore;
    private readonly embedder;
    private readonly chunker;
    private readonly parser;
    private readonly dbPath;
    /**
     * One or more allowed document base directories. The single source of
     * truth for both the security boundary (passed to `DocumentParser`) and
     * for scan iteration in `list_files` (P3-T2). Normalized from either the
     * legacy `{ baseDir }` config shape or the new `{ baseDirs }` shape so
     * downstream readers do not need to branch on shape.
     */
    private readonly baseDirs;
    /**
     * Legacy single-root accessor. Derived from `baseDirs[0]`. Preserved so
     * the legacy `ListFilesResult.baseDir` field and any direct readers of
     * `this.baseDir` continue to work; multi-root iteration uses `baseDirs`.
     */
    private readonly baseDir;
    private readonly cacheDir;
    private readonly excludePaths;
    private readonly configWarnings;
    /**
     * Structured base-dirs resolution error. When non-null, the server is in
     * degraded mode: `status` remains callable so the user can diagnose the
     * problem via MCP, while root-dependent tools should surface this error
     * (wired in P3-T3). See `resolveBaseDirs` for the error semantics.
     */
    private readonly configError;
    private readonly minChunkLength;
    private readonly device;
    constructor(config: RAGServerConfig);
    /**
     * Expose the base-dirs resolution error (if any) for the warning/error
     * attachment layer added in P3-T3. Returns `null` when configuration
     * resolved cleanly. Kept as a method so the field stays `private readonly`
     * — only the handler layer that wires error responses needs read access.
     */
    getConfigError(): BaseDirsConfigError | null;
    /**
     * Fail-fast guard for root-dependent tools. When a {@link BaseDirsConfigError}
     * is stored on the instance the server is in degraded mode (invalid
     * `BASE_DIRS` — see `resolveBaseDirs`) and every root-dependent tool MUST
     * reject BEFORE any DB / embedder / parser access so the user sees the
     * configuration problem unambiguously. Surfaces the error as an
     * `McpError(InvalidParams)` so MCP clients render it as a structured tool
     * error (per AC-009).
     *
     * `status` deliberately does NOT call this helper; it remains callable in
     * degraded mode and exposes the error via a diagnostic content block so
     * the user can recover via MCP without inspecting stderr.
     */
    private assertConfigOk;
    /**
     * Append the centralized config-warning blocks to a handler response.
     * Every tool handler funnels through this method so the warning shape
     * stays in exactly one place (design-doc-mandated countermeasure for the
     * "warning shape changes touch many handlers" risk).
     */
    private withWarnings;
    /**
     * Set up MCP handlers
     */
    private setupHandlers;
    /**
     * Initialization
     */
    initialize(): Promise<void>;
    /**
     * query_documents tool handler
     */
    handleQueryDocuments(args: QueryDocumentsInput): Promise<{
        content: RagContentBlock[];
    }>;
    /**
     * ingest_file tool handler (re-ingestion support, transaction processing, rollback capability)
     */
    handleIngestFile(args: IngestFileInput): Promise<{
        content: RagContentBlock[];
    }>;
    /**
     * ingest_data tool handler
     * Saves raw content to raw-data directory and calls handleIngestFile internally
     *
     * For HTML content:
     * - Parses HTML and extracts main content using Readability
     * - Converts to Markdown for better chunking
     * - Saves as .md file
     */
    handleIngestData(args: IngestDataInput): Promise<{
        content: RagContentBlock[];
    }>;
    /**
     * Bounded BFS scan of a single base directory for supported files,
     * excluding system-managed paths (dbPath, cacheDir). Returns sorted
     * absolute paths plus a list of non-fatal warnings (Finding #10).
     *
     * Behavior contract:
     *  - Depth is bounded by {@link RAGServer.LIST_MAX_DEPTH}, mirroring the
     *    CLI ingest walker so the same "how deep do we look under a root"
     *    boundary applies to every list/ingest surface.
     *  - A `readdir` failure under one directory is captured as a warning
     *    rather than aborting the whole list call. Pre-Finding-#10 behavior
     *    propagated the error, which meant one unreadable root could hide
     *    files under the other roots — the multi-root contract makes this
     *    asymmetry user-visible, so the policy is now best-effort per root.
     *  - Symlinks are skipped (mirrors the CLI ingest walker).
     */
    private scanBaseDir;
    /**
     * Maximum directory recursion depth for `list_files` scans. Mirrors the
     * CLI ingest walker's `MAX_DEPTH` so the same boundary applies across
     * every list/ingest surface.
     */
    private static readonly LIST_MAX_DEPTH;
    /**
     * list_files tool handler
     *
     * Scans every effective base directory (`this.baseDirs`) for supported
     * files and cross-references with ingested documents. Multi-root contract
     * (P3-T2, AC-008):
     * - Returns top-level `baseDirs` (all effective roots, already realpath-
     *   normalized and nested-root-pruned by `resolveBaseDirs`).
     * - Preserves legacy top-level `baseDir = baseDirs[0]` for clients written
     *   against the single-root shape.
     * - Annotates each file entry with the producing `baseDir`.
     * - De-duplicates exact duplicate file paths across roots (first occurrence
     *   wins, preserving root iteration order).
     * - Preserves raw-data / orphaned DB entries under `sources` with no
     *   producing-root annotation.
     * - Excludes `dbPath` and `cacheDir` uniformly across every root.
     */
    handleListFiles(): Promise<{
        content: RagContentBlock[];
    }>;
    /**
     * status tool handler (Phase 1: basic implementation)
     */
    handleStatus(): Promise<{
        content: RagContentBlock[];
    }>;
    /**
     * delete_file tool handler
     * Deletes chunks from VectorDB and physical raw-data files
     * Supports both filePath (for ingest_file) and source (for ingest_data)
     */
    handleDeleteFile(args: DeleteFileInput): Promise<{
        content: RagContentBlock[];
    }>;
    /**
     * read_chunk_neighbors tool handler
     * Returns chunks around a target chunkIndex within a single ingested document.
     * Context-expansion utility — not a search tool. Mirrors handleDeleteFile's
     * dual-input (filePath XOR source) resolution pattern.
     */
    handleReadChunkNeighbors(args: ReadChunkNeighborsInput): Promise<{
        content: RagContentBlock[];
    }>;
    /**
     * Start the server
     */
    run(): Promise<void>;
    /**
     * Stop the server and release resources
     */
    close(): Promise<void>;
}
//# sourceMappingURL=index.d.ts.map