import { defineConfig } from '@playwright/test'
import base from './playwright.config'

// Native browsers on hosted OS runners; these are engine checks, not evidence
// of installing the PWA on a physical Windows, iPhone or iPad device.
const windows = process.platform === 'win32'
export default defineConfig({
  ...base,
  testMatch: /(?:platform|intake|workspace|models)\.spec\.ts/,
  projects: windows ? [{
    name: 'windows-edge',
    use: { browserName: 'chromium', channel: 'msedge', viewport: { width: 1440, height: 900 } },
  }] : [{
    name: 'webkit-phone',
    use: { browserName: 'webkit', viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
  }],
})
