import { expect, test } from '@playwright/test'
import { jarvisMessages } from '../src/i18n/jarvis'
import { layoutMessages } from '../src/i18n/layout'
import { en as enMain } from '../src/i18n/en'
import { ar as arMain } from '../src/i18n/ar'

// One complete path on synthetic data (ADR 2026-11-03-generative-layout):
// upload → analysis → generated page → pick a priority → its drivers and
// records → a scoped question to Jarvis → calculated evidence → decide.
// The page is designed by the rule planner here: no model is configured.
const classes = ['Pumps', 'Doors', 'Signals', 'Track']
const rows = Array.from({ length: 24 }, (_, i) => {
  const cls = classes[i % 4]
  return [`SYN-${String(i + 1).padStart(2, '0')}`, `${cls.slice(0, 1)}-${(i % 3) + 1}`, cls, `2026-0${1 + (i % 6)}`,
    100 + (i % 4 === 0 ? 300 : 40) + i, 90 + (i % 5), 100, i % 4 === 0 ? 18 + (i % 3) : 4 + (i % 2), i % 4 === 0 ? 2 : i % 2].join(',')
})
const CSV = ['Record_ID,Asset_ID,Asset_Class,Period,Maintenance_Cost_USD,Operating_Hours,Planned_Operating_Hours,Downtime_Hours,Failure_Count', ...rows].join('\n')

for (const locale of ['en', 'ar'] as const) test(`upload to an evidence-backed decision through the generated page (${locale})`, async ({ page }, info) => {
  test.setTimeout(120_000)
  const l = layoutMessages[locale], j = jarvisMessages[locale]
  await page.addInitScript((language) => {
    localStorage.setItem('aos-onboarded', '1'); localStorage.setItem('aos-locale', language); localStorage.setItem('aos-theme', 'light')
  }, locale)
  const upload = await page.request.post(`/api/datasets?name=SYNTHETIC_fleet_${locale}.csv`, { data: CSV, headers: { 'content-type': 'text/csv' } })
  expect(upload.ok(), await upload.text()).toBeTruthy()
  let run = await (await page.request.post('/api/runs', { data: { goal: 'Synthetic fleet review', dataset_id: (await upload.json()).dataset.id } })).json()
  for (let i = 0; i < 40 && ['queued', 'running'].includes(run.state); i++) run = await (await page.request.post(`/api/runs/${run.id}/advance`)).json()
  expect(run.state).toBe('awaiting_approval')

  await page.goto(`/#/dashboard/${run.id}/designed`)
  await expect(page.getByText(l.happening, { exact: true })).toBeVisible({ timeout: 20_000 })
  await expect(page.getByText(l.decide, { exact: true })).toBeVisible()
  const cards = page.locator('.layout__priorities button')
  await expect(cards).toHaveCount(3)
  await expect(cards.first()).toContainText('Pumps')                  // the class with most downtime, computed
  await page.screenshot({ path: info.outputPath(`1-generated-${locale}.png`), fullPage: true })

  await cards.first().click()
  await expect(page).toHaveURL(/f\.Asset_Class=Pumps/)
  const focus = page.getByRole('region', { name: l.selected.replace('{name}', 'Pumps') })
  await expect(focus).toContainText(l.drivers)
  await expect(focus).toContainText('Asset_ID')                       // a record number is never a driver
  await expect(cards).toHaveCount(3)                                   // the other choices stay visible
  await expect(cards.first()).toHaveAttribute('aria-pressed', 'true')
  await expect(focus.locator('table tbody tr').first()).toContainText('Pumps')
  await page.screenshot({ path: info.outputPath(`2-focus-${locale}.png`), fullPage: true })

  await focus.getByRole('button', { name: l.askCost }).click()
  const assistant = page.locator('.dash-jarvis__assistant')
  await expect(assistant.getByRole('textbox')).toHaveValue(l.askCost, { timeout: 20_000 })
  await assistant.getByRole('button', { name: j.ask, exact: true }).click()
  // Pumps only: 6 records, cost 400+i for i = 0, 4, 8, 12, 16, 20 → 2,460.
  await expect(assistant.locator('.jarvis__evidence, .jarvis__measures').first()).toContainText(/2,?460|٢٬?٤٦٠/, { timeout: 20_000 })
  await page.screenshot({ path: info.outputPath(`3-jarvis-${locale}.png`), fullPage: true })

  await page.getByRole('button', { name: l.evidence }).click()
  await expect(page.locator('.layout__evidence li').first()).toBeVisible()
  await page.getByRole('button', { name: l.review }).click()
  await expect(page).toHaveURL(new RegExp(`#/runs/${run.id}`))
  await expect(page.getByRole('region', { name: (locale === 'ar' ? arMain : enMain)['runs.approval'] })).toBeVisible({ timeout: 20_000 })
})
