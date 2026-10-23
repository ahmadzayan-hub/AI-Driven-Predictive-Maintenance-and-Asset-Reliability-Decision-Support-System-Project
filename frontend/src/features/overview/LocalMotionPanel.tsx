import { useEffect, useState } from 'react'
import { API_BASE, authHeaders, request } from '../../shared/api'

type Job = {
  id: string; run_id: string; status: string
  error: string | null; video_sha: string | null
  reviewer: string | null; qa: { qa: string } | null
}

export function LocalMotionPanel({ runId, language }: { runId: string; language: 'en'|'ar' }) {
  const ar = language === 'ar'
  const t = (en: string, arabic: string) => ar ? arabic : en
  const [audio, setAudio] = useState<File | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [url, setUrl] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const prefix = '/api/motion/jobs/'

  useEffect(() => {
    if (!jobId) return
    let active = true
    const read = () => void request<Job>(prefix + encodeURIComponent(jobId))
      .then(data => { if (active) setJob(data) })
      .catch(() => { if (active) setError(t('Video job unavailable.', 'تعذر الحصول على الفيديو.')) })
    read()
    const timer = window.setInterval(read, 2500)
    return () => { active = false; clearInterval(timer) }
  }, [jobId, language])

  useEffect(() => () => { if (url) URL.revokeObjectURL(url) }, [url])

  async function render() {
    setBusy(true); setError('')
    try {
      const name = audio?.name.toLowerCase() ?? ''
      const extension = name.match(/\.(wav|m4a|mp3|aac|flac)$/)?.[0] ?? '.wav'
      if (audio && audio.size > 24_000_000) throw new Error('Maximum audio size is 24MB')
      const response = await request<{ id: string }>(
        '/api/motion/runs/' + encodeURIComponent(runId) + '/render?narration_suffix=' + encodeURIComponent(extension),
        { method: 'POST', body: audio ?? new Blob(), headers: { 'Content-Type': 'application/octet-stream' } },
        90_000,
      )
      setJobId(response.id)
    } catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }

  async function preview() {
    if (!jobId) return
    setBusy(true); setError('')
    try {
      const response = await fetch(
        API_BASE + prefix + encodeURIComponent(jobId) + '/preview',
        { headers: authHeaders(), cache: 'no-store' },
      )
      if (!response.ok) throw new Error('Media preview is not authorized or unavailable')
      setUrl(URL.createObjectURL(await response.blob()))
    } catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }

  async function submit() {
    if (!jobId) return
    setBusy(true); setError('')
    try {
      const row = await request<Job>(prefix + encodeURIComponent(jobId) + '/submit', { method: 'POST' })
      setJob(row)
    } catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }

  return <section className="card" aria-label={t('Local Motion Studio', 'استوديو الموشن المحلي')}>
    <h3 className="card__title">{t('Local MP4 production', 'إنتاج MP4 محلي')}</h3>
    <p className="card__meta">{t(
      'Opt-in persistent local worker only. Drafts are source-linked, private and subject to independent review.',
      'مسار إنتاج محلي اختياري، مرتبط بالمصادر وبمراجعة بشرية مستقلة.',
    )}</p>
    <label className="block text-sm">{t('Optional local narration (required for Arabic)', 'ملف التعليق الصوتي المحلي (إلزامي للعربية)')}
      <input type="file" accept=".wav,.mp3,.m4a,.aac,.flac" onChange={e => setAudio(e.target.files?.[0] ?? null)} />
    </label>
    <button type="button" className="btn btn--primary" disabled={busy || (ar && !audio)}
      onClick={() => void render()}>{t('Render source-backed MP4 draft', 'إنشاء مسودة فيديو MP4')}</button>
    {job && <p role="status" className="card__meta">{job.status} · {job.id}</p>}
    {job?.error && <p role="alert">{job.error}</p>}
    {job && ['RENDERED_DRAFT','REVIEW_REQUESTED','INTERNAL_APPROVED'].includes(job.status) && <>
      <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => void preview()}>
        {t('Load protected preview', 'عرض المعاينة المحمية')}
      </button>
      {url && <video controls preload="metadata" src={url} style={{ maxWidth: '100%', background: '#0c1825' }} />}
      {job.status === 'RENDERED_DRAFT' && <button type="button" className="btn btn--ghost"
        disabled={busy} onClick={() => void submit()}>
        {t('Request human review', 'طلب مراجعة بشرية')}
      </button>}
    </>}
    <p className="card__meta">{t(
      'A managed independent reviewer must approve the final SHA. Official publishing is not automated.',
      'يحتاج الفيديو مراجعة مستقلة مرتبطة ببصمته، ولا يتم نشره رسميًا تلقائيًا.',
    )}</p>
    {error && <p role="alert">{error}</p>}
  </section>
}
