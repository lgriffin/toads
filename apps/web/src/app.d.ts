declare global {
  namespace App {}
  /** True in the static GitHub Pages preview build (PREVIEW=1). */
  const __PREVIEW__: boolean;
  /** True while members see the coming-soon page (src/lib/launch.ts): lifted for the Forever launch; a build with LAUNCH_HOLD=1 holds again. */
  const __LAUNCH_HOLD__: boolean;
}
export {};
