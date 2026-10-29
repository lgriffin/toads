import { defineConfig } from 'vitest/config';

export default defineConfig({
  define: { __LAUNCH_HOLD__: 'true', __PREVIEW__: 'false' },
  // The web app's tsconfig extends one SvelteKit writes on `svelte-kit sync`; the desktop tests must not need it.
  // Vite passes `tsconfig` through to oxc-transform, though its OxcOptions type leaves it out.
  // @ts-expect-error -- see above
  oxc: { tsconfig: false },
  test: { include: ['test/**/*.test.ts'] }
});
