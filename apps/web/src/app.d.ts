declare global {
  namespace App {}
  /** True in the static GitHub Pages preview build (PREVIEW=1). */
  const __PREVIEW__: boolean;
  /** True while members see the coming-soon page (src/lib/launch.ts): always on the real site; LAUNCH_HOLD=1 in the preview. */
  const __LAUNCH_HOLD__: boolean;
}
export {};
