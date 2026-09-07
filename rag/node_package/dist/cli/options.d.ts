/**
 * Validate that a path is not a sensitive system directory.
 * Delegates to the shared `checkSensitivePath` helper so the CLI and the
 * MCP server entry point share one policy implementation.
 *
 * Returns an error message if invalid, or undefined if valid.
 */
export declare function validatePath(value: string, flagName: string): string | undefined;
/**
 * Validate model name against allowed pattern.
 * Returns an error message if invalid, or undefined if valid.
 */
export declare function validateModelName(value: string): string | undefined;
/**
 * Validate max file size is within acceptable range.
 * Returns an error message if invalid, or undefined if valid.
 */
export declare function validateMaxFileSize(value: number): string | undefined;
/**
 * Validate chunk minimum length is within acceptable range.
 * Returns an error message if invalid, or undefined if valid.
 */
export declare function validateChunkMinLength(value: number): string | undefined;
/**
 * Consume the value that follows a `--base-dir` flag and append it to
 * `collected`. Designed to be called from each subcommand's argv loop so
 * `--base-dir <path>` can be provided one or more times, with the order
 * preserved.
 *
 * `argv` is the full argv slice the loop is iterating; `flagIndex` is the
 * index of the `--base-dir` token itself. On success returns the index of
 * the value (so the caller can advance past it). On failure prints
 * `Missing value for --base-dir` to stderr and calls `process.exit(1)` —
 * matching the existing single-value error path so callers don't have to
 * special-case the new shape.
 *
 * Why a shared helper: both `ingest` and `list` parse `--base-dir` in
 * identical fashion, so centralizing the accumulate-and-validate step keeps
 * the two argv loops in lockstep when the contract evolves (e.g. P2-T2
 * adding per-path validation).
 */
export declare function consumeBaseDirArg(argv: string[], flagIndex: number, collected: string[]): number;
export interface GlobalOptions {
    dbPath?: string | undefined;
    cacheDir?: string | undefined;
    modelName?: string | undefined;
}
export interface ParsedGlobalResult {
    globalOptions: GlobalOptions;
    remainingArgs: string[];
}
export interface ResolvedGlobalConfig {
    dbPath: string;
    cacheDir: string;
    modelName: string;
}
export declare const GLOBAL_DEFAULTS: {
    readonly dbPath: "./lancedb/";
    readonly cacheDir: "./models/";
    readonly modelName: "Xenova/all-MiniLM-L6-v2";
};
export declare const ROOT_HELP_TEXT: string;
/**
 * Extract global options (--db-path, --cache-dir, --model-name, -h/--help)
 * from the argument list and return them along with the remaining args.
 *
 * Global options are only recognized BEFORE the first non-flag argument
 * (the subcommand). After the subcommand, everything is forwarded as-is.
 */
export declare function parseGlobalOptions(args: string[]): ParsedGlobalResult;
/**
 * Resolve global config with priority: CLI flags > environment variables > defaults.
 * Validates all resolved values before returning.
 */
export declare function resolveGlobalConfig(options: GlobalOptions): ResolvedGlobalConfig;
/**
 * Resolve RAG_DEVICE. The value is passed through to transformers.js — no
 * allowlist is maintained here. Whitespace-only is treated as unset.
 */
export declare function resolveDevice(value: string | undefined): string;
//# sourceMappingURL=options.d.ts.map