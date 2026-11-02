import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function open(page: Page, ar = false) {
  await page.addInitScript(() => { localStorage.setItem('aos-theme', 'light') })
  await page.goto('/?workspace=jarvis')
  if (ar) await page.getByRole('button', { name: 'العربية', exact: true }).click()
  await page.getByRole('button', { name: ar ? 'فتح مساحة العرض الاصطناعي' : 'Open synthetic workspace' }).click()
  await page.locator('summary').first().click()
  await page.getByRole('button', { name: ar ? 'عرض تقاريري' : 'Show my reports' }).click()
  const option = page.locator('select option').filter({ hasText: 'SYNTHETIC_RTA_review.csv' })
  await page.locator('select').selectOption(await option.getAttribute('value') as string)
  await page.getByRole('button', { name: ar ? 'استخدام هذا التقرير' : 'Use this report' }).click()
}
for (const ar of [false, true]) test(`grounded question, follow-up, review and missing data ${ar ? 'Arabic' : 'English'}`, async ({ page }) => {
  await open(page, ar)
  const ask = page.getByRole('button', { name: ar ? 'احسب من التقرير المحدد' : 'Calculate from selected report' })
  await page.getByRole('button', { name: ar ? 'ما إجمالي تكلفة الصيانة؟' : 'What is total maintenance cost?' }).click()
  await ask.click()
  await expect(page.locator('.jarvis__evidence')).toContainText('500')
  await expect(page.locator('.jarvis__evidence')).toContainText('SHA-256')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: ar ? 'تأكيد المراجعة المحلية' : 'Confirm local review' }).click()
  await expect(page.locator('.jarvis__card').last()).toContainText(ar ? 'لم يُنشأ اعتماد' : 'No approval, publication')
  await page.screenshot({ path: `../docs/screenshots/jarvis-${ar ? 'ar' : 'en'}-evidence.png` })
  await page.getByRole('heading', { name: 'Jarvis OS', exact: true }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: `../docs/screenshots/jarvis-${ar ? 'ar' : 'en'}.png` })
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
  await page.getByRole('button', { name: ar ? 'ما هو التوافر؟' : 'What is availability?' }).click()
  await expect(page.locator('.jarvis__evidence')).toHaveCount(0)
  await ask.click(); await expect(page.locator('.jarvis__evidence')).toContainText('94')
  await page.getByRole('button', { name: ar ? 'توقع الأعطال غداً' : 'Predict failures tomorrow' }).click()
  await ask.click(); await expect(page.getByRole('checkbox')).toHaveCount(0)
  const sparse = page.locator('select option').filter({ hasText: 'SYNTHETIC_missing_hours.csv' })
  await page.locator('select').selectOption(await sparse.getAttribute('value') as string)
  await page.getByRole('button', { name: ar ? 'استخدام هذا التقرير' : 'Use this report' }).click()
  await page.getByRole('button', { name: ar ? 'ما هو التوافر؟' : 'What is availability?' }).click()
  await ask.click(); await expect(page.locator('.jarvis__evidence')).toContainText(ar ? 'غير' : 'undefined')
  await page.setViewportSize({ width: 375, height: 812 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: `../docs/screenshots/jarvis-${ar ? 'ar' : 'en'}-phone.png`, fullPage: true })
})
test('interrupt, repeated clicks and unavailable service never keep stale evidence', async ({ page }) => {
  await open(page)
  let count = 0
  await page.route('**/data-query', async route => { count++; await new Promise(r => setTimeout(r, 700)); await route.abort() })
  await page.getByRole('button', { name: 'What is total maintenance cost?' }).click()
  const ask = page.getByRole('button', { name: 'Calculate from selected report' })
  await ask.click(); await expect(ask).toBeDisabled()
  await page.getByRole('button', { name: 'Stop / interrupt' }).click()
  await expect(page.getByText(/Request interrupted/)).toBeVisible()
  await expect(page.locator('.jarvis__evidence')).toHaveCount(0)
  await page.unrouteAll({ behavior: 'wait' })
  await page.context().setOffline(true)
  await ask.click(); await expect(page.getByRole('alert')).toContainText('No answer was confirmed')
  expect(count).toBeLessThanOrEqual(1)
})
test('another tab changing filters rejects the old scope until refreshed', async ({ page, context }) => {
  const selectedResponse = page.waitForResponse(r => r.url().endsWith('/data-context') && r.request().method() === 'PUT')
  await open(page)
  const selected = await selectedResponse
  const scope = (await selected.json()).data_context
  const other = await context.newPage()
  await other.goto('/?workspace=jarvis')
  const status = await other.evaluate(async ({ url, run }) => (await fetch(url, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: run, filters: [{ column: 'Record_ID', op: 'in', values: ['SYN-03'] }] }),
  })).status, { url: selected.url(), run: scope.run_id })
  expect(status).toBe(200)
  await other.close()
  await page.getByRole('button', { name: 'What is total maintenance cost?' }).click()
  const stale = page.waitForResponse(r => r.url().endsWith('/data-query'))
  await page.getByRole('button', { name: 'Calculate from selected report' }).click()
  expect((await stale).status()).toBe(409)
  await expect(page.getByRole('alert')).toContainText('context changed')
  await expect(page.locator('.jarvis__evidence')).toHaveCount(0)
  await page.getByRole('button', { name: 'Show my reports' }).click()
  await expect(page.locator('.tool-cards')).toContainText('SYN-03')
  await page.getByRole('button', { name: 'What is total maintenance cost?' }).click()
  await page.getByRole('button', { name: 'Calculate from selected report' }).click()
  await expect(page.locator('.jarvis__evidence')).toContainText('Maintenance cost: 80')
})

test('microphone needs consent; denied permission retains text input', async ({ page }) => {
  await page.addInitScript(() => {
    class DeniedRecognition {
      onerror?: (e: { error: string }) => void
      start() { this.onerror?.({ error: 'not-allowed' }) }
      stop() {}
    }
    Object.defineProperty(window, 'SpeechRecognition', { value: DeniedRecognition })
  })
  await open(page)
  await page.getByRole('button', { name: 'Enable audio controls' }).click()
  await page.locator('.voice-capture__button').click()
  await expect(page.locator('.voice-console__consent')).toBeVisible()
  await page.locator('.voice-console__consent .btn--primary').click()
  await expect(page.locator('.voice-console')).toContainText(/denied|blocked/i)
  await expect(page.getByRole('textbox')).toBeEnabled()
  await page.getByRole('button', { name: 'Mute audio' }).click()
  await expect(page.locator('.voice-console')).toHaveCount(0)
})
