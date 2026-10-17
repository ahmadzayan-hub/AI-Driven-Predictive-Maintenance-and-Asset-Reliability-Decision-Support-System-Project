import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mkdir, readFile } from 'node:fs/promises'

test('filters, evidence, keyboard review, local-only actions and sample export', async ({ page }) => {
  const requests: string[] = []
  const errors: string[] = []
  page.on('request', (request) => { if (request.url().includes('/api/')) requests.push(request.url()) })
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/?design=maintenance')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('A clear view of what needs attention.')
  await page.getByRole('combobox', { name: 'Site', exact: true }).selectOption('north')
  await expect(page.getByText('88 h', { exact: true })).toBeVisible()
  await expect(page.getByText('21,320 USD', { exact: true })).toBeVisible()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export sample summary' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('synthetic-maintenance-preview-summary.csv')
  const csv = await readFile((await download.path())!, 'utf8')
  expect(csv).toContain('fictional-ui-design-fixture,north,current,4,95.42,88,21320')
  await page.getByRole('button', { name: 'Review record PMP-101', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(page.getByRole('button', { name: 'Mark reviewed in preview' })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Close evidence' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Review record PMP-101', exact: true })).toBeFocused()
  await page.getByRole('button', { name: 'Maintenance reviews', exact: true }).click()
  await page.getByRole('button', { name: 'Review record PMP-101', exact: true }).click()
  await page.getByRole('button', { name: 'Mark reviewed in preview' }).click()
  await page.getByRole('button', { name: 'Close evidence' }).click()
  await expect(page.getByRole('button', { name: 'Review record PMP-101', exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 1 })).toBeFocused()
  await page.reload()
  await page.getByRole('button', { name: 'Maintenance reviews', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Review record PMP-101', exact: true })).toBeVisible()
  expect(requests).toEqual([])
  expect(errors).toEqual([])
})

test('English and Arabic pages remain accessible in both themes', async ({ page }, info) => {
  test.setTimeout(90_000)
  await page.goto('/?design=maintenance')
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await mkdir('../docs/screenshots/maintenance', { recursive: true })
  for (const language of ['en', 'ar']) {
    if (language === 'ar') await page.getByRole('button', { name: 'Change language', exact: true }).click()
    await expect(page.locator('html')).toHaveAttribute('dir', language === 'ar' ? 'rtl' : 'ltr')
    const labels = language === 'en'
      ? ['Executive overview', 'Asset reliability', 'Maintenance reviews', 'Cost & exposure', 'Model evidence']
      : ['النظرة التنفيذية', 'موثوقية الأصول', 'مراجعات الصيانة', 'التكلفة والأثر', 'أدلة النماذج']
    for (const theme of ['light', 'dark']) {
      if (theme === 'dark') await page.getByRole('button', { name: language === 'en' ? 'Switch to dark theme' : 'التبديل إلى المظهر الداكن', exact: true }).click()
      for (const label of labels) {
        await page.getByRole('navigation').getByRole('button', { name: label, exact: true }).click()
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
        expect(overflow, `${language} ${theme} ${label}`).toBe(false)
        const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
        expect(audit.violations, `${language} ${theme} ${label}`).toEqual([])
        if (label === labels[0]) {
          await page.screenshot({ path: `../docs/screenshots/maintenance/${info.project.name}-${language}-${theme}.png`, fullPage: true })
        }
      }
      if (theme === 'dark') await page.getByRole('button', { name: language === 'en' ? 'Switch to light theme' : 'التبديل إلى المظهر الفاتح', exact: true }).click()
    }
  }
  // Verify the minimum supported width separately from the phone screenshots.
  await page.setViewportSize({ width: 320, height: 812 })
  for (const language of ['ar', 'en']) {
    if (language === 'en') await page.getByRole('button', { name: 'تغيير اللغة', exact: true }).click()
    await page.getByRole('navigation').getByRole('button', { name: language === 'en' ? 'Executive overview' : 'النظرة التنفيذية', exact: true }).click()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const clipped = await page.locator('.maintenance__metric > strong, .maintenance__legend').evaluateAll((items) =>
      items.filter((item) => item.scrollWidth > item.clientWidth + 1).map((item) => item.textContent))
    expect(clipped).toEqual([])
  }
})
