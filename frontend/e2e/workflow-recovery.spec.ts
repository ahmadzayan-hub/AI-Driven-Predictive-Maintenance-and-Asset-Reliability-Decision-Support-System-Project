import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { skipOnboarding } from './helpers'

for (const language of ['en', 'ar'] as const) {
  test(`${language} analysis lists recover without losing the question or creating a run`, async ({ page }) => {
    await skipOnboarding(page)
    await page.addInitScript((locale) => localStorage.setItem('aos-locale', locale), language)
    let datasetReads = 0
    let runReads = 0
    let writes = 0
    await page.route('**/api/datasets', async (route) => {
      if (route.request().method() !== 'GET') { writes += 1; await route.abort(); return }
      datasetReads += 1
      await route.fulfill({ status: datasetReads === 1 ? 503 : 200, contentType: 'application/json',
        body: JSON.stringify(datasetReads === 1 ? { error: 'Synthetic unavailable' } : { datasets: [] }) })
    })
    await page.route('**/api/runs', async (route) => {
      if (route.request().method() !== 'GET') { writes += 1; await route.abort(); return }
      runReads += 1
      await route.fulfill({ status: runReads === 1 ? 503 : 200, contentType: 'application/json',
        body: JSON.stringify(runReads === 1 ? { error: 'Synthetic unavailable' } : { runs: [] }) })
    })
    await page.goto('/#/runs')
    const ar = language === 'ar'
    const question = page.getByLabel(ar ? 'الهدف' : 'Goal', { exact: true })
    await question.fill('Synthetic preserved question')
    await page.getByRole('button', { name: ar ? 'مجموعة بيانات مخزنة' : 'Stored dataset', exact: true }).click()
    const datasetRetry = page.getByRole('button', { name: ar ? 'إعادة محاولة تحميل البيانات' : 'Retry loading datasets', exact: true })
    const runRetry = page.getByRole('button', { name: ar ? 'إعادة محاولة تحميل التحليلات السابقة' : 'Retry loading previous runs', exact: true })
    await expect(datasetRetry).toBeVisible()
    await expect(runRetry).toBeVisible()
    await expect(page.getByRole('button', { name: ar ? 'بدء التحليل' : 'Start run', exact: true })).toBeDisabled()
    const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    expect(audit.violations).toEqual([])
    await datasetRetry.focus()
    await page.keyboard.press('Enter')
    await expect(datasetRetry).toHaveCount(0)
    await runRetry.focus()
    await page.keyboard.press('Enter')
    await expect(runRetry).toHaveCount(0)
    await expect(question).toHaveValue('Synthetic preserved question')
    await expect(page.locator('html')).toHaveAttribute('dir', ar ? 'rtl' : 'ltr')
    expect(writes).toBe(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  })
}
