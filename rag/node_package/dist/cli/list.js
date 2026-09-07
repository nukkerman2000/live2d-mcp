// CLI list subcommand — list files and ingestion status
import { readdir } from 'node:fs/promises';
import { extname, join, resolve, sep } from 'node:path';
import { SUPPORTED_EXTENSIONS } from '../parser/index.js';
import { displayPath, legacyBaseDir } from '../utils/base-dirs.js';
import { extractSourceFromPath, looksLikeRawDataPath } from '../utils/raw-data-utils.js';
import { createVectorStore, resolveCliBaseDirsOrExit } from './common.js';
import { consumeBaseDirArg, resolveGlobalConfig, validatePath } from './options.js';
// ============================================
// Constants
// ============================================
/**
 * Maximum directory recursion depth for `list` scans. Mirrors the
 * `MAX_DEPTH` used by `ingest`'s `walkDirectory` so the two CLI subcommands
 * apply the same boundary to "how deep do we look under a root".
 */
const MAX_DEPTH = 10;
/**
 * Bounded BFS scan of a single root, up to {@link MAX_DEPTH} levels deep.
 * Symlinks are skipped (mirrors `walkDirectory` in `cli/ingest.ts`) and
 * paths under `excludePaths` are filtered out. Per-directory `readdir`
 * errors are captured into the returned `warnings` and do not abort the
 * scan; this is the key change introduced by Finding #10 — a permission-
 * denied error under one root must not hide files under another root.
 */
async function scanRoot(root, excludePaths) {
    const files = [];
    const warnings = [];
    let depthLimited = false;
    const queue = [{ dirPath: root, depth: 0 }];
    while (queue.length > 0) {
        const { dirPath, depth } = queue.shift();
        if (depth >= MAX_DEPTH) {
            depthLimited = true;
            continue;
        }
        // TypeScript's `readdir` has overloads keyed on the options shape; when
        // `withFileTypes: true` is passed as a literal-typed object the inferred
        // return is `Dirent<string>[]`, which we use directly. The explicit
        // type here keeps the loop body's `entry.isFile()` / `entry.name`
        // accesses pointed at the string-encoded Dirent shape.
        let entries;
        try {
            entries = (await readdir(dirPath, {
                withFileTypes: true,
                encoding: 'utf8',
            }));
        }
        catch (error) {
            // Per-root error tolerance: record the warning and continue. The
            // typical case is permission-denied under a subdirectory; previously
            // this killed the whole `list` invocation.
            const code = error && typeof error === 'object' && 'code' in error
                ? (error.code ?? 'UNKNOWN')
                : 'UNKNOWN';
            warnings.push(`cannot read directory: ${displayPath(dirPath)} (${code})`);
            continue;
        }
        for (const entry of entries) {
            const fullPath = join(dirPath, entry.name);
            if (entry.isSymbolicLink())
                continue;
            if (excludePaths.some((ep) => fullPath.startsWith(ep)))
                continue;
            if (entry.isDirectory()) {
                queue.push({ dirPath: fullPath, depth: depth + 1 });
            }
            else if (entry.isFile() && SUPPORTED_EXTENSIONS.has(extname(entry.name).toLowerCase())) {
                files.push(fullPath);
            }
        }
    }
    if (depthLimited) {
        warnings.push(`some directories under ${displayPath(root)} were skipped because they exceed the maximum depth (${MAX_DEPTH})`);
    }
    return { files, warnings };
}
// ============================================
// Help
// ============================================
const HELP_TEXT = `Usage: mcp-local-rag [global-options] list [options]

List files and their ingestion status.

Options:
  --base-dir <path>      Base directory to scan for files (repeatable: pass once per root; default: BASE_DIRS/BASE_DIR env or cwd)
  -h, --help             Show this help

Global options (must appear before "list"):
  --db-path <path>       LanceDB database path
  --cache-dir <path>     Model cache directory
  --model-name <name>    Embedding model`;
// ============================================
// Arg Parsing
// ============================================
/**
 * Parse list-specific CLI arguments.
 * Flags: --base-dir, -h/--help
 * No positional arguments accepted.
 * Unknown flags cause exit(1).
 */
export function parseArgs(args) {
    const options = {};
    let help = false;
    let i = 0;
    while (i < args.length) {
        const arg = args[i];
        switch (arg) {
            case '-h':
            case '--help':
                help = true;
                i++;
                break;
            case '--base-dir': {
                // Repeatable: each `--base-dir <path>` occurrence appends one entry
                // to `options.baseDirs`. The accumulator is lazily initialized so an
                // absent flag leaves `options.baseDirs` as `undefined`, which the
                // resolver treats as "fall through to env / cwd".
                if (options.baseDirs === undefined) {
                    options.baseDirs = [];
                }
                const valueIndex = consumeBaseDirArg(args, i, options.baseDirs);
                i = valueIndex + 1;
                break;
            }
            default:
                if (arg.startsWith('-')) {
                    console.error(`Unknown option: ${arg}`);
                    console.error(HELP_TEXT);
                    process.exit(1);
                }
                console.error(`Unexpected argument: ${arg}`);
                console.error('The list command does not accept positional arguments.');
                process.exit(1);
        }
    }
    return { options, help };
}
// ============================================
// Main Entry Point
// ============================================
/**
 * Run the list CLI subcommand.
 * @param args - Arguments after "list"
 * @param globalOptions - Global options parsed before the subcommand
 */
