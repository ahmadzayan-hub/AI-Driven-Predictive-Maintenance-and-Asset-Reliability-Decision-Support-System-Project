import '../../shared/styles/analytics.css'
import './report-theme.css'
import './report-document.css'
import { ReportDocument } from './ReportDocument'
import { useState } from 'react'
import { useReadOnly } from '../../shared/readOnly'
import { useI18n } from '../../i18n'
import { api, ApiError } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import type { RunDetail } from '../../shared/types'
import { runStore, useRun } from './runStore'

export function ApprovalCard({ detail, onDecision }: {
  detail: RunDetail
  onDecision?: (detail: RunDetail) => void
}) {
  const readOnly = useReadOnly()
  const { t, formatNumber } = useI18n()
  const snapshot = useRun(detail.id)
  const run = snapshot.detail ?? detail
  const approval = run.approvals.find((item) => item.state === 'pending')
  const [message, setMessage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  // The gate is the core control: Approve needs the exact report opened
  // and the reader's word that it was read (assessment finding U3).
  const [opened, setOpened] = useState(false)
  const [read, setRead] = useState(false)
  if (!approval) return null
  const busy = submitting || snapshot.pending

  async function decide(decision: 'approve' | 'reject') {
    if (busy || !approval || (decision === 'approve' && (!run.report || !read))) return
    setSubmitting(true)
    setMessage(null)
    try {
      const result = await runStore.mutate(run.id, () => api.decideApproval(run.id, approval.id, decision))
      if (result) onDecision?.(result)
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : t('runs.actionFailed'))
    } finally { setSubmitting(false) }
  }

  return (
    <section className="card approvalcard" aria-label={t('runs.approval')} aria-busy={busy}>
      <div className="decision__heading">
        <span className="decision__icon"><Icon name="shield" size={22} /></span>
        <div><p className="eyebrow">{t('cockpit.humanDecision')}</p><h3 className="card__title">{t('runs.approval')}</h3></div>
      </div>
      <p className="decision__intro">{t('cockpit.approvalIntro')}</p>
      {run.report ? <p className="decision__artifact"><span dir="auto">{run.report.name}</span> · {t('cockpit.version', { version: formatNumber(run.report.version) })}</p> : null}
      {run.report ? <details className="decision__preview report-theme" onToggle={(event) => { if (event.currentTarget.open) setOpened(true) }}>
        <summary>{t('cockpit.exactReport')}</summary>
        <p className="card__meta">{t('cockpit.previewIncludesEvidence')}</p>
        <ReportDocument className="runreport__content" content={run.report.content} language={run.report_language === 'ar' ? 'ar' : 'en'} label={t('cockpit.exactReport')} />
      </details> : <p role="status">{t('cockpit.reportUnavailable')}</p>}
      <dl className="decision__facts">
        {[
          [t('runs.action'), approval.action, run.report_language], [t('runs.target'), approval.target, 'en'],
          [t('runs.risk'), approval.risk === 'high' ? t('runs.riskHigh') : approval.risk, undefined],
          [t('runs.impact'), approval.impact, run.report_language], [t('runs.reversibility'), approval.reversibility, run.report_language],
        ].map(([label, value, language]) => <div key={label}><dt>{label}</dt><dd dir="auto" lang={language}>{value}</dd></div>)}
      </dl>
      <p className="decision__binding"><Icon name="shield" size={14} />{t('cockpit.hashBound')}</p>
      {message ? <p role="alert" className="statusline statusline--error" dir="auto">{message}</p> : null}
      {readOnly ? <p className="panel__note">{t('demo.note')}</p> : <div className="dialog__actions">
        <label className="decision__read"><input type="checkbox" checked={read} disabled={!opened || busy} onChange={(event) => setRead(event.target.checked)} />{t('cockpit.readReport')}</label>
        <button type="button" className="btn btn--ghost" disabled={busy} onClick={() => void decide('reject')}>{t('runs.reject')}</button>
        <button type="button" className="btn btn--primary" disabled={busy || !run.report || !read} onClick={() => void decide('approve')}>
          {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="check" size={16} />}{busy ? t('cockpit.confirming') : t('runs.approve')}
        </button>
      </div>}
    </section>
  )
}
