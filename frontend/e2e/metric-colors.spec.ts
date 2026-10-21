import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { APIRequestContext, Download, Locator, Page, Response } from '@playwright/test'
import { execFile } from 'node:child_process'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'
import type { RunDetail, RunExecutive } from '../src/shared/types'
import { skipOnboarding, openFilters } from './helpers'
import { storeMaintenanceDataset } from './maintenance-dataset'

type Language = 'en' | 'ar'
type Assessment = 'good' | 'okay' | 'bad' | 'unassessed' | 'unavailable'
type Rule = { scale: string; source_ref: string; definition?: number } & (
  | { direction: 'higher' | 'lower'; good_at: number; okay_at: number }
  | { direction: 'range'; good_min: number; good_max: number; okay_min: number; okay_max: number }
)
interface Policy { revision: string; rules: Record<string, Rule> }
interface DocumentContents { text: string; tables: string[][][] }

const SOURCE = 'Fictional QA acceptance bands v1; not operational targets.'
const RULES: Record<string, Rule> = {
  // Redefined on 21 October to match the Power BI report (definition 2).
  first_time_fix: { direction: 'higher', scale: 'percent', good_at: 80, okay_at: 60, source_ref: SOURCE, definition: 2 },
  repeat_repair: { direction: 'lower', scale: 'percent', good_at: 5, okay_at: 20, source_ref: SOURCE, definition: 2 },
  // Set for availability's current definition (2), so it judges the figure.
  availability: { direction: 'higher', scale: 'percent', good_at: 95, okay_at: 80, source_ref: SOURCE, definition: 2 },
  downtime_per_record: { direction: 'range', scale: 'hours', good_min: 8, good_max: 12, okay_min: 4, okay_max: 16, source_ref: SOURCE },
}
const LABELS: Record<Language, Record<Assessment, string>> = {
  en: { good: 'Good', okay: 'Okay', bad: 'Bad', unassessed: 'Not assessed', unavailable: 'Unavailable' },
  ar: { good: 'جيد', okay: 'مقبول', bad: 'غير مرضٍ', unassessed: 'غير مقيّم', unavailable: 'غير متاح' },
}
// Four fictional records; the loss column is present but entirely unmeasured.
// The observed quantities stay fixed when policy changes: only assessment changes.
const CSV = [
  'month,Site,Record_ID,Work_Order_Type,Downtime_Hours,Operating_Hours,Planned_Operating_Hours,Preventive_WO_Count,Corrective_WO_Count,Completed_WO_Count,First_Time_Fix_Count,Repeat_Repair_Count,Overdue_WO_Count,Maintenance_Cost_USD,Production_Loss_USD',
  '2026-02,North,METRIC-QA-A,Corrective,4,80,100,0,10,10,8,2,1,100,',
  '2026-03,North,METRIC-QA-B,Corrective,10,95,100,0,30,30,27,3,2,300,',
  '2026-03,North,METRIC-QA-C,Preventive,6,90,100,5,0,5,0,0,0,200,',
  '2026-03,South,METRIC-QA-D,Corrective,20,60,100,0,20,20,10,10,3,900,',
].join('\n') + '\n'

test.use({ serviceWorkers: 'block', contextOptions: { reducedMotion: 'reduce' } })

