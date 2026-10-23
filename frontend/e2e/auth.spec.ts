import { expect, test } from '@playwright/test'
import { composerInput, skipOnboarding } from './helpers'

// A second server instance with managed auth enabled, so the sign-in
// wall and authenticated operation are both exercised for real. The
// token is minted with the same secret the server verifies against,
// standing in for a completed provider round-trip (the provider itself
// is external and is not called by these tests).
const AUTH_PORT = 8124
const AUTH_BASE = `http://127.0.0.1:${AUTH_PORT}`

// HS256 JWT — {"sub":"e2e-user","agentic_os_role":"analyst","aud":"authenticated",
// "iss":"https://example.supabase.co/auth/v1"} signed with the test-only secret
// the auth server verifies against (audience and issuer are required, finding B7). Minted by
// server/auth.py's helper; not a credential for any real system.
const TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  'eyJzdWIiOiJlMmUtdXNlciIsImV4cCI6Mjc5MjY5MTA0MywiYWdlbnRpY19vc19yb2xlIjoiYW5hbHlzdCIsImF1ZCI6ImF1dGhlbnRpY2F0ZWQiLCJpc3MiOiJodHRwczovL2V4YW1wbGUuc3VwYWJhc2UuY28vYXV0aC92MSJ9.' +
  'RNyXg3ACSP23KpieEeYMf3Lqo2eECjse8OzSJ2D6Jvg'

test.describe('managed authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Synthetic provider boundary: these tests never send email or contact OAuth.
    await page.route('https://example.supabase.co/auth/v1/**', (route) => {
      if (new URL(route.request().url()).pathname.endsWith('/settings')) return route.fulfill({
        json: { external: { email: true, google: false, apple: false }, disable_signup: false },
      })
      return route.abort()
    })
  })
  test.skip(
    ({ baseURL }) => baseURL === AUTH_BASE,
    'runs against the dedicated auth server only',
  )

  test('unauthenticated visitors get the sign-in wall', async ({ page }) => {
    await skipOnboarding(page)
    await page.goto(AUTH_BASE)

    const signIn = page.getByRole('main', { name: 'Sign in' })
    await expect(signIn).toBeVisible()
    await expect(signIn).toContainText('this app never sees them')
    // The workspace must not be reachable without credentials.
    await expect(page.getByRole('textbox', { name: 'Message' })).toHaveCount(0)
  })

  test('the sign-in form is keyboard operable and labelled', async ({ page }) => {
    await skipOnboarding(page)
    await page.goto(AUTH_BASE)
    await page.getByLabel('Email').focus()
    await page.keyboard.type('analyst@example.com')
    await page.keyboard.press('Tab')
    await expect(page.getByLabel('Password')).toBeFocused()
  })

  /** The identity chip lives in the sidebar, which is a drawer on mobile. */
  async function revealIdentity(page: import('@playwright/test').Page) {
    const menu = page.getByRole('button', { name: 'Open navigation' })
    if (await menu.isVisible()) await menu.click()
  }

  test('a valid token unlocks the workspace and shows the role', async ({ page }) => {
    await skipOnboarding(page)
    await page.addInitScript((token) => {
      localStorage.setItem('aos-token', token)
    }, TOKEN)
    // A signed-in reader lands where the address says (finding U12).
    await page.goto(`${AUTH_BASE}/#/assistant`)

    await expect(composerInput(page)).toBeVisible()
    // The signed-in principal and its role come from the server.
    await revealIdentity(page)
    await expect(page.locator('.sidebar__meta').first()).toContainText('analyst')
  })

  test('signing out clears the session and returns to the wall', async ({ page }) => {
    await skipOnboarding(page)
    await page.addInitScript((token) => {
      localStorage.setItem('aos-token', token)
    }, TOKEN)
    await page.goto(`${AUTH_BASE}/#/assistant`)
    await expect(composerInput(page)).toBeVisible()

    await revealIdentity(page)
    await page.getByRole('button', { name: 'Sign out' }).first().click()

    await expect(page.getByRole('main', { name: 'Sign in' })).toBeVisible()
    const stored = await page.evaluate(() => localStorage.getItem('aos-token'))
    expect(stored).toBeNull()
  })

  test('an invalid token is rejected and never unlocks the workspace', async ({ page }) => {
    await skipOnboarding(page)
    await page.addInitScript(() => {
      localStorage.setItem('aos-token', 'forged.token.value')
    })
    await page.goto(AUTH_BASE)

    await expect(page.getByRole('main', { name: 'Sign in' })).toBeVisible()
    const stored = await page.evaluate(() => localStorage.getItem('aos-token'))
    expect(stored).toBeNull()
  })
})


