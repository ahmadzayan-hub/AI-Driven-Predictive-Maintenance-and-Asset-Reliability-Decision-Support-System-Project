import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { APIRequestContext, Download, Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import type { RunDetail, RunExecutive, TableFilter } from '../src/shared/types'
import { skipOnboarding } from './helpers'

// Fictional records only. The default profile deliberately has no modelling
// stages: an executive brief must disclose that absence rather than score it.
// Both configured projects run these cases: desktop and a 375 px phone.
const CSV = [
  'month,Site,Record_ID,Work_Order_Type,Downtime_Hours,Operating_Hours,Planned_Operating_Hours,Preventive_WO_Count,Corrective_WO_Count,Completed_WO_Count,First_Time_Fix_Count,Repeat_Repair_Count,Overdue_WO_Count,Maintenance_Cost_USD,Production_Loss_USD',
  '2026-02,North,MIYAAR-FICTIONAL-A,Corrective,4,80,100,0,10,10,8,2,1,100,400',
  '2026-03,North,MIYAAR-FICTIONAL-B,Corrective,10,95,100,0,30,30,15,15,2,300,1000',
  '2026-03,North,MIYAAR-FICTIONAL-C,Preventive,6,90,100,5,0,5,0,0,0,200,600',
  '2026-03,South,MIYAAR-FICTIONAL-D,Corrective,20,60,100,0,20,20,10,10,3,900,2000',
].join('\n') + '\n'
const NORTH: TableFilter[] = [{ column: 'Site', op: 'in', values: ['North'] }]

test.use({ serviceWorkers: 'block', contextOptions: { reducedMotion: 'reduce' } })

async function maintenanceRun(request: APIRequestContext, language: 'en' | 'ar' = 'en') {
  const created = await request.post('/api/runs', {
    data: {
      goal: 'Review fictional maintenance evidence', dataset_text: CSV,
      dataset_name: 'executive-fictional.csv', profile: 'default', language, breakdown: 'Site',
    },
  })
  await expect(created).toBeOK()
  let run = await created.json() as RunDetail
  for (let step = 0; step < 80 && ['queued', 'running'].includes(run.state); step += 1) {
    const advanced = await request.post(`/api/runs/${run.id}/advance`)
    await expect(advanced).toBeOK()
    run = await advanced.json() as RunDetail
  }
  expect(run.state).toBe('awaiting_approval')
  expect(run.tasks.filter((task) => task.state === 'failed')).toEqual([])
  expect(run.report?.published_path).toBeNull()
  return run
}

async function executive(request: APIRequestContext, runId: string, filters: TableFilter[], language = 'en') {
  const response = await request.get(`/api/runs/${runId}/executive`, {
    params: { language, filters: JSON.stringify(filters) },
  })
  await expect(response).toBeOK()
  return await response.json() as RunExecutive
}

async function openOverview(page: Page, runId: string, query = '', language: 'en' | 'ar' = 'en') {
  await page.goto(`/#/dashboard/${runId}/overview${query ? `?${query}` : ''}`)
  await page.locator('.viewload').waitFor({ state: 'detached' })
  await expect(page.getByRole('heading', {
    name: language === 'ar' ? 'النظرة التنفيذية' : 'Executive overview', exact: true,
  })).toBeVisible()
}

async function chooseNorth(page: Page) {
  const filter = page.locator('details.dash-filter').filter({
    has: page.locator('summary').filter({ hasText: /^Site:/ }),
  })
  await filter.locator('summary').click()
  await filter.getByRole('checkbox', { name: 'North', exact: true }).check()
  await filter.locator('summary').click()
  await expect(page.locator('.exec-scope strong')).toHaveText('3')
}

async function readBrief(download: Download) {
  const path = await download.path()
  expect(path, 'the evidence brief should be a real downloaded JSON file').not.toBeNull()
  return JSON.parse(await readFile(path!, 'utf8')) as RunExecutive
}

async function expectAccessible(page: Page, context: string) {
  await page.evaluate(() => document.fonts.ready)
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(result.violations, `${context}: ${result.violations.map((v) => `${v.id} (${v.nodes.length})`).join(', ')}`).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth),
    `${context} must fit the viewport, including an open evidence table`).toBeLessThanOrEqual(0)
}

