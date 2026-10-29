// Bundles the main process into one file. The menus import the website's own nav, launch hold and access rules from
// apps/web/src/lib, so they are compiled in here rather than copied (src/menus.ts).
import { build } from 'esbuild';

await build({
  entryPoints: ['src/main.ts'],
  outfile: 'dist/main.cjs',
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node22',
  external: ['electron'],
  // The real site's build: the launch hold is on unless launch.ts lifts it (apps/web/vite.config.ts).
  define: { __LAUNCH_HOLD__: 'true', __PREVIEW__: 'false' },
  sourcemap: true,
  logLevel: 'info'
});
