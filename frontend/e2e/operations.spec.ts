import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { skipOnboarding } from './helpers'
import { messages } from '../src/features/operations/messages'
import { validationMessages } from '../src/features/operations/validationMessages'
import { performanceMessages } from '../src/shared/components/performanceMessages'

test.use({ serviceWorkers: 'block', contextOptions: { reducedMotion: 'reduce' } })

for (const language of ['en', 'ar'] as const) {
  test(`${language}: asset evidence becomes explicitly authorized work and a recorded outcome`, async ({ page }, info) => {
    test.setTimeout(90_000)
    const t = messages[language]
    await skipOnboarding(page)
    await page.addInitScript((locale) => localStorage.setItem('aos-locale', locale), language)
    // Fictional evidence is processed by the actual pipeline; no external model or CMMS.
    const uploaded = await page.request.post('/api/datasets', { params: { name: `operations-${language}-${info.project.name}.csv` }, headers: { 'Content-Type': 'text/csv' }, data: 'Asset_ID,cost\nP-10,10\nP-10,14\nP-20,7\n' })
    await expect(uploaded).toBeOK()
    const dataset = (await uploaded.json()).dataset
    const created = await page.request.post('/api/runs', { data: { goal: 'Review fictional pump cost evidence', dataset_id: dataset.id, profile: 'default', language } })
    await expect(created).toBeOK()
    let run = await created.json()
    for (let step = 0; step < 80 && ['queued', 'running'].includes(run.state); step++) {
      const advanced = await page.request.post(`/api/runs/${run.id}/advance`)
      await expect(advanced).toBeOK()
      run = await advanced.json()
    }
    expect(run.state).toBe('awaiting_approval')
    await page.goto('/#/operations')
    await expect(page.getByRole('heading', { name: t.title, exact: true })).toBeVisible()
    const setup = page.locator('.operations__setup')
    if (!await setup.getAttribute('open')) {
      // An empty attribute means open; null means closed.
      if (await setup.getAttribute('open') === null) await setup.locator('summary').click()
    }
    await page.getByLabel(t.organizationName, { exact: true }).fill(`Fictional ${language} ${info.project.name} ${Date.now()}`)
    const organizationResponse = page.waitForResponse((response) => response.url().includes('/api/operations/organizations?') && response.request().method() === 'POST')
    await page.getByRole('button', { name: t.createOrganization, exact: true }).click()
    const organization = await (await organizationResponse).json()
    const summary = page.getByRole('group', { name: t.summaryTitle })
    await expect(summary.locator('[data-performance="unassessed"]')).toHaveCount(3)
    await expect(summary.locator('.performance-value__status')).toHaveText(Array(3).fill(performanceMessages[language]['performance.unassessed']))
    await expect(page.getByRole('complementary', { name: performanceMessages[language]['performance.legend'] })).toBeVisible()
    await page.screenshot({ path: info.outputPath(`performance-status-operations-${language}.png`), fullPage: true })
    await page.getByRole('button', { name: t.registry, exact: true }).click()
    await page.getByLabel(t.siteName, { exact: true }).fill('Fictional station')
    await page.getByLabel(t.siteCode, { exact: true }).fill('FS')
    await page.getByRole('button', { name: t.addSite, exact: true }).click()
    await expect(page.getByLabel(t.site, { exact: true })).toBeEnabled()
    await page.getByLabel(t.site, { exact: true }).selectOption({ label: 'Fictional station' })
    await page.getByLabel(t.assetName, { exact: true }).fill('Fictional cooling pump')
    await page.getByLabel(t.assetId, { exact: true }).fill('P-10')
    await page.getByLabel(t.sourceSystem, { exact: true }).fill('Fictional CMMS')
    await page.getByRole('button', { name: t.addAsset, exact: true }).click()
    await expect(page.getByRole('region', { name: t.registry, exact: true }).locator('.operations__assets')).toContainText('Fictional cooling pump')
    await page.getByRole('button', { name: t.orders, exact: true }).click()
    await page.locator('.operations__draft > summary').click()
    await page.getByLabel(t.asset, { exact: true }).selectOption({ label: 'Fictional cooling pump · P-10' })
    await page.getByLabel(t.titleField, { exact: true }).fill('Inspect pump bearing')
    await page.getByLabel(t.rationale, { exact: true }).fill('Review fictional evidence before inspection')
    await page.getByLabel(t.run, { exact: true }).fill(run.id)
    await page.getByLabel(t.assignee, { exact: true }).selectOption({ index: 1 })
    await page.getByLabel(t.due, { exact: true }).fill('2026-12-01')
    await page.getByRole('button', { name: t.createDraft, exact: true }).click()
    const detail = page.getByRole('region', { name: t.details, exact: true })
    await expect(detail).toBeVisible()
    await detail.getByRole('button', { name: t.authorize, exact: true }).click()
    await expect(page.getByRole('dialog')).toContainText(t.authorizationHelp)
    const before = await (await page.request.get(`/api/operations/organizations/${organization.id}/overview`)).json()
    expect(before.work_orders[0].status).toBe('draft')
    await page.getByRole('dialog').getByRole('button', { name: t.authorize, exact: true }).click()
    await detail.getByRole('button', { name: t.start, exact: true }).click()
    await page.getByLabel(t.outcome, { exact: true }).fill('Wear observed')
    await page.getByLabel(t.notes, { exact: true }).fill('Fictional inspection and replacement recorded')
    await page.getByLabel(t.labor, { exact: true }).fill('2')
    await page.getByRole('button', { name: t.complete, exact: true }).click()
    await expect(detail).toContainText('Wear observed')
    await expect(detail.getByRole('button', { name: t.complete, exact: true })).toHaveCount(0)
    const after = await (await page.request.get(`/api/operations/organizations/${organization.id}/overview`)).json()
    expect(after.work_orders[0]).toMatchObject({ status: 'completed', version: 4, completion: { outcome: 'Wear observed', labor_hours: 2 } })
    expect(after.work_orders[0].audit).toHaveLength(4)
    // Maintenance authorization never publishes the source analytics report.
    expect((await (await page.request.get(`/api/runs/${run.id}`)).json()).state).toBe('awaiting_approval')
    // Prospective validation starts empty; this test records a future window,
    // never a fabricated outcome merely to produce an accuracy percentage.
    const v = validationMessages[language]
    await page.getByRole('button', { name: t.validation, exact: true }).click()
    const validation = page.getByRole('region', { name: v.title, exact: true })
    await expect(validation).toContainText(v.empty)
    await validation.locator('summary').filter({ hasText: v.create }).click()
    await validation.getByLabel(v.name, { exact: true }).fill('Fictional prospective pump pilot')
    await validation.getByLabel(v.model, { exact: true }).fill('fixture-model-v1')
    await validation.getByLabel(v.baseline, { exact: true }).fill('fixture-baseline-v1')
    await validation.getByLabel(v.trained, { exact: true }).fill('2026-01-01T00:00')
    await validation.getByLabel(v.horizon, { exact: true }).fill('24')
    await validation.getByLabel(v.threshold, { exact: true }).fill('0.7')
    await validation.getByLabel(v.failure, { exact: true }).fill('Recorded bearing failure requiring repair')
    await validation.getByLabel(v.cohort, { exact: true }).fill('Registered fictional pumps only')
    await validation.getByRole('button', { name: v.create, exact: true }).click()
    await expect(validation.getByRole('heading', { name: v.metrics, exact: true })).toBeVisible()
    await validation.locator('summary').filter({ hasText: v.prediction }).click()
    await validation.getByLabel(v.asset, { exact: true }).selectOption({ label: 'Fictional cooling pump' })
    await validation.getByLabel(v.probability, { exact: true }).fill('0.8')
    await validation.getByLabel(v.baselineProbability, { exact: true }).fill('0.3')
    const predictionResponse = page.waitForResponse((response) => response.url().includes('/predictions?') && response.request().method() === 'POST')
    await validation.getByRole('button', { name: v.prediction, exact: true }).click()
    const trial = await (await predictionResponse).json()
    expect(trial.metrics).toMatchObject({ registered: 1, evaluated: 0, pending: 1, brier_score: null })
    expect(trial.predictions[0].outcome).toBeNull()
    await expect(validation.getByText(v.unmeasured, { exact: false }).first()).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', language === 'ar' ? 'rtl' : 'ltr')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    expect(audit.violations).toEqual([])
  })
}
