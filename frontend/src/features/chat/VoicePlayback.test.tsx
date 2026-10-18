import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { VoicePlayback } from './VoicePlayback'
vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }))
class SpokenText {
  static last: SpokenText
  lang = ''
  rate = 1
  onstart: (() => void) | null = null
  onend: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(public text: string) { SpokenText.last = this }
}
const speak = vi.fn(), cancel = vi.fn()
beforeEach(() => {
  speak.mockClear(); cancel.mockClear()
  Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { speak, cancel } })
  Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: SpokenText })
})
afterEach(() => { vi.useRealTimers() })
describe('VoicePlayback', () => {
  it('only speaks after a click and distinguishes queued from audible playback', () => {
    render(<VoicePlayback text="Verified analysis summary" />)
    expect(speak).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'voice.readReply' }))
    expect(screen.getByText('voice.playbackQueued')).toBeInTheDocument()
    act(() => SpokenText.last.onstart?.())
    expect(screen.getByText('voice.playing')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'voice.stopReading' }))
    expect(cancel).toHaveBeenCalled()
    expect(screen.queryByText('voice.playing')).not.toBeInTheDocument()
  })
  it('transfers playback ownership and resets the previous reply', () => {
    const a = render(<VoicePlayback text="First reply" />)
    fireEvent.click(screen.getByRole('button', { name: 'voice.readReply' }))
    const b = render(<VoicePlayback text="الرد الثاني" />)
    fireEvent.click(screen.getByRole('button', { name: 'voice.readReply' }))
    expect(SpokenText.last.lang).toBe('ar-AE')
    expect(screen.getAllByRole('button', { name: 'voice.stopReading' })).toHaveLength(1)
    cancel.mockClear()
    a.unmount()
    expect(cancel).not.toHaveBeenCalled()
    b.unmount()
    expect(cancel).toHaveBeenCalledOnce()
  })
  it('reports a device that never starts playback', () => {
    vi.useFakeTimers()
    render(<VoicePlayback text="Delayed reply" />)
    fireEvent.click(screen.getByRole('button', { name: 'voice.readReply' }))
    act(() => vi.advanceTimersByTime(10000))
    expect(screen.getByText('voice.playbackUnavailable')).toBeInTheDocument()
  })
})
