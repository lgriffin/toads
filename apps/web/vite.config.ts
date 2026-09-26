import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [sveltekit()],
  define: { __PREVIEW__: JSON.stringify(process.env.PREVIEW === '1') },
  server: { proxy: { '/api': 'http://localhost:8000', '/auth': 'http://localhost:8000' } },
  test: { include: ['src/**/*.test.ts'] }
});
