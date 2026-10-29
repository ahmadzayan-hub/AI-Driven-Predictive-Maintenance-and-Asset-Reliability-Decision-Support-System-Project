import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { skipOnboarding } from './helpers'

test.use({ contextOptions: { reducedMotion: 'reduce' } })

for (const language of ['en', 'ar'] as const) {
  test(`trend point accepts a direct pointer click and keyboard release (${language})`, async ({ page }, testInfo) => {
    await skipOnboarding(page)
    await page.addInitScript((locale) => localStorage.setItem('aos-locale', locale), language)
    let run = await (await page.request.post('/api/runs', { data: { goal: 'Synthetic trend interaction review', report_language: language } })).json()
    for (let i = 0; i < 80 && ['queued', 'running'].includes(run.state); i++) {
      run = await (await page.request.post(`/api/runs/${run.id}/advance`)).json()
    }
    expect(run.state).toBe('awaiting_approval')
    await page.goto(`/#/dashboard/${run.id}/trend`)
    const chart = page.locator('.dash-page .dash-svg').first()
    const point = chart.locator('circle[role="button"]').nth(1)
    await expect(point).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath(`trend-${language}-before.png`), fullPage: true })
    const count = await page.locator('.dash-coverage').innerText()
    // Normal hit testing must reach the control at its centre. No force click.
    await point.click({ timeout: 5000 })
    await expect(page).toHaveURL(/from=2025-02&to=2025-02/)
    const held = chart.locator('circle[aria-pressed="true"]')
    await expect(held).toHaveCount(1)
    await expect(page.locator('.dash-coverage')).not.toHaveText(count)
    await page.screenshot({ path: testInfo.outputPath(`trend-${language}-selected.png`), fullPage: true })
    await held.press('Enter')
    await expect(page.locator('.dash-coverage')).toHaveText(count)
    expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()).violations).toEqual([])
  })
}

test('Arabic dashboard pages remain readable in RTL', async ({ page }, testInfo) => {
  test.setTimeout(60000)
  await skipOnboarding(page)
  await page.addInitScript(() => localStorage.setItem('aos-locale', 'ar'))
  let run = await (await page.request.post('/api/runs', { data: { goal: 'فحص عربي ببيانات تجريبية', report_language: 'ar' } })).json()
  for (let i = 0; i < 80 && ['queued', 'running'].includes(run.state); i++) {
    run = await (await page.request.post(`/api/runs/${run.id}/advance`)).json()
  }
  expect(run.state).toBe('awaiting_approval')
  for (const view of ['overview', 'breakdown', 'trend', 'distribution', 'relationship', 'records']) {
    await page.goto(`/#/dashboard/${run.id}/${view}`)
    await expect(page.locator('.dash-coverage')).toHaveText('يُعرض 72 من أصل 72 سجلاً.')
    await expect(page.locator('.dash-page .skeleton')).toHaveCount(0)
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
    expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()).violations).toEqual([])
    await page.screenshot({ path: testInfo.outputPath(`arabic-${view}.png`), fullPage: true })
  }
})
