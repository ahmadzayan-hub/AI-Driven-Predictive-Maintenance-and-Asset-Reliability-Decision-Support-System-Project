import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { APIRequestContext, Download, Locator, Page } from '@playwright/test'
import { execFile } from 'node:child_process'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import type { RunDetail, RunExecutive, TableFilter } from '../src/shared/types'
import { skipOnboarding, openFilters } from './helpers'
import { storeMaintenanceDataset } from './maintenance-dataset'

// Fictional records only. The default profile deliberately has no modelling
// stages: an executive brief must disclose that absence rather than score it.
// Both projects run these cases; KPI review captures also exercise a 320 px phone.
const CSV = [
  'month,Site,Record_ID,Work_Order_Type,Downtime_Hours,Operating_Hours,Planned_Operating_Hours,Preventive_WO_Count,Corrective_WO_Count,Completed_WO_Count,First_Time_Fix_Count,Repeat_Repair_Count,Overdue_WO_Count,Maintenance_Cost_USD,Production_Loss_USD',
  '2026-02,North,MIYAAR-FICTIONAL-A,Corrective,4,80,100,0,10,10,8,2,1,100,400',
  '2026-03,North,MIYAAR-FICTIONAL-B,Corrective,10,95,100,0,30,30,15,15,2,300,1000',
  '2026-03,North,MIYAAR-FICTIONAL-C,Preventive,6,90,100,5,0,5,0,0,0,200,600',
  '2026-03,South,MIYAAR-FICTIONAL-D,Corrective,20,60,100,0,20,20,10,10,3,900,2000',
].join('\n') + '\n'
const FIVE_SITE_CSV = CSV + [
  '2026-03,East processing and reliability campus,MIYAAR-FICTIONAL-E,Corrective,4,80,100,0,10,10,8,2,1,1200,100000',
  '2026-03,West,MIYAAR-FICTIONAL-F,Corrective,5,85,100,0,10,10,8,2,1,1500,100000',
  '2026-03,Central,MIYAAR-FICTIONAL-G,Corrective,6,90,100,0,10,10,8,2,1,2000,100000',
].join('\n') + '\n'
const NORTH: TableFilter[] = [{ column: 'Site', op: 'in', values: ['North'] }]

test.use({ serviceWorkers: 'block', contextOptions: { reducedMotion: 'reduce' } })

