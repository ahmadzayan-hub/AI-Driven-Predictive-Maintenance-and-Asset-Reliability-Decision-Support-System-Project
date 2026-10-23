import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { webcrypto } from 'node:crypto'
import { SignIn } from '../features/auth/SignIn'
import type { AuthConfig } from '../shared/types'
const CONFIG: AuthConfig = { mode: 'jwt', provider: 'supabase', provider_url: 'https://example.supabase.co', publishable_key: 'sb_publishable_testing_only', flows: ['password', 'pkce'], redirect_url: `${window.location.origin}/auth/callback` }
const AVAILABLE = { external: { email: true, google: false, apple: false }, disable_signup: false }
function mockFetch(body: unknown = { access_token: 'token-123' }, ok = true, settings = AVAILABLE) {
 const fn = vi.fn().mockImplementation(async (url: string) => ({ ok: url.endsWith('/settings') || ok, status: url.endsWith('/settings') || ok ? 200 : 400, json: async () => url.endsWith('/settings') ? settings : body }))
 vi.stubGlobal('fetch', fn); return fn
}
beforeEach(() => { localStorage.clear(); window.history.replaceState(null, '', '/'); vi.stubGlobal('crypto', webcrypto) })
afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); window.history.replaceState(null, '', '/') })
describe('managed SignIn', () => {
 it('sends passwords only to the provider and awaits server verification', async () => {
  const fetch = mockFetch(), onSignedIn = vi.fn().mockResolvedValue(undefined), user = userEvent.setup()
  render(<SignIn config={CONFIG} onSignedIn={onSignedIn} />)
  await user.type(screen.getByLabelText('Email'), 'analyst@example.com'); await user.type(screen.getByLabelText('Password'), 'correct horse battery'); await user.click(screen.getByRole('button', { name: 'Sign in' }))
  await waitFor(() => expect(onSignedIn).toHaveBeenCalledWith('token-123'))
  const [url, init] = fetch.mock.calls.find(([url]) => url.includes('grant_type=password'))!
  expect(url).toBe('https://example.supabase.co/auth/v1/token?grant_type=password'); expect(JSON.parse(init.body)).toEqual({ email: 'analyst@example.com', password: 'correct horse battery' })
  expect(init.headers.apikey).toBe(CONFIG.publishable_key); expect(init.headers.Authorization).toBeUndefined(); expect(init.credentials).toBe('omit'); expect(screen.getByLabelText('Password')).toHaveValue('')
 })
 it('does not pretend to sign in when API verification rejects the token', async () => {
  mockFetch(); const user = userEvent.setup(); render(<SignIn config={CONFIG} onSignedIn={vi.fn().mockRejectedValue(new Error('Invalid verified identity'))} />)
  await user.type(screen.getByLabelText('Email'), 'analyst@example.com'); await user.click(screen.getByRole('button', { name: 'Sign in' })); expect(await screen.findByText('Invalid verified identity')).toBeInTheDocument()
 })
 it.each([[false, { error_description: 'Invalid login credentials' }, 'Invalid login credentials'], [true, {}, 'The provider did not return an access token.']] as const)('rejects unsuccessful responses (%s)', async (ok, body, error) => {
  mockFetch(body, ok); const onSignedIn = vi.fn(), user = userEvent.setup(); render(<SignIn config={CONFIG} onSignedIn={onSignedIn} />)
  await user.type(screen.getByLabelText('Email'), 'analyst@example.com'); await user.click(screen.getByRole('button', { name: 'Sign in' })); expect(await screen.findByText(error)).toBeInTheDocument(); expect(onSignedIn).not.toHaveBeenCalled()
 })
 it.each([['Sign in by email link', false], ['Create account by email', true]] as const)('requests %s without claiming a session', async (button, createUser) => {
  const fetch = mockFetch({}), onSignedIn = vi.fn(), user = userEvent.setup(); render(<SignIn config={CONFIG} onSignedIn={onSignedIn} />)
  await user.type(screen.getByLabelText('Email'), 'analyst@example.com'); await user.click(await screen.findByRole('button', { name: button })); expect(await screen.findByText(/You are not signed in yet/)).toBeInTheDocument()
  const [url, init] = fetch.mock.calls.find(([url]) => url.includes('/otp?'))!
  expect(new URL(url).searchParams.get('redirect_to')).toBe(CONFIG.redirect_url); expect(JSON.parse(init.body)).toMatchObject({ email: 'analyst@example.com', create_user: createUser, code_challenge_method: 's256' }); expect(JSON.parse(init.body).code_challenge).toMatch(/^[A-Za-z0-9_-]{43}$/); expect(onSignedIn).not.toHaveBeenCalled()
 })
 it('renders Google and Apple only when actually enabled', async () => {
  mockFetch({}, true, { ...AVAILABLE, external: { email: true, google: true, apple: true } }); render(<SignIn config={CONFIG} onSignedIn={vi.fn()} />)
  expect(await screen.findByRole('button', { name: 'Continue with Google' })).toBeInTheDocument(); expect(screen.getByRole('button', { name: 'Continue with Apple' })).toBeInTheDocument()
 })
 it('explains disabled providers and respects disabled signup', async () => {
  mockFetch({}, true, { ...AVAILABLE, disable_signup: true }); render(<SignIn config={CONFIG} onSignedIn={vi.fn()} />)
  expect(await screen.findByText('Google and Apple sign-in are not enabled for this project.')).toBeInTheDocument(); expect(screen.queryByRole('button', { name: 'Continue with Google' })).not.toBeInTheDocument(); expect(screen.queryByRole('button', { name: 'Create account by email' })).not.toBeInTheDocument()
 })
 it('does not offer redirect flows before callback configuration', async () => {
  mockFetch(); render(<SignIn config={{ ...CONFIG, flows: ['password'], redirect_url: '' }} onSignedIn={vi.fn()} />)
  expect(await screen.findByText(/finish the secure callback setup/)).toBeInTheDocument(); expect(screen.queryByRole('button', { name: 'Sign in by email link' })).not.toBeInTheDocument()
 })
 it('offers explicit retry after discovery fails', async () => {
  const fetch = mockFetch(); fetch.mockRejectedValueOnce(new Error('offline')); const user = userEvent.setup(); render(<SignIn config={CONFIG} onSignedIn={vi.fn()} />)
  await user.click(await screen.findByRole('button', { name: 'Retry' })); expect(await screen.findByRole('button', { name: 'Sign in by email link' })).toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(2)
 })
 it('keeps verified viewers pending without a bypass', () => {
  const onSignOut = vi.fn(), fetch = mockFetch(); render(<SignIn config={CONFIG} onSignedIn={vi.fn()} accessPending onSignOut={onSignOut} />)
  expect(screen.getByText(/does not grant administrator access/)).toBeInTheDocument(); expect(screen.queryByLabelText('Password')).not.toBeInTheDocument(); screen.getByRole('button', { name: 'Use a different account' }).click(); expect(onSignOut).toHaveBeenCalledOnce(); expect(fetch).not.toHaveBeenCalled()
 })
 it('explains missing provider without fake submit', () => {
  render(<SignIn config={{ ...CONFIG, flows: [], provider_url: '', publishable_key: '' }} onSignedIn={vi.fn()} />); expect(screen.queryByLabelText('Password')).not.toBeInTheDocument(); expect(screen.getByText(/no provider is configured/)).toBeInTheDocument()
 })
})
