import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mkdir } from 'node:fs/promises'
import { createHash } from 'node:crypto'
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
      const fonts = await page.evaluate(async () => (await document.fonts.load('16px Dubai', 'معيار Asset maintenance')).map(f => ({ family: f.family, status: f.status })))
      expect(fonts).toEqual([{ family: 'Dubai', status: 'loaded' }])
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
        await expect(page.locator('.tabbar button')).toHaveText(locale === 'ar'
          ? ['مصادر البيانات', 'التحليل والأدلة', 'الأولويات والإجراءات', 'التقارير', 'المزيد']
          : ['Data sources', 'Analysis & evidence', 'Priorities & actions', 'Reports', 'More'])
        const more = page.locator('.tabbar button').last()
        await more.click()
        await expect(page.getByRole('dialog')).toBeVisible()
        await page.keyboard.press('Escape')
        await expect(page.getByRole('dialog')).toHaveCount(0)
        await expect(more).toBeFocused()
      }
      const steps = page.locator('.next-action__help')
      await expect(steps).not.toHaveAttribute('open')
      await steps.locator('summary').focus()
      await page.keyboard.press('Enter')
      await expect(steps.locator('ol')).toBeVisible()
      await page.keyboard.press('Enter')
      const recommendation = page.locator('.command__hero .command__limits')
      if (await recommendation.count()) {
        await recommendation.locator('summary').focus()
        await page.keyboard.press('Enter')
        await expect(recommendation.locator('p')).toBeVisible()
        await page.keyboard.press('Enter')
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


test('serves the exact original official Dubai face', async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'One asset integrity check')
  const response = page.waitForResponse(r => /Dubai-Regular.*\.ttf(?:$|\?)/.test(r.url()))
  await page.goto('/')
  const bytes = await (await response).body()
  expect(bytes.length).toBe(139928)
  expect(createHash('sha256').update(bytes).digest('hex')).toBe('e7b232e0d3a6699f9d9023c0b49a9288ead97a33bc5175b9d1619c09f8672298')
})

for (const locale of ['en', 'ar']) test(`font failure keeps ${locale} actions readable`, async ({ page }, info) => {
  test.skip(info.project.name !== 'desktop', 'Explicit fallback test')
  await page.setViewportSize({ width: 320, height: 900 })
  await page.addInitScript(lang => localStorage.setItem('aos-locale', lang), locale)
  await page.route('**/*.ttf', route => route.abort())
  await page.goto('/')
  await viewLoaded(page)
  await page.evaluate(() => document.fonts.ready)
  await expect(page.locator('.brand__name')).toHaveText(locale === 'ar' ? 'معيار' : 'Miyaar')
  await expect(page.locator('.next-action button')).toBeVisible()
  expect(await page.evaluate(() => document.fonts.check('16px Dubai', 'معيار Asset maintenance'))).toBe(false)
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  await mkdir('../docs/screenshots', { recursive: true })
  await page.screenshot({ path: `../docs/screenshots/miyaar-task-first-synthetic-fallback-${locale}-320.png` })
})
