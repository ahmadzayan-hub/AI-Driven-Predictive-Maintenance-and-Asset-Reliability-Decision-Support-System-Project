import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { composerInput, lastAgentBubble, sendMessage } from './helpers'

/** The composer's textbox, by its Arabic label. */
function arabicComposer(page: Page) {
  return page.getByRole('textbox', { name: 'الرسالة' })
}

async function sendArabic(page: Page, text: string) {
  const input = arabicComposer(page)
  await input.click()
  await input.fill(text)
  await input.press('Enter')
}

// The interface in Arabic: right-to-left, every label translated, the
// agent answering in Arabic, and the same accessibility bar as English.
// The locale is stamped before the page loads, the way a returning
// reader's browser would have it.

async function useArabic(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('aos-locale', 'ar')
    localStorage.setItem('aos-onboarded', '1')
  })
}

/** Open a tab by its Arabic name, through the drawer on mobile. */
async function openArabicTab(page: Page, name: RegExp) {
  const menu = page.getByRole('button', { name: 'فتح قائمة التنقل' })
  const target = page.getByRole('button', { name }).filter({ visible: true })
  await menu.or(target.first()).first().waitFor()
  if (await menu.isVisible()) await menu.click()
  await target.first().click()
}

async function expectNoViolations(page: Page, context: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(
    results.violations,
    `${context}: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(', ')}`,
  ).toEqual([])
}

async function horizontalOverflow(page: Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
}

