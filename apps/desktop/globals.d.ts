// The web app's build flags, which the bundled apps/web/src/lib modules read (set in build.mjs and vitest.config.ts).
declare const __LAUNCH_HOLD__: boolean;
declare const __PREVIEW__: boolean;
// True when the release build signs the Mac app with a Developer ID (build.mjs), so it can install its own updates.
declare const __MAC_SIGNED__: boolean;
