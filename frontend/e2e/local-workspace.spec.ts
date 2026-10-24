import { expect, test } from '@playwright/test'
import { skipOnboarding } from './helpers'

// A separate explicit profile, not the legacy no-config server or public demo.
test.use({ baseURL: 'http://127.0.0.1:8127' })

for (const language of ['en', 'ar'] as const) {
  test(`explicit local owner completes real ${language} intake without a login`, async ({ page }, info) => {
    test.setTimeout(75_000)
    await skipOnboarding(page)
    await page.addInitScript((locale) => localStorage.setItem('aos-locale', locale), language)
    await page.goto('/#/runs?source=upload')
    const identity = await (await page.request.get('/api/identity')).json()
    expect(identity.mode).toBe('local')
    expect(identity.principal.subject).toBe('local-owner')
    expect(identity.principal.permissions).not.toContain('admin')
    expect(await (await page.request.get('/api/auth/config')).json()).toEqual({ mode: 'local', flows: [] })
    const health = await (await page.request.get('/api/health')).json()
    expect(health.model_provider).toMatchObject({ provider: 'deterministic', configured: false, local_only: true })
    const name = `local-${language}-${info.project.name}.csv`
    const uploaded = page.waitForResponse((response) => response.url().includes('/api/datasets?') && response.request().method() === 'POST')
    await page.locator('#run-file').setInputFiles({
      name, mimeType: 'text/csv', buffer: Buffer.from(`month,team,sales\n2026-07,${language}-${info.project.name},110\n2026-08,B,220\n2026-09,A,330\n`),
    })
    expect((await uploaded).status()).toBe(201)
    const created = page.waitForResponse((response) => response.url().endsWith('/api/runs') && response.request().method() === 'POST')
    await page.getByRole('button', { name: language === 'ar' ? 'بدء التحليل' : 'Start run', exact: true }).click()
    const run = await (await created).json()
    await expect(page.getByRole('region', { name: language === 'ar' ? 'موافقة مطلوبة' : 'Approval required', exact: true })).toBeVisible({ timeout: 45_000 })
    await expect(page.locator('.runreport--full')).toContainText(name)
    await expect(page.locator('.runreport--full')).toContainText('660')
    const detail = await (await page.request.get(`/api/runs/${run.id}`)).json()
    expect(detail.state).toBe('awaiting_approval')
    expect(detail.report.published_path).toBeNull()
    expect(detail.report_language).toBe(language)
    const after = await (await page.request.get('/api/health')).json()
    expect(after.model_calls).toMatchObject({ entries_kept: 0, providers: {} })
    // Reload is not a server restart; restart/backup restoration has Python coverage.
    await page.reload()
    await expect(page.locator('.runreport--full')).toContainText(name, { timeout: 15_000 })
    await expect(page.locator('.runreport--full')).toContainText('660')
    await page.screenshot({ path: info.outputPath(`local-owner-${language}.png`), fullPage: true })
  })
}

test('explicit local owner rejects hostile HTTP origins and forwarding headers', async ({ request }) => {
  const cases: Array<Record<string, string>> = [
    { Origin: 'https://attacker.invalid' },
    { Origin: 'http://127.0.0.1:8123' },
    { Host: 'localhost.attacker.invalid' },
    { 'X-Forwarded-For': '127.0.0.1' },
    { Forwarded: 'for=127.0.0.1' },
  ]
  for (const headers of cases) {
    const response = await request.post('/api/sessions', { headers })
    expect(response.status()).toBe(403)
  }
})