export async function runList(args, globalOptions = {}) {
    // Parse CLI options
    const { options, help } = parseArgs(args);
    // Handle --help
    if (help) {
        console.error(HELP_TEXT);
        process.exit(0);
    }
    // Resolve global config
    const globalConfig = resolveGlobalConfig(globalOptions);
    // Validate CLI-supplied paths against the sensitive-path policy BEFORE
    // calling the resolver, so the user sees a `--base-dir`-attributed error
    // without an unnecessary realpath round-trip on a rejected path.
    const cliBaseDirs = options.baseDirs ?? [];
    for (const root of cliBaseDirs) {
        const baseDirError = validatePath(root, '--base-dir');
        if (baseDirError) {
            console.error(baseDirError);
            process.exit(1);
        }
    }
    // Resolve effective base directories via the shared CLI resolver
    // (CLI > BASE_DIRS > BASE_DIR > cwd). Resolver errors (invalid BASE_DIRS,
    // missing directory, ...) exit non-zero with a clear stderr message and
    // do NOT fall back. Resolver warnings (`base-dirs-overrides-base-dir`,
    // `nested-root-pruned`) are routed to stderr so the JSON-only stdout
    // contract is preserved.
    const { config: baseDirsConfig, warnings: baseDirsWarnings } = await resolveCliBaseDirsOrExit(cliBaseDirs);
    for (const warning of baseDirsWarnings) {
        console.error(warning.message);
    }
    // Scan every effective root (P2-T2). `legacyBaseDir` still surfaces the
    // first effective root as the JSON `baseDir` field for response back-compat;
    // the `list_files` MCP response evolves to add `baseDirs` and per-file
    // annotations in P3-T2, which is intentionally out of scope here.
    const baseDir = legacyBaseDir(baseDirsConfig);
    try {
        // Initialize VectorStore only (no Embedder needed for list)
        const vectorStore = createVectorStore(globalConfig);
        await vectorStore.initialize();
        // Build exclude paths (resolved to absolute, platform-aware trailing
        // separator). Applied uniformly to every root so dbPath/cacheDir remain
        // excluded under each root even when they happen to live below one of
        // them (AC-011).
        const excludePaths = [
            `${resolve(globalConfig.dbPath)}${sep}`,
            `${resolve(globalConfig.cacheDir)}${sep}`,
        ];
        // Get all ingested entries from the vector store
        const ingested = await vectorStore.listFiles();
        const ingestedMap = new Map(ingested.map((f) => [f.filePath, f]));
        // Scan every effective root, recording the producing root for each
        // file path. Disjoint roots can still surface the same file through
        // symlinks or bind mounts; the first-occurrence-wins dedup preserves
        // root iteration order, mirroring the MCP `list_files` contract.
        // Per-root errors are non-fatal (Finding #10): we collect them as stderr
        // warnings and continue with the remaining roots so one unreadable
        // root does not hide the others.
        const fileToRoot = new Map();
        for (const root of baseDirsConfig.baseDirs) {
            const { files: perRoot, warnings: rootWarnings } = await scanRoot(root, excludePaths);
            for (const warning of rootWarnings) {
                console.error(`Warning [${root}]: ${warning}`);
            }
            for (const filePath of perRoot) {
                if (!fileToRoot.has(filePath)) {
                    fileToRoot.set(filePath, root);
                }
            }
        }
        const baseDirFiles = [...fileToRoot.keys()].sort();
        const baseDirSet = new Set(baseDirFiles);
        // Files with ingestion status and producing-root annotation. The
        // producing root is guaranteed to be present because the path came from
        // the scan above; the non-null assertion below documents the invariant.
        const files = baseDirFiles.map((filePath) => {
            const producingRoot = fileToRoot.get(filePath);
            if (producingRoot === undefined) {
                // Cannot happen by construction (the key came from the same map).
                // Surface as a programming error rather than silently shipping an
                // empty `baseDir` field.
                throw new Error(`internal: missing producing root for ${filePath}`);
            }
            const entry = ingestedMap.get(filePath);
            return entry
                ? {
                    filePath,
                    baseDir: producingRoot,
                    ingested: true,
                    chunkCount: entry.chunkCount,
                    timestamp: entry.timestamp,
                }
                : { filePath, baseDir: producingRoot, ingested: false };
        });
        // Content ingested via ingest_data (web pages, clipboard, etc.) plus any
        // orphaned DB entries whose files no longer exist on disk. Sources are
        // never annotated with a producing root — matches the MCP contract.
        const sources = ingested
            .filter((f) => !baseDirSet.has(f.filePath))
            .map((f) => {
            if (looksLikeRawDataPath(f.filePath)) {
                const source = extractSourceFromPath(f.filePath);
                if (source)
                    return { source, chunkCount: f.chunkCount, timestamp: f.timestamp };
            }
            return { filePath: f.filePath, chunkCount: f.chunkCount, timestamp: f.timestamp };
        });
        const result = {
            baseDirs: [...baseDirsConfig.baseDirs],
            baseDir,
            files,
            sources,
        };
        // Output JSON to stdout
        process.stdout.write(JSON.stringify(result, null, 2));
    }
    catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        console.error(`Failed to list files: ${message}`);
        process.exit(1);
    }
}
//# sourceMappingURL=list.js.map