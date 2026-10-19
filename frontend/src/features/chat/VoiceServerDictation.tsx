import { useEffect, useRef, useState } from 'react'
import { usePack } from '../../i18n/pack'
import { api, ApiError } from '../../shared/api'
import type { VoiceStatus } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import { VoiceDictation } from './VoiceDictation'
import type { DictationProps } from './VoiceDictation'
import { voiceMessages } from './voiceMessages'

type CaptureState = 'idle' | 'requesting' | 'listening' | 'processing' | 'review' | 'error'
type LocalMessage = keyof typeof voiceMessages.en
type Props = DictationProps & { sessionId: string; status: VoiceStatus }

/** Records only after consent. Audio is bounded and released on every exit;
 * the result is a draft insertion, never a chat submission or agent action. */
export default function VoiceServerDictation({ language, disabled, onTranscript, onActiveChange, sessionId, status }: Props) {
  const { t } = usePack(voiceMessages)
  const [state, setState] = useState<CaptureState>('idle')
  const [message, setMessage] = useState<LocalMessage>('voiceLocal.ready')
  const [consentOpen, setConsentOpen] = useState(false)
  const [consented, setConsented] = useState(false)
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const upload = useRef<AbortController | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generation = useRef(0)
  const activeRef = useRef(false)
  const transcriptCallback = useRef(onTranscript)
  transcriptCallback.current = onTranscript
  const activeCallback = useRef(onActiveChange)
  activeCallback.current = onActiveChange
  const supported = window.isSecureContext !== false && typeof MediaRecorder !== 'undefined'
    && Boolean(navigator.mediaDevices?.getUserMedia)
  const mimeType = supported ? ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']
    .find((type) => MediaRecorder.isTypeSupported(type)) : undefined
  const active = state === 'requesting' || state === 'listening' || state === 'processing'

  function stopTracks() {
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
  }
  function detach() {
    generation.current++
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
    upload.current?.abort()
    upload.current = null
    const current = recorder.current
    recorder.current = null
    if (current) {
      current.onstart = current.ondataavailable = current.onstop = current.onerror = null
      try { if (current.state !== 'inactive') current.stop() } catch { /* Already stopped. */ }
    }
    stopTracks()
    activeRef.current = false
    activeCallback.current?.(false)
  }
  function cancel() {
    detach()
    setState('idle')
    setMessage('voiceLocal.ready')
    setConsentOpen(false)
  }
  function fail(key: LocalMessage) {
    detach()
    setState('error')
    setMessage(key)
  }
  useEffect(() => {
    if (disabled) cancel()
    return () => detach()
  }, [disabled, language, sessionId])
  useEffect(() => {
    setState('idle'); setMessage('voiceLocal.ready'); setConsentOpen(false)
  }, [language, sessionId])

  function finishRecording(current: MediaRecorder) {
    if (timer.current) clearTimeout(timer.current)
    setState('processing')
    setMessage('voiceLocal.processing')
    timer.current = setTimeout(() => fail('voiceLocal.error'), 6000)
    try { current.stop(); stopTracks() } catch { fail('voiceLocal.error') }
  }
  function stop() {
    const current = recorder.current
    if (!current || state !== 'listening') { cancel(); return }
    finishRecording(current)
  }
  async function start() {
    if (disabled || activeRef.current || !supported || !mimeType) return
    detach()
    const token = generation.current
    activeRef.current = true
    activeCallback.current?.(true)
    setState('requesting')
    setMessage('voiceLocal.requesting')
    timer.current = setTimeout(() => {
      if (generation.current === token) fail('voiceLocal.error')
    }, 12_000)
    try {
      const capture = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (generation.current !== token) { capture.getTracks().forEach((track) => track.stop()); return }
      stream.current = capture
      const current = new MediaRecorder(capture, { mimeType })
      recorder.current = current
      const chunks: Blob[] = []
      let bytes = 0
      const maxBytes = Math.min(2_000_000, status.max_bytes || 2_000_000)
      current.onstart = () => {
        if (generation.current !== token) return
        if (timer.current) clearTimeout(timer.current)
        setState('listening')
        setMessage('voiceLocal.listening')
        // Leave one second for container timestamps and event scheduling; the
        // server enforces the advertised 30-second decoded-audio limit.
        timer.current = setTimeout(() => {
          if (generation.current !== token) return
          finishRecording(current)
        }, Math.max(1, Math.min(30, status.max_seconds || 30) - 1) * 1000)
      }
      current.ondataavailable = (event) => {
        if (generation.current !== token || !event.data.size) return
        bytes += event.data.size
        if (bytes > maxBytes) { fail('voiceLocal.tooLarge'); return }
        chunks.push(event.data)
      }
      current.onerror = () => { if (generation.current === token) fail('voiceLocal.error') }
      current.onstop = async () => {
        if (generation.current !== token) return
        if (timer.current) clearTimeout(timer.current)
        timer.current = null
        recorder.current = null
        stopTracks()
        if (!bytes) { fail('voiceLocal.noSpeech'); return }
        setState('processing')
        setMessage('voiceLocal.processing')
        const controller = new AbortController()
        upload.current = controller
        try {
          const result = await api.transcribeSession(sessionId,
            new Blob(chunks, { type: current.mimeType || mimeType }), language, controller.signal)
          if (generation.current !== token) return
          const text = result?.text?.trim()
          if (!text) { fail('voiceLocal.noSpeech'); return }
          detach()
          transcriptCallback.current(text)
          setState('review')
          setMessage('voiceLocal.review')
        } catch (error) {
          if (generation.current !== token) return
          const code = error instanceof ApiError ? error.status : 0
          fail(code === 401 || code === 403 ? 'voiceLocal.auth'
            : code === 503 ? 'voiceLocal.unavailable' : code === 429 ? 'voiceLocal.busy'
              : code === 422 ? 'voiceLocal.noSpeech' : code === 413 ? 'voiceLocal.tooLarge' : 'voiceLocal.error')
        }
      }
      current.start(250)
    } catch (error) {
      if (generation.current !== token) return
      const name = error && typeof error === 'object' && 'name' in error ? error.name : ''
      fail(name === 'NotAllowedError' || name === 'SecurityError' ? 'voiceLocal.denied'
        : name === 'NotFoundError' || name === 'NotReadableError' ? 'voiceLocal.noMicrophone' : 'voiceLocal.error')
    }
  }

  if (!supported || !mimeType) return <><p role="status">{t('voiceLocal.unsupported')}</p><VoiceDictation
    language={language} disabled={disabled} onTranscript={onTranscript} onActiveChange={onActiveChange} /></>

  return <div className="voice-console" data-state={state}>
    <div className="voice-console__row">
      <button type="button" className="voice-capture__button" disabled={disabled}
        aria-label={state === 'listening' ? t('voiceLocal.stop') : active ? t('voiceLocal.cancel') : t('voiceLocal.start')}
        aria-pressed={active} onClick={() => {
          if (state === 'listening') stop()
          else if (active) cancel()
          else if (!consented) setConsentOpen(true)
          else void start()
        }}><Icon name={active ? 'x' : 'mic'} size={18} /></button>
      <div className="voice-console__copy"><strong>{t('voiceLocal.title')}</strong>
        <span role="status">{disabled ? t('voice.paused') : t(message)}</span></div>
      {state === 'listening' ? <span className="voice-wave" aria-hidden="true"><i /><i /><i /><i /><i /></span> : null}
      {state === 'requesting' || state === 'processing' ? <span className="spinner" aria-hidden="true" /> : null}
      {state === 'listening' ? <button type="button" className="btn btn--ghost"
        onClick={cancel}>{t('voiceLocal.cancel')}</button> : null}
    </div>
    {consentOpen ? <div className="voice-console__consent" role="group" aria-label={t('voiceLocal.privacyTitle')}>
      <strong>{t('voiceLocal.privacyTitle')}</strong><p>{t('voiceLocal.privacy')}</p>
      <div className="voice-capture__choices"><button type="button" className="btn btn--primary" disabled={disabled}
        onClick={() => { setConsented(true); setConsentOpen(false); void start() }}>{t('voiceLocal.allow')}</button>
      <button type="button" className="btn btn--ghost" onClick={() => setConsentOpen(false)}>{t('voiceLocal.cancel')}</button></div>
    </div> : null}
  </div>
}
