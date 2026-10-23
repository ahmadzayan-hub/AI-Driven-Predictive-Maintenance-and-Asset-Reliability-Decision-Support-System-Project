import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../../i18n'
import type { MessageKey } from '../../i18n'
import { Icon } from '../../shared/components/Icon'

interface RecognitionResult extends ArrayLike<{ transcript: string }> { isFinal: boolean }
export interface VoiceRecognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onstart: (() => void) | null
  onaudioend: (() => void) | null
  onresult: ((event: { resultIndex?: number; results: ArrayLike<RecognitionResult> }) => void) | null
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
  const browser = window as VoiceWindow
  return Boolean(browser.SpeechRecognition || browser.webkitSpeechRecognition)
}
export interface DictationProps {
  language: 'en' | 'ar'
  disabled: boolean
  onTranscript: (text: string) => void
  onActiveChange?: (active: boolean) => void
}
type CaptureState = 'idle' | 'requesting' | 'listening' | 'processing' | 'review' | 'error'

/** Browser recognition is an optional, consented transport. Interim text is
 * preview only. Final text becomes an editable draft, never a submitted action. */
export function VoiceDictation({ language, disabled, onTranscript, onActiveChange }: DictationProps) {
  const { t } = useI18n()
  const supported = speechRecognitionSupported()
  const insecure = window.isSecureContext === false
  const [consentOpen, setConsentOpen] = useState(false)
  const [consented, setConsented] = useState(false)
  const [state, setState] = useState<CaptureState>('idle')
  const [message, setMessage] = useState<MessageKey>('voice.ready')
  const [preview, setPreview] = useState('')
  const [permission, setPermission] = useState<PermissionState | 'unknown'>('unknown')
  const recognitionRef = useRef<VoiceRecognition | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const transcriptCallback = useRef(onTranscript)
  transcriptCallback.current = onTranscript
  const activeCallback = useRef(onActiveChange)
  activeCallback.current = onActiveChange
  const active = state === 'requesting' || state === 'listening' || state === 'processing'

  function detach() {
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
    const recognition = recognitionRef.current
    recognitionRef.current = null
    if (recognition) {
      recognition.onstart = recognition.onaudioend = recognition.onend = null
      recognition.onresult = recognition.onerror = null
      try { recognition.stop() } catch { /* Already stopped by the browser. */ }
    }
    activeCallback.current?.(false)
  }
  function cancel() {
    detach()
    setState('idle')
    setMessage('voice.ready')
    setPreview('')
  }
  useEffect(() => {
    let disposed = false
    let status: PermissionStatus | undefined
    const update = () => { if (!disposed && status) setPermission(status.state) }
    navigator.permissions?.query({ name: 'microphone' as PermissionName })
      .then((result) => {
        if (disposed) return
        status = result
        update()
        status.addEventListener('change', update)
      }).catch(() => { /* Not every browser exposes microphone permissions. */ })
    return () => { disposed = true; status?.removeEventListener('change', update) }
  }, [])

  useEffect(() => {
    if (disabled) { cancel(); setConsentOpen(false) }
    // A different recognition locale needs a fresh user gesture.
    return () => detach()
  }, [disabled, language])
  useEffect(() => { setState('idle'); setMessage('voice.ready'); setPreview('') }, [language])

  function fail(key: MessageKey) {
    detach()
    setState('error')
    setMessage(key)
    setPreview('')
  }
  function bound(milliseconds: number, key: MessageKey) {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => fail(key), milliseconds)
  }
  function stop() {
    if (state === 'requesting') { cancel(); return }
    setState('processing')
    setMessage('voice.processing')
    bound(6000, 'voice.noSpeech')
    try { recognitionRef.current?.stop() } catch { fail('voice.error') }
  }
  function start() {
    if (disabled || recognitionRef.current) return
    const browser = window as VoiceWindow
    const Constructor = browser.SpeechRecognition || browser.webkitSpeechRecognition
    if (!Constructor) { fail('voice.unsupported'); return }
    if (insecure) { fail('voice.insecure'); return }
    setPreview('')
    setState('requesting')
    setMessage('voice.requesting')
    activeCallback.current?.(true)
    try {
      const recognition = new Constructor()
      recognitionRef.current = recognition
      recognition.lang = language === 'ar' ? 'ar-AE' : 'en-US'
      recognition.continuous = false
      recognition.interimResults = true
      recognition.maxAlternatives = 1
      recognition.onstart = () => {
        if (recognitionRef.current !== recognition) return
        setPermission('granted')
        setState('listening')
        setMessage('voice.listening')
        bound(60000, 'voice.noSpeech')
      }
      recognition.onaudioend = () => {
        if (recognitionRef.current !== recognition) return
        setState('processing')
        setMessage('voice.processing')
        bound(6000, 'voice.noSpeech')
      }
      recognition.onresult = (event) => {
        if (recognitionRef.current !== recognition) return
        const interim: string[] = [], finals: string[] = []
        for (let i = event.resultIndex ?? 0; i < event.results.length; i++) {
          const result = event.results[i], text = result?.[0]?.transcript?.trim()
          if (!text) continue
          if (result.isFinal) finals.push(text)
          else interim.push(text)
        }
        setPreview([...finals, ...interim].join(' '))
        if (finals.length) {
          // Invalidate callbacks before adding text, so end/duplicate events
          // cannot add the same words a second time.
          detach()
          transcriptCallback.current(finals.join(' '))
          setState('review')
          setMessage('voice.review')
          setPreview('')
        }
      }
      recognition.onerror = ({ error }) => {
        if (recognitionRef.current !== recognition) return
        if (error === 'not-allowed' || error === 'service-not-allowed') {
          setPermission('denied'); fail('voice.denied')
        } else if (error === 'no-speech') fail('voice.noSpeech')
        else if (error === 'audio-capture') fail('voice.noMicrophone')
        else if (error === 'network') fail('voice.network')
        else fail('voice.error')
      }
      recognition.onend = () => {
        if (recognitionRef.current !== recognition) return
        fail('voice.noSpeech')
      }
      bound(12000, 'voice.startTimeout')
      recognition.start()
    } catch { fail('voice.error') }
  }
  const status = !supported ? 'voice.unsupported' : insecure ? 'voice.insecure'
    : disabled ? 'voice.paused' : permission === 'denied' ? 'voice.denied' : message

  return <div className="voice-console" data-state={state}>
    <div className="voice-console__row">
      <button type="button" className="voice-capture__button"
        disabled={disabled || !supported || insecure}
        aria-label={t('voice.toggle')}
        title={active ? t('voice.stop') : t('voice.start')}
        aria-pressed={active}
        onClick={() => {
          if (state === 'processing') cancel()
          else if (active) stop()
          else if (!consented) setConsentOpen(true)
          else start()
        }}>
        <Icon name={active ? 'x' : 'mic'} size={18} />
      </button>
      <div className="voice-console__copy">
        <strong>{t('voice.title')}</strong>
        <span role="status">{t(status)}</span>
      </div>
      {state === 'listening' ? <span className="voice-wave" aria-hidden="true">
        <i /><i /><i /><i /><i />
      </span> : null}
      {state === 'requesting' || state === 'processing' ? <span className="spinner" aria-hidden="true" /> : null}
      <span className="voice-console__permission">{t(
        permission === 'granted' ? 'voice.permissionGranted'
          : permission === 'denied' ? 'voice.permissionDenied' : 'voice.permissionPrompt'
      )}</span>
    </div>
    {preview ? <p className="voice-console__preview"><span>{t('voice.preview')}</span> <bdi>{preview}</bdi></p> : null}
    {consentOpen ? <div className="voice-console__consent" role="group" aria-label={t('voice.privacyTitle')}>
      <strong>{t('voice.privacyTitle')}</strong>
      <p>{t('voice.privacyText')}</p>
      <div className="voice-capture__choices">
        <button type="button" className="btn btn--primary" disabled={disabled} onClick={() => {
          setConsented(true); setConsentOpen(false); start()
        }}>{t('voice.allow')}</button>
        <button type="button" className="btn btn--ghost" onClick={() => setConsentOpen(false)}>{t('voice.cancel')}</button>
      </div>
    </div> : null}
  </div>
}
