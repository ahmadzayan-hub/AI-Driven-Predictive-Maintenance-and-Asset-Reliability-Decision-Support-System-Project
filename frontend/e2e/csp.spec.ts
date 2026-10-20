import { expect, test } from '@playwright/test'
import { composerInput, skipOnboarding } from './helpers'

const AUTH_BASE = 'http://127.0.0.1:8124'
// The successful mocked provider response uses the established, synthetic
// auth.spec token. No real identity provider or credentials are contacted.
const TEST_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  'eyJzdWIiOiJlMmUtdXNlciIsImV4cCI6Mjc4NjQwMTcwMywiYWdlbnRpY19vc19yb2xlIjoiYW5hbHlzdCJ9.' +
  'J_dVri2xv87fsz8tl31lIpFa9mlPuStl3HBUnpMuFr0'

test('CSP preserves prepaint preferences and blocks injected inline scripts', async ({ page }) => {
  await skipOnboarding(page)
  await page.addInitScript(() => {
    localStorage.setItem('aos-theme', 'light')
    localStorage.setItem('aos-motion', 'reduce')
    localStorage.setItem('aos-locale', 'ar')
    const observed: string[] = []
    Object.assign(window, { cspObserved: observed, cspInjected: false })
    document.addEventListener('securitypolicyviolation', (event) => observed.push(event.effectiveDirective))
  })
  const response = await page.goto('/')
  expect(response?.headers()['content-security-policy']).toContain("script-src 'self' 'sha256-")
  await expect(page.locator('.composer textarea')).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await expect(page.locator('html')).toHaveAttribute('data-motion', 'reduce')
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar')
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await page.evaluate(() => document.fonts.ready)
  expect(await page.evaluate(() => (window as unknown as { cspObserved: string[] }).cspObserved)).toEqual([])
  await page.evaluate(() => {
    const script = document.createElement('script')
    script.textContent = 'window.cspInjected = true'
    document.head.append(script)
  })
  await expect.poll(() => page.evaluate(() => (window as unknown as { cspObserved: string[] }).cspObserved)).toContain('script-src-elem')
  expect(await page.evaluate(() => (window as unknown as { cspInjected: boolean }).cspInjected)).toBe(false)
})

test('CSP allows the configured managed sign-in endpoint', async ({ page }) => {
  await skipOnboarding(page)
  let providerCalled = false
  await page.route('https://example.supabase.co/auth/v1/token?grant_type=password', async (route) => {
    providerCalled = true
    await route.fulfill({ status: 200, contentType: 'application/json',
      headers: { 'access-control-allow-origin': '*' },
      body: JSON.stringify({ access_token: TEST_TOKEN, token_type: 'bearer' }) })
  })
  await page.goto(AUTH_BASE)
  await page.getByLabel('Email').fill('synthetic.user@example.invalid')
  await page.getByLabel('Password', { exact: true }).fill('synthetic-password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(composerInput(page)).toBeVisible()
  expect(providerCalled).toBe(true)
})

test('CSP allows the service worker, blob audio and generated downloads', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/')
  await expect(composerInput(page)).toBeVisible()
  const workerUrl = await page.evaluate(async () => (await navigator.serviceWorker.ready).active?.scriptURL)
  expect(workerUrl).toMatch(/\/sw\.js$/)
  const ready = await page.evaluate(async () => {
    const bytes = new ArrayBuffer(44 + 1600)
    const view = new DataView(bytes)
    const word = (offset: number, value: string) => { for (let i = 0; i < value.length; i += 1) view.setUint8(offset + i, value.charCodeAt(i)) }
    word(0, 'RIFF'); view.setUint32(4, 1636, true); word(8, 'WAVE'); word(12, 'fmt ')
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true)
    view.setUint32(24, 8000, true); view.setUint32(28, 16000, true); view.setUint16(32, 2, true)
    view.setUint16(34, 16, true); word(36, 'data'); view.setUint32(40, 1600, true)
    const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
    const audio = document.createElement('audio')
    try {
      const loaded = new Promise<number>((resolve, reject) => {
        audio.onloadedmetadata = () => resolve(audio.readyState)
        audio.onerror = () => reject(new Error('Blob audio did not load'))
      })
      audio.src = url; audio.load()
      return await loaded
    } finally { audio.remove(); URL.revokeObjectURL(url) }
  })
  expect(ready).toBeGreaterThanOrEqual(1)
  const download = page.waitForEvent('download')
  await page.evaluate(() => {
    const url = URL.createObjectURL(new Blob(['group,value\nSynthetic,1\n'], { type: 'text/csv' }))
    const link = document.createElement('a')
    link.href = url; link.download = 'synthetic-csp.csv'; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  })
  expect((await download).suggestedFilename()).toBe('synthetic-csp.csv')
})
