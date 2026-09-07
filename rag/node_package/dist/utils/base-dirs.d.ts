/**
 * Internal representation of the effective document roots.
 *
 * `baseDirs` is the post-normalization, post-deduplication, post-nested-prune
 * list of realpath-resolved directories used as the security boundary for
 * file access. Order is preserved from the original configuration input so
 * the first element is meaningful as the legacy single-root accessor (see
 * {@link legacyBaseDir}).
 */
export interface BaseDirsConfig {
    baseDirs: string[];
}
/**
 * Discriminated union of configuration warnings surfaced by helpers in this
 * module. Both CLI (stderr) and MCP (tool response content block) paths
 * consume these — the consumer decides how to render them.
 */
export type BaseDirsConfigWarning = {
    kind: 'nested-root-pruned';
    message: string;
    parent: string;
    pruned: string;
} | {
    kind: 'base-dirs-overrides-base-dir';
    message: string;
};
/**
 * Configuration error raised by parsers and the realpath helper. Modeled as
 * a dedicated subclass so consumers can distinguish configuration problems
 * from other I/O errors (e.g. `ValidationError` from `DocumentParser`).
 */
export declare class BaseDirsConfigError extends Error {
    readonly cause?: Error | undefined;
    constructor(message: string, cause?: Error | undefined);
}
/**
 * Result of {@link parseBaseDirsEnv}. A discriminated union avoids forcing
 * callers to use `try/catch` for what is a routine configuration-validation
 * branch (invalid input → structured error → user-facing message).
 */
export type ParseBaseDirsResult = {
    ok: true;
    value: string[];
} | {
    ok: false;
    error: BaseDirsConfigError;
};
/**
 * Render an absolute path for inclusion in user-visible error/warning
 * messages, substituting the current `$HOME` prefix with `~`. The substitution
 * keeps the message useful for debugging while avoiding leaking the operating
 * username when warnings/errors flow out through MCP responses to clients.
 *
 * `$HOME` resolution is read once at call time, so processes that mutate
 * `HOME` between invocations still see the current value (no caching).
 *
 * Exact-match on the home directory itself (`/Users/me` → `~`) and prefix
 * match with a trailing separator (`/Users/me/work` → `~/work`) are both
 * supported; other paths pass through unchanged.
 */
export declare function displayPath(path: string): string;
/**
 * Parse the `BASE_DIRS` environment variable.
 *
 * Accepts only a JSON array of one or more non-empty, non-whitespace-only
 * strings — e.g. `'["/Users/me/work","/Users/me/specs"]'`. Anything else
 * (delimiter syntax such as `'/a:/b'`, an empty array, an array containing
 * empty strings, non-string elements, JSON scalars, JSON objects, ...)
 * produces a {@link BaseDirsConfigError}.
 *
 * This helper performs only syntactic validation. It does not resolve
 * realpaths or check that the directories exist — that is the job of
 * {@link normalizeRealpath} after the resolver picks a source.
 */
export declare function parseBaseDirsEnv(raw: string): ParseBaseDirsResult;
/**
 * Append a trailing path separator if the input does not already end with
 * one. This is the prefix-safety pattern used throughout the parser
 * (`/foo/bar` must not match `/foo/barista`).
 */
export declare function withTrailingSeparator(path: string): string;
/**
 * Resolve a directory to its realpath form and append a trailing separator
 * so the result can be used directly as a prefix in security checks.
 *
 * Throws {@link BaseDirsConfigError} when the directory does not exist or
 * is not a directory — root configuration must point at real directories
 * the process is allowed to read.
 */
export declare function normalizeRealpath(path: string): Promise<string>;
/**
 * Output of {@link dedupAndPruneRoots}.
 */
export interface DedupAndPruneResult {
    /** Effective roots in input order, after exact dedup and nested pruning. */
    roots: string[];
    /** Warnings describing pruned nested roots, in pruning order. */
    warnings: BaseDirsConfigWarning[];
}
/**
 * Reduce a list of realpath-normalized roots to the effective set.
 *
 * Behavior:
 *  - Exact duplicates (`A === B` after realpath normalization) are silently
 *    deduplicated. This is treated as user convenience rather than a
 *    configuration mistake, so no warning is emitted.
 *  - Nested roots (`B` lives under `A` after realpath normalization) are
 *    pruned: the parent `A` is kept, the child `B` is dropped, and a
 *    `nested-root-pruned` warning describes both paths. This avoids
 *    duplicate `list_files` / CLI scan output without widening the security
 *    boundary beyond the parent root the user already configured.
 *
 * Input order is preserved for the surviving roots so the first element
 * remains a meaningful legacy `baseDir` (see {@link legacyBaseDir}).
 *
 * All inputs MUST already have a trailing separator (see
 * {@link normalizeRealpath}) — that is what makes the `startsWith`-based
 * nested check safe against sibling-prefix paths like `/foo/barista`.
 */