test.describe('Arabic interface', () => {
  test.use({ contextOptions: { reducedMotion: 'reduce' } })

  test.beforeEach(async ({ page }) => {
    await useArabic(page)
  })

  test('renders right-to-left with the agent replying in Arabic', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text())
    })
    page.on('pageerror', (error) => consoleErrors.push(String(error)))

    await page.goto('/')
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    await expect(page.locator('html')).toHaveAttribute('lang', 'ar')
    await expect(page.getByRole('status').filter({ hasText: 'جاهز' })).toBeVisible()

    // The session was created with the interface language, so the
    // welcome message needed no second request to be in Arabic.
    await expect(page.getByRole('heading', { name: 'لكل أصل، قرار أوضح.' })).toBeVisible()

    await sendArabic(page, 'مرحبا')
    await expect(lastAgentBubble(page)).toContainText('يسعدني المساعدة')

    // A slash command still works; its confirmation is Arabic.
    await sendArabic(page, '/remember لغتي المفضلة هي العربية')
    await expect(lastAgentBubble(page)).toHaveText('تم حفظ المعلومة.')

    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0)
    expect(consoleErrors).toEqual([])
  })

  test('every view is translated and passes WCAG 2.2 AA', async ({ page }, testInfo) => {
    // This full-language journey audits each view, completes a pipeline and
    // cleans up memory. Preserve those checks beyond the default test budget.
    test.setTimeout(120_000)
    const memoryText = `قهوة في الثامنة — ${testInfo.project.name}`
    await page.goto('/')
    await sendArabic(page, 'مرحبا')
    await lastAgentBubble(page).waitFor()
    await expectNoViolations(page, 'chat view (ar)')

    await openArabicTab(page, /^الذاكرة/)
    await expect(page.getByRole('heading', { name: 'الذاكرة المحفوظة' })).toBeVisible()
    await page.getByLabel('معلومة لحفظها').fill(memoryText)
    await page.getByRole('button', { name: 'إضافة إلى الذاكرة' }).click()
    await expect(page.getByText(memoryText, { exact: true })).toBeVisible()
    await expectNoViolations(page, 'memory view (ar)')

    await openArabicTab(page, /^التفضيلات/)
    await expect(page.getByRole('heading', { name: 'تفضيلات الرد' })).toBeVisible()
    await expectNoViolations(page, 'preferences view (ar)')

    await openArabicTab(page, /^النشاط/)
    await expect(page.getByRole('heading', { name: 'النشاط', exact: true })).toBeVisible()
    await expectNoViolations(page, 'activity view (ar)')

    await openArabicTab(page, /^التحليلات/)
    await expect(page.getByRole('heading', { name: 'عمليات التحليل' })).toBeVisible()
    await expect(page.getByLabel('لغة التقرير', { exact: true })).toHaveValue('ar')
    await expectNoViolations(page, 'runs view (ar)')
    await page.getByRole('button', { name: 'بدء التحليل' }).click()
    await expect(page.getByRole('region', { name: 'موافقة مطلوبة' })).toBeVisible({
      timeout: 40_000,
    })
    // A run started in Arabic writes its reports in Arabic (ADR 0022), and
    // the blocks say so, so a screen reader and the bidi algorithm read
    // them as Arabic rather than as English.
    const sectionReport = page.getByRole('tabpanel').locator('.runreport.report-document')
    await expect(sectionReport).toHaveAttribute('lang', 'ar')
    await expect(sectionReport).toHaveAttribute('dir', 'rtl')
    await expect(sectionReport.getByRole('heading', { name: 'التحليل الوصفي: ماذا حدث؟', exact: true })).toBeVisible()
    const fullReport = page.locator('.runreport--full.report-document')
    await expect(fullReport).toHaveAttribute('lang', 'ar')
    await expect(fullReport).toHaveAttribute('dir', 'rtl')
    await expect(fullReport.getByRole('heading', { name: 'تقرير تحليل الأعمال: بيانات مبيعات تجريبية', exact: true })).toBeVisible()
    await expect(fullReport.getByRole('heading', { name: 'الملخص التنفيذي', exact: true })).toBeVisible()
    const metrics = fullReport.getByRole('table', { name: 'المؤشرات الرئيسية', exact: true })
    await expect(metrics.getByRole('columnheader')).toHaveText(['المؤشر', 'القيمة', 'الطريقة'])
    await expect(metrics.getByRole('cell', { name: 'إجمالي الإيرادات', exact: true })).toBeVisible()
    // Identifiers and calculated values remain the evidence record's exact text.
    const forecast = metrics.getByRole('row').filter({ has: page.getByRole('cell', { name: 'التوقع للفترة 2026-01', exact: true }) })
    await expect(forecast.getByRole('cell', { name: '361505.45', exact: true })).toBeVisible()
    await expect(fullReport.locator('pre')).toHaveCount(0)
    await expect(fullReport).not.toContainText('# تقرير تحليل الأعمال')
    await expect(fullReport).not.toContainText('| المؤشر | القيمة | الطريقة |')
    await expect(fullReport).not.toContainText('**الهدف:**')
    await expect(fullReport).toContainText('تطابق الأرقام بين اللغتين')
    const unusual = metrics.getByRole('row').filter({ has: page.getByRole('cell', { name: 'الصفوف غير المعتادة', exact: true }) })
    await expect(unusual.getByRole('cell')).toHaveCount(3)
    await expect(unusual).toContainText('|القيمة - المتوسط|')
    const regionChart = page.getByRole('figure').filter({
      has: page.getByText('إجمالي الإيرادات حسب المنطقة', { exact: true }),
    })
    await expect(regionChart.getByRole('img', { name: 'مخطط أعمدة لإجمالي الإيرادات لكل المنطقة، من الأكبر إلى الأصغر.', exact: true })).toBeVisible()
    await expect(regionChart.locator('svg text').filter({ hasText: /^الشمال$/ })).toBeVisible()
    await expect(regionChart.locator('svg text').filter({ hasText: /^الجنوب$/ })).toBeVisible()
    await regionChart.getByText('اعرض الأرقام', { exact: true }).click()
    const regionData = regionChart.getByRole('table')
    await expect(regionData.getByRole('columnheader')).toHaveText(['العنصر', 'القيمة'])
    await expect(regionData.getByRole('rowheader', { name: 'الشمال', exact: true })).toBeVisible()
    await expect(regionData.getByRole('rowheader', { name: 'الجنوب', exact: true })).toBeVisible()
    await expectNoViolations(page, 'runs view with approval, charts and reports (ar)')
    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0)

    await page.keyboard.press('ControlOrMeta+k')
    await page.getByRole('dialog', { name: 'لوحة الأوامر' }).waitFor()
    await expectNoViolations(page, 'command palette (ar)')
    await page.keyboard.press('Escape')

    // Reset shared memory for the other specs.
    await openArabicTab(page, /^الذاكرة/)
    await page.getByRole('button', { name: /حذف كل الذاكرة/ }).click()
    const confirm = page.getByRole('dialog', { name: 'هل تريد حذف كل الذاكرة؟' })
    await confirm.getByRole('button', { name: 'حذف كل الذاكرة' }).click()
    await expect(page.getByText('لا يوجد شيء محفوظ بعد', { exact: false })).toBeVisible()
  })

  test('switching language from the header changes the interface and the agent together', async ({
    page,
  }) => {
    await page.goto('/')
    await expect(arabicComposer(page)).toBeVisible()

    // The control is labelled in the other language, so it is findable
    // by someone who cannot read the current one.
    await page.getByRole('button', { name: 'تغيير اللغة' }).click()
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
    await expect(page.getByRole('status').filter({ hasText: 'Ready' })).toBeVisible()
    await expect(composerInput(page)).toBeVisible()

    // The agent was told: its next reply is English.
    await sendMessage(page, 'hello')
    await expect(lastAgentBubble(page)).toContainText('Happy to help')

    // And back, from the English side.
    await page.getByRole('button', { name: 'Change language' }).click()
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    await sendArabic(page, 'مرحبا')
    await expect(lastAgentBubble(page)).toContainText('يسعدني المساعدة')

    // The choice survives a reload with no left-to-right flash: the
    // direction is already right-to-left on the first paint.
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    await expect(page.getByRole('status').filter({ hasText: 'جاهز' })).toBeVisible()
  })

  test('the first-run dialog is Arabic and accessible', async ({ page }) => {
    await page.addInitScript(() => localStorage.removeItem('aos-onboarded'))
    await page.goto('/')
    const dialog = page.getByRole('dialog', { name: 'مرحبًا بك في موثوقية الأصول' })
    await dialog.waitFor()
    await expectNoViolations(page, 'onboarding dialog (ar)')
    await dialog.getByRole('button', { name: 'ابدأ الآن' }).click()
    await expect(dialog).toBeHidden()
  })
})
