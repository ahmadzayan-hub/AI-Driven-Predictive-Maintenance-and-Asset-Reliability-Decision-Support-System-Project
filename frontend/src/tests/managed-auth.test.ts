import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createHash, webcrypto } from 'node:crypto'
import { accessToken, beginPkce, callbackAllowed, discardRequest, emailLink, exchangeCallback, oauthUrl, providerRequest, REQUEST_KEY, settings } from '../features/auth/managedAuth'
import type { AuthConfig } from '../shared/types'
const config: AuthConfig = { mode: 'jwt', provider_url: 'https://example.supabase.co', publishable_key: 'public-only', flows: ['password', 'pkce'], redirect_url: `${window.location.origin}/auth/callback` }
function reply(body: unknown = { access_token: 'synthetic-token' }, ok = true) { const f = vi.fn().mockResolvedValue({ ok, json: async () => body }); vi.stubGlobal('fetch', f); return f }
function pending() { return JSON.parse(localStorage.getItem(REQUEST_KEY)!) }
function callback(query = '?code=one-use') { window.history.replaceState(null, '', `/auth/callback${query}`) }
beforeEach(() => { localStorage.clear(); window.history.replaceState(null, '', '/'); vi.stubGlobal('crypto', webcrypto) })
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); window.history.replaceState(null, '', '/') })
describe('managed authentication boundaries', () => {
 it('generates an unpredictable S256 verifier and challenge, never an implicit token', async () => {
  const a = await beginPkce(config), b = await beginPkce(config)
  expect(a.verifier).toMatch(/^[A-Za-z0-9_-]{43}$/); expect(b.verifier).not.toBe(a.verifier)
  expect(a.code_challenge).toBe(createHash('sha256').update(a.verifier).digest('base64url'))
  expect(a.code_challenge_method).toBe('s256'); expect(pending().verifier).toBe(b.verifier)
 })
 it.each(['https://foreign.invalid/auth/callback', `${window.location.origin}/other`, `${window.location.origin}/auth/callback?next=https://evil.invalid`, `${window.location.origin}/auth/callback#token=x`, 'not a url'])('rejects unsafe callback %s', async (redirect_url) => {
  expect(callbackAllowed({ ...config, redirect_url })).toBe(false)
  await expect(beginPkce({ ...config, redirect_url })).rejects.toThrow('configuration')
  expect(localStorage.getItem(REQUEST_KEY)).toBeNull()
 })
 it('does not allow callback flows when the server only advertises passwords', () => expect(callbackAllowed({ ...config, flows: ['password'] })).toBe(false))
 it('fails before sending email if storage is unavailable', async () => {
  const fetch = reply(); vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked') })
  await expect(emailLink(config, 'synthetic@example.invalid', false)).rejects.toThrow('blocked'); expect(fetch).not.toHaveBeenCalled()
 })
 it('builds a Google authorization URL with exact redirect and PKCE, no token or password', async () => {
  const url = new URL(await oauthUrl(config, 'google'))
  expect(url.origin).toBe(config.provider_url); expect(url.pathname).toBe('/auth/v1/authorize')
  expect(url.searchParams.get('provider')).toBe('google'); expect(url.searchParams.get('redirect_to')).toBe(config.redirect_url)
  expect(url.searchParams.get('code_challenge')).toBe(createHash('sha256').update(pending().verifier).digest('base64url'))
  expect(url.searchParams.has('response_type')).toBe(false)
 })
 it('exchanges once, removes callback secrets from the URL and consumes the verifier', async () => {
  const fetch = reply(); const p = await beginPkce(config); callback()
  expect(await exchangeCallback(config)).toBe('synthetic-token')
  expect(window.location.pathname).toBe('/'); expect(window.location.search).toBe(''); expect(localStorage.getItem(REQUEST_KEY)).toBeNull()
  const [url, init] = fetch.mock.calls[0]; expect(url).toBe(`${config.provider_url}/auth/v1/token?grant_type=pkce`)
  expect(JSON.parse(init.body)).toEqual({ auth_code: 'one-use', code_verifier: p.verifier })
  callback(); await expect(exchangeCallback(config)).rejects.toThrow('callback'); expect(fetch).toHaveBeenCalledOnce()
 })
 it.each(['?code=a&code=b', '?error=access_denied', '?code=a&error_code=expired', '#access_token=untrusted', '', `?code=${'x'.repeat(2049)}`])('rejects malformed or implicit callback %s', async (query) => {
  const fetch = reply(); await beginPkce(config); callback(query)
  await expect(exchangeCallback(config)).rejects.toThrow('callback'); expect(fetch).not.toHaveBeenCalled(); expect(window.location.href).not.toContain('access_token'); expect(localStorage.getItem(REQUEST_KEY)).toBeNull()
 })
 it.each([{ provider: 'https://other.supabase.co' }, { redirect: 'https://other.invalid/auth/callback' }, { created: 0 }, { created: Date.now() + 3600000 }, { verifier: 'bad' }])('rejects altered/expired local binding %j', async (change) => {
  const fetch = reply(); await beginPkce(config); localStorage.setItem(REQUEST_KEY, JSON.stringify({ ...pending(), ...change })); callback()
  await expect(exchangeCallback(config)).rejects.toThrow('callback'); expect(fetch).not.toHaveBeenCalled()
 })
 it('does not retry uncertain callback exchanges', async () => {
  const fetch = reply(); fetch.mockRejectedValue(new Error('network uncertain')); await beginPkce(config); callback()
  await expect(exchangeCallback(config)).rejects.toThrow('network uncertain'); expect(localStorage.getItem(REQUEST_KEY)).toBeNull()
  callback(); await expect(exchangeCallback(config)).rejects.toThrow('callback'); expect(fetch).toHaveBeenCalledOnce()
 })
 it('keeps a newer request when an earlier email request fails', async () => {
  const first = await beginPkce(config), second = await beginPkce(config); discardRequest(first.verifier); expect(pending().verifier).toBe(second.verifier)
 })
 it('clears its own pending request on email provider failure and shows the error', async () => {
  reply({ msg: 'Email rate limit exceeded' }, false)
  await expect(emailLink(config, 'synthetic@example.invalid', true)).rejects.toThrow('Email rate limit exceeded'); expect(localStorage.getItem(REQUEST_KEY)).toBeNull()
 })
 it('defaults signup disabled when provider settings are incomplete', async () => {
  reply({ external: { email: true } }); expect((await settings(config)).disable_signup).toBe(true)
 })
 it('rejects malformed provider settings', async () => { reply({}); await expect(settings(config)).rejects.toThrow('provider') })
 it.each(['http://example.supabase.co', 'https://user:password@example.supabase.co', 'https://example.supabase.co/untrusted', 'https://example.supabase.co?redirect=evil'])('rejects unsafe provider %s before requests', async (provider_url) => {
  const fetch = reply(); await expect(providerRequest({ ...config, provider_url }, '/settings')).rejects.toThrow('configuration'); expect(fetch).not.toHaveBeenCalled()
 })
 it('bounds provider messages and never accepts missing tokens', async () => {
  reply({ msg: 'x'.repeat(1000) }, false); await expect(providerRequest(config, '/settings')).rejects.toThrow('x'.repeat(300))
  expect(() => accessToken({ access_token: 12 })).toThrow('token'); expect(() => accessToken(null)).toThrow('token')
 })
})
