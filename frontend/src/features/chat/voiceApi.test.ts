import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../shared/api'

afterEach(() => { vi.unstubAllGlobals(); localStorage.removeItem('aos-token') })

describe('local speech API transport', () => {
  it('sends raw audio with the existing bearer token and selected language', async () => {
    const result = { text: 'افحص المضخة', language: 'ar', provider: 'faster-whisper' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => result }))
    localStorage.setItem('aos-token', 'voice-test-token')
    const recording = new Blob(['audio'], { type: 'audio/webm;codecs=opus' })
    await expect(api.transcribeSession('session/1', recording, 'ar', new AbortController().signal)).resolves.toEqual(result)
    const [path, init] = vi.mocked(fetch).mock.calls[0]
    expect(path).toBe('/api/sessions/session%2F1/transcriptions?language=ar')
    expect(init).toMatchObject({ method: 'POST', body: recording,
      headers: { 'Content-Type': 'audio/webm;codecs=opus', Authorization: 'Bearer voice-test-token' } })
  })
  it('aborts the fetch when the recorder owner cancels its upload', async () => {
    let requestSignal: AbortSignal | null = null
    vi.stubGlobal('fetch', vi.fn((_path: string, init: RequestInit) => new Promise((_resolve, reject) => {
      requestSignal = init.signal as AbortSignal
      requestSignal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError')))
    })))
    const controller = new AbortController()
    const pending = api.transcribeSession('s1', new Blob(['audio']), 'en', controller.signal)
    controller.abort()
    await expect(pending).rejects.toMatchObject({ name: 'ApiError' })
    expect(requestSignal!.aborted).toBe(true)
  })
})