test('filtered executive measures, evidence and downloaded brief share the exact scope', async ({ page }) => {
  test.setTimeout(75_000)
  await skipOnboarding(page)
  const run = await maintenanceRun(page.request)
  await openOverview(page, run.id)
  await expectScope(page, 4, 4)
  await chooseNorth(page)
  await expect(page.locator('.dash-coverage')).toHaveText('Showing 3 of 4 records.')
  await expectScope(page, 3, 4)

  const expected = await executive(page.request, run.id, NORTH)
  expect(expected.scope).toEqual({ records: 3, total_records: 4, filters: NORTH })
  // These constants come from the fixture, independently of the endpoint:
  // (8 + 15) / (10 + 30), excluding the preventive record, not a mean of rates.
  expect(expected.kpis.measures.find((m) => m.key === 'first_time_fix')).toMatchObject({
    value: 57.5, numerator: 23, denominator: 40, records: 2,
    records_excluded: 1, records_unmeasured: 0, undefined_reason: null,
  })
  expect(expected.kpis.measures.find((m) => m.key === 'availability')).toMatchObject({
    numerator: 265, denominator: 300, records: 3,
  })
  expect(expected.kpis.measures.find((m) => m.key === 'downtime_per_record')).toMatchObject({
    numerator: 20, denominator: 3, records: 3,
  })
  const fix = page.locator('[data-source="kpi.first_time_fix"]')
  await expect(fix.locator('.exec-kpi-value')).toHaveText('57.5 %')
  await expect(fix.getByText('2 measured records', { exact: true })).toBeVisible()
  await fix.locator('summary').click()
  await expect(fix.locator('dd').first()).toContainText('23 / 40')
  await expect(fix).toContainText('1 records outside this measure’s population')

  const priority = page.locator('.exec-priorities > li').filter({
    has: page.getByRole('heading', { name: 'Review overdue work', exact: true }),
  })
  await priority.getByRole('button', { name: 'View evidence (1)', exact: true }).click()
  const evidence = page.getByRole('region', { name: 'Evidence register', exact: true })
  const selected = evidence.getByRole('row', { name: /executive\.kpi\.overdue_share/ })
  await expect(selected).toBeFocused()
  await expect(selected).toHaveAttribute('data-selected', 'true')
  await expect(selected).toContainText('6.67')

  const models = page.getByRole('region', { name: 'Model quality', exact: true })
  await expect(models).toContainText('No evaluated models in this analysis. A performance score is not available.')
  await expect(models.getByRole('table')).toHaveCount(0)
  expect(expected.models).toEqual([])
  await page.getByRole('button', { name: 'Prepare executive brief', exact: true }).click()
  const prepared = page.getByRole('region', { name: 'Brief prepared for the current scope', exact: true })
  await expect(prepared).toContainText(expected.headline)
  for (const question of expected.questions) await expect(prepared).toContainText(question.text)
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    prepared.getByRole('button', { name: 'Download evidence brief (JSON)', exact: true }).click(),
  ])
  expect(download.suggestedFilename()).toBe(`miyaar-executive-${run.id}-en.json`)
  const exported = await readBrief(download)
  expect(exported).toEqual(expected)
  expect(JSON.stringify(exported)).not.toContain('MIYAAR-FICTIONAL-')
  await expectAccessible(page, 'English executive brief and selected evidence')

  // Preparing and exporting a brief cannot satisfy the publication approval.
  const after = await (await page.request.get(`/api/runs/${run.id}`)).json() as RunDetail
  expect(after.state).toBe('awaiting_approval')
  expect(after.approvals).toEqual(run.approvals)
  expect(after.report?.published_path).toBeNull()

  // A prepared snapshot must disappear when the reader changes its scope.
  await page.getByLabel('From', { exact: true }).selectOption('2026-03')
  await expect(page.locator('.exec-scope strong')).toHaveText('2')
  await expect(prepared).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Prepare executive brief', exact: true })).toBeVisible()
  await expect(fix.locator('.exec-kpi-value')).toHaveText('50 %')
})

test('an executive priority preserves the period filter when drilling into records and reloading', async ({ page }) => {
  test.setTimeout(75_000)
  await skipOnboarding(page)
  const run = await maintenanceRun(page.request)
  await openOverview(page, run.id)
  await page.getByLabel('From', { exact: true }).selectOption('2026-03')
  await expect(page.locator('.dash-coverage')).toHaveText('Showing 3 of 4 records.')
  await expectScope(page, 3, 4)
  const priority = page.locator('.exec-priorities > li').filter({
    has: page.getByRole('heading', { name: 'Review the largest observed downtime group', exact: true }),
  })
  await expect(priority).toContainText('Site: South')
  await priority.getByRole('button', { name: 'Inspect this group', exact: true }).click()
  const pages = page.getByRole('navigation', { name: 'Dashboard pages', exact: true })
  await expect(pages.getByRole('link', { name: 'Records', exact: true })).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('.dash-coverage')).toHaveText('Showing 1 of 4 records.')
  const query = new URLSearchParams(new URL(page.url()).hash.split('?')[1])
  expect(query.get('from')).toBe('2026-03')
  expect(query.getAll('f.Site')).toEqual(['South'])
  const records = page.getByRole('region', { name: 'Records', exact: true })
  await expect(records.getByRole('row')).toHaveCount(2)
  await expect(records).toContainText('MIYAAR-FICTIONAL-D')
  await expect(records).not.toContainText('MIYAAR-FICTIONAL-B')
  await expect(records).not.toContainText('MIYAAR-FICTIONAL-C')

  const address = page.url()
  await page.reload()
  await page.locator('.viewload').waitFor({ state: 'detached' })
  await expect(page).toHaveURL(address)
  await expect(page.locator('.dash-coverage')).toHaveText('Showing 1 of 4 records.')
  await expect(records).toContainText('MIYAAR-FICTIONAL-D')
  await pages.getByRole('link', { name: 'Overview', exact: true }).click()
  await expectScope(page, 1, 4)
  const filters: TableFilter[] = [
    { column: 'Site', op: 'in', values: ['South'] }, { column: 'month', op: 'gte', value: '2026-03' },
  ]
  const expected = await executive(page.request, run.id, filters)
  expect(expected.scope).toEqual({ records: 1, total_records: 4, filters })
  expect(expected.kpis.measures.find((m) => m.key === 'downtime_per_record')).toMatchObject({
    value: 20, numerator: 20, denominator: 1, records: 1,
  })
  await expect(page.locator('[data-source="kpi.downtime_per_record"] .exec-kpi-value')).toHaveText('20 h')
  await expect(page.getByLabel('From', { exact: true })).toHaveValue('2026-03')
})