async function createRun(request: APIRequestContext, language: Language) {
  const datasetId = await storeMaintenanceDataset(request, CSV, 'fictional-metric-colors.csv', language, false)
  const response = await request.post('/api/runs', { data: {
    goal: 'Assess fictional maintenance metrics against explicit QA targets',
    dataset_id: datasetId, profile: 'default', language,
  } })
  await expect(response).toBeOK()
  let run = await response.json() as RunDetail
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

async function readPolicy(request: APIRequestContext, id: string) {
  const response = await request.get(`/api/runs/${id}/kpi-policy`)
  await expect(response).toBeOK()
  return await response.json() as Policy
}

async function writePolicy(request: APIRequestContext, id: string, current: Policy, rules: Record<string, Rule>) {
  const response = await request.put(`/api/runs/${id}/kpi-policy`, { data: {
    expected_revision: current.revision, rules,
  } })
  await expect(response).toBeOK()
  const policy = await response.json() as Policy
  expect(policy.revision).not.toBe(current.revision)
  expect(policy.rules).toEqual(rules)
  return policy
}

async function saveFirstFixTarget(page: Page, id: string, language: Language, current: Policy) {
  const ar = language === 'ar'
  const title = ar ? 'أهداف الأداء' : 'Performance targets'
  await page.getByRole('button', { name: title, exact: true }).click()
  const editor = page.getByRole('region', { name: title, exact: true })
  await editor.getByLabel(ar ? 'المؤشر' : 'Measure', { exact: true }).selectOption('first_time_fix')
  await editor.getByLabel(ar ? 'الاتجاه المطلوب' : 'Desired direction', { exact: true }).selectOption('higher')
  await editor.getByLabel(ar ? 'حد الجيد (شامل)' : 'Good boundary (inclusive)', { exact: true }).fill('80')
  await editor.getByLabel(ar ? 'حد المقبول (شامل)' : 'Okay boundary (inclusive)', { exact: true }).fill('60')
  await editor.getByLabel(ar ? 'مصدر الهدف / مبرره' : 'Target source / rationale', { exact: true }).fill(SOURCE)
  const accessibility = await new AxeBuilder({ page }).include('.policy-editor')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
  expect(accessibility.violations, `${language} target editor`).toEqual([])
  const [response] = await Promise.all([
    page.waitForResponse((result) => new URL(result.url()).pathname === `/api/runs/${id}/kpi-policy`
      && result.request().method() === 'PUT'),
    editor.getByRole('button', { name: ar ? 'حفظ الهدف' : 'Save target', exact: true }).click(),
  ])
  expect(response.status()).toBe(200)
  expect(response.request().postDataJSON()).toEqual({ expected_revision: current.revision, rules: RULES })
  const policy = await response.json() as Policy
  expect(policy.rules).toEqual(RULES)
  expect(policy.revision).not.toBe(current.revision)
  await expect(editor).toBeHidden()
  return policy
}

async function readExecutive(request: APIRequestContext, id: string, language: Language) {
  const response = await request.get(`/api/runs/${id}/executive`, { params: { language, filters: '[]' } })
  await expect(response).toBeOK()
  return await response.json() as RunExecutive
}

function metric(page: Page, key: string) {
  return page.locator(`[data-source="kpi.${key}"]`)
}

async function expectMetric(page: Page, key: string, status: Assessment, value: RegExp, language: Language) {
  const card = metric(page, key)
  await expect(card.locator('[data-performance]')).toHaveAttribute('data-performance', status)
  await expect(card.locator('.performance-value__number')).toHaveText(value)
  await expect(card.locator('.performance-value__number')).toBeVisible()
  await expect(card.locator('.performance-value__status')).toHaveText(LABELS[language][status])
  await expect(card.locator('.performance-value__status')).toBeVisible()
}

async function expectFullScope(page: Page, language: Language) {
  await expect(page.locator('.exec-scope strong')).toHaveText('4')
  await expectMetric(page, 'first_time_fix', 'okay', /^75\s*%$/, language)
  await expectMetric(page, 'repeat_repair', 'bad', /^25\s*%$/, language)
  // 1 - (4 + 10 + 6 + 20) / 400: planned time not lost to downtime (was operating / planned, 81.25%).
  await expectMetric(page, 'availability', 'okay', /^90\s*%$/, language)
  await expectMetric(page, 'downtime_per_record', 'good', language === 'ar' ? /^10\s*ساعة$/ : /^10\s*h$/, language)
  await expectMetric(page, 'preventive_share', 'unassessed', /^7\.69\s*%$/, language)
  await expectMetric(page, 'loss_per_downtime_hour', 'unavailable', language === 'ar' ? /^غير متاح\s*$/ : /^Not available\s*$/, language)
}

function contrast(first: string, second: string) {
  const luminance = (color: string) => {
    const channels = color.match(/[\d.]+/g)!.map(Number)
    expect(channels.length).toBeGreaterThanOrEqual(3)
    if (channels.length > 3) expect(channels[3], 'resolve translucent layers before asserting contrast').toBe(1)
    // color-mix() resolves to color(srgb r g b) with channels from 0 to 1, not rgb() from 0 to 255.
    const scale = color.startsWith('color(srgb') ? 1 : 255
    const [red, green, blue] = channels.slice(0, 3).map((n) => n / scale)
      .map((n) => n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4)
    return .2126 * red + .7152 * green + .0722 * blue
  }
  const values = [luminance(first), luminance(second)].sort((a, b) => a - b)
  return (values[1] + .05) / (values[0] + .05)
}

async function expectRenderedContrast(target: Locator) {
  const colors = await target.evaluate((element) => {
    let parent: Element | null = element
    while (parent) {
      const style = getComputedStyle(parent)
      const stops = style.backgroundImage.match(/rgba?\([^)]*\)/g)
      if (stops?.length) return { text: getComputedStyle(element).color, backgrounds: stops }
      if (style.backgroundColor !== 'rgba(0, 0, 0, 0)' && style.backgroundColor !== 'transparent') {
        return { text: getComputedStyle(element).color, backgrounds: [style.backgroundColor] }
      }
      parent = parent.parentElement
    }
    return { text: getComputedStyle(element).color, backgrounds: [] }
  })
  expect(colors.backgrounds, 'a rendered number must have a resolved surface').not.toEqual([])
  for (const background of colors.backgrounds) expect(contrast(colors.text, background),
    `rendered text ${colors.text} against ${background}`).toBeGreaterThanOrEqual(4.5)
}

