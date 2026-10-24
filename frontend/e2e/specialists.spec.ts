import { expect, test } from '@playwright/test'
import { createHmac } from 'node:crypto'
import { skipOnboarding } from './helpers'

// Synthetic managed identity and scripted transport, not a live provider test.
// The backend fixture uses actual API creation, worker leases and checkpoints.
const BASE = 'http://127.0.0.1:8126'
const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
const claims = Buffer.from(JSON.stringify({ sub: 'synthetic-browser-owner', agentic_os_role: 'owner',
  exp: 2792691043, aud: 'authenticated', iss: 'https://test.supabase.invalid/auth/v1',
})).toString('base64url')
const signed = `${header}.${claims}`
const TOKEN = `${signed}.${createHmac('sha256', 'synthetic-browser-test-only-not-a-real-key').update(signed).digest('base64url')}`

for (const locale of ['en', 'ar'] as const) {
  test(`synthetic specialist evidence is inspectable before human approval (${locale})`, async ({ page, request }) => {
    const headers = { Authorization: `Bearer ${TOKEN}` }
    const list = await request.get(`${BASE}/api/runs`, { headers })
    expect(list.ok()).toBeTruthy()
    const run = (await list.json()).runs.find((item: { goal: string }) => item.goal.endsWith(` ${locale}`))
    expect(run).toBeTruthy()
    const response = await request.get(`${BASE}/api/runs/${run.id}`, { headers })
    const detail = await response.json()
    expect(detail.state).toBe('awaiting_approval')
    expect(detail.report.published_path).toBeNull()
    const analyst = detail.tasks.find((task: { role: string }) => task.role === 'analysis_investigator')
    const verifier = detail.tasks.find((task: { role: string }) => task.role === 'evidence_verifier')
    expect(analyst.claims.length).toBeGreaterThan(0)
    expect(verifier.quality_checks[0].passed).toBe(true)
    await skipOnboarding(page)
    await page.addInitScript(({ token, language }) => {
      localStorage.setItem('aos-token', token)
      localStorage.setItem('aos-locale', language)
    }, { token: TOKEN, language: locale })
    await page.route('https://test.supabase.invalid/**', (route) => route.abort())
    await page.goto(`${BASE}/#/runs/${run.id}`)
    // Standalone reports must have a keyboard-accessible initial selected tab.
    const selected = page.locator('.reporttabs [role="tab"][aria-selected="true"]')
    await expect(selected).toHaveCount(1)
    await expect(selected).toHaveAttribute('tabindex', '0')
    await expect(page.getByRole('tabpanel').first()).toBeVisible()
    const disclosure = page.locator('.run-timeline__disclosure')
    if (!(await disclosure.evaluate((node) => (node as HTMLDetailsElement).open))) {
      await disclosure.locator(':scope > summary').click()
    }
    await page.locator('.runtask').filter({ hasText: analyst.title }).locator('.evidence-link').click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog).toContainText(analyst.claims[0].text)
    await expect(dialog.locator('table')).toContainText('c_mean')
    await expect(dialog.locator('table')).toContainText('20')
    await page.keyboard.press('Escape')
    await page.locator('.runtask').filter({ hasText: verifier.title }).locator('.evidence-link').click()
    await expect(page.getByRole('dialog')).toContainText('independent_evidence_replay')
    await expect(page.getByRole('dialog')).toContainText(locale === 'ar' ? 'ليست موافقة نشر بشرية' : 'not human publication approval')
    await page.keyboard.press('Escape')
    const after = await request.get(`${BASE}/api/runs/${run.id}`, { headers })
    expect((await after.json()).state).toBe('awaiting_approval')
  })
}
