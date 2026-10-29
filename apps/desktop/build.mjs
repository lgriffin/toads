// Bundles the main process into one file. The menus import the website's own nav, launch hold and access rules from
// apps/web/src/lib, so they are compiled in here rather than copied (src/menus.ts).
import { build } from 'esbuild';
import { copyFileSync, mkdirSync } from 'node:fs';

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

// The offline page wears the site's top bar mark (apps/web's favicon.svg) and wordmark face (Cinzel, from the same
// @fontsource package the site uses). They are copied in on every build rather than kept here, so neither drifts.
const shared = new URL('./static/shared/', import.meta.url);
mkdirSync(shared, { recursive: true });
for (const [from, name] of [
  ['../web/static/favicon.svg', 'toads-mark.svg'],
  ['./node_modules/@fontsource/cinzel/files/cinzel-latin-700-normal.woff2', 'cinzel-latin-700-normal.woff2']
]) {
  copyFileSync(new URL(from, import.meta.url), new URL(name, shared));
}
