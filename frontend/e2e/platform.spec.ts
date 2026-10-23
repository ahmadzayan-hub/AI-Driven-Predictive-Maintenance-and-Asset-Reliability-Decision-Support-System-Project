import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { skipOnboarding } from './helpers'

// Route-controlled failure must reach Playwright in WebKit as well as Chromium.
test.use({ serviceWorkers: 'block', contextOptions: { reducedMotion: 'reduce' } })

test('a committed run with a lost response recovers after reload without a duplicate', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/#/runs')
  const question = `Synthetic recovery ${test.info().project.name}`
  await page.getByLabel('Goal', { exact: true }).fill(question)
  let firstId = '', firstKey = '', requests = 0
  await page.route('**/api/runs', async (route) => {
    if (route.request().method() !== 'POST') return route.continue()
    requests += 1
    const response = await route.fetch()
    const body = await response.json()
    const key = route.request().headers()['idempotency-key']
    expect(key).toBeTruthy()
    if (requests === 1) {
      expect(response.status()).toBe(201)
      firstId = body.id; firstKey = key
      // The server committed. Only the browser's response is lost.
      await route.abort('failed')
    } else {
      expect(response.status()).toBe(200)
      expect(key).toBe(firstKey)
      expect(body.id).toBe(firstId)
      await route.fulfill({ response })
    }
  })
  await page.getByRole('button', { name: 'Start run', exact: true }).click()
  await expect.poll(() => requests).toBe(1)
  await expect(page.getByRole('alert')).toContainText('Cannot reach')
  await expect(page.getByLabel('Goal', { exact: true })).toHaveValue(question)
  await page.reload()
  await expect(page.getByLabel('Goal', { exact: true })).toHaveValue(question)
  await page.getByRole('button', { name: 'Start run', exact: true }).click()
  await expect(page).toHaveURL(new RegExp(`#/runs/${firstId}`))
  expect(requests).toBe(2)
  const list = await (await page.request.get('/api/runs')).json()
  expect(list.runs.filter((run: { goal: string }) => run.goal === question)).toHaveLength(1)
})

for (const language of ['en', 'ar'] as const) {
  test(`every relationship point has the same numeric alternative in ${language}`, async ({ page }) => {
    test.setTimeout(60_000)
    await skipOnboarding(page)
    await page.addInitScript((locale) => localStorage.setItem('aos-locale', locale), language)
    const csv = ['month,plant,sales,units', ...Array.from({ length: 300 }, (_, i) =>
      `2025-${String(i % 12 + 1).padStart(2, '0')},Plant ${i % 3},${i + 1},${i * 2 + 1}`)].join('\n')
    let run = await (await page.request.post('/api/runs', { data: {
      goal: `Synthetic relationship ${language}`, dataset_text: csv, dataset_name: 'synthetic-relationship.csv',
    } })).json()
    for (let i = 0; i < 80 && ['queued', 'running'].includes(run.state); i += 1)
      run = await (await page.request.post(`/api/runs/${run.id}/advance`)).json()
    expect(run.state).toBe('awaiting_approval')
    await page.goto(`/#/dashboard/${run.id}/relationship`)
    const figure = page.locator('.dash-figure')
    await expect(figure.locator('svg circle')).toHaveCount(300)
    await figure.locator('summary').click()
    await expect(figure.locator('tbody tr')).toHaveCount(300)
    await expect(figure.locator('tbody tr').last()).toContainText('300')
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
    const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
    expect(audit.violations).toEqual([])
  })
}
