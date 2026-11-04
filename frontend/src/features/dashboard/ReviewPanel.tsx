import { useEffect, useRef, useState } from 'react'
import { API_BASE, ApiError, authHeaders, request } from '../../shared/api'
import { definePack, usePack } from '../../i18n/pack'
import type { RunExecutive, TableFilter } from '../../shared/types'

/** One review step for every executive output (ADR 2026-11-04-shared-review):
 *  the state of each output for this exact brief, a decision with a comment,
 *  the history, and the executive video rendered from the same snapshot. */
const messages = definePack({
  title: 'Review before release', help: 'Each output is reviewed as the exact file produced from this brief. Any later change needs a new review. Release still needs the run’s own approval.',
  dashboard: 'Dashboard brief', html: 'Report (HTML, print to PDF)', docx: 'Word document', slides: 'Slides', video: 'Executive video',
  draft: 'Draft · not reviewed', approved: 'Approved', changes_requested: 'Changes requested', changed_since_review: 'Changed since review · needs a new review',
  failed: 'Failed export', not_rendered: 'Not rendered', by: '{who} · {time}', comment: 'Comment', approve: 'Approve', ask: 'Request changes',
  render: 'Render video', rendering: 'Rendering on this host… about a minute', preview: 'Preview', download: 'Download MP4', subtitles: 'Subtitles (WebVTT)',
  unavailable: 'Video cannot be rendered on this host: {missing}.', history: 'Review history', none: 'No review recorded yet.',
  snapshot: 'Snapshot {id}', error: 'The review state could not be loaded.', saved: 'Decision recorded.', trace: 'What the video shows and where each figure comes from',
}, {
  title: 'المراجعة قبل النشر', help: 'يُراجع كل مخرج بوصفه الملف نفسه الناتج من هذا الموجز. أي تغيير لاحق يتطلب مراجعة جديدة. ويظل النشر بحاجة إلى اعتماد التشغيل نفسه.',
  dashboard: 'موجز اللوحة', html: 'التقرير (HTML، الطباعة إلى PDF)', docx: 'مستند Word', slides: 'الشرائح', video: 'الفيديو التنفيذي',
  draft: 'مسودة · لم تُراجع', approved: 'معتمد', changes_requested: 'مطلوب تعديل', changed_since_review: 'تغير بعد المراجعة · يحتاج مراجعة جديدة',
  failed: 'تصدير فاشل', not_rendered: 'لم يُنتج', by: '{who} · {time}', comment: 'تعليق', approve: 'اعتماد', ask: 'طلب تعديل',
  render: 'إنتاج الفيديو', rendering: 'جارٍ الإنتاج على هذا الخادم… نحو دقيقة', preview: 'معاينة', download: 'تنزيل MP4', subtitles: 'الترجمة (WebVTT)',
  unavailable: 'لا يمكن إنتاج الفيديو على هذا الخادم: {missing}.', history: 'سجل المراجعات', none: 'لا توجد مراجعة مسجلة بعد.',
  snapshot: 'اللقطة {id}', error: 'تعذر تحميل حالة المراجعة.', saved: 'سُجل القرار.', trace: 'ما يعرضه الفيديو ومصدر كل رقم',
})

type Format = 'dashboard' | 'html' | 'docx' | 'slides' | 'video'
const FORMATS: Format[] = ['dashboard', 'html', 'docx', 'slides', 'video']
interface Review { id: string; format: Format; decision: string; comment: string; reviewer: string; created_at: string; language: string }
interface Scene { id: string; heading: string; figures: Array<{ label: string; shown: string; source: string }> }
interface Video { id: string; state: string; manifest: { duration: number; scenes: Scene[] } | null }
interface State {
  snapshot_id: string
  formats: Record<Format, { state: string; artifact_sha256: string | null; review: Review | null }>
  history: Review[]; video: Video | null; video_renderer: { available: boolean; missing: string[] }
}

