import { forwardRef, lazy, Suspense, useImperativeHandle, useRef, useState } from 'react'
import { useI18n } from '../../i18n'
import { ViewBoundary } from '../../app/lazyViews'
import { Icon } from '../../shared/components/Icon'
import { useSessionDraft } from '../../shared/useSessionDraft'

const VoiceInput = lazy(() => import('./VoiceInput').then((module) => ({ default: module.VoiceInput })))

export interface ComposerHandle {
  insert: (text: string) => void
  focus: () => void
}

interface ComposerProps {
  onSend: (text: string) => void | Promise<boolean>
  busy: boolean
  disabled?: boolean
  offline?: boolean
  placeholder?: string
  draftKey?: string
  sessionId?: string
}

/** Multiline message input. Enter sends, Shift+Enter adds a line break.
 *  While a request is in flight the send action is disabled, which also
 *  prevents duplicate submissions. */
export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { onSend, busy, disabled = false, offline = false, placeholder, draftKey = 'composer', sessionId },
  ref,
) {
  const { t, tx, locale } = useI18n()
  const [text, setText] = useSessionDraft(draftKey, () => '')
  const [submitting, setSubmitting] = useState(false)
  const [capturing, setCapturing] = useState(false)
  const submittingRef = useRef(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useImperativeHandle(ref, () => ({
    insert(value: string) {
      setText(value)
      const textarea = textareaRef.current
      if (textarea) {
        textarea.focus()
        requestAnimationFrame(() => {
          textarea.setSelectionRange(value.length, value.length)
        })
      }
    },
    focus() {
      textareaRef.current?.focus()
    },
  }))

  function autosize() {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`
  }

  async function submit() {
    const value = text.trim()
    if (!value || busy || submittingRef.current || disabled || capturing) return
    submittingRef.current = true
    setSubmitting(true)
    try {
      const sent = await onSend(value)
      if (sent !== false) setText((current) => current.trim() === value ? '' : current)
    } catch { /* The caller reports the error; retain this draft for recovery. */ }
    finally { submittingRef.current = false; setSubmitting(false); requestAnimationFrame(autosize) }
  }

  return (
    <div className="composer">
      <ViewBoundary fallback={<div className="voice-console" role="alert"><p>{t('app.viewFailed')}</p>
        <button type="button" className="btn btn--ghost" onClick={() => window.location.reload()}>{t('app.reload')}</button>
      </div>}><Suspense fallback={<div className="voice-console"><div className="voice-console__copy">
        <strong>{t('voice.title')}</strong><span role="status">{t('voice.paused')}</span>
      </div></div>}>
        <VoiceInput
          sessionId={sessionId}
          language={locale}
          disabled={disabled || busy || submitting}
          onActiveChange={setCapturing}
          onTranscript={(value) => {
            setText((existing) => [existing.trim(), value].filter(Boolean).join(' '))
            requestAnimationFrame(() => { textareaRef.current?.focus(); autosize() })
          }}
        />
      </Suspense></ViewBoundary>

      <form
        className="composer__inner"
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        <label className="visually-hidden" htmlFor="composer-input">
          {t('composer.label')}
        </label>
        {/* dir="auto": a message is typed in whichever language the person
            thinks in, not necessarily the interface language. */}
        <textarea
          id="composer-input"
          ref={textareaRef}
          className="composer__input"
          rows={1}
          dir="auto"
          value={text}
          placeholder={disabled ? t(offline ? 'composer.offline' : 'composer.ended') : (placeholder ?? t('composer.placeholder'))}
          disabled={disabled}
          onChange={(event) => {
            setText(event.target.value)
            autosize()
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              void submit()
            }
          }}
        />
        <button
          type="submit"
          className="composer__send"
          disabled={busy || submitting || disabled || capturing || !text.trim()}
          aria-label={busy ? t('composer.sending') : t('composer.send')}
        >
          {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="send" size={18} />}
        </button>
      </form>
      <p className="composer__hint">
        <span>
          {tx('composer.hintSend', { enter: <kbd>Enter</kbd>, shift: <kbd>Shift</kbd> })}
        </span>
        <span>{tx('composer.hintCommands', { ctrl: <kbd>Ctrl</kbd>, k: <kbd>K</kbd> })}</span>
      </p>
    </div>
  )
})

