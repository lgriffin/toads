import { defineConfig, devices } from '@playwright/test';

// E2E runs against the static GitHub Pages preview build (PREVIEW=1) served under a base path.
const BASE_PATH = '/toads';
const PORT = 4173;

export default defineConfig({
  testDir: 'e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}${BASE_PATH}/`,
    trace: 'retain-on-failure'
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run build && node e2e/serve.mjs',
    env: { PREVIEW: '1', BASE_PATH, PORT: String(PORT) },
    url: `http://127.0.0.1:${PORT}${BASE_PATH}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000
  }
});