export default function ReviewPanel({ runId, brief, filters, language, canReview }: {
  runId: string; brief: RunExecutive; filters: TableFilter[]; language: 'en' | 'ar'; canReview: boolean
}) {
  const { t, formatDate } = usePack(messages)
  const [state, setState] = useState<State | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [note, setNote] = useState<Record<string, string>>({})
  const [problem, setProblem] = useState<string | null>(null)
  const [media, setMedia] = useState<{ video: string; vtt: string } | null>(null)
  const urls = useRef<string[]>([])
  const query = new URLSearchParams({ language, filters: JSON.stringify(filters) }).toString()
  const base = `/api/runs/${encodeURIComponent(runId)}/executive`

  async function load() {
    try { setState(await request<State>(`${base}/reviews?${query}`)); setProblem(null) } catch { setProblem(t('error')) }
  }
  useEffect(() => { void load() }, [runId, query, brief.snapshot_id]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { urls.current.forEach(URL.revokeObjectURL) }, [])

  async function decide(format: Format, decision: 'approved' | 'changes_requested') {
    if (!state) return
    setBusy(format)
    try {
      const done = await request<{ formats: State['formats'] }>(`${base}/reviews`, { method: 'POST', body: JSON.stringify({
        format, language, filters: JSON.stringify(filters), expected_snapshot_id: state.snapshot_id,
        artifact_sha256: state.formats[format].artifact_sha256, decision, comment: note[format] ?? '' }) })
      setNote({ ...note, [format]: '' }); setProblem(t('saved'))
      setState({ ...state, formats: done.formats }); void load()
    } catch (error) { setProblem(error instanceof ApiError ? error.message : t('error')) } finally { setBusy(null) }
  }
  async function render() {
    setBusy('render')
    try {
      await request(`${base}/video?${query}&expected_snapshot_id=${state?.snapshot_id ?? brief.snapshot_id}`, { method: 'POST' }, 600_000)
      setMedia(null); await load()
    } catch (error) { setProblem(error instanceof ApiError ? error.message : t('error')); await load() } finally { setBusy(null) }
  }
  async function file(name: string) {
    // The files need the reader's token, so they are fetched, never linked.
    const response = await fetch(`${API_BASE}${base}/video/${state!.video!.id}/${name}`, { headers: authHeaders() })
    if (!response.ok) throw new ApiError(t('error'), response.status)
    const url = URL.createObjectURL(await response.blob())
    urls.current.push(url)
    return url
  }
  async function preview() {
    try { setMedia({ video: await file('video.mp4'), vtt: await file('subtitles.vtt') }) } catch { setProblem(t('error')) }
  }
  async function save(name: string, as: string) {
    try { const a = document.createElement('a'); a.href = await file(name); a.download = as; a.click() } catch { setProblem(t('error')) }
  }

  if (!state) return <section className="exec-review" aria-label={t('title')}><p role="status">{problem ?? '…'}</p></section>
  const stem = `${runId}-${language}-${state.snapshot_id.slice(0, 12)}`
  return <section className="exec-review" aria-labelledby="exec-review-title">
    <h4 id="exec-review-title">{t('title')}</h4>
    <p className="exec-muted">{t('help')} <bdi>{t('snapshot', { id: state.snapshot_id.slice(0, 12) })}</bdi></p>
    <ul className="exec-review__list">{FORMATS.map((format) => {
      const entry = state.formats[format]
      const reviewable = canReview && entry.artifact_sha256 && !['approved'].includes(entry.state)
      return <li key={format} data-state={entry.state}>
        <div className="exec-review__row"><strong>{t(format)}</strong><span className="exec-review__state">{t(entry.state as 'draft')}</span></div>
        {entry.review ? <p className="exec-muted"><bdi>{t('by', { who: entry.review.reviewer, time: formatDate(entry.review.created_at) })}</bdi>{entry.review.comment ? <> · <span dir="auto">{entry.review.comment}</span></> : null}</p> : null}
        {format === 'video' ? <div className="exec-review__actions">
          {state.video_renderer.available ? <button type="button" className="btn btn--ghost" disabled={busy !== null || !canReview} onClick={() => void render()}>{busy === 'render' ? t('rendering') : t('render')}</button>
            : <p className="exec-muted">{t('unavailable', { missing: state.video_renderer.missing.join(', ') })}</p>}
          {state.video?.state === 'rendered' ? <>
            <button type="button" className="btn btn--subtle" onClick={() => void preview()}>{t('preview')}</button>
            <button type="button" className="btn btn--subtle" onClick={() => void save('video.mp4', `${stem}-video.mp4`)}>{t('download')}</button>
            <button type="button" className="btn btn--subtle" onClick={() => void save('subtitles.vtt', `${stem}-subtitles.vtt`)}>{t('subtitles')}</button></> : null}
        </div> : null}
        {format === 'video' && media ? <video className="exec-review__video" controls src={media.video}>
          <track kind="subtitles" src={media.vtt} srcLang={language} label={t('subtitles')} default /></video> : null}
        {format === 'video' && state.video?.manifest ? <details><summary>{t('trace')}</summary><ol>{state.video.manifest.scenes.map((scene) =>
          <li key={scene.id}><span dir="auto">{scene.heading}</span>{scene.figures.length ? <ul>{scene.figures.map((f) =>
            <li key={f.label}><span dir="auto">{f.label}: <bdi>{f.shown}</bdi></span> · <code dir="ltr">{f.source}</code></li>)}</ul> : null}</li>)}</ol></details> : null}
        {reviewable ? <div className="exec-review__decide">
          <label className="visually-hidden" htmlFor={`review-${format}`}>{t('comment')}</label>
          <input id={`review-${format}`} className="field__input" placeholder={t('comment')} value={note[format] ?? ''} maxLength={2000}
            onChange={(event) => setNote({ ...note, [format]: event.target.value })} />
          <button type="button" className="btn btn--primary" disabled={busy !== null} onClick={() => void decide(format, 'approved')}>{t('approve')}</button>
          <button type="button" className="btn btn--ghost" disabled={busy !== null || !(note[format] ?? '').trim()} onClick={() => void decide(format, 'changes_requested')}>{t('ask')}</button>
        </div> : null}
      </li>
    })}</ul>
    {problem ? <p role="status">{problem}</p> : null}
    <details><summary>{t('history')}</summary>{state.history.length ? <ol>{state.history.slice(0, 20).map((r) =>
      <li key={r.id}><bdi>{t(r.format)} · {r.language} · {t(r.decision as 'approved')} · {t('by', { who: r.reviewer, time: formatDate(r.created_at) })}</bdi>{r.comment ? <> · <span dir="auto">{r.comment}</span></> : null}</li>)}</ol>
      : <p className="exec-muted">{t('none')}</p>}</details>
  </section>
}
