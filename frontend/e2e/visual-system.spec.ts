import { expect, test } from '@playwright/test'
import { skipOnboarding, viewLoaded } from './helpers'

// Disposable test server only. No private records, model requests or screenshots.
const routes = ['overview', 'datasets', 'runs', 'assets', 'rmd', 'approvals',
  'operations', 'dashboard', 'assistant', 'memory', 'activity', 'preferences']

for (const locale of ['en', 'ar']) {
  test(`shared visual system and reachable content across all routes (${locale})`, async ({ page }) => {
    await skipOnboarding(page)
    await page.addInitScript(language => {
      localStorage.setItem('aos-locale', language)
      localStorage.setItem('aos-theme', 'light')
    }, locale)
    for (const route of routes) {
      await page.goto(`/#/${route}`)
      await expect(page.locator('.main')).toBeVisible()
      await viewLoaded(page)
      await expect(page.locator('.shell__header')).toHaveCSS('background-color', 'rgb(16, 36, 58)')
      await expect(page.locator('.shell')).toHaveCSS('background-color', 'rgb(243, 246, 250)')
      await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr')
      const dimensions = await page.evaluate(() => ({
        horizontal: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        vertical: document.documentElement.scrollHeight - document.documentElement.clientHeight,
        text: document.querySelector('.main')?.textContent?.trim().length ?? 0,
      }))
      expect(dimensions.horizontal, `${route}: horizontal page overflow`).toBeLessThanOrEqual(1)
      expect(dimensions.vertical, `${route}: nested outer scrollbar`).toBeLessThanOrEqual(1)
      expect(dimensions.text, `${route}: meaningful content`).toBeGreaterThan(10)
    }
  })
}
