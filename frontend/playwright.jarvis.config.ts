import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e-jarvis', outputDir: './e2e/.tmp/jarvis-results', workers: 1, timeout: 45_000,
  webServer: process.env.JARVIS_DATA_DIR ? {
    command: `python ../scripts/serve_jarvis_demo.py --data-dir "${process.env.JARVIS_DATA_DIR}" --port 8017`,
    url: 'http://127.0.0.1:8017/api/jarvis-demo', reuseExistingServer: false,
  } : undefined,
  reporter: [['list']], use: { serviceWorkers: 'block', baseURL: 'http://127.0.0.1:8017', viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure', launchOptions: { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } },
})
