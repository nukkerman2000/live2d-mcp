import type { GlobalOptions } from './cli/options.js';
export declare const SUBCOMMANDS: readonly ["skills", "ingest", "list", "query", "status", "delete", "read-neighbors"];
export type Subcommand = (typeof SUBCOMMANDS)[number];
/**
 * Handle CLI subcommands. The caller is expected to have already validated
 * `subcommand` against `SUBCOMMANDS`; the union type makes the switch exhaustive.
 * @param subcommand - The validated subcommand name
 * @param args - Arguments following the subcommand (subcommand itself excluded)
 * @param globalOptions - Global options parsed before the subcommand
 */
export declare function handleCli(subcommand: Subcommand, args: string[], globalOptions?: GlobalOptions): Promise<void>;
//# sourceMappingURL=cli-main.d.ts.map