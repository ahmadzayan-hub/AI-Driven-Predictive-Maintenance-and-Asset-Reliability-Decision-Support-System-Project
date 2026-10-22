import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { skipOnboarding } from './helpers'

// Real API-backed ingestion and publication with explicitly synthetic OOXML
// fixtures. No response interception, RMD originals or operational baselines.
const root = fileURLToPath(new URL('../../', import.meta.url))
const localPython = fileURLToPath(new URL(process.platform === 'win32' ? '../../.venv/Scripts/python.exe' : '../../.venv/bin/python', import.meta.url))
const python = process.env.PYTHON_EXECUTABLE ?? (existsSync(localPython) ? localPython : 'python3')
function fixture(kind: 'workbook' | 'document') {
  return execFileSync(python, ['-c', `import sys; from tests.test_rmd_ingestion import ${kind}; sys.stdout.buffer.write(${kind}())`], { cwd: root })
}
const labels = {
  en: {
    title: 'RMD Evidence and Insights', packName: 'Pack name', pack: 'Evidence pack', create: 'Create',
    import: 'Import sources', kind: 'Source type', file: 'Source file', upload: 'Import file', map: 'Review workbook mapping',
    grain: 'Record grain', header: 'Header row', date: 'Text date convention', sr: 'SR identifier', wo: 'WO identifier',
    status: 'Recorded WO status', location: 'Recorded location', category: 'Recorded category', event: 'Event date',
    save: 'Save mapping', mapped: 'Mapping saved. A new analysis will use this mapping.', calculate: 'Calculate analysis',
    overview: 'Executive overview', investigations: 'Reconciliation and investigations', knowledge: 'Knowledge and control evidence', quality: 'Data quality and readiness',
    kpi: 'MMS source rows', evidence: 'Inspect evidence', records: 'Supporting records', priorities: 'Management priorities',
    search: 'Search', query: 'Search procedure clauses', actions: 'Add proposed action', actionAdded: 'Proposed action recorded. It is not an authorised maintenance instruction.',
    export: 'Download action register', explain: 'Explain this analysis in the assistant', question: 'Evidence question', ask: 'Ask',
    assistant: 'Ask about the selected evidence', review: 'Review report', approval: 'Approval required', read: 'I have read this exact report',
    approve: 'Approve and publish', unavailable: 'Unavailable', readiness: 'Predictive-readiness gate',
  },
  ar: {
    title: 'أدلة وإحصاءات إدارة صيانة السكك الحديدية', packName: 'اسم الحزمة', pack: 'حزمة الأدلة', create: 'إنشاء',
    import: 'استيراد المصادر', kind: 'نوع المصدر', file: 'ملف المصدر', upload: 'استيراد الملف', map: 'مراجعة تعيين أعمدة المصنف',
    grain: 'مستوى السجل', header: 'صف العناوين', date: 'تنسيق التواريخ النصية', sr: 'معرّف SR', wo: 'معرّف WO',
    status: 'حالة أمر العمل المسجلة', location: 'الموقع المسجل', category: 'الفئة المسجلة', event: 'تاريخ الحدث',
    save: 'حفظ التعيين', mapped: 'تم حفظ التعيين. سيستخدمه التحليل الجديد.', calculate: 'حساب التحليل',
    overview: 'النظرة التنفيذية', investigations: 'المطابقة والتحقيقات', knowledge: 'المعرفة وأدلة الضوابط', quality: 'جودة البيانات وجاهزية التنبؤ',
    kpi: 'صفوف مصدر MMS', evidence: 'فحص الأدلة', records: 'السجلات الداعمة', priorities: 'الأولويات الإدارية',
    search: 'بحث', query: 'البحث في بنود الإجراءات', actions: 'إضافة إجراء مقترح', actionAdded: 'تم تسجيل الإجراء المقترح. وهو ليس تفويضًا بتنفيذ صيانة.',
    export: 'تنزيل سجل الإجراءات', explain: 'شرح هذا التحليل في المساعد', question: 'سؤال عن الأدلة', ask: 'اسأل',
    assistant: 'اسأل عن الأدلة المحددة', review: 'مراجعة التقرير', approval: 'موافقة مطلوبة', read: 'قرأت هذا التقرير المحدد',
    approve: 'الموافقة والنشر', unavailable: 'غير متاح', readiness: 'بوابة جاهزية التنبؤ',
  },
} as const

