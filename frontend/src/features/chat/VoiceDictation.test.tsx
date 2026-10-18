import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { VoiceDictation } from './VoiceDictation'

vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }))

class MockRecognition {
  static instance: MockRecognition
  lang = ''
  continuous = true
  interimResults = true
  maxAlternatives = 0
  onresult: ((e: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null = null
  onerror: ((e: { error?: string }) => void) | null = null
  onend: (() => void) | null = null
  start = vi.fn()
  stop = vi.fn()
  constructor() { MockRecognition.instance = this }
}

afterEach(() => {
  delete (window as unknown as { webkitSpeechRecognition?: typeof MockRecognition }).webkitSpeechRecognition
})

describe('VoiceDictation, explicit opt-in and draft-only safety', () => {
  it('requires consent and never starts a microphone before approval', () => {
    ;(window as unknown as { webkitSpeechRecognition: typeof MockRecognition }).webkitSpeechRecognition = MockRecognition
    const onTranscript = vi.fn()
    render(<VoiceDictation language="ar" disabled={false} onTranscript={onTranscript} />)
    fireEvent.click(screen.getByRole('button', { name: 'voice.start' }))
    expect(screen.getByText('voice.privacyText')).toBeTruthy()
    expect(MockRecognition.instance).toBeUndefined()
    fireEvent.click(screen.getByRole('button', { name: 'voice.allow' }))
    expect(MockRecognition.instance.lang).toBe('ar-AE')
    expect(MockRecognition.instance.start).toHaveBeenCalledTimes(1)
    expect(onTranscript).not.toHaveBeenCalled()
  })

  it('places speech in the draft callback, never sends or executes it', () => {
    ;(window as unknown as { webkitSpeechRecognition: typeof MockRecognition }).webkitSpeechRecognition = MockRecognition
    const onTranscript = vi.fn()
    render(<VoiceDictation language="en" disabled={false} onTranscript={onTranscript} />)
    fireEvent.click(screen.getByRole('button', { name: 'voice.start' }))
    fireEvent.click(screen.getByRole('button', { name: 'voice.allow' }))
    act(() => {
      MockRecognition.instance.onresult?.({ resultIndex: 0, results: [[{ transcript: '  summarize asset risk  ' }]] })
    })
    expect(onTranscript).toHaveBeenCalledWith('summarize asset risk')
    expect(screen.getByText('voice.review')).toBeTruthy()
  })

  it('allows immediate stop and disables capture when chat is unavailable', () => {
    ;(window as unknown as { webkitSpeechRecognition: typeof MockRecognition }).webkitSpeechRecognition = MockRecognition
    const onTranscript = vi.fn()
    const view = render(<VoiceDictation language="en" disabled={false} onTranscript={onTranscript} />)
    fireEvent.click(screen.getByRole('button', { name: 'voice.start' }))
    fireEvent.click(screen.getByRole('button', { name: 'voice.allow' }))
    fireEvent.click(screen.getByRole('button', { name: 'voice.stop' }))
    expect(MockRecognition.instance.stop).toHaveBeenCalled()
    view.rerender(<VoiceDictation language="en" disabled={true} onTranscript={onTranscript} />)
    expect((screen.getByRole('button', { name: 'voice.start' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('explains unsupported browsers rather than attempting an API request', () => {
    render(<VoiceDictation language="en" disabled={false} onTranscript={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: 'voice.start' }))
    fireEvent.click(screen.getByRole('button', { name: 'voice.allow' }))
    expect(screen.getByText('voice.unsupported')).toBeTruthy()
  })
})
