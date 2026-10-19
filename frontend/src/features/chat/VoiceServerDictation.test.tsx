import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api, ApiError } from '../../shared/api'
import type { VoiceStatus, VoiceTranscript } from '../../shared/api'
import { Composer } from './Composer'
import VoiceServerDictation from './VoiceServerDictation'
import { VoiceInput } from './VoiceInput'
import { voiceMessages } from './voiceMessages'

const status: VoiceStatus = { enabled: true, available: true, provider: 'faster-whisper', model: 'small', max_seconds: 30, max_bytes: 2_000_000 }
const track = { stop: vi.fn() }
const capture = { getTracks: () => [track] } as unknown as MediaStream
const getUserMedia = vi.fn()

class MockRecorder {
  static instance: MockRecorder | undefined
  static isTypeSupported = (type: string) => type === 'audio/webm;codecs=opus'
  state: RecordingState = 'inactive'
  mimeType = 'audio/webm;codecs=opus'
  onstart: (() => void) | null = null
  ondataavailable: ((event: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  onerror: (() => void) | null = null
  start = vi.fn(() => { this.state = 'recording' })
  stop = vi.fn(() => {
    this.state = 'inactive'
    this.ondataavailable?.({ data: new Blob(['voice recording'], { type: this.mimeType }) })
    this.onstop?.()
  })
  constructor() { MockRecorder.instance = this }
}

async function begin(language: 'en' | 'ar' = 'en') {
  const onTranscript = vi.fn(), onActiveChange = vi.fn()
  const view = render(<VoiceServerDictation status={status} sessionId="session1" language={language}
    disabled={false} onTranscript={onTranscript} onActiveChange={onActiveChange} />)
  fireEvent.click(screen.getByRole('button', { name: 'Record with local Whisper' }))
  expect(getUserMedia).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Allow microphone and record' }))
  await waitFor(() => expect(MockRecorder.instance).toBeDefined())
  return { ...view, onTranscript, onActiveChange, recorder: MockRecorder.instance! }
}

beforeEach(() => {
  MockRecorder.instance = undefined
  track.stop.mockClear()
  getUserMedia.mockReset().mockResolvedValue(capture)
  vi.stubGlobal('MediaRecorder', MockRecorder)
  vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } })
  vi.spyOn(api, 'voiceStatus').mockResolvedValue(status)
  vi.spyOn(api, 'transcribeSession').mockResolvedValue({ text: 'Inspect the pump', language: 'en', provider: 'faster-whisper' })
})
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers() })

