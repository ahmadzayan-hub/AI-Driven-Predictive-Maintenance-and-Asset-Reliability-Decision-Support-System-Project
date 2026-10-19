import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { VoiceDictation, type VoiceRecognition } from './VoiceDictation'

vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }))

class MockRecognition implements VoiceRecognition {
  static instance: MockRecognition | undefined
  lang = ''
  continuous = true
  interimResults = false
  maxAlternatives = 0
  onstart: VoiceRecognition['onstart'] = null
  onaudioend: VoiceRecognition['onaudioend'] = null
  onresult: VoiceRecognition['onresult'] = null
  onerror: VoiceRecognition['onerror'] = null
  onend: VoiceRecognition['onend'] = null
  start = vi.fn()
  stop = vi.fn()
  constructor() { MockRecognition.instance = this }
}
function result(text: string, isFinal: boolean) {
  return { resultIndex: 0, results: [Object.assign([{ transcript: text }], { isFinal })] }
}
function begin(language: 'en' | 'ar' = 'en') {
  const onTranscript = vi.fn(), onActiveChange = vi.fn()
  const view = render(<VoiceDictation language={language} disabled={false} onTranscript={onTranscript} onActiveChange={onActiveChange} />)
  fireEvent.click(screen.getByRole('button', { name: 'voice.start' }))
  fireEvent.click(screen.getByRole('button', { name: 'voice.allow' }))
  return { ...view, onTranscript, onActiveChange, recognition: MockRecognition.instance! }
}
beforeEach(() => {
  MockRecognition.instance = undefined
  Object.defineProperty(window, 'webkitSpeechRecognition', { configurable: true, value: MockRecognition })
})
afterEach(() => {
  delete (window as unknown as { webkitSpeechRecognition?: typeof MockRecognition }).webkitSpeechRecognition
  vi.useRealTimers()
})

describe('VoiceDictation lifecycle', () => {
  it('does not request capture before consent, and waits for an actual start event', () => {
    render(<VoiceDictation language="ar" disabled={false} onTranscript={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'voice.start' }))
    expect(MockRecognition.instance).toBeUndefined()
    fireEvent.click(screen.getByRole('button', { name: 'voice.allow' }))
    expect(MockRecognition.instance!.lang).toBe('ar-AE')
    expect(screen.getByText('voice.requesting')).toBeInTheDocument()
    expect(screen.queryByText('voice.listening')).not.toBeInTheDocument()
    act(() => MockRecognition.instance!.onstart?.())
    expect(screen.getByText('voice.listening')).toBeInTheDocument()
  })
  it('previews interim words but adds final text to the draft only once', () => {
    const { recognition, onTranscript } = begin()
    act(() => recognition.onresult?.(result('asset', false)))
    expect(screen.getByText('asset')).toBeInTheDocument()
    expect(onTranscript).not.toHaveBeenCalled()
    const late = recognition.onresult
    act(() => late?.(result('asset reliability', true)))
    act(() => late?.(result('asset reliability', true)))
    expect(onTranscript).toHaveBeenCalledExactlyOnceWith('asset reliability')
    expect(screen.getByText('voice.review')).toBeInTheDocument()
  })
  it('finalizes on stop, then allows the final transcript to be reviewed', () => {
    const { recognition, onTranscript } = begin()
    act(() => recognition.onstart?.())
    fireEvent.click(screen.getByRole('button', { name: 'voice.stop' }))
    expect(recognition.stop).toHaveBeenCalled()
    expect(screen.getByText('voice.processing')).toBeInTheDocument()
    act(() => recognition.onresult?.(result('inspect pump', true)))
    expect(onTranscript).toHaveBeenCalledWith('inspect pump')
  })
  it('cancels a pending permission request and ignores its late results', () => {
    const { recognition, onTranscript } = begin()
    const late = recognition.onresult
    fireEvent.click(screen.getByRole('button', { name: 'voice.stop' }))
    act(() => late?.(result('late text', true)))
    expect(onTranscript).not.toHaveBeenCalled()
    expect(screen.getByText('voice.ready')).toBeInTheDocument()
  })
  it('invalidates callbacks and stops capture when chat is disabled', () => {
    const { recognition, onTranscript, rerender } = begin()
    const late = recognition.onresult
    rerender(<VoiceDictation language="en" disabled onTranscript={onTranscript} />)
    act(() => late?.(result('late private text', true)))
    expect(recognition.stop).toHaveBeenCalled()
    expect(onTranscript).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'voice.start' })).toBeDisabled()
  })
  it('invalidates callbacks when changing language or unmounting', () => {
    const { recognition, onTranscript, rerender, unmount } = begin()
    const late = recognition.onresult
    rerender(<VoiceDictation language="ar" disabled={false} onTranscript={onTranscript} />)
    act(() => late?.(result('old language', true)))
    unmount()
    act(() => late?.(result('unmounted', true)))
    expect(onTranscript).not.toHaveBeenCalled()
  })
  it.each([
    ['not-allowed', 'voice.denied'], ['audio-capture', 'voice.noMicrophone'],
    ['network', 'voice.network'], ['no-speech', 'voice.noSpeech'],
  ])('explains %s and clears active capture', (error, key) => {
    const { recognition, onActiveChange } = begin()
    act(() => recognition.onerror?.({ error }))
    expect(screen.getByText(key)).toBeInTheDocument()
    expect(onActiveChange).toHaveBeenLastCalledWith(false)
  })
  it('resolves a browser that never starts instead of remaining active forever', () => {
    vi.useFakeTimers()
    begin()
    act(() => vi.advanceTimersByTime(12000))
    expect(screen.getByText('voice.startTimeout')).toBeInTheDocument()
  })
  it('explains unsupported recognition without opening consent or capture', () => {
    delete (window as unknown as { webkitSpeechRecognition?: typeof MockRecognition }).webkitSpeechRecognition
    render(<VoiceDictation language="en" disabled={false} onTranscript={vi.fn()} />)
    expect(screen.getByText('voice.unsupported')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'voice.start' })).toBeDisabled()
    expect(MockRecognition.instance).toBeUndefined()
  })
})
