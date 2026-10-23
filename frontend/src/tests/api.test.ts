import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, AUTH_EXPIRED_EVENT } from '../shared/api'

function mockFetchOnce(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const impl = {
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    ...response,
  } as Response
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(impl))
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  localStorage.removeItem('aos-token')
})

describe('api client', () => {
  function delayedRunResponse(delay: number) {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((resolve, reject) => {
      const timer = setTimeout(() => resolve({ ok: true, json: async () => ({ id: 'r1' }) } as Response), delay)
      init?.signal?.addEventListener('abort', () => {
        clearTimeout(timer)
        reject(new DOMException('Aborted', 'AbortError'))
      }, { once: true })
    })))
  }

  it.each([
    ['advance', () => api.advanceRun('r1')],
    ['read', () => api.getRun('r1')],
    ['pause', () => api.pauseRun('r1')],
    ['resume', () => api.resumeRun('r1')],
    ['cancel', () => api.cancelRun('r1')],
    ['approval', () => api.decideApproval('r1', 'a1', 'approve')],
  ] as const)('keeps a run %s request alive through a bounded model step and response overhead', async (_name, operation) => {
    delayedRunResponse(65_000)
    const result = operation().then((value) => value, (error: unknown) => error)
    await vi.advanceTimersByTimeAsync(10_000)
    expect(vi.mocked(fetch).mock.calls[0][1]?.signal?.aborted).toBe(false)
    await vi.advanceTimersByTimeAsync(55_000)
    expect(await result).toMatchObject({ id: 'r1' })
    expect(fetch).toHaveBeenCalledOnce()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('still bounds an unresponsive run step without replaying its POST', async () => {
    delayedRunResponse(91_000)
    const result = expect(api.advanceRun('r1')).rejects.toMatchObject({ name: 'ApiError', message: expect.stringMatching(/too long/) })
    await vi.advanceTimersByTimeAsync(89_999)
    expect(vi.mocked(fetch).mock.calls[0][1]?.signal?.aborted).toBe(false)
    await vi.advanceTimersByTimeAsync(1)
    await result
    expect(fetch).toHaveBeenCalledOnce()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('retains the short timeout for health requests', async () => {
    delayedRunResponse(11_000)
    const result = expect(api.health()).rejects.toMatchObject({ name: 'ApiError', message: expect.stringMatching(/too long/) })
    await vi.advanceTimersByTimeAsync(10_000)
    await result
    expect(vi.getTimerCount()).toBe(0)
  })

  it.each(['mapping', 'csv', 'executive'])('signals an expired credential from the %s transport', async (kind) => {
    localStorage.setItem('aos-token', 'expired-token')
    mockFetchOnce({ ok: false, status: 401, json: async () => ({ detail: 'Expired' }) })
    const expired = vi.fn()
    window.addEventListener(AUTH_EXPIRED_EVENT, expired)
    try {
      const operation = kind === 'mapping' ? api.getDataset('r1')
        : kind === 'csv' ? api.downloadTable('r1')
          : api.downloadExecutive('r1', 'en', [], 'stamp', 'snapshot', 'html')
      await expect(operation).rejects.toMatchObject({ status: 401 })
      expect(expired).toHaveBeenCalledOnce()
    } finally { window.removeEventListener(AUTH_EXPIRED_EVENT, expired) }
  })
  it('does not expire a new login when an older credential receives a delayed 401', async () => {
    localStorage.setItem('aos-token', 'old-token')
    let finish!: (response: Partial<Response>) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise((resolve) => { finish = resolve })))
    const expired = vi.fn()
    window.addEventListener(AUTH_EXPIRED_EVENT, expired)
    try {
      const operation = api.listDatasets()
      localStorage.setItem('aos-token', 'new-token')
      finish({ ok: false, status: 401, json: async () => ({ detail: 'Expired old token' }) })
      await expect(operation).rejects.toMatchObject({ status: 401 })
      expect(expired).not.toHaveBeenCalled()
      expect(localStorage.getItem('aos-token')).toBe('new-token')
    } finally { window.removeEventListener(AUTH_EXPIRED_EVENT, expired) }
  })
  it('uses an owned run policy route, exact optimistic revision and the authenticated transport', async () => {
    localStorage.setItem('aos-token', 'tok')
    const policy = { revision: 'a'.repeat(64), rules: {} }
    mockFetchOnce({ json: () => Promise.resolve(policy) })
    const controller = new AbortController()
    await expect(api.kpiPolicy('run/one', 'ar', controller.signal)).resolves.toEqual(policy)
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe('/api/runs/run%2Fone/kpi-policy?language=ar')
    await api.saveKpiPolicy('run/one', policy, 'ar', controller.signal)
    const [, init] = vi.mocked(fetch).mock.calls[1]
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer tok' })
    expect(init?.method).toBe('PUT')
    expect(JSON.parse(String(init?.body))).toEqual({ expected_revision: policy.revision, rules: {} })
    localStorage.removeItem('aos-token')
  })
  it('returns parsed JSON for successful requests', async () => {
    mockFetchOnce({ json: () => Promise.resolve({ status: 'ok', agent_name: 'A', version: '1' }) })
    const result = await api.health()
    expect(result.status).toBe('ok')
  })

  it('surfaces the server "detail" message on API errors', async () => {
    mockFetchOnce({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ detail: 'This session has ended.' }),
    })
    await expect(api.sendMessage('sid', 'hello')).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      message: 'This session has ended.',
    })
  })

  it('maps network failures to a friendly offline error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    try {
      await api.health()
      expect.unreachable('health() should have thrown')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).offline).toBe(true)
      expect((error as ApiError).message).toMatch(/Cannot reach/)
    }
  })

  it('falls back to a status message when the error body is not JSON', async () => {
    mockFetchOnce({ ok: false, status: 500, json: () => Promise.reject(new Error('not json')) })
    await expect(api.health()).rejects.toMatchObject({ message: 'Request failed (500).' })
  })

  it('analyses a stored dataset by its id and sends no file text', async () => {
    mockFetchOnce({ json: () => Promise.resolve({ id: 'r1' }) })
    await api.createRun('Analyse it', 'a,b\n1,2', 'local.csv', undefined, 'ar', 'ds1')
    const [path, init] = vi.mocked(fetch).mock.calls[0]
    expect(path).toBe('/api/runs')
    expect(JSON.parse(String(init?.body))).toEqual({
      goal: 'Analyse it',
      dataset_text: null,
      dataset_name: null,
      dataset_id: 'ds1',
      profile: null,
      language: 'ar',
      joins: null,
      breakdown: null,
      assumptions: null,
    })
  })

  it('sends joins and their breakdown with a stored dataset (ADR 0030)', async () => {
    mockFetchOnce({ json: () => Promise.resolve({ id: 'r1' }) })
    const joins = [{ dataset_id: 'ds2', keys: [{ left: 'item', right: 'code' }], how: 'left' as const }]
    await api.createRun('Analyse it', undefined, undefined, undefined, 'en', 'ds1', { joins, breakdown: 'family' })
    const body = JSON.parse(String(vi.mocked(fetch).mock.calls[0][1]?.body))
    expect(body.joins).toEqual(joins)
    expect(body.breakdown).toBe('family')
    mockFetchOnce({ json: () => Promise.resolve({ rows_before: 1 }) })
    await api.previewJoins('ds1', joins, null, 'ar')
    // Each mock is a fresh fetch, so the preview is its first call.
    const [path, init] = vi.mocked(fetch).mock.calls[0]
    expect(path).toBe('/api/joins/preview?language=ar')
    expect(JSON.parse(String(init?.body))).toEqual({ dataset_id: 'ds1', joins, breakdown: null })
  })

  it('downloads the cleaned table with the token and the server\'s file name (ADR 0031)', async () => {
    localStorage.setItem('aos-token', 'tok')
    mockFetchOnce({
      blob: () => Promise.resolve(new Blob(['a,b'])),
      headers: new Headers({ 'content-disposition': 'attachment; filename="sales-r1-cleaned.csv"' }),
    })
    const { name, blob } = await api.downloadTable('r1', 'ar')
    const [path, init] = vi.mocked(fetch).mock.calls[0]
    expect(path).toBe('/api/runs/r1/data.csv?language=ar')
    expect((init?.headers as Record<string, string>).Authorization).toBe('Bearer tok')
    expect(name).toBe('sales-r1-cleaned.csv')
    expect(await blob.text()).toBe('a,b')
    localStorage.removeItem('aos-token')
  })

  it('uploads a file as the request body, named and in the reader\'s language', async () => {
    localStorage.setItem('aos-token', 'tok')
    mockFetchOnce({ status: 201, json: () => Promise.resolve({ created: true }) })
    const file = new File(['a,b\n1,2\n'], 'ventes été.csv', { type: 'text/csv' })
    await api.uploadDataset(file, 'ar')
    const [path, init] = vi.mocked(fetch).mock.calls[0]
    expect(path).toBe('/api/datasets?name=ventes%20%C3%A9t%C3%A9.csv&language=ar')
    expect(init?.method).toBe('POST')
    expect(init?.body).toBe(file)
    // The file's own type replaces JSON, and the token is still sent.
    expect(init?.headers).toMatchObject({ 'Content-Type': 'text/csv', Authorization: 'Bearer tok' })
    localStorage.removeItem('aos-token')
  })

  it('lists the stored datasets', async () => {
    mockFetchOnce({ json: () => Promise.resolve({ datasets: [] }) })
    await expect(api.listDatasets()).resolves.toEqual({ datasets: [] })
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe('/api/datasets')
  })
})
