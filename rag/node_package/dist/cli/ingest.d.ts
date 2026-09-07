import { SemanticChunker } from '../chunker/index.js';
import type { Embedder } from '../embedder/index.js';
import { DocumentParser } from '../parser/index.js';
import type { QualityProfile } from '../pdf-visual/types.js';
import type { BaseDirsConfig, BaseDirsConfigWarning } from '../utils/base-dirs.js';
import type { VectorStore } from '../vectordb/index.js';
import type { GlobalOptions, ResolvedGlobalConfig } from './options.js';
interface IngestConfig {
    baseDirs: BaseDirsConfig;
    baseDirsWarnings: BaseDirsConfigWarning[];
    dbPath: string;
    cacheDir: string;
    modelName: string;
    maxFileSize: number;
    chunkMinLength?: number;
}
interface IngestCliOptions {
    /**
     * Collected `--base-dir` values in CLI order. Repeatable: each flag
     * occurrence appends one entry. An empty array means the flag was not
     * provided (resolver then falls through to env / cwd).
     */
    baseDirs?: string[] | undefined;
    maxFileSize?: number | undefined;
    chunkMinLength?: number | undefined;
    visual?: boolean | undefined;
    /**
     * Visual-quality profile selector. Only meaningful when `visual` is true;
     * silently ignored otherwise (mirrors the existing `--visual` precedent
     * of silently coercing for non-PDF files). Defaults to `'fast'`.
     */
    visualQuality?: QualityProfile | undefined;
}
interface ParsedArgs {
    positional: string | undefined;
    options: IngestCliOptions;
    help: boolean;
}
/**
 * Parse ingest-specific CLI arguments into options and a positional path.
 * Flags: --base-dir, --max-file-size, -h/--help
 * Unknown flags (including global flags passed after subcommand) cause an error.
 */
export declare function parseArgs(args: string[]): ParsedArgs;
/**
 * Resolve ingest config by merging global config with ingest-specific options.
 *
 * Base directories are resolved via the shared CLI resolver
 * ({@link resolveCliBaseDirsOrExit}) which applies the documented precedence
 * (CLI roots > `BASE_DIRS` > `BASE_DIR` > `cwd`), realpath-normalizes every
 * effective root, dedupes exact duplicates, and prunes nested roots. CLI
 * roots are pre-validated against the sensitive-path policy here so the
 * user sees `--base-dir`-attributed errors before the resolver touches the
 * filesystem.
 *
 * Other ingest-specific values (maxFileSize, chunkMinLength) follow the
 * existing CLI > env > defaults order and are validated against the same
 * ranges as before.
 */
export declare function resolveConfig(globalConfig: ResolvedGlobalConfig, ingestOptions?: IngestCliOptions): Promise<IngestConfig>;
/**
 * Options for `ingestSingleFile`. Discriminated on `visual` so the visual
 * path is type-only callable with the VLM config it actually needs:
 *  - `visual` absent or `false` → no VLM fields required (and not accepted).
 *  - `visual: true` → `profile` and `cacheDir` required; `device` optional.
 *
 * Why a union rather than always-required fields: making the VLM fields
 * unconditionally required forces non-visual callers (default-mode tests,
 * future direct-import callers that only ingest non-PDF files) to fabricate
 * VLM config they will never use. The visual-true variant still catches
 * accidental misuse at compile time, which was the original goal.
 */
export type IngestSingleFileOptions = {
    visual?: false | undefined;
} | {
    visual: true;
    profile: QualityProfile;
    cacheDir: string;
    device?: string | undefined;
};
/**
 * Ingest a single file: parse, chunk, embed, delete old chunks, insert new chunks.
 * Returns the number of chunks inserted.
 *
 * When `options.visual === true` AND the file is a `.pdf`, routes through the
 * visual-enrichment path: `parsePdfPages` + VLM captioning (`pdf-visual`
 * orchestrator) + joined-text chunking. `pdf-visual` is loaded via dynamic
 * `await import('../pdf-visual/index.js')` so the default (non-visual) path
 * never pulls the VLM module into the bundle (NFR-1 dynamic-import discipline,
 * verified by AC-001 Proxy sentinel in T4.6).
 *
 * Non-visual, non-PDF, and `visual: true` + non-PDF (silently falls through
 * to the default branch — AC-006) paths are byte-identical to the post-T0.3
 * state and never load `pdf-visual`.
 */
export declare function ingestSingleFile(filePath: string, parser: DocumentParser, chunker: SemanticChunker, embedder: Embedder, vectorStore: VectorStore, options?: IngestSingleFileOptions): Promise<number>;
/**
 * Run the ingest CLI subcommand.
 * @param args - Arguments after "ingest" (e.g., option flags and file/directory path)
 * @param globalOptions - Global options parsed before the subcommand
 */
export declare function runIngest(args: string[], globalOptions?: GlobalOptions): Promise<void>;
export {};
//# sourceMappingURL=ingest.d.ts.map