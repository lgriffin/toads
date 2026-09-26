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
    paths: { base: process.env.BASE_PATH ?? '' }
  }
};
