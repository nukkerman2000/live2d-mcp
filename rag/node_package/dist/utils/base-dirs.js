// Shared base-dirs module.
//
// Provides one internal representation of the effective document roots used
// by both the CLI (`ingest`, `list`, ...) and the MCP server entry point
// (`server-main.ts`), plus the pure helpers needed to derive it from raw
// configuration inputs (env vars, CLI flags).
//
// Scope: this file ships only pure helpers and the types. Wiring into
// `DocumentParser`, `RAGServer`, and CLI subcommands is performed by later
// tasks (P1-T2 / P1-T3 / P2-T1 / P3-T1). Keeping the wiring out of this
// module lets every consumer adopt the same realpath/prefix-safety semantics
// without duplicating the trailing-separator pattern that `DocumentParser`
// currently inlines.
import { realpath, stat } from 'node:fs/promises';
import { homedir } from 'node:os';
import { resolve, sep } from 'node:path';
/**
 * Configuration error raised by parsers and the realpath helper. Modeled as
 * a dedicated subclass so consumers can distinguish configuration problems
 * from other I/O errors (e.g. `ValidationError` from `DocumentParser`).
 */
export class BaseDirsConfigError extends Error {
    cause;
    constructor(message, cause) {
        super(message);
        this.cause = cause;
        this.name = 'BaseDirsConfigError';
    }
}
// ============================================
// Path display helpers
// ============================================
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
export function displayPath(path) {
    const home = process.env['HOME'] || homedir();
    if (home.length === 0)
        return path;
    const isWin = process.platform === 'win32';
    const cmp = (s) => (isWin ? s.toLowerCase() : s);
    const homeCmp = cmp(home);
    const pathCmp = cmp(path);
    if (pathCmp === homeCmp)
        return '~';
    if (pathCmp.startsWith(homeCmp + sep) || pathCmp.startsWith(`${homeCmp}/`)) {
        return `~${path.slice(home.length)}`;
    }
    return path;
}
// ============================================
// JSON-array parser for BASE_DIRS
// ============================================
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
export function parseBaseDirsEnv(raw) {
    const trimmed = raw.trim();
    if (trimmed.length === 0) {
        return {
            ok: false,
            error: new BaseDirsConfigError('BASE_DIRS must be a JSON array of non-empty path strings (received empty value).'),
        };
    }
    let parsed;
    try {
        parsed = JSON.parse(trimmed);
    }
    catch (error) {
        return {
            ok: false,
            error: new BaseDirsConfigError(`BASE_DIRS must be a JSON array of non-empty path strings. Failed to parse as JSON: ${truncate(raw)}`, error),
        };
    }
    if (!Array.isArray(parsed)) {
        return {
            ok: false,
            error: new BaseDirsConfigError(`BASE_DIRS must be a JSON array (received ${describeJsonShape(parsed)}).`),
        };
    }
    if (parsed.length === 0) {
        return {
            ok: false,
            error: new BaseDirsConfigError('BASE_DIRS must not be an empty array.'),
        };
    }
    const value = [];
    for (let i = 0; i < parsed.length; i++) {
        const item = parsed[i];
        if (typeof item !== 'string') {
            return {
                ok: false,
                error: new BaseDirsConfigError(`BASE_DIRS[${i}] must be a string (received ${describeJsonShape(item)}).`),
            };
        }
        if (item.trim().length === 0) {
            return {
                ok: false,
                error: new BaseDirsConfigError(`BASE_DIRS[${i}] must be a non-empty, non-whitespace path string.`),
            };
        }
        value.push(item);
    }
    return { ok: true, value };
}
// ============================================
// Realpath normalization
// ============================================
/**
 * Append a trailing path separator if the input does not already end with
 * one. This is the prefix-safety pattern used throughout the parser
 * (`/foo/bar` must not match `/foo/barista`).
 */