test('Arabic RTL executive evidence and its JSON brief work in light and dark themes', async ({ page }) => {
  test.setTimeout(90_000)
  await skipOnboarding(page)
  await page.addInitScript(() => {
    localStorage.setItem('aos-locale', 'ar')
    if (!localStorage.getItem('aos-theme')) localStorage.setItem('aos-theme', 'light')
  })
  const run = await maintenanceRun(page.request, 'ar')
  await openOverview(page, run.id, '', 'ar')
  await chooseNorth(page)
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar')
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await expect(page.locator('.exec-overview')).toHaveAttribute('dir', 'rtl')
  await expect(page.getByRole('heading', { name: 'وكيل معيار التنفيذي', exact: true })).toBeVisible()
  await expectScope(page, 3, 4, 'ar')
  const fix = page.locator('[data-source="kpi.first_time_fix"]')
  await expect(fix.getByRole('heading', { name: 'معدل الإصلاح من المرة الأولى' })).toBeVisible()
  await expect(fix.locator('.exec-kpi-value')).toHaveText('57.5 %')
  await fix.locator('summary').click()
  await expect(fix.locator('dd').first()).toContainText('23 / 40')
  const priority = page.locator('.exec-priorities > li').filter({
    has: page.getByRole('heading', { name: 'مراجعة الأعمال المتأخرة', exact: true }),
  })
  await priority.getByRole('button', { name: 'عرض الأدلة (1)', exact: true }).click()
  const evidence = page.getByRole('region', { name: 'سجل الأدلة', exact: true })
  await expect(evidence.getByRole('row', { name: /executive\.kpi\.overdue_share/ })).toBeFocused()
  await expectAccessible(page, 'Arabic light executive overview with evidence open')

  // Use the actual Preferences control, also available on phone widths.
  const address = page.url()
  await page.goto('/#/preferences')
  await page.getByRole('button', { name: 'داكن', exact: true }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.goto(address)
  await expect(page.getByRole('heading', { name: 'النظرة التنفيذية', exact: true })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('.exec-scope strong')).toHaveText('3')
  await page.getByRole('button', { name: 'إعداد الموجز التنفيذي', exact: true }).click()
  const prepared = page.getByRole('region', { name: 'أُعدّ الموجز للنطاق الحالي', exact: true })
  const expected = await executive(page.request, run.id, NORTH, 'ar')
  await expect(prepared).toContainText(expected.headline)
  await expect(page.getByRole('region', { name: 'جودة النماذج', exact: true }))
    .toContainText('لا توجد نماذج مقيّمة في هذا التحليل. لا تتوفر درجة أداء.')
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    prepared.getByRole('button', { name: 'تنزيل الموجز وأدلته (JSON)', exact: true }).click(),
  ])
  expect(download.suggestedFilename()).toBe(`miyaar-executive-${run.id}-ar.json`)
  expect(await readBrief(download)).toEqual(expected)
  await expectAccessible(page, 'Arabic dark executive brief')
})

// The compact scope presents the selected count and total in separate elements.
// Assert both rather than relying on whitespace between adjacent DOM nodes.
async function expectScope(page: Page, records: number, total: number, language: 'en' | 'ar' = 'en') {
  const scope = page.locator('.exec-scope')
  await expect(scope.locator('strong')).toHaveText(String(records))
  await expect(scope.getByText(language === 'ar'
    ? `من أصل ${total} سجلًا منظَّفًا` : `of ${total} cleaned records`, { exact: true })).toBeVisible()
}
