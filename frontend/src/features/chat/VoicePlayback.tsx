import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { Icon } from '../../shared/components/Icon'

/** Optional browser text-to-speech for a user-selected agent reply.
 * It never starts on its own or executes the reply's contents as actions. */
export function VoicePlayback({ text }: { text: string }) {
  const { t } = useI18n()
  const [speaking, setSpeaking] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
  }, [])

  function toggle() {
    if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {
      setError(true)
      return
    }
    const engine = window.speechSynthesis
    if (speaking) {
      engine.cancel()
      setSpeaking(false)
      return
    }
    if (!text.trim()) return
    engine.cancel()
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 1800))
    utterance.lang = /[\u0600-\u06ff]/.test(text) ? 'ar-AE' : 'en-US'
    utterance.rate = 0.95
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => { setSpeaking(false); setError(true) }
    try {
      engine.speak(utterance)
      setSpeaking(true)
      setError(false)
    } catch {
      setError(true)
    }
  }

  return <>
    <button type="button" className="msg__copy" onClick={toggle}
      aria-label={speaking ? t('voice.stopReading') : t('voice.readReply')}
      aria-pressed={speaking}>
      <Icon name={speaking ? 'volumeOff' : 'volume'} size={15} />
      {speaking ? t('voice.stopReading') : t('voice.readReply')}
    </button>
    {error ? <span role="status">{t('voice.playbackUnavailable')}</span> : null}
  </>
}