async function expectAccessibleStatuses(page: Page, language: Language, theme: string) {
  await page.evaluate(() => document.fonts.ready)
  // Observe the actual rendered foreground, independently of CSS class names.
  for (const [key, dominant] of [['downtime_per_record', 1], ['first_time_fix', 2], ['repeat_repair', 0]] as const) {
    const channels = (await metric(page, key).locator('.performance-value__number')
      .evaluate((element) => getComputedStyle(element).color)).match(/[\d.]+/g)!.slice(0, 3).map(Number)
    for (let channel = 0; channel < 3; channel += 1) {
      if (channel !== dominant) expect(channels[dominant], `${key}: expected green/blue/red respectively`).toBeGreaterThan(channels[channel])
    }
  }
  for (const key of ['first_time_fix', 'repeat_repair', 'downtime_per_record', 'preventive_share', 'loss_per_downtime_hour']) {
    await expectRenderedContrast(metric(page, key).locator('.performance-value__number'))
    await expectRenderedContrast(metric(page, key).locator('.performance-value__status'))
  }
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
  expect(result.violations, `${language} ${theme} assessed metrics`).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
}

async function openOverview(page: Page, id: string, language: Language) {
  await page.goto(`/#/dashboard/${id}/overview`)
  await expect(page.getByRole('heading', { name: language === 'ar' ? 'النظرة التنفيذية' : 'Executive overview', exact: true })).toBeVisible()
}

async function chooseNorth(page: Page) {
  await openFilters(page)
  const filter = page.locator('details.dash-filter').filter({ has: page.locator('summary').filter({ hasText: /^Site:/ }) })
  await filter.locator('summary').click()
  const checkbox = filter.getByRole('checkbox', { name: 'North', exact: true })
  await checkbox.click()
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
  expect(path).not.toBeNull()
  return path!
}

