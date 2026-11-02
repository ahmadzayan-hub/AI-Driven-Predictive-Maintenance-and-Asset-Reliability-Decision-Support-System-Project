import { useEffect, useRef, useState } from 'react'
import { request as send } from '../../shared/api'
import type { DataContext, SessionState } from '../../shared/types'
import { usePack } from '../../i18n/pack'
import { jarvisMessages } from '../../i18n/jarvis'
import { jarvisSpeech } from './jarvisSpeech'
import { DataChatContext } from './DataChatContext'
import { VoiceDictation } from './VoiceDictation'
import { VoicePlayback } from './VoicePlayback'
import { useReadOnly } from '../../shared/readOnly'
import './jarvis.css'

export interface JarvisAnswer {
  text: string; source: 'rules'; why?: string
  result?: DataContext & { provenance: string; currency: string | null; llm_explanation: null;
    measures: { key: string; title: string; value: number | null; formula?: string; records?: number;
      records_unmeasured?: number; scale?: string; reason?: string }[] }
}

/** Read-only query transport, kept in this lazy chunk so first load stays within budget. */
export const jarvisApi = { query: (id: string, text: string, context: DataContext, language: 'en' | 'ar', signal: AbortSignal) =>
  send<JarvisAnswer>(`/api/sessions/${encodeURIComponent(id)}/data-query`, {
    method: 'POST', body: JSON.stringify({ text, language, scope: {
      run_id: context.run_id, dataset_id: context.dataset_id, source_sha256: context.source_sha256,
      analysis_revision: context.analysis_revision, filters: context.filters,
    } }), signal,
  }) }

/** Selection uses Miyaar's existing permission-bound API. */
export function JarvisWorkspace({ session, disabled = false }: { session: SessionState; disabled?: boolean }) {
  const { t, locale } = usePack(jarvisMessages)
  const readOnly = useReadOnly()
  const [context, setContext] = useState(session.data_context ?? null)
  const [draft, setDraft] = useState('')
  const [answer, setAnswer] = useState<JarvisAnswer | null>(null)
  const [asked, setAsked] = useState('')
  const [status, setStatus] = useState<'idle' | 'working' | 'failed' | 'stopped'>('idle')
  const [muted, setMuted] = useState(true)
  const [voiceKey, setVoiceKey] = useState(0)
  const [accepted, setAccepted] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const request = useRef<AbortController | null>(null)
  const generation = useRef(0)
  function invalidate() {
    generation.current++; request.current?.abort(); request.current = null
    setAnswer(null); setAccepted(false); setConfirmed(false); setStatus('idle'); setVoiceKey(k => k + 1)
  }
  useEffect(() => { invalidate(); setContext(session.data_context ?? null); setDraft('') }, [session.session_id, session.data_context, locale])
  useEffect(() => () => { generation.current++; request.current?.abort() }, [])
  function select(next: DataContext | null) { invalidate(); setContext(next); setDraft('') }
  function edit(text: string) { invalidate(); setDraft(text) }
  async function ask() {
    if (request.current || !context || !draft.trim() || disabled || session.ended) return
    invalidate()
    const token = generation.current
    const controller = new AbortController(); request.current = controller
    setStatus('working'); setAsked(draft.trim())
    try {
      const result = await jarvisApi.query(session.session_id, draft.trim(), context, locale, controller.signal)
      if (token !== generation.current) return
      setAnswer(result); setStatus('idle')
    } catch { if (token === generation.current) setStatus('failed') }
    finally { if (token === generation.current) request.current = null }
  }
  const speechText = jarvisSpeech(answer, locale)
  return <section className="jarvis" aria-label={t('title')}>
    <header className="jarvis__hero"><p className="eyebrow">{t('subtitle')}</p><h1>{t('title')}</h1><p>{t('boundary')}</p></header>
    <div className="jarvis__grid">
      <section className="jarvis__card"><h2>{t('input')}</h2>
        <DataChatContext session={session} disabled={disabled || session.ended} onSelected={select} onPending={() => { invalidate(); setContext(null) }} />
        <p>{context ? <bdi>{context.dataset_name} · {context.records} / {context.total_records}</bdi> : t('selectFirst')}</p>
        <label>{t('question')}<textarea value={draft} maxLength={2000} disabled={disabled || session.ended}
          onChange={e => edit(e.target.value)} dir="auto" /></label>
        <div className="jarvis__actions">{(['cost', 'follow', 'missing'] as const).map(key => <button className="btn btn--ghost" key={key} disabled={disabled} onClick={() => edit(t(key))}>{t(key)}</button>)}</div>
        <div className="jarvis__actions"><button className="btn btn--primary" disabled={!context || !draft.trim() || status === 'working' || disabled || session.ended} onClick={() => void ask()}>{t('ask')}</button>
          <button className="btn btn--ghost" onClick={() => { invalidate(); setStatus('stopped') }}>{t('stop')}</button>
          <button className="btn btn--ghost" aria-pressed={muted} onClick={() => { setMuted(!muted); setVoiceKey(k => k + 1) }}>{t(muted ? 'unmute' : 'muted')}</button></div>
        {!muted && <><p>{t('voiceHelp')}</p><VoiceDictation key={`${voiceKey}:${locale}`} language={locale} disabled={disabled || session.ended || status === 'working'} onTranscript={text => edit(text)} /></>}
        {status !== 'idle' && <p role={status === 'failed' ? 'alert' : 'status'}>{t(status)}</p>}
      </section>
      <aside className="jarvis__card"><h2>{t('function')}</h2><p>{t('functionText')}</p><h2>{t('value')}</h2><p>{t('valueText')}</p></aside>
    </div>
    <section className="jarvis__card" aria-live="polite"><h2>{t('output')}</h2>
      {!answer ? <p>{t('prompt')}</p> : <><p className="jarvis__question" dir="auto">{asked}</p><pre className="jarvis__evidence" dir="auto">{answer.text}</pre>
        {answer.result && <><h3>{t('source')}</h3><dl className="jarvis__sources"><dt>{t('source')}</dt><dd><bdi>{answer.result.dataset_name} · {answer.result.run_id}</bdi></dd>
          <dt>SHA-256</dt><dd><bdi>{answer.result.source_sha256}</bdi></dd><dt>{t('result')}</dt><dd><bdi>{answer.result.analysis_revision}</bdi></dd></dl>
          <a href={`/#/runs/${encodeURIComponent(answer.result.run_id)}`}>{t('source')}</a>
          <h3>{t('review')}</h3><p>{t('recommendation')}</p><p>{t('reviewLimit')}</p>
          <label><input type="checkbox" checked={accepted} disabled={readOnly || confirmed} onChange={e => setAccepted(e.target.checked)} /> {t('acknowledge')}</label>
          <button className="btn btn--primary" disabled={!accepted || confirmed || readOnly} onClick={() => setConfirmed(true)}>{t('confirm')}</button>
          {confirmed && <p role="status">{t('confirmed')}</p>}</>}
        <details><summary>{t('speech')}</summary><p>{t('speechHelp')}</p><p dir="auto">{speechText}</p></details>
        {!muted && <VoicePlayback key={`${voiceKey}:${asked}`} text={speechText} localOnly />}
      </>}
    </section>
  </section>
}
