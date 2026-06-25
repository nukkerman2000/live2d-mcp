import type { Captioner, CaptionerConfig } from './types.js';
/**
 * ONNX quantization variant. Pinned to the smallest viable variant for both
 * profiles. Exposed for tests only — production has no user-facing knob.
 */
export declare const VLM_DTYPE = "q4";
/**
 * Create a captioner for the requested visual-quality profile. Sets
 * `env.cacheDir` immediately so the global is correct even if the captioner
 * is constructed before any embedder initializes.
 *
 * Concurrency assumption: `env.cacheDir` is a process-global from
 * `@huggingface/transformers`. Setting it here at construction time is safe
 * for the current single-instance usage (one captioner per ingest run). If
 * the codebase ever constructs multiple captioners with DIFFERENT `cacheDir`
 * values in parallel, the last writer wins and the first captioner's
 * `from_pretrained` may resolve against the wrong cache. Avoid concurrent
 * construction with differing cacheDirs.
 */
export declare function createCaptioner(config: CaptionerConfig): Captioner;
//# sourceMappingURL=captioner.d.ts.map