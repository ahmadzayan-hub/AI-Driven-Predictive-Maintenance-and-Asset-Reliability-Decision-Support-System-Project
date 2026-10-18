import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { VoicePlayback } from './VoicePlayback'

vi.mock('../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }))

class SpokenText {
  static last: SpokenText
  lang = ''
  rate = 1
  onend: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(public text: string) { SpokenText.last = this }
}

afterEach(() => {
  delete (window as unknown as { SpeechSynthesisUtterance?: typeof SpokenText }).SpeechSynthesisUtterance
})

describe('VoicePlayback', () => {
  it('never speaks until the user requests playback', () => {
    const speak = vi.fn(), cancel = vi.fn()
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true, value: { speak, cancel },
    })
    ;(window as unknown as { SpeechSynthesisUtterance: typeof SpokenText }).SpeechSynthesisUtterance = SpokenText
    const view = render(<VoicePlayback text="Verified analysis summary" />)
    expect(speak).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'voice.readReply' }))
    expect(speak).toHaveBeenCalledOnce()
    expect(SpokenText.last.lang).toBe('en-US')
    fireEvent.click(screen.getByRole('button', { name: 'voice.stopReading' }))
    expect(cancel).toHaveBeenCalled()
    view.unmount()
  })
})
