import { expect, test } from '@playwright/test'
import { jarvisMessages } from '../src/i18n/jarvis'
import { layoutMessages } from '../src/i18n/layout'

// The same page designs itself differently for different records (ADR
// 2026-11-03-generative-layout, slice 4): contracts lead to obligations and
// due dates, budgets to spend against budget. Synthetic files only.
const contracts = ['Contract_ID,Vendor,Status,Value_AED,Due_Date',
  ...Array.from({ length: 30 }, (_, i) => [`CT-${String(i + 1).padStart(2, '0')}`,
    ['Vendor A', 'Vendor B', 'Vendor C', 'Vendor D'][i % 4], ['Open', 'Overdue', 'Closed'][i % 3],
    1000 * (i + 1) + (i % 3 === 1 ? 20000 : 0), `2027-0${1 + (i % 6)}-15`].join(','))].join('\n')
const budget = ['Category,Month,Budget,Actual',
  ...Array.from({ length: 36 }, (_, i) => [['Energy', 'Staff', 'Parts', 'IT'][i % 4],
    `2026-${String(1 + (i % 9)).padStart(2, '0')}-01`, 500 + i, 480 + 3 * i].join(','))].join('\n')

const KINDS = [
  // total: the summed measure and its hand-checked total for the first group.
  { name: 'contracts', csv: contracts, first: 'Overdue', column: 'Status', absent: 'distribution', measure: 'Value_AED', total: /355,?000|٣٥٥٬?٠٠٠/ },
  { name: 'budget', csv: budget, first: 'IT', column: 'Category', absent: 'gap-predictive-risk', measure: 'Actual', total: /4,?833|٤٬?٨٣٣/ },
] as const

for (const kind of KINDS) for (const locale of ['en', 'ar'] as const) test(`${kind.name} records design their own page (${locale})`, async ({ page }, info) => {
  test.setTimeout(120_000)
  const l = layoutMessages[locale]
  await page.addInitScript((language) => {
    localStorage.setItem('aos-onboarded', '1'); localStorage.setItem('aos-locale', language); localStorage.setItem('aos-theme', 'light')
  }, locale)
  const upload = await page.request.post(`/api/datasets?name=SYNTHETIC_${kind.name}_${locale}.csv`, { data: kind.csv, headers: { 'content-type': 'text/csv' } })
  expect(upload.ok(), await upload.text()).toBeTruthy()
  let run = await (await page.request.post('/api/runs', { data: { goal: `Synthetic ${kind.name} review`, dataset_id: (await upload.json()).dataset.id } })).json()
  for (let i = 0; i < 40 && ['queued', 'running'].includes(run.state); i++) run = await (await page.request.post(`/api/runs/${run.id}/advance`)).json()
  expect(run.state).toBe('awaiting_approval')

  const layout = await (await page.request.post(`/api/runs/${run.id}/layout`, { data: { objective: '', use_model: false } })).json()
  const ids = layout.plan.sections.map((s: { id: string }) => s.id)
  expect(layout.domain.name).toBe(kind.name === 'budget' ? 'costs' : 'contracts')
  expect(ids[0]).toBe('brief')
  expect(ids).not.toContain(kind.absent)

  await page.goto(`/#/dashboard/${run.id}/designed`)
  await expect(page.getByText(l.decide, { exact: true })).toBeVisible({ timeout: 20_000 })
  const cards = page.locator('.layout__priorities button')
  await expect(cards).toHaveCount(3)
  await expect(cards.first()).toContainText(kind.first)
  await page.screenshot({ path: info.outputPath(`1-${kind.name}-${locale}.png`), fullPage: true })

  await cards.first().click()
  await expect(page).toHaveURL(new RegExp(`f\\.${kind.column}=${kind.first}`))
  const focus = page.getByRole('region', { name: l.selected.replace('{name}', kind.first) })
  await expect(focus.locator('table tbody tr').first()).toContainText(kind.first)
  await expect(cards).toHaveCount(3)
  await page.screenshot({ path: info.outputPath(`2-${kind.name}-focus-${locale}.png`), fullPage: true })

  // Jarvis sums this kind's own measure for the selection, calculated, not guessed.
  const question = l.askTotal.replace('{column}', kind.measure)
  await focus.getByRole('button', { name: question }).click()
  const assistant = page.locator('.dash-jarvis__assistant')
  await expect(assistant.getByRole('textbox')).toHaveValue(question, { timeout: 20_000 })
  await assistant.getByRole('button', { name: jarvisMessages[locale].ask, exact: true }).click()
  await expect(assistant.locator('.jarvis__evidence, .jarvis__measures').first()).toContainText(kind.total, { timeout: 20_000 })
  await page.screenshot({ path: info.outputPath(`3-${kind.name}-jarvis-${locale}.png`), fullPage: true })
})
