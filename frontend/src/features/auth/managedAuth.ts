import type { AuthConfig } from '../../shared/types'

export const CALLBACK_PATH = '/auth/callback'
export const REQUEST_KEY = 'aos-auth-request'
const MAX_AGE = 10 * 60_000
export type ProviderSettings = { external: Record<string, boolean>; disable_signup: boolean }
type Pending = { verifier: string; provider: string; redirect: string; created: number }

function provider(config: AuthConfig) {
  const url = new URL(config.provider_url)
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || !['', '/'].includes(url.pathname)) throw new Error('configuration')
  return url.origin
}

export function callbackAllowed(config: AuthConfig) {
  try {
    const url = new URL(config.redirect_url || '')
    return config.flows.includes('pkce') && url.origin === window.location.origin &&
      url.pathname === CALLBACK_PATH && !url.search && !url.hash && !url.username && !url.password
  } catch { return false }
}

export async function providerRequest(config: AuthConfig, path: string, body?: unknown, signal?: AbortSignal) {
  const response = await fetch(`${provider(config)}/auth/v1${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json', apikey: config.publishable_key },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15_000)]) : AbortSignal.timeout(15_000),
    credentials: 'omit',
    redirect: 'error',
  })
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.error_description ?? payload?.msg ?? payload?.message
    throw new Error(typeof detail === 'string' ? detail.slice(0, 300) : 'provider')
  }
  return payload as Record<string, unknown> | null
}

export async function settings(config: AuthConfig, signal?: AbortSignal): Promise<ProviderSettings> {
  const value = await providerRequest(config, '/settings', undefined, signal)
  if (!value?.external || typeof value.external !== 'object') throw new Error('provider')
  return { external: value.external as Record<string, boolean>, disable_signup: value.disable_signup !== false }
}

function base64(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** No implicit-token callback, shared password or client-assigned role. The
 * provider owns OAuth state; S256 binds its one-use code to this browser. */
export async function beginPkce(config: AuthConfig) {
  if (!callbackAllowed(config)) throw new Error('configuration')
  const verifier = base64(crypto.getRandomValues(new Uint8Array(32)))
  const challenge = base64(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))))
  const pending: Pending = { verifier, provider: provider(config), redirect: config.redirect_url!, created: Date.now() }
  // A denied/unavailable storage write must stop before redirect or email.
  localStorage.setItem(REQUEST_KEY, JSON.stringify(pending))
  return { code_challenge: challenge, code_challenge_method: 's256', verifier }
}

export function discardRequest(verifier?: string) {
  try {
    const pending = JSON.parse(localStorage.getItem(REQUEST_KEY) || 'null') as Pending | null
    if (!verifier || pending?.verifier === verifier) localStorage.removeItem(REQUEST_KEY)
  } catch { /* no usable request remains */ }
}

export function accessToken(payload: Record<string, unknown> | null) {
  if (typeof payload?.access_token !== 'string' || !payload.access_token) throw new Error('token')
  return payload.access_token
}

export async function exchangeCallback(config: AuthConfig) {
  const url = new URL(window.location.href)
  if (url.pathname !== CALLBACK_PATH) throw new Error('callback')
  // Remove credentials/errors before a request, rendering or later navigation.
  window.history.replaceState(null, '', '/')
  let pending: Pending | null
  try { pending = JSON.parse(localStorage.getItem(REQUEST_KEY) || 'null') as Pending | null }
  catch { throw new Error('callback') }
  finally { localStorage.removeItem(REQUEST_KEY) }
  const code = url.searchParams.get('code')
  if (!callbackAllowed(config) || url.hash || url.searchParams.has('error') ||
      url.searchParams.has('error_code') || !code || code.length > 2048 ||
      url.searchParams.getAll('code').length !== 1 || !pending ||
      pending.provider !== provider(config) || pending.redirect !== config.redirect_url ||
      typeof pending.created !== 'number' || Date.now() - pending.created > MAX_AGE ||
      Date.now() < pending.created || !/^[A-Za-z0-9_-]{43}$/.test(pending.verifier)) throw new Error('callback')
  // Consume locally before exchanging: an uncertain response is never retried.
  return accessToken(await providerRequest(config, '/token?grant_type=pkce', {
    auth_code: code, code_verifier: pending.verifier,
  }))
}

export async function emailLink(config: AuthConfig, email: string, createUser: boolean) {
  const pkce = await beginPkce(config)
  try {
    await providerRequest(config, `/otp?redirect_to=${encodeURIComponent(config.redirect_url!)}`, {
      email, create_user: createUser, code_challenge: pkce.code_challenge, code_challenge_method: pkce.code_challenge_method,
    })
  } catch (error) { discardRequest(pkce.verifier); throw error }
}

export async function oauthUrl(config: AuthConfig, name: 'google' | 'apple') {
  const pkce = await beginPkce(config)
  const url = new URL(`${provider(config)}/auth/v1/authorize`)
  url.search = new URLSearchParams({ provider: name, redirect_to: config.redirect_url!,
    code_challenge: pkce.code_challenge, code_challenge_method: pkce.code_challenge_method }).toString()
  return url.href
}
