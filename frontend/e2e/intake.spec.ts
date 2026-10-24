import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { skipOnboarding } from './helpers'

test('maintenance preview leads to a real upload, agents, approval gate and dashboard', async ({ page }) => {
  test.setTimeout(75_000)
  await skipOnboarding(page)
  await page.goto('/?design=maintenance')
  // Every upload call to action reaches the one Datasets flow (U15), where
  // the preview and the mapping live; the stored dataset is then analysed.
  await page.getByRole('link', { name: 'Upload & analyze your data', exact: true }).click()
  await expect(page).toHaveURL(/#\/datasets$/)
  const uploadPromise = page.waitForResponse((response) => response.url().includes('/api/datasets?') && response.request().method() === 'POST')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'maintenance-intake.csv', mimeType: 'text/csv',
    buffer: Buffer.from('month,plant,maintenance_cost,downtime_hours\n2026-07,North,310,2\n2026-08,South,322,4\n2026-09,North,331,3\n'),
  })
  const uploaded = await (await uploadPromise).json()
  await page.getByRole('button', { name: 'Analyse maintenance-intake.csv', exact: true }).click()
  await expect(page).toHaveURL(/#\/runs/)
  const start = page.getByRole('button', { name: 'Start run', exact: true })
  await expect(start).toBeEnabled()
  const createPromise = page.waitForResponse((response) => response.url().endsWith('/api/runs') && response.request().method() === 'POST')
  await start.click()
  const created = await createPromise
  expect(created.request().postDataJSON().dataset_id).toBe(uploaded.dataset.id)
  const run = await created.json()
  await expect(page.getByRole('region', { name: 'Approval required' })).toBeVisible({ timeout: 45_000 })
  await expect(page.locator('.runreport--full')).toContainText('maintenance-intake.csv')
  await expect(page.locator('.runreport--full')).toContainText('963')
  const detail = await (await page.request.get(`/api/runs/${run.id}`)).json()
  expect(detail.report.published_path).toBeNull()
  expect(detail.tasks.filter((task: { state: string }) => task.state === 'failed')).toHaveLength(0)
  await page.goto(`/#/dashboard/${run.id}/overview`)
  await expect(page.locator('main')).toContainText('maintenance_cost')
  await expect(page.locator('main')).toContainText('963')
  // Reading contrast must hold throughout the applied entrance motion, not
  // only after its final frame. Reduced motion may correctly remove it entirely.
  const opacities = await page.locator('.exec-hero, .exec-featured .exec-kpi').evaluateAll((elements) =>
    elements.flatMap((element) => element.getAnimations().flatMap((animation) =>
      animation.effect instanceof KeyframeEffect
        ? animation.effect.getKeyframes().flatMap((frame) => frame.opacity === undefined ? [] : [Number(frame.opacity)])
        : [])))
  expect(opacities.every((opacity) => opacity === 1), 'Executive text remains opaque in every entrance frame').toBe(true)
  const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(audit.violations).toEqual([])
})

test('Arabic JSON upload keeps its schema and language through the real agent pipeline', async ({ page }) => {
  test.setTimeout(75_000)
  await skipOnboarding(page)
  await page.addInitScript(() => localStorage.setItem('aos-locale', 'ar'))
  await page.goto('/#/runs?source=upload')
  const uploadPromise = page.waitForResponse((response) => response.url().includes('/api/datasets?') && response.request().method() === 'POST')
  await page.locator('#run-file').setInputFiles({
    name: 'regional-intake.json', mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify([{ region: 'East', revenue: 241 }, { region: 'West', revenue: 352 }, { region: 'East', revenue: 467 }])),
  })
  const uploaded = await (await uploadPromise).json()
  const createPromise = page.waitForResponse((response) => response.url().endsWith('/api/runs') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'بدء التحليل', exact: true }).click()
  const created = await createPromise
  expect(created.request().postDataJSON().language).toBe('ar')
  expect(created.request().postDataJSON().dataset_id).toBe(uploaded.dataset.id)
  const run = await created.json()
  await expect(page.locator('.runreport--full')).toContainText('regional-intake.json', { timeout: 45_000 })
  await expect(page.locator('.runreport--full')).toContainText('1060')
  await expect(page.getByRole('region', { name: 'موافقة مطلوبة', exact: true })).toBeVisible()
  const detail = await (await page.request.get(`/api/runs/${run.id}`)).json()
  expect(detail.report_language).toBe('ar')
  expect(detail.state).toBe('awaiting_approval')
  expect(detail.report.published_path).toBeNull()
  const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(audit.violations).toEqual([])
})