async function maintenanceRun(request: APIRequestContext, language: 'en' | 'ar' = 'en', csv = CSV, name = 'executive-fictional.csv', currency?: string) {
  const datasetId = await storeMaintenanceDataset(request, csv, name, language, true, currency)
  const created = await request.post('/api/runs', {
    data: {
      goal: 'Review fictional maintenance evidence', dataset_id: datasetId,
      profile: 'default', language,
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
  await expect(page.locator('.viewload')).toHaveCount(0)
  await expect(page.getByRole('heading', {
    name: language === 'ar' ? 'النظرة التنفيذية' : 'Executive overview', exact: true,
  })).toBeVisible()
}

test('the opening shows governed KPIs and a real comparison before the detailed register', async ({ page }, testInfo) => {
  await skipOnboarding(page)
  await page.setViewportSize(testInfo.project.name === 'mobile'
    ? { width: 320, height: 812 } : { width: 1280, height: 720 })
  const run = await maintenanceRun(page.request, 'en', FIVE_SITE_CSV, 'executive-five-sites-long-currency-fixture.csv', 'USD')
  await openOverview(page, run.id)
  const snapshot = await executive(page.request, run.id, [])
  const featured = page.locator('.exec-featured .exec-kpi')
  await expect(featured).toHaveCount(Math.min(4, snapshot.kpis.measures.length))
  for (const card of await featured.all()) {
    const source = await card.getAttribute('data-source')
    expect(snapshot.kpis.measures.some((measure) => source === `kpi.${measure.key}`)).toBe(true)
    const duration = await card.evaluate((element) => getComputedStyle(element).animationDuration)
    expect(parseFloat(duration)).toBeLessThanOrEqual(0.00001)
  }
  const chart = page.locator('.dash-overview-charts').getByRole('img').first()
  await expect(chart).toBeVisible()
  // Capture the actual opening before layout assertions, including failures.
  // This remains a synthetic test preview, never live-data acceptance evidence.
  await page.screenshot({ path: `../docs/screenshots/${testInfo.project.name}-phase1-executive-opening.png`, animations: 'disabled' })
  await expect(chart.locator('.dash-bars__row')).toHaveCount(5)
  await expect(page.locator('[data-source="kpi.loss_per_record"] .exec-kpi-n')).toHaveText('USD 43,428.57')
  const clipped = await featured.evaluateAll((cards) => cards.flatMap((card) => {
    const bounds = card.getBoundingClientRect()
    return [...card.querySelectorAll('h4, p, .performance-value__number, summary')].filter((node) => {
      if (!node.getClientRects().length) return false
      const rect = node.getBoundingClientRect()
      return rect.left < bounds.left || rect.right > bounds.right || node.scrollWidth > node.clientWidth + 1
    }).map((node) => node.textContent)
  }))
  expect(clipped, 'Complete values and units must fit their governed cards').toEqual([])
  if (testInfo.project.name === 'desktop') {
    await expect(featured.first()).toBeInViewport({ ratio: 1 })
    await expect(chart).toBeInViewport({ ratio: 1 })
  } else {
    expect(await featured.first().evaluate((element) => getComputedStyle(element.parentElement!).gridTemplateColumns.split(' ').length)).toBe(2)
    await chart.scrollIntoViewIfNeeded()
    await expect(chart).toBeInViewport({ ratio: 1 })
    // A real API-backed, long fictional group name must remain legible at 320px.
    // Keep the chart labels and exact values visible without reversing the axis.
    const longLabel = chart.locator('.dash-bars__label').filter({ hasText: 'East processing and reliability campus' })
    await expect(longLabel).toBeVisible()
    await expect(longLabel).toHaveCSS('white-space', 'normal')
    expect(await longLabel.evaluate((element) => element.scrollWidth <= element.clientWidth + 1)).toBe(true)
    const longRow = longLabel.locator('..')
    const trackWidth = await longRow.locator('.dash-bars__track').evaluate((element) => element.getBoundingClientRect().width)
    const rowWidth = await longRow.evaluate((element) => element.getBoundingClientRect().width)
    expect(trackWidth).toBeGreaterThan(rowWidth / 2)
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  await expect(page.locator('.dash-provenance > bdi')).toHaveText(snapshot.run.dataset_name)
  await expect(page.locator('.exec-meta')).toContainText('Deterministic')
})

async function chooseNorth(page: Page) {
  await openFilters(page)
  const filter = page.locator('details.dash-filter').filter({
    has: page.locator('summary').filter({ hasText: /^Site:/ }),
  })
  await filter.locator('summary').click()
  const checkbox = filter.getByRole('checkbox', { name: 'North', exact: true })
  await checkbox.click()
  // The hash is the controlled input's source of truth; wait for hashchange
  // to settle its new prop rather than requiring a synchronous check action.
  await expect(checkbox).toBeChecked()
  await expect(page).toHaveURL((url) => {
    const values = new URLSearchParams(url.hash.split('?')[1]).getAll('f.Site')
    return values.length === 1 && values[0] === 'North'
  })
  await filter.locator('summary').click()
  await expect(page.locator('.exec-scope strong')).toHaveText('3')
}

async function downloadPath(download: Download) {
  const path = await download.path()
  expect(path, 'the report should be a real downloaded file').not.toBeNull()
  return path!
}

interface DocumentContents {
  text: string
  tables: string[][][]
}

async function inspectHtml(page: Page, html: string, language: 'en' | 'ar') {
  expect(html).toMatch(/^<!doctype html>/i)
  expect(() => JSON.parse(html)).toThrow()
  const document = await page.evaluate((source) => {
    // DOMParser is inert: inspecting a downloaded report does not run its code.
    const doc = new DOMParser().parseFromString(source, 'text/html')
    const text = (node: Element) => (node.textContent ?? '').replace(/\s+/gu, ' ').trim()
    return {
      lang: doc.documentElement.lang, dir: doc.documentElement.dir,
      text: text(doc.body),
      tables: Array.from(doc.querySelectorAll('table'), (table) =>
        Array.from(table.rows, (row) => Array.from(row.cells, text))),
      executable: doc.querySelectorAll('script,iframe,object,embed,form').length,
      contentsCount: doc.querySelectorAll('nav#contents').length,
      frontmatterTargets: Array.from(doc.querySelectorAll('nav#contents a'))
        .slice(0, 3).map((link) => link.getAttribute('href')),
      destinationsValid: Array.from(doc.querySelectorAll('nav#contents a')).every((link) => {
        const href = link.getAttribute('href') ?? ''
        return /^#(?:section-\d+|list-of-(?:tables|figures))$/.test(href) && doc.querySelectorAll(href).length === 1
      }),
    }
  }, html)
  expect(document.lang).toBe(language)
  expect(document.dir).toBe(language === 'ar' ? 'rtl' : 'ltr')
  expect(document.executable).toBe(0)
  expect(document.contentsCount).toBe(1)
  expect(document.frontmatterTargets).toEqual(['#list-of-tables', '#list-of-figures', '#section-0'])
  expect(document.destinationsValid).toBe(true)
  expect(document.text).not.toContain('MIYAAR-FICTIONAL-')
  return document
}

async function inspectDocx(download: Download, language: 'en' | 'ar') {
  const path = await downloadPath(download)
  expect((await readFile(path)).subarray(0, 4).toString('hex')).toBe('504b0304')
  // Match playwright.config.ts's interpreter selection; no ZIP dependency or
  // Office installation is needed to inspect the actual downloaded package.
  const localPython = fileURLToPath(new URL(process.platform === 'win32'
    ? '../../.venv/Scripts/python.exe' : '../../.venv/bin/python', import.meta.url))
  const python = process.env.PYTHON_EXECUTABLE ?? (existsSync(localPython) ? localPython : 'python3')
  const script = [
    'import json, sys, zipfile, xml.etree.ElementTree as ET',
    'ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}',
    'def text(node): return " ".join("".join(node.itertext()).split())',
    'with zipfile.ZipFile(sys.argv[1]) as archive:',
    '    assert archive.testzip() is None',
    '    doc = ET.fromstring(archive.read("word/document.xml"))',
    '    tables = [[[text(cell) for cell in row.findall("w:tc", ns)] for row in table.findall("w:tr", ns)] for table in doc.findall(".//w:tbl", ns)]',
    '    print(json.dumps({"members": archive.namelist(), "text": text(doc), "tables": tables, "bidi": len(doc.findall(".//w:bidi", ns)), "rtl": len(doc.findall(".//w:rtl", ns)), "bidiVisual": len(doc.findall(".//w:bidiVisual", ns))}, ensure_ascii=False))',
  ].join('\n')
  const { stdout } = await promisify(execFile)(python, ['-c', script, path], {
    encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' }, maxBuffer: 1_000_000,
  })
  const document = JSON.parse(stdout) as DocumentContents & {
    members: string[]; bidi: number; rtl: number; bidiVisual: number
  }
  expect(document.members).toEqual(expect.arrayContaining(['[Content_Types].xml', '_rels/.rels', 'word/document.xml', 'word/styles.xml']))
  expect(document.members.some((name) => /vbaProject|embeddings\//i.test(name))).toBe(false)
  expect(document.text).not.toContain('MIYAAR-FICTIONAL-')
  if (language === 'ar') {
    expect(document.bidi).toBeGreaterThan(0)
    expect(document.rtl).toBeGreaterThan(0)
    expect(document.bidiVisual).toBeGreaterThan(0)
  }
  return document
}

function expectReportScope(document: DocumentContents, snapshot: RunExecutive) {
  const ar = snapshot.language === 'ar'
  const rows = document.tables.flat()
  const labels = ar ? {
    run: 'معرّف التشغيل', dataset: 'مجموعة البيانات', updated: 'آخر تحديث للقطة',
    selected: 'السجلات المحددة', total: 'إجمالي السجلات', formula: 'الصيغة',
    value: 'القيمة', scale: 'مقياس القيمة',
    numerator: 'البسط', denominator: 'المقام', population: 'مجموعة القياس',
    measured: 'السجلات المقاسة', unmeasured: 'السجلات غير المقاسة', excluded: 'السجلات المستبعدة',
  } : {
    run: 'Run ID', dataset: 'Dataset', updated: 'Snapshot updated',
    selected: 'Selected records', total: 'Total records', formula: 'Formula',
    value: 'Value', scale: 'Scale',
    numerator: 'Numerator', denominator: 'Denominator', population: 'Population',
    measured: 'Measured records', unmeasured: 'Unmeasured records', excluded: 'Excluded records',
  }
  for (const row of [
    [labels.run, snapshot.run.id], [labels.dataset, snapshot.run.dataset_name],
    [labels.updated, snapshot.run.updated_at], [labels.selected, '3'], [labels.total, '4'],
  ]) expect(rows).toContainEqual(row)
  expect(document.text).toContain(snapshot.headline)
  expect(document.text).toContain('معيار | Miyaar')
  expect(document.text).toContain(ar ? 'الملخص التنفيذي' : 'Executive summary')
  expect(document.text).toContain(snapshot.advisory!.recommendation)
  expect(document.text).toContain(snapshot.advisory!.preservation)
  expect(rows.some((row) => row.includes('Site') && row.some((cell) => cell.includes('North')))).toBe(true)
  const firstFix = snapshot.kpis.measures.find((measure) => measure.key === 'first_time_fix')!
  const scale = ar ? 'نسبة مئوية، من 0 إلى 100 (percent)' : 'Percent, 0–100 (percent)'
  const population = ar ? `جميع السجلات (${firstFix.population})` : firstFix.population
  expect(rows).toContainEqual([firstFix.title, '57.5', scale, '3'])
  const properties = document.tables.find((table) => table.some((row) =>
    row[0] === labels.formula && row[1] === firstFix.formula))
  expect(properties, 'the exported first-time-fix definition must retain its controlled population').toBeDefined()
  for (const row of [
    [labels.value, '57.5'], [labels.scale, scale],
    [labels.numerator, '23'], [labels.denominator, '40'], [labels.population, population],
    [labels.measured, '3'], [labels.unmeasured, '0'], [labels.excluded, '0'],
  ]) expect(properties).toContainEqual(row)
  for (const question of snapshot.questions) expect(document.text).toContain(question.text)
  for (const evidence of snapshot.evidence) expect(document.text).toContain(evidence.id)
  expect(document.text).toContain(ar ? 'أدلة النماذج المسجلة وحدودها' : 'Recorded model evidence and limitations')
  expect(document.text).toContain(ar
    ? 'لا يتوفر تقييم نموذج؛ ولا يُدّعى وجود أداء تنبؤي.'
    : 'No model evaluation is available; predictive performance is not claimed.')
}

async function downloadReport(page: Page, prepared: Locator, snapshot: RunExecutive, format: 'html' | 'docx') {
  const ar = snapshot.language === 'ar'
  const selector = prepared.getByRole('combobox', { name: ar ? 'تنسيق التقرير' : 'Report format', exact: true })
  if (format === 'html') await expect(selector).toHaveValue('html')
  else await selector.selectOption('docx')
  const [download, response] = await Promise.all([
    page.waitForEvent('download'),
    page.waitForResponse((response) => new URL(response.url()).pathname === `/api/runs/${snapshot.run.id}/executive/export`),
    prepared.getByRole('button', { name: ar ? 'تنزيل التقرير' : 'Download report', exact: true }).click(),
  ])
  expect(response.status()).toBe(200)
  const params = new URL(response.url()).searchParams
  expect(params.get('format')).toBe(format)
  expect(params.get('language')).toBe(snapshot.language)
  expect(JSON.parse(params.get('filters')!)).toEqual(snapshot.scope.filters)
  expect(snapshot.run.updated_at).toBeTruthy()
  expect(params.get('expected_updated_at')).toBe(snapshot.run.updated_at)
  expect(snapshot.snapshot_id).toMatch(/^[a-f0-9]{64}$/)
  expect(params.get('expected_snapshot_id')).toBe(snapshot.snapshot_id)
  expect(response.headers()['content-type']).toContain(format === 'html'
    ? 'text/html' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
  expect(download.suggestedFilename()).toBe(`miyaar-executive-${snapshot.run.id}-${snapshot.language}.${format}`)
  const document = format === 'html'
    ? await inspectHtml(page, await readFile(await downloadPath(download), 'utf8'), snapshot.language)
    : await inspectDocx(download, snapshot.language)
  expectReportScope(document, snapshot)
}

async function printReport(page: Page, prepared: Locator, snapshot: RunExecutive) {
  // This applies to the popup again when it navigates to the HTML Blob. Check
  // the print request without opening a native dialog or inventing a PDF file.
  await page.context().addInitScript(() => {
    window.print = () => { window.document.documentElement.dataset.printRequested = 'true' }
  })
  const downloads: Download[] = []
  const recordDownload = (download: Download) => downloads.push(download)
  page.on('download', recordDownload)
  const [popup, response] = await Promise.all([
    page.waitForEvent('popup'),
    page.waitForResponse((response) => new URL(response.url()).pathname === `/api/runs/${snapshot.run.id}/executive/export`),
    prepared.getByRole('button', { name: snapshot.language === 'ar' ? 'طباعة / حفظ بصيغة PDF' : 'Print / Save as PDF', exact: true }).click(),
  ])
  expect(response.status()).toBe(200)
  const params = new URL(response.url()).searchParams
  expect(params.get('format')).toBe('html')
  expect(params.get('language')).toBe(snapshot.language)
  expect(JSON.parse(params.get('filters')!)).toEqual(snapshot.scope.filters)
  expect(params.get('expected_updated_at')).toBe(snapshot.run.updated_at)
  expect(snapshot.snapshot_id).toMatch(/^[a-f0-9]{64}$/)
  expect(params.get('expected_snapshot_id')).toBe(snapshot.snapshot_id)
  await expect(popup).toHaveURL(/^blob:/)
  await expect(popup.locator('html')).toHaveAttribute('lang', snapshot.language)
  expect(await popup.evaluate(() => window.print.toString()),
    'the test print stub must survive Blob navigation before checking whether the application called it').toContain('printRequested')
  await expect(popup.locator('html')).toHaveAttribute('data-print-requested', 'true')
  const document = await inspectHtml(page, await popup.content(), snapshot.language)
  expectReportScope(document, snapshot)
  expect(downloads, 'printing requests a browser dialog, not a direct PDF download').toEqual([])
  await popup.setViewportSize({ width: 816, height: 1056 })
  await popup.emulateMedia({ media: 'print' })
  await popup.evaluate(() => window.document.fonts.ready)
  const printLayout = await popup.evaluate(() => ({
    frontBottom: window.document.querySelector('.compact')!.getBoundingClientRect().bottom,
    overflowingCells: Array.from(window.document.querySelectorAll<HTMLElement>('th,td'))
      .filter((cell) => cell.scrollWidth > cell.clientWidth + 2).length,
  }))
  expect(printLayout.frontBottom, 'summary fits the Letter page inside its print margins').toBeLessThanOrEqual(912)
  expect(printLayout.overflowingCells).toBe(0)
  page.off('download', recordDownload)
  await popup.close()
  await expect(prepared.getByRole('button', {
    name: snapshot.language === 'ar' ? 'طباعة / حفظ بصيغة PDF' : 'Print / Save as PDF', exact: true,
  })).toBeEnabled()
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

test('filtered executive measures, evidence and downloaded reports share the exact scope', async ({ page }) => {
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
  // (8 + 15) / (10 + 30), not a mean of rates. Summed over every record, as
  // the Power BI Method page defines it: the preventive record adds 0 to both.
  const firstTimeFix = expected.kpis.measures.find((m) => m.key === 'first_time_fix')
  expect(firstTimeFix).toMatchObject({
    numerator: 23, denominator: 40, records: 3,
    records_excluded: 0, records_unmeasured: 0, undefined_reason: null,
  })
  expect(firstTimeFix!.value).toBeCloseTo(57.5, 12)
  // Availability is 1 - downtime / planned: downtime 4 + 10 + 6 = 20 over planned 300.
  // It used to be operating / planned (265 / 300), which is utilisation.
  expect(expected.kpis.measures.find((m) => m.key === 'availability')).toMatchObject({
    numerator: 20, denominator: 300, records: 3,
  })
  expect(expected.kpis.measures.find((m) => m.key === 'utilisation')).toMatchObject({
    numerator: 265, denominator: 300, records: 3,
  })
  expect(expected.kpis.measures.find((m) => m.key === 'downtime_per_record')).toMatchObject({
    numerator: 20, denominator: 3, records: 3,
  })
  const fix = page.locator('[data-source="kpi.first_time_fix"]')
  await expect(fix.locator('.exec-kpi-value .performance-value__number')).toHaveText('57.5 %')
  await fix.locator('summary').click()
  await expect(fix.getByText('3 measured records', { exact: true })).toBeVisible()
  await expect(fix.locator('dd').first()).toContainText('23 / 40')
  await expect(fix).not.toContainText('outside this measure’s population')

  const priority = page.locator('.exec-priorities > li').filter({
    has: page.getByRole('heading', { name: 'Review overdue work', exact: true }),
  })
  await priority.getByRole('button', { name: 'View evidence (1)', exact: true }).click()
  const evidence = page.getByRole('region', { name: 'Evidence register', exact: true })
  const selected = evidence.getByRole('row', { name: /executive\.kpi\.overdue_share/ })
  await expect(selected).toBeFocused()
  await expect(selected).toHaveAttribute('data-selected', 'true')
  await expect(selected).toContainText('6.67')

  const models = page.locator('.exec-models')
  await models.locator(':scope > summary').click()
  await expect(models).toContainText('No evaluated models in this analysis. A performance score is not available.')
  await expect(models.getByRole('table')).toHaveCount(0)
  expect(expected.models).toEqual([])
  await page.getByRole('button', { name: 'Prepare executive brief', exact: true }).click()
  const prepared = page.getByRole('region', { name: 'Brief prepared for the current scope', exact: true })
  await expect(page.locator('.exec-hero')).toContainText(expected.headline)
  await expect(prepared).toContainText(expected.advisory?.recommendation ?? expected.headline)
  for (const question of expected.questions) await expect(prepared).toContainText(question.text)
  await expect(prepared.getByRole('option', { name: /JSON/ })).toHaveCount(0)
  await downloadReport(page, prepared, expected, 'html')
  await downloadReport(page, prepared, expected, 'docx')
  await expectAccessible(page, 'English executive brief and selected evidence')

  // Preparing and exporting a brief cannot satisfy the publication approval.
  const after = await (await page.request.get(`/api/runs/${run.id}`)).json() as RunDetail
  expect(after.state).toBe('awaiting_approval')
  expect(after.approvals).toEqual(run.approvals)
  expect(after.report?.published_path).toBeNull()

  // A prepared snapshot must disappear when the reader changes its scope.
  await openFilters(page)
  await page.getByLabel('From', { exact: true }).selectOption('2026-03')
  await expect(page.locator('.exec-scope strong')).toHaveText('2')
  await expect(prepared).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Prepare executive brief', exact: true })).toBeVisible()
  await expect(fix.locator('.exec-kpi-value .performance-value__number')).toHaveText('50 %')
})

test('an executive priority preserves the period filter when drilling into records and reloading', async ({ page }) => {
  test.setTimeout(75_000)
  await skipOnboarding(page)
  const run = await maintenanceRun(page.request)
  await openOverview(page, run.id)
  await openFilters(page)
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
  await expect(page.locator('.viewload')).toHaveCount(0)
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
  await expect(page.locator('[data-source="kpi.downtime_per_record"] .exec-kpi-value .performance-value__number')).toHaveText('20 h')
  await expect(page.getByLabel('From', { exact: true })).toHaveValue('2026-03')
})

test('Arabic RTL business reports and PDF print preview retain evidence in both themes', async ({ page }) => {
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
  await expect(page.getByRole('heading', { name: 'موجز القرار', exact: true })).toBeVisible()
  await expectScope(page, 3, 4, 'ar')
  const fix = page.locator('[data-source="kpi.first_time_fix"]')
  await expect(fix.getByRole('heading', { name: 'معدل الإصلاح من المرة الأولى' })).toBeVisible()
  await expect(fix.locator('.exec-kpi-value .performance-value__number')).toHaveText('57.5 %')
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
  await expect(page.locator('.exec-hero')).toContainText(expected.headline)
  await expect(prepared).toContainText(expected.advisory?.recommendation ?? expected.headline)
  await page.locator('.exec-models > summary').click()
  await expect(page.locator('.exec-models')).toContainText('لا توجد نماذج مقيّمة في هذا التحليل. لا تتوفر درجة أداء.')
  await downloadReport(page, prepared, expected, 'html')
  await downloadReport(page, prepared, expected, 'docx')
  await printReport(page, prepared, expected)
  await expectAccessible(page, 'Arabic dark executive brief')

  const after = await (await page.request.get(`/api/runs/${run.id}`)).json() as RunDetail
  expect(after.state).toBe('awaiting_approval')
  expect(after.approvals).toEqual(run.approvals)
  expect(after.report?.published_path).toBeNull()
})

test('a stale export reports the snapshot conflict without downloading a document', async ({ page }) => {
  test.setTimeout(75_000)
  await skipOnboarding(page)
  const run = await maintenanceRun(page.request)
  await openOverview(page, run.id)
  await chooseNorth(page)
  await page.getByRole('button', { name: 'Prepare executive brief', exact: true }).click()
  const prepared = page.getByRole('region', { name: 'Brief prepared for the current scope', exact: true })
  const snapshot = await executive(page.request, run.id, NORTH)
  const message = 'The analysis changed. Refresh the overview before exporting.'
  const downloads: Download[] = []
  page.on('download', (download) => downloads.push(download))
  let intercepted = 0
  // Only this one response is simulated. The run, scope, KPI calculations and
  // surrounding page remain real; the renderer's stale guard has API tests.
  await page.route((url) => url.pathname === `/api/runs/${run.id}/executive/export`, async (route) => {
    intercepted += 1
    const params = new URL(route.request().url()).searchParams
    expect(route.request().method()).toBe('GET')
    expect(params.get('format')).toBe('html')
    expect(params.get('expected_updated_at')).toBe(snapshot.run.updated_at)
    expect(params.get('expected_snapshot_id')).toBe(snapshot.snapshot_id)
    expect(JSON.parse(params.get('filters')!)).toEqual(NORTH)
    await route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ detail: message }) })
  }, { times: 1 })
  await prepared.getByRole('button', { name: 'Download report', exact: true }).click()
  await expect(prepared.getByRole('alert')).toHaveText('This snapshot is no longer current or has no verifiable content revision. Refresh the overview and prepare the brief again before exporting.')
  expect(intercepted).toBe(1)
  expect(downloads).toEqual([])
  await expectScope(page, 3, 4)
  const after = await (await page.request.get(`/api/runs/${run.id}`)).json() as RunDetail
  expect(after.approvals).toEqual(run.approvals)
  expect(after.report?.published_path).toBeNull()
})

// The compact scope presents the selected count and total in separate elements.
// Assert both rather than relying on whitespace between adjacent DOM nodes.
async function expectScope(page: Page, records: number, total: number, language: 'en' | 'ar' = 'en') {
  const disclosure = page.locator('.exec-limitations')
  if (!(await disclosure.evaluate((element) => (element as HTMLDetailsElement).open))) await disclosure.locator('summary').click()
  const scope = page.locator('.exec-scope')
  await expect(scope.locator('strong')).toHaveText(String(records))
  await expect(scope.getByText(language === 'ar'
    ? `من أصل ${total} سجلًا منظَّفًا` : `of ${total} cleaned records`, { exact: true })).toBeVisible()
}

// Capture the actual cards, not the header above them. These are real API
// calculations over the fictional fixture, never production or model data.
for (const language of ['en', 'ar'] as const) {
  test(`KPI review context and evidence fit the viewport (${language})`, async ({ page }, testInfo) => {
    test.setTimeout(60_000)
    if (testInfo.project.name === 'mobile') await page.setViewportSize({ width: 320, height: 812 })
    await skipOnboarding(page)
    await page.addInitScript((locale) => localStorage.setItem('aos-locale', locale), language)
    const run = await maintenanceRun(page.request, language)
    await openOverview(page, run.id, 'f.Site=North', language)
    await expectScope(page, 3, 4, language)
    await expect(page.locator('html')).toHaveAttribute('dir', language === 'ar' ? 'rtl' : 'ltr')
    const snapshot = await executive(page.request, run.id, NORTH, language)
    const cards = page.locator('.exec-kpi')
    await expect(cards).toHaveCount(snapshot.kpis.measures.length)
    const unknown = language === 'ar'
      ? 'الفترة والمسؤول غير محددين. الحداثة غير مقيّمة؛ التحديث ليس قراءة.'
      : 'Period/owner unknown; freshness unassessed. Update ≠ observation.'
    for (const card of await cards.all()) {
      await expect(card.locator(':scope > details > .exec-muted')).toHaveText(unknown)
    }
    const fix = page.locator('[data-source="kpi.first_time_fix"]')
    const measure = snapshot.kpis.measures.find((item) => item.key === 'first_time_fix')!
    expect(measure.value).toBeCloseTo(57.5, 12)
    await expect(fix.locator('.exec-kpi-value .performance-value__number')).toHaveText('57.5 %')
    const disclosure = fix.locator('details')
    const summary = disclosure.locator('summary')
    await summary.focus()
    await page.keyboard.press('Enter')
    await expect(disclosure).toHaveAttribute('open', '')
    await expect(fix).toContainText(snapshot.run.dataset_name)
    await expect(fix).toContainText(run.id)
    await expect(fix.getByText(language === 'ar'
      ? `من يراجع «${measure.title}»؟` : `Who reviews “${measure.title}”?`, { exact: true })).toBeVisible()
    await expect(fix.locator('input, select, textarea')).toHaveCount(0)
    await page.evaluate(() => document.fonts.ready)

    for (const theme of ['light', 'dark']) {
      await page.evaluate((value) => { document.documentElement.dataset.theme = value }, theme)
      // Element captures include the disclosure even when it is below the fold.
      // Keep every KPI family as well as the expanded, source-bound card.
      const prefix = `../docs/screenshots/${testInfo.project.name}-kpi-review-${language}-${theme}`
      const viewport = page.viewportSize()!
      if (testInfo.project.name === 'mobile') {
        // Actual 320 x 812 acceptance evidence, before any height expansion.
        // An expanded disclosure is taller than the shell's scrollport. Keep
        // collapsed cards whole, then prove both ends are reachable by scrolling
        // rather than pretending the expanded card fits in one phone screen.
        await summary.click()
        await expect(disclosure).not.toHaveAttribute('open', '')
        for (const card of await cards.all()) {
          await card.evaluate((element) => element.scrollIntoView({ block: 'center', behavior: 'instant' }))
          await expect(card).toBeInViewport({ ratio: 1 })
          await card.screenshot({ path: `${prefix}-phone-${await card.getAttribute('data-source')}.png`, animations: 'disabled' })
        }
        await summary.click()
        await expect(disclosure).toHaveAttribute('open', '')
        await fix.locator('.exec-kpi-value').evaluate((element) => element.scrollIntoView({ block: 'center', behavior: 'instant' }))
        await expect(fix.locator('.exec-kpi-value')).toBeInViewport({ ratio: 1 })
        await expect(summary).toBeInViewport({ ratio: 1 })
        await page.screenshot({ path: `${prefix}-phone-disclosure-top.png`, animations: 'disabled' })
        const action = fix.getByRole('button', { name: language === 'ar' ? 'عرض الأدلة (1)' : 'View evidence (1)', exact: true })
        await action.evaluate((element) => element.scrollIntoView({ block: 'center', behavior: 'instant' }))
        await expect(action).toBeInViewport({ ratio: 1 })
        await expect(fix.getByText(run.id, { exact: true })).toBeInViewport({ ratio: 1 })
        await page.screenshot({ path: `${prefix}-phone-disclosure-bottom.png`, animations: 'disabled' })
      }
      // The app scrolls inside its shell. A locator taller than that scrollport
      // can otherwise capture unrelated content or clipped cards even though
      // Playwright succeeds. Enlarge only capture height, never tested width;
      // restore the actual phone height before layout/accessibility assertions.
      const captureHeight = await page.locator('.exec-family, .exec-featured').evaluateAll((groups) =>
        Math.max(...groups.map((group) => group.getBoundingClientRect().height)))
      await page.setViewportSize({ width: viewport.width, height: Math.ceil(captureHeight) + 400 })
      await fix.evaluate((element) => element.scrollIntoView({ block: 'center', behavior: 'instant' }))
      await expect(fix).toBeInViewport({ ratio: 1 })
      await fix.screenshot({ path: `${prefix}-expanded-evidence.png`, animations: 'disabled' })
      for (const family of await page.locator('.exec-family').all()) {
        const name = await family.getAttribute('data-family')
        await family.evaluate((element) => element.scrollIntoView({ block: 'center', behavior: 'instant' }))
        await expect(family).toBeInViewport({ ratio: 1 })
        await family.screenshot({ path: `${prefix}-expanded-${name}.png`, animations: 'disabled' })
      }
      await page.setViewportSize(viewport)
      const clipped = await cards.evaluateAll((elements) => elements.flatMap((card) => {
        const nodes = [card, ...card.querySelectorAll('h4, h5, p, summary, dt, dd, button')]
        return nodes.filter((node) => {
          const element = node as HTMLElement
          if (!element.getClientRects().length) return false
          const rect = element.getBoundingClientRect()
          return rect.left < -1 || rect.right > document.documentElement.clientWidth + 1
            || element.scrollWidth > element.clientWidth + 1
        }).map((node) => `${card.getAttribute('data-source')}: ${node.textContent}`)
      }))
      expect(clipped, `${language} ${theme}: KPI content must not clip or scroll sideways`).toEqual([])
    }
    await expectAccessible(page, `${language} KPI review at ${page.viewportSize()!.width}px`)
    await fix.getByRole('button', { name: language === 'ar' ? 'عرض الأدلة (1)' : 'View evidence (1)', exact: true }).click()
    const selected = page.locator('.exec-evidence tr[data-selected="true"]')
    await expect(selected).toHaveCount(1)
    await expect(selected).toContainText('executive.kpi.first_time_fix')
    await expect(selected).toBeFocused()
    await expectAccessible(page, `${language} open KPI evidence at ${page.viewportSize()!.width}px`)
    // Returning to a disclosure and reopening it must retain the same context.
    await summary.focus()
    await page.keyboard.press('Enter')
    await expect(disclosure).not.toHaveAttribute('open', '')
    await page.keyboard.press('Enter')
    await expect(disclosure).toHaveAttribute('open', '')
    await expect(fix).toContainText(run.id)
    const after = await (await page.request.get(`/api/runs/${run.id}`)).json() as RunDetail
    expect(after.approvals).toEqual(run.approvals)
    expect(after.report?.published_path).toBeNull()
  })
}

