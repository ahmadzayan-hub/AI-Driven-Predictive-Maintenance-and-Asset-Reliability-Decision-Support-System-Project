import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { runFixture } from '../src/tests/run-fixture'
import { skipOnboarding } from './helpers'

test.use({ serviceWorkers: 'block' })

const task = runFixture().tasks[0]
const initial = runFixture({
  id: 'flowtest', state: 'running',
  tasks: [
    { ...task, id: 'collect', role: 'collector', title: 'Collect data', state: 'succeeded' },
    { ...task, state: 'running', summary: 'Initial observation', quality_checks: [{ name: 'synthetic-check', passed: true, detail: 'Synthetic evidence' }] },
    { ...task, id: 'publish', role: 'publish', title: 'Publish report' },
  ],
})

test('live handoffs can be paused without stopping analysis, and respect motion settings', async ({ page }) => {
  await skipOnboarding(page)
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  let current = initial
  let advances = 0
  const mutations: string[] = []
  await page.route(/\/api\/runs\/flowtest(?:\/.*)?$/, async (route) => {
    if (route.request().method() === 'POST') {
      mutations.push(new URL(route.request().url()).pathname)
      advances += 1
    }
    await route.fulfill({ json: current })
  })
  await page.goto('/#/runs/flowtest')
  const flow = page.getByRole('region', { name: 'Agents working together' })
  await expect(flow).toBeVisible()
  await flow.getByRole('button', { name: /^Analytics/ }).focus()
  await page.keyboard.press('Enter')
  await expect(flow.getByText('Initial observation', { exact: true })).toBeVisible()
  // Loading an existing running snapshot does not replay an invented handoff.
  await expect(flow.locator('.agent-flow__signal')).toHaveCSS('animation-name', 'none')
  await flow.getByRole('button', { name: 'Pause live view' }).click()
  const heldAt = advances
  current = { ...initial, updated_at: '2026-10-16T10:01:00Z', tasks: initial.tasks.map((item) => item.id === task.id ? { ...item, state: 'succeeded', summary: 'Updated observation' } : item) }
  await expect.poll(() => advances).toBeGreaterThan(heldAt)
  await expect(flow.getByText('Initial observation', { exact: true })).toBeVisible()
  await expect(flow.getByText('Updated observation', { exact: true })).toHaveCount(0)
  await flow.getByRole('button', { name: 'Resume live view' }).click()
  await expect(flow.getByText('Updated observation', { exact: true })).toBeVisible()
  const signal = flow.locator('.agent-flow__signal')
  await expect(signal).toHaveCSS('animation-duration', '0.9s')
  await expect(signal).toHaveCSS('animation-iteration-count', '1')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(signal).toHaveCSS('animation-name', 'none')
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await page.evaluate(() => { document.documentElement.dataset.motion = 'reduce' })
  await expect(signal).toHaveCSS('animation-name', 'none')
  await flow.getByRole('button', { name: 'Open current evidence' }).click()
  await expect(page.getByRole('dialog')).toContainText('Synthetic evidence')
  await page.keyboard.press('Escape')
  await expect(flow.getByRole('button', { name: 'Open current evidence' })).toBeFocused()
  expect(mutations.every((path) => path === '/api/runs/flowtest/advance')).toBe(true)
})

test('Arabic stage inspection fits small screens and both themes with accessible controls', async ({ page }, testInfo) => {
  await skipOnboarding(page)
  await page.addInitScript(() => localStorage.setItem('aos-locale', 'ar'))
  const failed = {
    ...initial, state: 'failed', error: 'Synthetic interruption',
    tasks: initial.tasks.map((item) => item.id === task.id ? { ...item, state: 'failed', summary: 'تعذّر التحقق من النتائج. راجع الأدلة.' } : item),
  }
  await page.route(/\/api\/runs\/flowtest(?:\/.*)?$/, (route) => route.fulfill({ json: failed }))
  await page.goto('/#/runs/flowtest')
  const flow = page.getByRole('region', { name: 'الوكلاء يعملون معاً' })
  await flow.getByRole('button', { name: /^التحليلات/ }).click()
  await expect(flow.getByText('تعذّر التحقق من النتائج. راجع الأدلة.')).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await expect(page.locator('.pipeline__band > summary > span').last()).toHaveAttribute('dir', 'ltr')
  await expect(flow).toHaveAttribute('data-working', 'false')
  for (const theme of ['light', 'dark']) {
    await page.evaluate((value) => { document.documentElement.dataset.theme = value }, theme)
    for (const width of testInfo.project.name === 'mobile' ? [375, 320] : [1440]) {
      await page.setViewportSize({ width, height: 900 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
      for (const button of await flow.getByRole('button').all()) {
        const bounds = await button.boundingBox()
        expect(bounds!.width).toBeGreaterThanOrEqual(44)
        expect(bounds!.height).toBeGreaterThanOrEqual(44)
      }
      await flow.getByRole('heading', { name: 'الوكلاء يعملون معاً' }).evaluate((element) => element.scrollIntoView({ block: 'center' }))
      await page.screenshot({ path: testInfo.outputPath(`collaboration-${theme}-${width}-ar.png`) })
      await flow.locator('.agent-flow__inspector').evaluate((element) => element.scrollIntoView({ block: 'center' }))
      await page.screenshot({ path: testInfo.outputPath(`collaboration-details-${theme}-${width}-ar.png`) })
    }
    expect((await new AxeBuilder({ page }).include('.agent-flow').withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze()).violations).toEqual([])
  }
  await flow.getByRole('button', { name: 'فتح الأدلة الحالية' }).click()
  await expect(page.getByRole('dialog')).toContainText('Synthetic evidence')
  await page.keyboard.press('Escape')
})
