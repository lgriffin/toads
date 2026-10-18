import nodeAdapter from '@sveltejs/adapter-node';
import staticAdapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// PREVIEW=1 builds a static site with sample data for GitHub Pages; BASE_PATH is the Pages subpath (e.g. /toads).
const preview = process.env.PREVIEW === '1';

/** @type {import('@sveltejs/kit').Config} */
export default {
  preprocess: vitePreprocess(),
  kit: {
    adapter: preview ? staticAdapter({ fallback: '404.html' }) : nodeAdapter(),
    paths: { base: process.env.BASE_PATH ?? '' },
    // SvelteKit's own CSP header carries a nonce for its inline start-up script, which a fixed policy from Caddy would
    // block. Caddy (infra/Caddyfile*) sets the same policy only on responses that have none, such as the API's.
    // Inline style attributes (bar widths, chart colours) need 'unsafe-inline' for styles. Highlight reels embed only
    // from these three frame sources, and only after a visitor presses play.
    csp: preview
      ? undefined
      : {
          mode: 'auto',
          directives: {
            'default-src': ['self'],
            'script-src': ['self'],
            'style-src': ['self', 'unsafe-inline'],
            'img-src': ['self', 'data:'],
            'frame-src': ['https://www.youtube-nocookie.com', 'https://clips.twitch.tv', 'https://streamable.com'],
            'frame-ancestors': ['none']
          }
        }
  }
};