test.describe('managed PKCE onboarding', () => {
  async function prepare(page: import('@playwright/test').Page) {
    await skipOnboarding(page)
    await page.route(`${AUTH_BASE}/api/auth/config`, (route) => route.fulfill({ json: {
      mode: 'jwt', provider: 'supabase', provider_url: 'https://example.supabase.co',
      publishable_key: 'synthetic-public-key', flows: ['password', 'pkce'], redirect_url: `${AUTH_BASE}/auth/callback`,
    } }))
    await page.route('https://example.supabase.co/auth/v1/**', (route) => {
      const path = new URL(route.request().url()).pathname
      if (path.endsWith('/settings')) return route.fulfill({ json: {
        external: { email: true, google: false, apple: false }, disable_signup: false,
      } })
      if (path.endsWith('/otp')) return route.fulfill({ json: {} })
      return route.abort()
    })
    await page.goto(AUTH_BASE)
  }

  test('email registration stays pending until PKCE exchange and real API identity verification', async ({ page }) => {
    await prepare(page)
    await page.getByLabel('Email').fill('synthetic@example.invalid')
    const request = page.waitForRequest('https://example.supabase.co/auth/v1/otp?**')
    await page.getByRole('button', { name: 'Create account by email' }).click()
    const sent = await request
    expect(sent.postDataJSON()).toMatchObject({ create_user: true, code_challenge_method: 's256' })
    await expect(page.getByText(/You are not signed in yet/)).toBeVisible()
    expect(await page.evaluate(() => localStorage.getItem('aos-token'))).toBeNull()
    const pending = await page.evaluate(() => JSON.parse(localStorage.getItem('aos-auth-request')!))
    let exchanges = 0
    await page.route('https://example.supabase.co/auth/v1/token?grant_type=pkce', (route) => {
      exchanges += 1
      expect(route.request().postDataJSON()).toEqual({ auth_code: 'synthetic-one-use', code_verifier: pending.verifier })
      return route.fulfill({ json: { access_token: TOKEN } })
    })
    await page.goto(`${AUTH_BASE}/auth/callback?code=synthetic-one-use`)
    await expect(page.getByRole('main', { name: 'Sign in' })).toHaveCount(0)
    await expect.poll(() => page.evaluate(() => localStorage.getItem('aos-token'))).toBe(TOKEN)
    expect(exchanges).toBe(1)
    expect(new URL(page.url()).search).toBe('')
    expect(await page.evaluate(() => localStorage.getItem('aos-auth-request'))).toBeNull()
    // This request hits the real test API, not a mocked identity endpoint.
    await page.goto(`${AUTH_BASE}/#/assistant`)
    await expect(composerInput(page)).toBeVisible()
  })

  test('an exchanged but forged token never unlocks the workspace', async ({ page }) => {
    await prepare(page)
    await page.getByLabel('Email').fill('synthetic@example.invalid')
    await page.getByRole('button', { name: 'Sign in by email link' }).click()
    await expect(page.getByText(/You are not signed in yet/)).toBeVisible()
    await page.route('https://example.supabase.co/auth/v1/token?grant_type=pkce', (route) => route.fulfill({ json: { access_token: 'forged.token.value' } }))
    await page.goto(`${AUTH_BASE}/auth/callback?code=synthetic`)
    await expect(page.getByRole('main', { name: 'Sign in' })).toBeVisible()
    await expect.poll(() => page.evaluate(() => localStorage.getItem('aos-token'))).toBeNull()
    await expect(composerInput(page)).toHaveCount(0)
    await expect(page.locator('.statusline--error')).toContainText(/token|credentials|authentication/i)
  })

  test('cancelled callbacks are consumed without an exchange or implicit-token acceptance', async ({ page }) => {
    await prepare(page)
    let exchanges = 0
    await page.route('https://example.supabase.co/auth/v1/token?**', (route) => { exchanges += 1; return route.abort() })
    await page.goto(`${AUTH_BASE}/auth/callback?error=access_denied#access_token=untrusted`)
    await expect(page.getByText(/cancelled, expired, already used/)).toBeVisible()
    expect(exchanges).toBe(0)
    expect(new URL(page.url()).search).toBe(''); expect(new URL(page.url()).hash).toBe('')
    expect(await page.evaluate(() => localStorage.getItem('aos-token'))).toBeNull()
  })

  test('disabled social providers do not show fake login buttons', async ({ page }) => {
    await prepare(page)
    await expect(page.getByText('Google and Apple sign-in are not enabled for this project.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Continue with Google' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Continue with Apple' })).toHaveCount(0)
  })
})