describe('local Whisper capture', () => {
  it('waits for consent and actual recording, then adds editable text without sending', async () => {
    const onSend = vi.fn()
    render(<Composer sessionId="s1" busy={false} onSend={onSend} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Record with local Whisper' }, { timeout: 3000 }))
    expect(getUserMedia).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Allow microphone and record' }))
    await waitFor(() => expect(MockRecorder.instance).toBeDefined())
    expect(screen.getByText('Waiting for microphone permission…')).toBeInTheDocument()
    expect(screen.queryByText('Recording on this device. Stop to transcribe.')).not.toBeInTheDocument()
    act(() => MockRecorder.instance!.onstart?.())
    fireEvent.click(screen.getByRole('button', { name: 'Stop recording and transcribe' }))
    await waitFor(() => expect(screen.getByLabelText('Message')).toHaveValue('Inspect the pump'))
    expect(onSend).not.toHaveBeenCalled()
    expect(track.stop).toHaveBeenCalledOnce()
    expect(api.transcribeSession).toHaveBeenCalledWith('s1', expect.any(Blob), 'en', expect.any(AbortSignal))
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Inspect pump P-102' } })
    expect(screen.getByLabelText('Message')).toHaveValue('Inspect pump P-102')
  })
  it('cancels an upload, stops the microphone and ignores a late transcript', async () => {
    let resolve!: (result: VoiceTranscript) => void
    vi.mocked(api.transcribeSession).mockReturnValue(new Promise((done) => { resolve = done }))
    const { recorder, onTranscript, onActiveChange } = await begin()
    act(() => recorder.onstart?.())
    fireEvent.click(screen.getByRole('button', { name: 'Stop recording and transcribe' }))
    const signal = vi.mocked(api.transcribeSession).mock.calls[0][3]
    expect(track.stop).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel voice capture' }))
    expect(signal.aborted).toBe(true)
    await act(async () => resolve({ text: 'Late private words', language: 'en', provider: 'faster-whisper' }))
    expect(onTranscript).not.toHaveBeenCalled()
    expect(onActiveChange).toHaveBeenLastCalledWith(false)
  })
  it('releases a microphone that arrives after capture was cancelled', async () => {
    let resolve!: (stream: MediaStream) => void
    getUserMedia.mockReturnValue(new Promise((done) => { resolve = done }))
    render(<VoiceServerDictation status={status} sessionId="s1" language="en" disabled={false} onTranscript={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Record with local Whisper' }))
    fireEvent.click(screen.getByRole('button', { name: 'Allow microphone and record' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel voice capture' }))
    await act(async () => resolve(capture))
    expect(track.stop).toHaveBeenCalledOnce()
    expect(MockRecorder.instance).toBeUndefined()
    expect(api.transcribeSession).not.toHaveBeenCalled()
  })
  it('discards recording on language/session changes and unmount', async () => {
    const { recorder, onTranscript, rerender, unmount } = await begin()
    act(() => recorder.onstart?.())
    const lateStop = recorder.onstop
    rerender(<VoiceServerDictation status={status} sessionId="session2" language="ar" disabled={false} onTranscript={onTranscript} />)
    await act(async () => { await lateStop?.() })
    unmount()
    expect(track.stop).toHaveBeenCalledOnce()
    expect(recorder.stop).toHaveBeenCalledOnce()
    expect(api.transcribeSession).not.toHaveBeenCalled()
    expect(onTranscript).not.toHaveBeenCalled()
  })
  it('explains denied permission and makes capture usable again', async () => {
    getUserMedia.mockRejectedValue(new DOMException('denied', 'NotAllowedError'))
    render(<VoiceServerDictation status={status} sessionId="s1" language="en" disabled={false} onTranscript={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Record with local Whisper' }))
    fireEvent.click(screen.getByRole('button', { name: 'Allow microphone and record' }))
    expect(await screen.findByText(/Microphone access was denied/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Record with local Whisper' })).toBeEnabled()
    expect(api.transcribeSession).not.toHaveBeenCalled()
  })
  it.each([[503, /Local Whisper is unavailable/], [429, /processing another recording/], [422, /No speech was transcribed/]])(
    'explains server status %s without submitting a message', async (code, message) => {
      vi.mocked(api.transcribeSession).mockRejectedValue(new ApiError('server message', code as number))
      const { recorder, onTranscript } = await begin()
      act(() => recorder.onstart?.())
      fireEvent.click(screen.getByRole('button', { name: 'Stop recording and transcribe' }))
      expect(await screen.findByText(message as RegExp)).toBeInTheDocument()
      expect(onTranscript).not.toHaveBeenCalled()
      expect(track.stop).toHaveBeenCalledOnce()
    },
  )
  it('rejects oversized recordings and releases the microphone without uploading', async () => {
    const { recorder } = await begin()
    act(() => recorder.onstart?.())
    act(() => recorder.ondataavailable?.({ data: new Blob([new Uint8Array(2_000_001)]) }))
    expect(screen.getByText(/exceeded the 2 MB limit/)).toBeInTheDocument()
    expect(track.stop).toHaveBeenCalledOnce()
    expect(api.transcribeSession).not.toHaveBeenCalled()
  })
  it('stops before the strict 30-second server cap and uses the chosen recognition language', async () => {
    const { recorder } = await begin('ar')
    vi.useFakeTimers()
    act(() => recorder.onstart?.())
    await act(async () => { vi.advanceTimersByTime(28_999) })
    expect(recorder.stop).not.toHaveBeenCalled()
    await act(async () => { vi.advanceTimersByTime(1) })
    expect(recorder.stop).toHaveBeenCalledOnce()
    expect(api.transcribeSession).toHaveBeenCalledWith('session1', expect.any(Blob), 'ar', expect.any(AbortSignal))
    expect(track.stop).toHaveBeenCalledOnce()
  })
  it('falls back to the browser controls when discovery fails or local recording is unsupported', async () => {
    vi.mocked(api.voiceStatus).mockRejectedValue(new Error('old backend'))
    const view = render(<VoiceInput sessionId="s1" language="en" disabled={false} onTranscript={vi.fn()} />)
    await waitFor(() => expect(api.voiceStatus).toHaveBeenCalledOnce())
    expect(screen.queryByText('Local Whisper voice')).not.toBeInTheDocument()
    expect(getUserMedia).not.toHaveBeenCalled()
    view.unmount()
    vi.stubGlobal('MediaRecorder', undefined)
    render(<VoiceServerDictation status={status} sessionId="s1" language="en" disabled={false} onTranscript={vi.fn()} />)
    expect(screen.getByText(/Local audio recording is unavailable/)).toBeInTheDocument()
  })
  it('covers the same local voice labels in Arabic and English', () => {
    expect(Object.keys(voiceMessages.ar).sort()).toEqual(Object.keys(voiceMessages.en).sort())
    for (const key of Object.keys(voiceMessages.en) as Array<keyof typeof voiceMessages.en>) {
      expect(voiceMessages.ar[key]).toMatch(/[\u0600-\u06ff]/)
      expect((voiceMessages.ar[key].match(/\{\w+\}/g) || []).sort())
        .toEqual((voiceMessages.en[key].match(/\{\w+\}/g) || []).sort())
    }
  })
  it('keeps browser voice available when no supported recording format exists', () => {
    vi.spyOn(MockRecorder, 'isTypeSupported').mockReturnValue(false)
    render(<VoiceServerDictation status={status} sessionId="s1" language="en" disabled={false} onTranscript={vi.fn()} />)
    expect(screen.getByText(/Local audio recording is unavailable/)).toBeInTheDocument()
    expect(getUserMedia).not.toHaveBeenCalled()
  })
})