async function inspectWord(download: Download): Promise<DocumentContents> {
  const path = await downloadPath(download)
  expect((await readFile(path)).subarray(0, 4).toString('hex')).toBe('504b0304')
  const local = fileURLToPath(new URL(process.platform === 'win32' ? '../../.venv/Scripts/python.exe' : '../../.venv/bin/python', import.meta.url))
  const python = process.env.PYTHON_EXECUTABLE ?? (existsSync(local) ? local : 'python3')
  const script = [
    'import json,sys,zipfile,xml.etree.ElementTree as ET',
    'ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}',
    'def text(node):return " ".join("".join(node.itertext()).split())',
    'with zipfile.ZipFile(sys.argv[1]) as archive:',
    ' root=ET.fromstring(archive.read("word/document.xml"))',
    ' print(json.dumps({"text":text(root),"tables":[[[text(c) for c in r.findall("w:tc",ns)] for r in t.findall("w:tr",ns)] for t in root.findall(".//w:tbl",ns)]},ensure_ascii=False))',
  ].join('\n')
  const { stdout } = await promisify(execFile)(python, ['-c', script, path], { encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' } })
  return JSON.parse(stdout) as DocumentContents
}

async function inspectHtml(page: Page, download: Download): Promise<DocumentContents> {
  const source = await readFile(await downloadPath(download), 'utf8')
  expect(source).toMatch(/^<!doctype html>/i)
  return page.evaluate((html) => {
    const doc = new DOMParser().parseFromString(html, 'text/html')
    const text = (node: Element) => (node.textContent ?? '').replace(/\s+/gu, ' ').trim()
    return { text: text(doc.body), tables: Array.from(doc.querySelectorAll('table'),
      (table) => Array.from(table.rows, (row) => Array.from(row.cells, text))) }
  }, source)
}

function expectExportRequest(response: Response, snapshot: RunExecutive, format: string) {
  expect(response.status()).toBe(200)
  const params = new URL(response.url()).searchParams
  expect(params.get('format')).toBe(format)
  expect(params.get('language')).toBe(snapshot.language)
  expect(JSON.parse(params.get('filters')!)).toEqual([])
  expect(params.get('expected_snapshot_id')).toBe(snapshot.snapshot_id)
  expect(params.get('expected_updated_at')).toBe(snapshot.run.updated_at)
}

for (const language of ['en', 'ar'] as const) {
  test(`explicit metric assessments retain values, evidence and readable colors (${language})`, async ({ page }) => {
    test.setTimeout(110_000)
    await skipOnboarding(page)
    await page.addInitScript((locale) => {
      localStorage.setItem('aos-locale', locale)
      if (!localStorage.getItem('aos-theme')) localStorage.setItem('aos-theme', 'light')
    }, language)
    const run = await createRun(page.request, language)
    const initial = await readPolicy(page.request, run.id)
    expect(initial.rules).toEqual({})
    await openOverview(page, run.id, language)
    await expectMetric(page, 'first_time_fix', 'unassessed', /^75\s*%$/, language)
    await expect(metric(page, 'first_time_fix').locator('.performance-value__status')).not.toHaveText(LABELS[language].okay)

    const otherTargets = Object.fromEntries(Object.entries(RULES).filter(([key]) => key !== 'first_time_fix'))
    const seeded = await writePolicy(page.request, run.id, initial, otherTargets)
    const policy = await saveFirstFixTarget(page, run.id, language, seeded)
    await expectFullScope(page, language)
    await expectAccessibleStatuses(page, language, 'light')

    const address = page.url()
    await page.goto('/#/preferences')
    await page.getByRole('button', { name: language === 'ar' ? 'داكن' : 'Dark', exact: true }).click()
    await page.goto(address)
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await expect(page.locator('html')).toHaveAttribute('dir', language === 'ar' ? 'rtl' : 'ltr')
    await expectFullScope(page, language)
    await expectAccessibleStatuses(page, language, 'dark')

    await chooseNorth(page)
    await expectMetric(page, 'first_time_fix', 'good', /^87\.5\s*%$/, language)
    await expectMetric(page, 'repeat_repair', 'okay', /^12\.5\s*%$/, language)
    await page.reload()
    await expectMetric(page, 'first_time_fix', 'good', /^87\.5\s*%$/, language)
    await page.getByRole('button', { name: language === 'ar' ? 'مسح المرشحات (1)' : 'Clear filters (1)', exact: true }).click()
    await expectFullScope(page, language)

    await page.getByRole('button', { name: language === 'ar' ? 'إعداد الموجز التنفيذي' : 'Prepare executive brief', exact: true }).click()
    const prepared = page.getByRole('region', { name: language === 'ar' ? 'أُعدّ الموجز للنطاق الحالي' : 'Brief prepared for the current scope', exact: true })
    const snapshot = await readExecutive(page.request, run.id, language)
    expect(snapshot.kpi_policy).toEqual(policy)
    expect(snapshot.kpis.measures.find((measure) => measure.key === 'first_time_fix')?.assessment?.status).toBe('okay')
    const documents: DocumentContents[] = []
    for (const format of ['html', 'docx'] as const) {
      await prepared.getByRole('combobox', { name: language === 'ar' ? 'تنسيق التقرير' : 'Report format', exact: true }).selectOption(format)
      const [download, response] = await Promise.all([
        page.waitForEvent('download'),
        page.waitForResponse((response) => new URL(response.url()).pathname === `/api/runs/${run.id}/executive/export`),
        prepared.getByRole('button', { name: language === 'ar' ? 'تنزيل التقرير' : 'Download report', exact: true }).click(),
      ])
      expectExportRequest(response, snapshot, format)
      expect(download.suggestedFilename()).toBe(`miyaar-executive-${run.id}-${language}.${format}`)
      documents.push(format === 'html' ? await inspectHtml(page, download) : await inspectWord(download))
    }
    for (const document of documents) {
      expect(document.text).toContain(SOURCE)
      expect(document.text).not.toContain('METRIC-QA-')
      expect(document.tables.some((table) => table.some((row) =>
        row[0] === (language === 'ar' ? 'السجلات المحددة' : 'Selected records') && row[1] === '4'))).toBe(true)
      const audits = new Map<string, string[][]>()
      for (const [key, status] of [
        ['first_time_fix', 'okay'], ['repeat_repair', 'bad'], ['downtime_per_record', 'good'],
        ['preventive_share', 'unassessed'], ['loss_per_downtime_hour', 'unavailable'],
      ] as const) {
        const matches = document.tables.filter((table) => table.some((row) =>
          row[0] === (language === 'ar' ? 'معرّف الدليل' : 'Evidence ID') && row[1] === `executive.kpi.${key}`))
        expect(matches, `${key} must retain exactly one evidence audit table`).toHaveLength(1)
        const audit = matches[0]
        audits.set(key, audit)
        expect(audit).toContainEqual([language === 'ar' ? 'حالة الأداء' : 'Performance status', LABELS[language][status]])
        expect(audit).toContainEqual([language === 'ar' ? 'مصدر الهدف' : 'Target source',
          RULES[key] ? SOURCE : (language === 'ar' ? 'غير متاح' : 'Not available')])
        const assessment = snapshot.kpis.measures.find((measure) => measure.key === key)?.assessment
        expect(assessment?.reason).toBeTruthy()
        expect(audit).toContainEqual([language === 'ar' ? 'سبب التقييم' : 'Assessment reason', assessment!.reason])
      }
      const firstFix = audits.get('first_time_fix')!
      expect(firstFix).toContainEqual([language === 'ar' ? 'القيمة' : 'Value', '75'])
      expect(firstFix).toContainEqual([language === 'ar' ? 'البسط' : 'Numerator', '45'])
      expect(firstFix).toContainEqual([language === 'ar' ? 'المقام' : 'Denominator', '60'])
      const loss = audits.get('loss_per_downtime_hour')!
      expect(loss).toContainEqual([language === 'ar' ? 'القيمة' : 'Value', language === 'ar' ? 'غير متاح' : 'Not available'])
      expect(loss).toContainEqual([language === 'ar' ? 'السجلات المقاسة' : 'Measured records', '0'])
      expect(loss).toContainEqual([language === 'ar' ? 'السجلات غير المقاسة' : 'Unmeasured records', '4'])
    }

    await writePolicy(page.request, run.id, policy, {
      ...RULES,
      first_time_fix: { direction: 'higher', scale: 'percent', good_at: 70, okay_at: 60, source_ref: `${SOURCE} Revision two.`, definition: 2 },
    })
    const changed = await readExecutive(page.request, run.id, language)
    expect(changed.snapshot_id).not.toBe(snapshot.snapshot_id)
    expect(changed.kpis.measures.find((measure) => measure.key === 'first_time_fix')?.value).toBe(75)
    expect(changed.kpis.measures.find((measure) => measure.key === 'first_time_fix')?.assessment?.status).toBe('good')
    const downloads: Download[] = []
    page.on('download', (download) => downloads.push(download))
    await prepared.getByRole('combobox', { name: language === 'ar' ? 'تنسيق التقرير' : 'Report format', exact: true }).selectOption('html')
    const [stale] = await Promise.all([
      page.waitForResponse((response) => new URL(response.url()).pathname === `/api/runs/${run.id}/executive/export`),
      prepared.getByRole('button', { name: language === 'ar' ? 'تنزيل التقرير' : 'Download report', exact: true }).click(),
    ])
    expect(stale.status()).toBe(409)
    await expect(prepared.getByRole('alert')).toBeVisible()
    expect(downloads).toEqual([])
    const after = await (await page.request.get(`/api/runs/${run.id}`)).json() as RunDetail
    expect(after.state).toBe('awaiting_approval')
    expect(after.approvals).toEqual(run.approvals)
    expect(after.report?.published_path).toBeNull()
  })
}
