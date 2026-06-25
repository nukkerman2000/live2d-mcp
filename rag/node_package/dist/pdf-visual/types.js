// Shared types for the `pdf-visual` package.
//
// `VlmError` is the package-wide named error for the visual ingest path. It
// was originally staged in `renderer.ts` (T3.1) and promoted here at T3.3 so
// that `renderer.ts`, `captioner.ts`, and the orchestrator (`index.ts`) can
// all import from a single source. Shape mirrors
// `src/parser/index.ts:54-62`'s `ValidationError` pattern: a named class
// extending `Error`, with `name` assignment and a public override `cause`.
//
// `CaptionerConfig` / `Captioner` are the captioner's public interface,
// declared per DD § Component → pdf-visual/captioner.ts.
/**
 * Error raised by any module on the visual ingest path. Carries the offending
 * 1-based page number so callers can correlate it with the page list.
 */
export class VlmError extends Error {
    cause;
    pageNum;
    constructor(message, options) {
        super(message);
        this.name = 'VlmError';
        if (options.cause !== undefined) {
            this.cause = options.cause;
        }
        this.pageNum = options.pageNum;
    }
}
//# sourceMappingURL=types.js.map