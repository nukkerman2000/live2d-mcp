/**
 * Returns the literal prefixes joined with their `realpath`-resolved forms.
 * Without canonicalization macOS would let `/etc` (which realpaths to
 * `/private/etc`) slip past once the resolver normalizes the path. The
 * literal is always kept so a realpath failure cannot weaken the policy.
 */
export declare function buildSensitivePrefixes(realpathSyncFn?: (p: string) => string): string[];
/**
 * Returns a user-facing error string when `value` resolves to a sensitive
 * system or credential directory. Returns `undefined` when the path is
 * acceptable.
 *
 * `flagName` is interpolated into the error message so the surfacing
 * surface (CLI flag, env var, ...) is visible at the call site. The CLI uses
 * `'--base-dir'`; the server entry point uses `'BASE_DIR'` or `'BASE_DIRS'`
 * to attribute the rejection to the env var actually consulted.
 *
 * The trailing-separator check on system prefixes guards against sibling
 * paths like `/etcetera`. Both the `~/.ssh` and the expanded form are
 * rejected so the policy holds when `$HOME` is unset.
 */
export declare function checkSensitivePath(value: string, flagName: string): string | undefined;
//# sourceMappingURL=sensitive-path.d.ts.map