export declare function dedupAndPruneRoots(inputs: string[]): DedupAndPruneResult;
/**
 * Input to {@link resolveBaseDirs}. Each axis maps directly to one of the
 * configuration sources defined in the multi-base-dirs plan:
 *
 *  - `cliRoots` — collected `--base-dir` flag occurrences (highest precedence)
 *  - `envBaseDirs` — raw `BASE_DIRS` env value (JSON array)
 *  - `envBaseDir` — raw `BASE_DIR` env value (single path string)
 *  - `cwd` — `process.cwd()` snapshot (lowest precedence, always required)
 *
 * The resolver is pure with respect to its inputs (no `process.env` reads,
 * no `process.cwd()` calls) so it can be exercised under deterministic tests
 * and reused from both the CLI entry and the MCP server entry without
 * implicitly depending on process state.
 */
export interface ResolveBaseDirsInput {
    cliRoots?: string[] | undefined;
    envBaseDirs?: string | undefined;
    envBaseDir?: string | undefined;
    cwd: string;
}
/**
 * Result of {@link resolveBaseDirs}. Discriminated by `ok` so callers can
 * branch on configuration validity without try/catch — invalid `BASE_DIRS`
 * is a routine user-facing error path, not an exceptional condition.
 *
 * On success, `warnings` aggregates every warning surfaced during resolution
 * in display order:
 *  1. `base-dirs-overrides-base-dir` (when applicable) — shown first so the
 *     precedence note is visible before per-root pruning notes.
 *  2. `nested-root-pruned` — one warning per pruned child, in pruning order.
 */
export type ResolveBaseDirsResult = {
    ok: true;
    config: BaseDirsConfig;
    warnings: BaseDirsConfigWarning[];
} | {
    ok: false;
    error: BaseDirsConfigError;
};
/**
 * Resolve effective base directories from CLI / env / cwd inputs.
 *
 * Resolution order (per the multi-base-dirs plan):
 *   1. `cliRoots` (one or more `--base-dir` flags) — when non-empty, replaces
 *      env roots. CLI and env are never merged.
 *   2. `envBaseDirs` (JSON array) — when CLI roots are absent.
 *   3. `envBaseDir` (single path) — when CLI and `BASE_DIRS` are absent.
 *   4. `cwd` — when none of the above are set.
 *
 * Warning rules:
 *  - `BASE_DIRS > BASE_DIR` precedence warning fires only when CLI roots are
 *    absent AND both `BASE_DIRS` and `BASE_DIR` are set. CLI-driven runs do
 *    not produce this warning even if both env vars are also set.
 *  - Nested-root pruning warnings always fire when applicable, regardless
 *    of which source provided the roots.
 *
 * Error rules:
 *  - Invalid `BASE_DIRS` (malformed JSON, non-array, empty array, empty
 *    string element, ...) returns `{ ok: false, error }`. The resolver does
 *    NOT fall back to `BASE_DIR` or `cwd` — callers surface the error per
 *    their UI contract (CLI exit code, MCP tool error, `status` diagnostic).
 *  - A path that fails realpath resolution (does not exist, not a directory,
 *    permission denied) also returns `{ ok: false, error }`. Roots must
 *    point at real directories the process is allowed to read.
 *
 * Post-resolution normalization:
 *  - Every selected path is realpath-normalized and gets a trailing path
 *    separator (see {@link normalizeRealpath}) so it can be used as a prefix
 *    in security checks.
 *  - Exact duplicates are silently deduplicated.
 *  - Nested roots are pruned with a warning (see {@link dedupAndPruneRoots}).
 */
export declare function resolveBaseDirs(input: ResolveBaseDirsInput): Promise<ResolveBaseDirsResult>;
/**
 * Return the legacy single-root `baseDir` value for a {@link BaseDirsConfig}.
 *
 * Used for backward compatibility with consumers (and response fields) that
 * pre-date the multi-root model. The contract is "first effective root after
 * normalization and nested-root pruning"; callers must build the config via
 * {@link dedupAndPruneRoots} for this to hold.
 */
export declare function legacyBaseDir(config: BaseDirsConfig): string;
//# sourceMappingURL=base-dirs.d.ts.map