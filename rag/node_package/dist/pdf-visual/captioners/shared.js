// Profile-agnostic helpers shared by every `captioners/*` profile.
//
// `stripControlChars` + `postProcess` are the post-generation pipeline
// documented in the captioner contract: control-char stripping, whitespace
// trim, empty → `null`, length cap with ellipsis. Both `fast` and `quality`
// profiles run the captioner output through the same pipeline so caption
// chunk shape is independent of profile.
/**
 * Strip C0 (U+0000–U+001F) and C1 (U+007F–U+009F) control characters from the
 * input, except `\n` (U+000A) and `\t` (U+0009) which are kept verbatim.
 */
export function stripControlChars(input) {
    let out = '';
    for (let i = 0; i < input.length; i++) {
        const code = input.charCodeAt(i);
        if (code === 0x09 || code === 0x0a) {
            out += input[i];
            continue;
        }
        if (code <= 0x1f)
            continue;
        if (code >= 0x7f && code <= 0x9f)
            continue;
        out += input[i];
    }
    return out;
}
/**
 * Apply the post-generation processing rules. Returns the final caption or
 * `null` when the result is empty after stripping.
 */
export function postProcess(decoded) {
    const stripped = stripControlChars(decoded).trim();
    if (stripped.length === 0)
        return null;
    if (stripped.length > 1000)
        return `${stripped.slice(0, 1000)}…`;
    return stripped;
}
//# sourceMappingURL=shared.js.map