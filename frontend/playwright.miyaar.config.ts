import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e-miyaar',
  outputDir: './test-results/miyaar',
  timeout: 45_000,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4175',
    reducedMotion: 'reduce',
    trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : undefined,
  },
  webServer: {
    command: 'node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4175 --strictPort',
    url: 'http://127.0.0.1:4175', reuseExistingServer: false,
  },
})
