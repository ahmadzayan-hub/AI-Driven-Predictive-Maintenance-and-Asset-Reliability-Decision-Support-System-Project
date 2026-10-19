import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../shared/api'

afterEach(() => { vi.unstubAllGlobals(); localStorage.removeItem('aos-token') })

it('requests the exact executive scope in Arabic with the current owner token', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ source: 'engine' }) }))
  localStorage.setItem('aos-token', 'executive-test-token')
  const filters = [{ column: 'Site', op: 'in' as const, values: ['دبي', 'A & B'] }]
  await api.runExecutive('run/1', 'ar', filters)
  const [path, init] = vi.mocked(fetch).mock.calls[0]
  const url = new URL(String(path), 'http://localhost')
  expect(url.pathname).toBe('/api/runs/run%2F1/executive')
  expect(url.searchParams.get('language')).toBe('ar')
  expect(JSON.parse(url.searchParams.get('filters')!)).toEqual(filters)
  expect(init?.headers).toMatchObject({ Authorization: 'Bearer executive-test-token' })
})

it('cancels obsolete executive requests through the shared transport', async () => {
  let signal: AbortSignal | null = null
  vi.stubGlobal('fetch', vi.fn((_path, init: RequestInit) => new Promise((_resolve, reject) => {
    signal = init.signal as AbortSignal
    signal.addEventListener('abort', () => reject(new DOMException('Cancelled', 'AbortError')))
  })))
  const controller = new AbortController()
  const response = api.runExecutive('run1', 'en', [], controller.signal)
  controller.abort()
  await expect(response).rejects.toMatchObject({ name: 'ApiError' })
  expect(signal!.aborted).toBe(true)
})
