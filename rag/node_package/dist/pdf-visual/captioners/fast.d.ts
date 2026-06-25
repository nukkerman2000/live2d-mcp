import type { Captioner } from '../types.js';
/**
 * Create a `fast` profile captioner. The dispatcher has already configured
 * `env.cacheDir`; this profile only owns lazy model loading and inference.
 */
export declare function createFastCaptioner(resolvedDevice: string): Captioner;
//# sourceMappingURL=fast.d.ts.map