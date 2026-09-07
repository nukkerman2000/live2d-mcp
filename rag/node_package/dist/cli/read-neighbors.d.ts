import type { GlobalOptions } from './options.js';
/**
 * Run the read-neighbors CLI subcommand.
 * Reads chunks adjacent to a target chunkIndex within a single document.
 * Does NOT perform any search; this is an index-adjacent retrieval utility.
 *
 * @param args - Arguments after "read-neighbors"
 * @param globalOptions - Global options parsed before the subcommand
 */
export declare function runReadNeighbors(args: string[], globalOptions?: GlobalOptions): Promise<void>;
//# sourceMappingURL=read-neighbors.d.ts.map