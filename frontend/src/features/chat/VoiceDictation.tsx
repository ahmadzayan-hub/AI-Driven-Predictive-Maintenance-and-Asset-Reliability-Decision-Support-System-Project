import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../../i18n'
import { Icon } from '../../shared/components/Icon'

/** Browser speech recognition is an optional transport, not a new agent.
 * No hotword, no stored audio and no automatic submission. The transcription
 * enters the standard composer and must be reviewed before Send. Browsers
 * may process speech remotely; explicit consent is required before capture.
 */
interface SpeechRecognitionResult {
  transcript: string
}
interface VoiceRecognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onresult: ((event: { resultIndex?: number; results: ArrayLike<ArrayLike<SpeechRecognitionResult>> }) => void) | null
  onerror: ((event: { error?: string }) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}
interface VoiceWindow extends Window {
  SpeechRecognition?: new () => VoiceRecognition
  webkitSpeechRecognition?: new () => VoiceRecognition
}

export function speechRecognitionSupported(): boolean {
  if (typeof window === 'undefined') return false
  const speechWindow = window as VoiceWindow
  return Boolean(speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition)
}

interface DictationProps {
  language: 'en' | 'ar'
  disabled: boolean
  onTranscript: (text: string) => void
}

export function VoiceDictation({ language, disabled, onTranscript }: DictationProps) {
  const { t } = useI18n()
  const [consentOpen, setConsentOpen] = useState(false)
  const [consented, setConsented] = useState(false)
  const [listening, setListening] = useState(false)
  const [message, setMessage] = useState('')
  const recognitionRef = useRef<VoiceRecognition | null>(null)

  useEffect(() => () => {
    if (recognitionRef.current) {
      const recognition = recognitionRef.current
      recognition.onresult = null
      recognition.onerror = null
      recognition.onend = null
      recognition.stop()
      recognitionRef.current = null
    }
  }, [])

  function stop() {
    recognitionRef.current?.stop()
    setListening(false)
  }

  function start() {
    if (disabled || listening) return
    const browser = window as VoiceWindow
    const Constructor = browser.SpeechRecognition || browser.webkitSpeechRecognition
    if (!Constructor) {
      setMessage(t('voice.unsupported'))
      return
    }
    try {
      const recognition = new Constructor()
      recognition.lang = language === 'ar' ? 'ar-AE' : 'en-US'
      recognition.continuous = false
      recognition.interimResults = false
      recognition.maxAlternatives = 1
      recognition.onresult = (event) => {
        const final = event.results[event.resultIndex ?? 0]?.[0]?.transcript?.trim()
        if (final) {
          onTranscript(final)
          setMessage(t('voice.review'))
        }
      }
      recognition.onerror = (event) => {
        setMessage(event.error === 'not-allowed' || event.error === 'service-not-allowed'
          ? t('voice.denied') : t('voice.error'))
      }
      recognition.onend = () => {
        setListening(false)
        recognitionRef.current = null
      }
      recognitionRef.current = recognition
      recognition.start()
      setListening(true)
      setMessage(t('voice.listening'))
    } catch {
      recognitionRef.current = null
      setListening(false)
      setMessage(t('voice.denied'))
    }
  }

  return (
    <div className="voice-capture">
      <button type="button" className={listening ? 'voice-capture__button voice-capture__button--listening' : 'voice-capture__button'}
        disabled={disabled}
        aria-label={listening ? t('voice.stop') : t('voice.start')}
        aria-pressed={listening}
        title={listening ? t('voice.stop') : t('voice.start')}
        onClick={() => {
          if (listening) stop()
          else if (!consented) setConsentOpen(true)
          else start()
        }}>
        <Icon name="mic" size={19} />
      </button>
      {consentOpen ? (
        <div className="voice-capture__consent" role="group" aria-label={t('voice.privacyTitle')}>
          <strong>{t('voice.privacyTitle')}</strong>
          <p>{t('voice.privacyText')}</p>
          <div className="voice-capture__choices">
            <button type="button" onClick={() => {
              setConsented(true)
              setConsentOpen(false)
              start()
            }}>{t('voice.allow')}</button>
            <button type="button" onClick={() => setConsentOpen(false)}>{t('voice.cancel')}</button>
          </div>
        </div>
      ) : null}
      {message && !consentOpen ? <span className="voice-capture__status" role="status">{message}</span> : null}
    </div>
  )
}
