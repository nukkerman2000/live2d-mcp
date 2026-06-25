import type { GroupingMode } from './vectordb/index.js';
/** Result of parsing an environment variable */
export interface ParseResult<T> {
    value: T | undefined;
    warning?: string;
}
/**
 * Parse grouping mode from environment variable
 */
export declare function parseGroupingMode(value: string | undefined): ParseResult<GroupingMode>;
/**
 * Parse max distance from environment variable
 */
export declare function parseMaxDistance(value: string | undefined): ParseResult<number>;
/**
 * Parse max files from environment variable
 */
export declare function parseMaxFiles(value: string | undefined): ParseResult<number>;
/**
 * Parse hybrid weight from environment variable
 */
export declare function parseHybridWeight(value: string | undefined): ParseResult<number>;
/**
 * Parse chunk minimum length from environment variable
 */
export declare function parseChunkMinLength(value: string | undefined): ParseResult<number>;
/**
 * Start the RAG MCP Server
 * Configuration is read from environment variables only (no CLI flags).
 * This ensures the bare `mcp-local-rag` launch is suitable for MCP clients.
 */
export declare function startServer(): Promise<void>;
//# sourceMappingURL=server-main.d.ts.map