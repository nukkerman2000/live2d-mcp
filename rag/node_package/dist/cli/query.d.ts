import type { GlobalOptions } from './options.js';
interface QueryCliOptions {
    limit?: number | undefined;
}
interface ParsedArgs {
    queryText: string | undefined;
    options: QueryCliOptions;
    help: boolean;
}
/**
 * Parse query-specific CLI arguments into options and a positional query text.
 * Flags: --limit, -h/--help
 * Unknown flags (including global flags passed after subcommand) cause an error.
 */
export declare function parseArgs(args: string[]): ParsedArgs;
/**
 * Run the query CLI subcommand.
 * @param args - Arguments after "query" (e.g., option flags and query text)
 * @param globalOptions - Global options parsed before the subcommand
 */
export declare function runQuery(args: string[], globalOptions?: GlobalOptions): Promise<void>;
export {};
//# sourceMappingURL=query.d.ts.map