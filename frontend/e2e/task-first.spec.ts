import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mkdir } from 'node:fs/promises'
import { viewLoaded } from './helpers'

// Actual browser captures of the explicit fictional demo, never live operational data.
test.use({ baseURL: 'http://127.0.0.1:8125', contextOptions: { reducedMotion: 'reduce' } })
for (const theme of ['light', 'dark'] as const) {
for (const locale of ['en', 'ar'] as const) {
  for (const width of [320, 360, 390, 1440]) {
    test(`task-first ${theme} ${locale} at ${width}px`, async ({ page }, info) => {
      test.skip(info.project.name !== 'desktop', 'Explicit viewport matrix runs once')
      await page.setViewportSize({ width, height: 900 })
      await page.addInitScript((language) => localStorage.setItem('aos-locale', language), locale)
      if (theme === 'dark') await page.addInitScript(() => localStorage.setItem('aos-theme', 'dark'))
      await page.goto('/')
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
      await viewLoaded(page)
      await expect(page.locator('.next-action')).toBeVisible()
      await expect(page.locator('.command--pending')).toHaveCount(0)
      await expect(page.locator('.brand__name')).toHaveText(locale === 'ar' ? 'معيار' : 'Miyaar')
      await expect(page.locator('.shell__mode')).toBeVisible()
      await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr')
      const action = page.locator('.next-action button')
      const bounds = await action.boundingBox()
      expect(bounds).not.toBeNull()
      expect(bounds!.y + bounds!.height).toBeLessThan(800)
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
      expect(await page.locator('.brand__name').evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true)
      if (width < 1024) {
        await expect(page.locator('.tabbar button')).toHaveCount(5)
        const more = page.locator('.tabbar button').last()
        await more.click()
        await expect(page.getByRole('dialog')).toBeVisible()
        await page.keyboard.press('Escape')
        await expect(page.getByRole('dialog')).toHaveCount(0)
        await expect(more).toBeFocused()
      }
      const summary = page.locator('.overview__disclosure > summary').first()
      await summary.focus()
      await page.keyboard.press('Enter')
      await expect(summary.locator('..')).toHaveAttribute('open', '')
      await page.keyboard.press('Enter')
      await expect(summary.locator('..')).not.toHaveAttribute('open')
      await page.locator('.panel:visible').evaluate((el) => { el.scrollTop = 0 })
      const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
      expect(axe.violations).toEqual([])
      await mkdir('../docs/screenshots', { recursive: true })
      await page.screenshot({ path: `../docs/screenshots/miyaar-task-first-synthetic-${theme}-${locale}-${width}.png` })
      // Text zoom / reflow: CSS zoom exercises layout without claiming physical-device QA.
      await page.locator('html').evaluate((el) => { el.style.zoom = '2' })
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
      await expect(action).toBeVisible()
      await page.locator('html').evaluate((el) => { el.style.zoom = '' })
      await action.click()
      await expect(page).toHaveURL(/#\/runs\/[a-zA-Z0-9_-]+$/)
    })
  }
}
}
