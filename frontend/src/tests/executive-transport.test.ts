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

it('downloads a genuine Word attachment for the exact prepared Arabic snapshot with authentication', async () => {
  const blob = new Blob(['PK synthetic package'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true,
    headers: new Headers({ 'content-type': blob.type, 'content-disposition': 'attachment; filename="miyaar-executive-r1-ar.docx"' }),
    blob: async () => blob,
  }))
  localStorage.setItem('aos-token', 'executive-download-token')
  const filters = [{ column: 'Site', op: 'in' as const, values: ['دبي', 'A & B'] }]
  const version = '2026-10-19T10:01:02.123456+00:00'
  const snapshot = 'a'.repeat(64)
  const result = await api.downloadExecutive('run/1', 'ar', filters, version, snapshot, 'docx')
  expect(result).toEqual({ blob, name: 'miyaar-executive-r1-ar.docx' })
  const [path, init] = vi.mocked(fetch).mock.calls[0]
  const url = new URL(String(path), 'http://localhost')
  expect(url.pathname).toBe('/api/runs/run%2F1/executive/export')
  expect(Object.fromEntries(url.searchParams)).toMatchObject({ format: 'docx', language: 'ar', expected_updated_at: version, expected_snapshot_id: snapshot })
  expect(JSON.parse(url.searchParams.get('filters')!)).toEqual(filters)
  expect(init?.headers).toEqual({ Authorization: 'Bearer executive-download-token' })
})

it('rejects stale snapshots and JSON masquerading as a business file', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false, status: 409,
    json: async () => ({ detail: 'Refresh the prepared brief.' }),
  }).mockResolvedValueOnce({ ok: true, status: 200, headers: new Headers({ 'content-type': 'application/json' }) }))
  await expect(api.downloadExecutive('r1', 'en', [], 'version', 'a'.repeat(64), 'html')).rejects.toMatchObject({ status: 409, message: 'Refresh the prepared brief.' })
  await expect(api.downloadExecutive('r1', 'en', [], 'version', 'a'.repeat(64), 'docx')).rejects.toMatchObject({ status: 200 })
})

it('cancels a business download when the owning view becomes obsolete', async () => {
  let signal: AbortSignal | null = null
  vi.stubGlobal('fetch', vi.fn((_path, init: RequestInit) => new Promise((_resolve, reject) => {
    signal = init.signal as AbortSignal
    signal.addEventListener('abort', () => reject(new DOMException('Cancelled', 'AbortError')))
  })))
  const controller = new AbortController()
  const response = api.downloadExecutive('r1', 'ar', [], 'version', 'a'.repeat(64), 'html', controller.signal)
  controller.abort()
  await expect(response).rejects.toMatchObject({ name: 'ApiError' })
  expect(signal!.aborted).toBe(true)
})
