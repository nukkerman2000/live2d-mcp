import { Embedder } from '../embedder/index.js';
import { type BaseDirsConfig, type BaseDirsConfigWarning } from '../utils/base-dirs.js';
import { VectorStore } from '../vectordb/index.js';
import { type ResolvedGlobalConfig } from './options.js';
/**
 * Create an uninitialized VectorStore from resolved global config.
 * Callers are responsible for calling initialize() before use.
 */
export declare function createVectorStore(config: ResolvedGlobalConfig): VectorStore;
/**
 * Create an uninitialized Embedder from resolved global config.
 * Callers are responsible for managing the Embedder lifecycle.
 */
export declare function createEmbedder(config: ResolvedGlobalConfig): Embedder;
/**
 * Result of {@link resolveCliBaseDirsOrExit}. Resolution warnings travel with
 * the config so subcommands can render them per their own UI contract (CLI
 * subcommands generally write them to stderr).
 */
export interface CliBaseDirsResolution {
    config: BaseDirsConfig;
    warnings: BaseDirsConfigWarning[];
}
/**
 * Resolve effective base directories for a CLI subcommand using the shared
 * resolver, surfacing any configuration error as a process-level failure.
 *
 * Inputs (single source of truth for CLI precedence — kept here so per-
 * subcommand entry points don't each replicate the env-fallback chain):
 *  - `cliRoots`: repeated `--base-dir` flag values in CLI order. When non-
 *    empty, REPLACES env roots — no merge.
 *  - `process.env['BASE_DIRS']`: JSON array, used only when CLI roots are
 *    absent.
 *  - `process.env['BASE_DIR']`: single path, used only when CLI roots and
 *    `BASE_DIRS` are absent.
 *  - `process.cwd()`: final fallback.
 *
 * Failure mode: a `BaseDirsConfigError` (invalid `BASE_DIRS` JSON, missing
 * directory, not-a-directory, ...) is reported to stderr and exits with
 * code 1. This is intentional: the resolver explicitly does NOT fall back
 * (see §Technical Decisions → Resolution order in the multi-base-dirs
 * plan), so CLI consumers should fail fast rather than silently degrading
 * to `cwd`.
 *
 * Warnings (`base-dirs-overrides-base-dir`, `nested-root-pruned`) are
 * returned to the caller rather than written here, so each subcommand can
 * decide its own rendering (JSON-output subcommands like `list` may need
 * to keep stderr clean even when warnings are present).
 */
export declare function resolveCliBaseDirsOrExit(cliRoots: string[]): Promise<CliBaseDirsResolution>;
//# sourceMappingURL=common.d.ts.map