async function navigate(page: Page, locale: 'en' | 'ar', name: RegExp) {
  const menu = page.getByRole('button', { name: locale === 'ar' ? 'فتح قائمة التنقل' : 'Open navigation' })
  const target = page.getByRole('button', { name }).filter({ visible: true })
  await menu.or(target.first()).first().waitFor()
  if (await menu.isVisible()) await menu.click()
  await target.first().click()
  await expect(page.locator('.viewload')).toHaveCount(0)
}
async function accessible(page: Page, context: string) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
  expect(results.violations, `${context}: ${results.violations.map(v => v.id).join(', ')}`).toEqual([])
}
async function fits(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
}

test.use({ contextOptions: { reducedMotion: 'reduce' }, actionTimeout: 15_000 })

for (const locale of ['en', 'ar'] as const) {
  test(`synthetic RMD evidence → mapping → findings → exact report → confirmed publication (${locale})`, async ({ page, request }, testInfo) => {
    test.setTimeout(120_000)
    const text = labels[locale], workbookName = `synthetic-evidence-${locale}.xlsx`, procedureName = `synthetic-reference-${locale}.docx`
    const packName = `Synthetic evidence ${locale} ${testInfo.project.name} ${Date.now()}`
    await skipOnboarding(page)
    await page.addInitScript(value => localStorage.setItem('aos-locale', value), locale)
    await page.goto('/#/rmd')
    await expect(page.getByRole('heading', { name: text.title, exact: true })).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr')
    const create = page.locator('.rmd-create')
    await create.waitFor()
    if ((await create.getAttribute('open')) === null) await create.locator(':scope > summary').click()
    await page.getByLabel(text.packName, { exact: true }).fill(packName)
    const created = page.waitForResponse(r => new URL(r.url()).pathname === '/api/rmd/packs' && r.request().method() === 'POST')
    await page.getByRole('button', { name: text.create, exact: true }).click()
    const packResponse = await created
    expect(packResponse.ok()).toBe(true)
    const pack = await packResponse.json() as { id: string }
    await expect(page.locator('.rmd-context > strong')).toHaveText(packName)

    const importer = page.locator('.rmd-import')
    await importer.locator(':scope > summary').click()
    for (const input of [
      { kind: 'workbook', name: workbookName, mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: fixture('workbook') },
      { kind: 'procedure', name: procedureName, mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: fixture('document') },
    ]) {
      await importer.getByRole('combobox', { name: text.kind, exact: true }).selectOption(input.kind)
      await importer.getByLabel(text.file, { exact: true }).setInputFiles({ name: input.name, mimeType: input.mimeType, buffer: input.buffer })
      const imported = page.waitForResponse(r => new URL(r.url()).pathname === `/api/rmd/packs/${pack.id}/sources` && r.request().method() === 'POST')
      await importer.getByRole('button', { name: text.upload, exact: true }).click()
      expect((await imported).ok()).toBe(true)
    }

    const sources = page.locator('details.rmd-card').filter({ has: page.locator('.rmd-source-list') }).first()
    if ((await sources.getAttribute('open')) === null) await sources.locator(':scope > summary').click()
    await page.getByRole('button', { name: text.map, exact: true }).click()
    const mapping = page.getByRole('dialog', { name: workbookName, exact: true })
    const working = mapping.getByRole('group', { name: 'Working sheet', exact: true })
    await working.getByRole('combobox', { name: text.grain, exact: true }).selectOption('mms_work_order')
    await working.getByLabel(text.header, { exact: true }).fill('3')
    await working.getByRole('combobox', { name: text.date, exact: true }).selectOption('DMY')
    for (const [label, column] of [[text.sr, 'A'], [text.wo, 'B'], [text.status, 'C'], [text.location, 'D'], [text.category, 'E'], [text.event, 'F']]) {
      await working.getByRole('combobox', { name: label, exact: true }).selectOption(column)
    }
    const summary = mapping.getByRole('group', { name: 'Summary', exact: true })
    await summary.getByRole('combobox', { name: text.grain, exact: true }).selectOption('summary')
    await summary.getByLabel(text.header, { exact: true }).fill('1')
    await mapping.getByRole('button', { name: text.save, exact: true }).click()
    await expect(mapping.getByText(text.mapped, { exact: true })).toBeVisible()
    await accessible(page, `mapping ${locale}`)
    await fits(page)
    await page.keyboard.press('Escape')
    await expect(mapping).toBeHidden()

    const calculated = page.waitForResponse(r => new URL(r.url()).pathname === `/api/rmd/packs/${pack.id}/analyses` && r.request().method() === 'POST')
    await page.getByRole('button', { name: text.calculate, exact: true }).click()
    const analysisResponse = await calculated
    expect(analysisResponse.ok()).toBe(true)
    const analysis = await analysisResponse.json() as { id: string; counts_by_grain: Record<string, number>; language: string }
    // Independently known from the tiny synthetic fixture: three physical
    // work-order source rows, one separate summary row. No unique-incident claim.
    expect(analysis.counts_by_grain.mms_work_order).toBe(3)
    expect(analysis.counts_by_grain.summary).toBe(1)
    expect(analysis.language).toBe(locale)
    const kpi = page.locator('.rmd-kpi').filter({ has: page.getByRole('heading', { name: text.kpi, exact: true }) })
    await expect(kpi.locator('.rmd-number')).toHaveText('3')
    await expect(page.getByRole('heading', { name: text.priorities, exact: true })).toBeVisible()
    await accessible(page, `overview ${locale}`)
    // Exercise both actual theme controls; all fixtures here are synthetic.
    for (let theme = 0; theme < 2; theme += 1) {
      await page.getByRole('button', { name: locale === 'ar' ? /التبديل إلى المظهر/ : /Switch to .* theme/ }).click()
      await accessible(page, 'overview ' + locale + ' theme ' + theme)
    }
    await kpi.getByRole('button', { name: text.evidence, exact: true }).click()
    const evidence = page.getByRole('dialog', { name: text.kpi, exact: true })
    const records = evidence.getByRole('table', { name: text.records, exact: true })
    await expect(records.getByRole('cell', { name: 'WO-001', exact: true })).toBeVisible()
    await expect(records.getByRole('cell', { name: 'WO-002', exact: true })).toBeVisible()
    await expect(records.getByRole('cell', { name: 'WO-003', exact: true })).toBeVisible()
    await expect(records.getByRole('row')).toHaveCount(4)
    await accessible(page, `evidence ${locale}`)
    await page.keyboard.press('Escape')

    for (const tab of [text.investigations, text.quality, text.knowledge]) {
      await page.getByRole('tab', { name: tab, exact: true }).click()
      await accessible(page, `${tab} ${locale}`)
      await fits(page)
    }
    await page.getByLabel(text.query, { exact: true }).fill('manager')
    await page.getByRole('button', { name: text.search, exact: true }).click()
    const clauses = page.locator('.rmd-excerpt')
    await expect(clauses.first()).toContainText('five working days')
    await clauses.first().locator('..').getByRole('button', { name: text.evidence, exact: true }).click()
    await expect(page.locator('.rmd-clause')).toContainText('review manager')
    await page.keyboard.press('Escape')

    await page.getByRole('tab', { name: text.quality, exact: true }).click()
    await expect(page.getByRole('heading', { name: text.readiness, exact: true })).toBeVisible()
    await expect(page.locator('.rmd-two-col .rmd-eyebrow').filter({ hasText: text.unavailable })).toHaveCount(6)
    await page.getByRole('tab', { name: text.overview, exact: true }).click()
    const proposed = page.getByRole('button', { name: text.actions, exact: true }).first()
    await proposed.click()
    await expect(page.getByText(text.actionAdded, { exact: true })).toBeVisible()
    const csv = page.waitForEvent('download')
    await page.getByRole('button', { name: text.export, exact: true }).click()
    expect((await csv).suggestedFilename()).toMatch(/\.csv$/)

    // Reload reads the durable analysis and explicitly selected pack again.
    await page.reload()
    await page.getByRole('combobox', { name: text.pack, exact: true }).selectOption(pack.id)
    await expect(kpi.locator('.rmd-number')).toHaveText('3')
    await page.getByRole('button', { name: text.explain, exact: true }).click()
    await expect(page.getByRole('heading', { name: text.assistant, exact: true })).toBeVisible()
    const question = 'Which junction has the most recorded issues in this extract?'
    await page.getByRole('textbox', { name: text.question, exact: true }).fill(question)
    const answered = page.waitForResponse(r => new URL(r.url()).pathname === `/api/rmd/packs/${pack.id}/assistant` && r.request().method() === 'POST')
    await page.getByRole('button', { name: text.ask, exact: true }).click()
    expect((await answered).ok()).toBe(true)
    await expect(page.locator('.rmd-assistant__answer')).not.toBeEmpty()
    await navigate(page, locale, locale === 'ar' ? /^أدلة RMD$/ : /^RMD Evidence$/)
    await page.getByRole('button', { name: text.explain, exact: true }).click()
    await expect(page.getByRole('textbox', { name: text.question, exact: true })).toHaveValue(question)
    await expect(page.locator('.rmd-assistant__answer')).toHaveCount(0)
    await navigate(page, locale, locale === 'ar' ? /^أدلة RMD$/ : /^RMD Evidence$/)

    const previousViewport = page.viewportSize()
    for (const width of [1440, 768, 390, 320]) { await page.setViewportSize({ width, height: 900 }); await fits(page) }
    if (previousViewport) await page.setViewportSize(previousViewport)
    const reviewed = page.waitForResponse(r => new URL(r.url()).pathname === `/api/rmd/packs/${pack.id}/analyses/${analysis.id}/review-run` && r.request().method() === 'POST')
    await page.getByRole('button', { name: text.review, exact: true }).click()
    const reviewResponse = await reviewed
    expect(reviewResponse.ok()).toBe(true)
    const { run_id: runId } = await reviewResponse.json() as { run_id: string }
    const approval = page.getByRole('region', { name: text.approval, exact: true })
    await expect(approval).toBeVisible({ timeout: 40_000 })
    const pending = await request.get(`/api/runs/${runId}`)
    expect(pending.ok()).toBe(true)
    const before = await pending.json() as { state: string; report: { published_path: string | null } }
    expect(before.state).toBe('awaiting_approval'); expect(before.report.published_path).toBeNull()

    // All publication controls are completed with keyboard activation.
    await approval.locator('.decision__preview > summary').focus(); await page.keyboard.press('Enter')
    await expect(approval.getByRole('checkbox', { name: text.read, exact: true })).toBeEnabled()
    await approval.getByRole('checkbox', { name: text.read, exact: true }).focus(); await page.keyboard.press('Space')
    await expect(approval.getByRole('button', { name: text.approve, exact: true })).toBeEnabled()
    await approval.getByRole('button', { name: text.approve, exact: true }).focus(); await page.keyboard.press('Enter')
    let publishedPath = ''
    await expect.poll(async () => {
      const result = await request.get(`/api/runs/${runId}`)
      const run = await result.json() as { state: string; report: { published_path: string | null } }
      publishedPath = run.report?.published_path ?? ''; return run.state
    }, { timeout: 40_000 }).toBe('completed')
    expect(publishedPath).not.toBe('')
    await expect(page.getByText(publishedPath, { exact: false }).first()).toBeVisible()
    await accessible(page, `published report ${locale}`)
    await fits(page)
  })
}
