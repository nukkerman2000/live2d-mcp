import type { Annotations } from '@modelcontextprotocol/sdk/types.js';
/**
 * Shape of a single MCP content block used by RAG server handlers. Mirrors
 * the SDK's `TextContent` minus the strictly internal fields — defined here
 * (rather than imported) because the SDK exposes the type through a
 * widely-imported union; using a local alias keeps handler signatures stable
 * if the SDK widens the union later.
 */
export type RagContentBlock = {
    type: 'text';
    text: string;
    annotations?: Annotations;
};
/**
 * Build the (zero or one) warning content block for the supplied warnings.
 *
 * Returns `[]` when no warnings exist so the caller can spread the result
 * unconditionally without producing a spurious block. The single emitted
 * block joins all warnings with ` | ` so MCP clients display them together
 * — the per-warning structured form lives in the configuration layer
 * (`BaseDirsConfigWarning`); here we render a single user-facing string.
 *
 * Centralizing this in one helper is the design-doc-mandated countermeasure
 * for the "warning shape changes touch many handlers" risk (P3-T3). Every
 * handler must use this helper — do not inline the content shape.
 */
export declare function buildConfigWarningBlocks(warnings: readonly string[]): RagContentBlock[];
/**
 * Append config-warning blocks to an existing content array. Returns the
 * same `content` reference for chainability (handlers typically build the
 * array first, then call this once before returning).
 */
export declare function appendConfigWarnings(content: RagContentBlock[], warnings: readonly string[]): RagContentBlock[];
/**
 * Build a diagnostic content block exposing the supplied config-error
 * message. Used by `status` when the server is in degraded mode (invalid
 * `BASE_DIRS`) so the user can read the error via the MCP response without
 * inspecting stderr.
 */
export declare function buildConfigErrorBlock(message: string): RagContentBlock;
/**
 * Format error message based on environment.
 * Shows stack trace in development mode for debugging.
 * Shows only error message in production for security (secure by default).
 */
export declare function formatErrorMessage(error: unknown): string;
//# sourceMappingURL=error-utils.d.ts.map