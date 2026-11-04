import { useEffect, useRef, useState } from 'react'
import { jarvisApi } from './jarvisApi'
import type { DataContext, SessionState } from '../../shared/types'
import { usePack } from '../../i18n/pack'
import { formatNumberIn } from '../../i18n'
import { jarvisMessages } from '../../i18n/jarvis'
import { jarvisSpeech } from './jarvisSpeech'
import { DataChatContext } from './DataChatContext'
import { describeFilters } from './describeFilters'
import { VoiceDictation, type CaptureState } from './VoiceDictation'
import { VoicePlayback } from './VoicePlayback'
import { JarvisCore, type CoreState } from './JarvisCore'
import { useReadOnly } from '../../shared/readOnly'
import { faithfulOptions } from '../../shared/faithfulNumber'
import './jarvis.css'

export interface JarvisAnswer {
  text: string; source: 'rules'; why?: string
  result?: DataContext & { provenance: string; currency: string | null; llm_explanation: null;
    measures: { key: string; title: string; value: number | null; formula?: string; records?: number;
      records_unmeasured?: number; scale?: string; reason?: string }[] }
}

/** Read-only query transport; selection uses Miyaar's existing permission-bound API. */
export function JarvisWorkspace({ session, disabled = false, embedded = false, prompt, reportId }: { session: SessionState; disabled?: boolean; embedded?: boolean; prompt?: { text: string; n: number }; reportId?: string }) {
  const { t, locale } = usePack(jarvisMessages)
  const readOnly = useReadOnly()
  const [context, setContext] = useState(session.data_context ?? null)
  const [selecting, setSelecting] = useState(false)
  const [draft, setDraft] = useState(prompt?.text ?? '')
  const [answer, setAnswer] = useState<JarvisAnswer | null>(null)
  const [asked, setAsked] = useState('')
  const [status, setStatus] = useState<'idle' | 'working' | 'failed' | 'stopped'>('idle')
  const [muted, setMuted] = useState(true)
  const [voiceKey, setVoiceKey] = useState(0)
  const [capture, setCapture] = useState<CaptureState | 'unavailable'>('idle')
  const [playback, setPlayback] = useState<'idle' | 'queued' | 'speaking' | 'error'>('idle')
  const [playbackKey, setPlaybackKey] = useState(0)
  const [accepted, setAccepted] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const request = useRef<AbortController | null>(null)
  const generation = useRef(0)
  function invalidate() {
    generation.current++; request.current?.abort(); request.current = null
    setAnswer(null); setAccepted(false); setConfirmed(false); setStatus('idle'); setVoiceKey(k => k + 1)
    setCapture('idle'); setPlayback('idle')
  }
  useEffect(() => { invalidate(); setContext(session.data_context ?? null); setDraft('') }, [session.session_id, session.data_context, locale])
  // A screen section may hand over a question; it fills the draft after a
  // (re)binding has cleared it, and the reader still presses Ask.
  useEffect(() => { if (prompt) setDraft(prompt.text) }, [prompt, session.session_id, session.data_context])
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
  // Figures read as figures: grouped, at most two decimals. The full value stays in the references.
  const show = (value: number) => formatNumberIn(locale, value, faithfulOptions(value))
  const capturing = ['requesting', 'listening', 'processing'].includes(capture)
  const coreState: CoreState = status === 'failed' || capture === 'error' || capture === 'unavailable' || playback === 'error' ? 'unavailable'
    : status === 'working' ? 'processing' : capture === 'listening' ? 'listening'
    : capture === 'requesting' ? 'requesting' : capture === 'processing' ? 'transcribing' : playback === 'queued' ? 'preparing'
    : playback === 'speaking' ? 'speaking' : 'ready'
  const units: Record<string, string> = { percent: '%', hours: t('hours'), years: t('years'), count: t('count'), ratio: t('times'), money: answer?.result?.currency ?? t('currencyUnknown') }
  return <section className={`jarvis${embedded ? ' jarvis--embedded' : ''}`} aria-label={t('title')}>
    {embedded ? <p>{t('boundary')}</p> : <header className="jarvis__hero"><p className="eyebrow">{t('subtitle')}</p><h1>{t('title')}</h1><p>{t('boundary')}</p></header>}
    <div className="jarvis__console">
      <JarvisCore state={coreState} muted={muted} onToggleAudio={() => { setMuted(!muted); setVoiceKey(k => k + 1); setCapture('idle'); setPlayback('idle') }}>
        <div className="jarvis__actions"><button className="btn btn--ghost" onClick={() => { invalidate(); setStatus('stopped') }}>{t('stop')}</button></div>
        {!muted && <><p className="jarvis-core__privacy">{t('voiceHelp')}</p><VoiceDictation key={`${voiceKey}:${locale}`} language={locale}
          disabled={disabled || session.ended || selecting || !context || status === 'working'} onTranscript={text => edit(text)} onStateChange={setCapture}
          onActiveChange={active => { if (active) { setPlaybackKey(k => k + 1); setPlayback('idle') } }} />
          {answer && <VoicePlayback key={`${voiceKey}:${playbackKey}:${asked}`} text={speechText} language={locale} disabled={capturing} localOnly onStateChange={setPlayback} />}</>}
        {playback === 'error' && <p>{t('localVoiceUnavailable')}</p>}
      </JarvisCore>
      <section className="jarvis__card jarvis__composer"><h2>{t(embedded ? 'question' : 'input')}</h2>
        {!embedded && <DataChatContext session={session} want={reportId} disabled={disabled || session.ended} onSelected={select} onPending={pending => { setSelecting(pending); if (pending) { invalidate(); setContext(null) } }} />}
        {/* The scope every answer is calculated on, always in view: data, records, filters. */}
        <p className="jarvis__scope">{context ? <><bdi>{context.dataset_name}</bdi> · <bdi>{context.records} / {context.total_records}</bdi> · {t('periodLabel')}: <bdi>{context.period ? `${context.period.from} – ${context.period.to}` : t('noPeriod')}</bdi> · {t('filtersLabel')}: <bdi>{describeFilters(context.filters) || t('allRecords')}</bdi></> : t('selectFirst')}</p>
        <label>{t('question')}<textarea value={draft} maxLength={2000} disabled={disabled || session.ended || selecting}
          onChange={e => edit(e.target.value)} dir="auto" /></label>
        <div className="jarvis__actions">{(['cost', 'follow'] as const).map(key => <button className="btn btn--ghost" key={key} disabled={disabled || session.ended || selecting} onClick={() => edit(t(key))}>{t(key)}</button>)}</div>
        <p className="jarvis__hint">{t('forecastNote')}</p>
        <p className="jarvis__hint">{t('transcript')}</p>
        <div className="jarvis__actions"><button className="btn btn--primary" disabled={!context || !draft.trim() || status === 'working' || disabled || session.ended || capturing} onClick={() => void ask()}>{t('ask')}</button></div>
        {status !== 'idle' && <p role={status === 'failed' ? 'alert' : 'status'}>{t(status)}</p>}
      </section>
    <section className="jarvis__card jarvis__answer" aria-live="polite"><h2>{t(embedded ? 'result' : 'output')}</h2>
      {!answer ? <p>{t('prompt')}</p> : <><p className="jarvis__question" dir="auto">{asked}</p>
        {/* What kind of answer this is, before anything else is read. */}
        <p className="performance-value jarvis__state" data-performance={!answer.result ? 'unavailable' : answer.result.measures.some(m => m.value === null) ? 'okay' : 'good'}>
          <span className="performance-value__status">{t(!answer.result ? 'stateUnsupported' : answer.result.measures.some(m => m.value === null) ? 'stateInsufficient' : 'stateCalculated')}</span></p>
        {!answer.result && <pre className="jarvis__evidence" dir="auto">{answer.text}</pre>}
        {answer.result && <>{answer.result.measures[0] && <p className="jarvis__lead" dir="auto">{t('lead', { title: answer.result.measures[0].title,
          value: answer.result.measures[0].value === null ? t('noValue') : `${show(answer.result.measures[0].value)} ${units[answer.result.measures[0].scale ?? ''] ?? t('unitUnknown')}`,
          records: answer.result.records, total: answer.result.total_records })}</p>}
          <div className="jarvis__metrics">{answer.result.measures.map(m => <article key={m.key}>
          <h3>{m.title}</h3><p className="jarvis__metric-value">{m.value === null ? t('noValue') : <bdi>{show(m.value)} <small>{units[m.scale ?? ''] ?? t('unitUnknown')}</small></bdi>}</p>
          <p>{m.records === undefined || m.records_unmeasured === undefined ? t('coverageUnknown') : t('speechCoverage', { measured: m.records, unmeasured: m.records_unmeasured })}</p>
          {(m.reason || m.value === null) && <p>{m.reason ?? t('undefinedReason')}</p>}
        </article>)}</div><p className="jarvis__hint">{t('speechScope', { records: answer.result.records, total: answer.result.total_records })}</p>
          <details><summary>{t('references')}</summary><pre className="jarvis__evidence" dir="auto">{answer.text}</pre></details>
          <details className="jarvis__measures"><summary>{t('measures')}</summary><table><caption>{t('evidenceView')}</caption><thead><tr><th>{t('metric')}</th><th>{t('valueUnit')}</th><th>{t('formula')}</th><th>{t('coverage')}</th></tr></thead><tbody>{answer.result.measures.map(m => <tr key={m.key}><th scope="row">{m.title}</th><td>{m.value === null ? t('noValue') : <bdi>{show(m.value)} {units[m.scale ?? ''] ?? t('unitUnknown')}</bdi>}{m.reason && <p>{m.reason}</p>}</td><td><bdi>{m.formula}</bdi></td><td>{m.records ?? '-'} / {m.records_unmeasured ?? '-'}</td></tr>)}</tbody></table></details>
          <details><summary>{t('source')}</summary><dl className="jarvis__sources"><dt>{t('source')}</dt><dd><bdi>{answer.result.dataset_name} · {answer.result.run_id}</bdi></dd>
          <dt>SHA-256</dt><dd><bdi>{answer.result.source_sha256}</bdi></dd><dt>{t('result')}</dt><dd><bdi>{answer.result.analysis_revision}</bdi></dd></dl></details>
          <a href={`/#/runs/${encodeURIComponent(answer.result.run_id)}`}>{t('source')}</a>
          <h3>{t('review')}</h3><p>{t('recommendation')}</p><p>{t('reviewLimit')}</p>
          <label><input type="checkbox" checked={accepted} disabled={readOnly || confirmed} onChange={e => setAccepted(e.target.checked)} /> {t('acknowledge')}</label>
          <button className="btn btn--primary" disabled={!accepted || confirmed || readOnly} onClick={() => setConfirmed(true)}>{t('confirm')}</button>
          {confirmed && <p role="status">{t('confirmed')}</p>}</>}
        <details><summary>{t('speech')}</summary><p>{t('speechHelp')}</p><p dir="auto">{speechText}</p></details>
      </>}
    </section>
    </div>
    {!embedded && <details className="jarvis__method"><summary>{t('function')}</summary><p>{t('functionText')}</p><h2>{t('value')}</h2><p>{t('valueText')}</p></details>}
  </section>
}