export function withTrailingSeparator(path) {
    return path.endsWith(sep) ? path : path + sep;
}
/**
 * Resolve a directory to its realpath form and append a trailing separator
 * so the result can be used directly as a prefix in security checks.
 *
 * Throws {@link BaseDirsConfigError} when the directory does not exist or
 * is not a directory — root configuration must point at real directories
 * the process is allowed to read.
 */
export async function normalizeRealpath(path) {
    let resolved;
    try {
        resolved = await realpath(resolve(path));
    }
    catch (error) {
        throw new BaseDirsConfigError(`Failed to resolve base directory: ${displayPath(path)}. The directory may not exist or is inaccessible.`, error);
    }
    let stats;
    try {
        stats = await stat(resolved);
    }
    catch (error) {
        throw new BaseDirsConfigError(`Failed to stat resolved base directory: ${displayPath(resolved)}.`, error);
    }
    if (!stats.isDirectory()) {
        throw new BaseDirsConfigError(`Base directory is not a directory: ${displayPath(path)} (resolved: ${displayPath(resolved)}).`);
    }
    return withTrailingSeparator(resolved);
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
export function dedupAndPruneRoots(inputs) {
    // Phase 1: exact dedup, preserving order.
    const deduped = [];
    const seen = new Set();
    for (const root of inputs) {
        if (!seen.has(root)) {
            seen.add(root);
            deduped.push(root);
        }
    }
    // Phase 2: nested-root pruning.
    //
    // A root `child` is pruned when some other root `parent` (parent !== child)
    // is a strict prefix of `child`. Because every input ends with `sep`, the
    // prefix check correctly distinguishes `/foo/bar/` (parent of `/foo/bar/baz/`)
    // from `/foo/barista/` (sibling, not a parent).
    //
    // When a chain like `[grandparent, parent, child]` is provided, both
    // `parent` and `child` are pruned and each emits a warning referencing the
    // closest SURVIVING ancestor (the grandparent). This is the same result the
    // user would have gotten by passing only the grandparent, and avoids the
    // confusing case where a warning points at another path that was itself
    // pruned. Implementation note: a single pass over `deduped` in input order
    // works because exact-prefix ancestors of a candidate must precede it in
    // the realpath-sorted-by-discovery order only when shorter; we therefore
    // compute the closest ancestor against the surviving `roots` set so the
    // reported parent is always a surviving root.
    const roots = [];
    const warnings = [];
    // Pre-pass: identify every candidate that has any ancestor in `deduped`
    // (these are the pruned candidates). The candidates that do NOT have any
    // ancestor in `deduped` are the surviving roots.
    const survivors = [];
    for (const candidate of deduped) {
        if (findParent(candidate, deduped) === undefined) {
            survivors.push(candidate);
        }
    }
    for (const candidate of deduped) {
        const survivingAncestor = findParent(candidate, survivors);
        if (survivingAncestor === undefined) {
            // This candidate is itself a surviving root.
            roots.push(candidate);
            continue;
        }
        warnings.push({
            kind: 'nested-root-pruned',
            message: `Nested base directory pruned: ${displayPath(candidate)} is inside ${displayPath(survivingAncestor)}. Keeping ${displayPath(survivingAncestor)} only.`,
            parent: survivingAncestor,
            pruned: candidate,
        });
    }
    return { roots, warnings };
}
/**
 * Return the closest ancestor of `candidate` in `all` (excluding `candidate`
 * itself), or `undefined` if no ancestor exists. Closest is measured by
 * prefix length — longer prefix wins so we report the most specific
 * surviving parent.
 */
function findParent(candidate, all) {
    let best;
    for (const other of all) {
        if (other === candidate)
            continue;
        // `other` ends with `sep` (precondition), so this prefix check is
        // sibling-prefix safe.
        if (candidate.startsWith(other)) {
            if (best === undefined || other.length > best.length) {
                best = other;
            }
        }
    }
    return best;
}
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
export async function resolveBaseDirs(input) {
    const selection = selectRoots(input);
    if (!selection.ok) {
        return selection;
    }
    const warnings = [];
    if (selection.precedenceWarning) {
        warnings.push(selection.precedenceWarning);
    }
    // Realpath-normalize each selected root. Failures (missing directory,
    // permission denied, ...) are surfaced as a structured config error.
    const normalized = [];
    for (const root of selection.roots) {
        try {
            normalized.push(await normalizeRealpath(root));
        }
        catch (error) {
            if (error instanceof BaseDirsConfigError) {
                return { ok: false, error };
            }
            throw error;
        }
    }
    const { roots, warnings: pruningWarnings } = dedupAndPruneRoots(normalized);
    warnings.push(...pruningWarnings);
    return {
        ok: true,
        config: { baseDirs: roots },
        warnings,
    };
}
/**
 * Apply the source-precedence rules to pick which input set of roots to use.
 *
 * Kept as a small helper so the realpath normalization in
 * {@link resolveBaseDirs} stays focused on I/O, not precedence logic. This
 * function performs only string-level parsing and selection — no fs access.
 */
function selectRoots(input) {
    // 1. CLI roots — when non-empty, replace env entirely (no precedence
    //    warning even if env vars are also set, because the user explicitly
    //    overrode them via CLI).
    if (input.cliRoots !== undefined && input.cliRoots.length > 0) {
        return { ok: true, roots: input.cliRoots };
    }
    // 2. BASE_DIRS — when CLI absent. Whitespace-only is treated as an
    //    invalid value (consistent with parseBaseDirsEnv), not as "unset",
    //    so the user notices a malformed env var instead of silently falling
    //    through to BASE_DIR.
    if (input.envBaseDirs !== undefined && input.envBaseDirs.length > 0) {
        const parsed = parseBaseDirsEnv(input.envBaseDirs);
        if (!parsed.ok) {
            return { ok: false, error: parsed.error };
        }
        const precedenceWarning = input.envBaseDir !== undefined && input.envBaseDir.trim().length > 0
            ? {
                kind: 'base-dirs-overrides-base-dir',
                message: 'BASE_DIRS is set; BASE_DIR is ignored. Unset BASE_DIR or remove BASE_DIRS to silence this warning.',
            }
            : undefined;
        return precedenceWarning
            ? { ok: true, roots: parsed.value, precedenceWarning }
            : { ok: true, roots: parsed.value };
    }
    // 3. BASE_DIR — when CLI and BASE_DIRS are absent. Whitespace-only is
    //    treated as "unset" (a user clearing the value with spaces gets the
    //    same behavior as not setting it at all).
    if (input.envBaseDir !== undefined && input.envBaseDir.trim().length > 0) {
        return { ok: true, roots: [input.envBaseDir] };
    }
    // 4. cwd — final fallback.
    return { ok: true, roots: [input.cwd] };
}
// ============================================
// Legacy single-root accessor
// ============================================
/**
 * Return the legacy single-root `baseDir` value for a {@link BaseDirsConfig}.
 *
 * Used for backward compatibility with consumers (and response fields) that
 * pre-date the multi-root model. The contract is "first effective root after
 * normalization and nested-root pruning"; callers must build the config via
 * {@link dedupAndPruneRoots} for this to hold.
 */
export function legacyBaseDir(config) {
    const first = config.baseDirs[0];
    if (first === undefined) {
        throw new BaseDirsConfigError('BaseDirsConfig must contain at least one base directory.');
    }
    return first;
}
// ============================================
// Private helpers
// ============================================
/**
 * Describe a JSON value's shape for error messages without dumping its full
 * (possibly large) content.
 */
function describeJsonShape(value) {
    if (value === null)
        return 'null';
    if (Array.isArray(value))
        return 'array';
    return typeof value;
}
/**
 * Truncate user-supplied input so configuration error messages stay readable
 * even when the offending value is large.
 */
function truncate(input, max = 100) {
    if (input.length <= max)
        return input;
    return `${input.slice(0, max)}...`;
}
//# sourceMappingURL=base-dirs.js.map