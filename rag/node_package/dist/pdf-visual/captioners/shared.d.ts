/**
 * Strip C0 (U+0000–U+001F) and C1 (U+007F–U+009F) control characters from the
 * input, except `\n` (U+000A) and `\t` (U+0009) which are kept verbatim.
 */
export declare function stripControlChars(input: string): string;
/**
 * Apply the post-generation processing rules. Returns the final caption or
 * `null` when the result is empty after stripping.
 */
export declare function postProcess(decoded: string): string | null;
//# sourceMappingURL=shared.d.ts.map