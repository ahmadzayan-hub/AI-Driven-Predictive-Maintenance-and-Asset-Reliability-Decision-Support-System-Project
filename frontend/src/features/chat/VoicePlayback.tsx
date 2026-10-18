import { useCallback, useEffect, useRef, useState } from 'react'
import { useI18n } from '../../i18n'
import { Icon } from '../../shared/components/Icon'

// Ownership is shared so selecting a different reply also resets the old UI.
let stopCurrent: (() => void) | null = null

export function VoicePlayback({ text }: { text: string }) {
  const { t } = useI18n()
  const [state, setState] = useState<'idle' | 'queued' | 'speaking' | 'error'>('idle')
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const active = state === 'queued' || state === 'speaking'

  function release() {
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
    const utterance = utteranceRef.current
    if (utterance) utterance.onstart = utterance.onend = utterance.onerror = null
    utteranceRef.current = null
    if (stopCurrent === stop) {
      stopCurrent = null
      window.speechSynthesis?.cancel()
    }
  }
  const stop = useCallback(() => { release(); setState('idle') }, [])
  useEffect(() => () => release(), [text])

  function toggle() {
    if (active) { stop(); return }
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) { setState('error'); return }
    if (!text.trim()) return
    stopCurrent?.()
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 1800))
    utterance.lang = /[\u0600-\u06ff]/.test(text) ? 'ar-AE' : 'en-US'
    utterance.rate = 0.95
    utteranceRef.current = utterance
    stopCurrent = stop
    const fail = () => { release(); setState('error') }
    utterance.onstart = () => {
      if (utteranceRef.current !== utterance) return
      if (timer.current) clearTimeout(timer.current)
      setState('speaking')
    }
    utterance.onend = () => { release(); setState('idle') }
    utterance.onerror = fail
    setState('queued')
    timer.current = setTimeout(fail, 10000)
    try { window.speechSynthesis.speak(utterance) } catch { fail() }
  }
  return <>
    <button type="button" className="msg__copy" onClick={toggle}
      aria-label={active ? t('voice.stopReading') : t('voice.readReply')} aria-pressed={active}>
      <Icon name={active ? 'volumeOff' : 'volume'} size={15} />
      {active ? t('voice.stopReading') : t('voice.readReply')}
    </button>
    {state !== 'idle' ? <span className="msg__source" role="status">{t(
      state === 'error' ? 'voice.playbackUnavailable' : state === 'queued' ? 'voice.playbackQueued' : 'voice.playing'
    )}</span> : null}
    {active && text.length > 1800 ? <span className="msg__source">{t('voice.playbackLimit')}</span> : null}
  </>
}
