import type { GlobalOptions } from './options.js';
interface ListCliOptions {
    /**
     * Collected `--base-dir` values in CLI order. Repeatable: each flag
     * occurrence appends one entry. `undefined` means the flag was not
     * provided.
     */
    baseDirs?: string[] | undefined;
}
interface ParsedArgs {
    options: ListCliOptions;
    help: boolean;
}
/**
 * Parse list-specific CLI arguments.
 * Flags: --base-dir, -h/--help
 * No positional arguments accepted.
 * Unknown flags cause exit(1).
 */
export declare function parseArgs(args: string[]): ParsedArgs;
/**
 * Run the list CLI subcommand.
 * @param args - Arguments after "list"
 * @param globalOptions - Global options parsed before the subcommand
 */
export declare function runList(args: string[], globalOptions?: GlobalOptions): Promise<void>;
export {};
//# sourceMappingURL=list.d.ts.map