import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { usePack } from '../../i18n/pack'
import { api } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import { PerformanceValue, performanceTone } from '../../shared/components/PerformanceValue'
import type { KpiMeasure, RunExecutive, TableFilter } from '../../shared/types'
import { executiveMessages } from './executiveMessages'
import { policyMessages } from './policyMessages'
import './executive.css'

const KpiPolicyEditor = lazy(() => import('./KpiPolicyEditor'))

interface Props {
  runId: string
  filters: TableFilter[]
  onOpenRun: () => void
  onDrill: (filters: TableFilter[]) => void
  canDrill: (filters: TableFilter[]) => boolean
  children: ReactNode
}

interface ExportJob {
  controller: AbortController
  scope: string
  popup: Window | null
  url?: string
  poll?: ReturnType<typeof setInterval>
  timeout?: ReturnType<typeof setTimeout>
  ready?: () => void
  printing?: boolean
  printed?: () => void
}

/** Each response belongs to one exact run, language and filter scope.
 * No cross-user/module cache; changing scope aborts and hides old figures. */
export function ExecutiveOverview({ runId, filters, onOpenRun, onDrill, canDrill, children }: Props) {
  const { t, locale, isRtl, formatNumber } = usePack(executiveMessages)
  const key = JSON.stringify([runId, locale, filters])
  const [revision, setRevision] = useState(0)
  const [policyOpen, setPolicyOpen] = useState(false)
  const requestKey = `${key}:${revision}`
  const [answer, setAnswer] = useState<{ key: string; data: RunExecutive | null; failed: boolean }>({ key: '', data: null, failed: false })
  const [brief, setBrief] = useState<RunExecutive | null>(null)
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [selectedEvidence, setSelectedEvidence] = useState<string[]>([])
  const [exportFormat, setExportFormat] = useState<'html' | 'docx'>('html')
  const [exportBusy, setExportBusy] = useState(false)
  const [exportError, setExportError] = useState<keyof typeof executiveMessages.en | null>(null)
  const [exportStatus, setExportStatus] = useState<keyof typeof executiveMessages.en | null>(null)
  const exportRef = useRef<ExportJob | null>(null)
  const objectUrls = useRef(new Set<string>())
  const currentScope = useRef('')
  currentScope.current = requestKey
  const evidenceRef = useRef<HTMLDetailsElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    let current = true
    setAnswer({ key: requestKey, data: null, failed: false })
    setBrief(null)
    setPolicyOpen(false)
    setEvidenceOpen(false)
    setSelectedEvidence([])
    setExportBusy(false)
    setExportError(null)
    setExportStatus(null)
    api.runExecutive(runId, locale, filters, controller.signal)
      .then((data) => { if (current) setAnswer({ key: requestKey, data, failed: false }) })
      .catch(() => { if (current) setAnswer({ key: requestKey, data: null, failed: true }) })
    return () => {
      current = false
      controller.abort()
      if (exportRef.current) disposeExport(exportRef.current)
      for (const url of objectUrls.current) revoke(url)
    }
    // The serialized key includes the complete request, independent of prop identity.
  }, [key, revision]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!evidenceOpen || !selectedEvidence.length) return
    const row = evidenceRef.current?.querySelector<HTMLTableRowElement>('tr[data-selected="true"]')
    row?.scrollIntoView?.({ block: 'nearest', behavior: 'instant' })
    if (row) row.focus()
    else evidenceRef.current?.querySelector('summary')?.focus()
  }, [evidenceOpen, selectedEvidence])

  const data = answer.key === requestKey ? answer.data : null
  const failed = answer.key === requestKey && answer.failed
  const number = (value: number | null | undefined) => value == null ? '—' : formatNumber(value, { maximumFractionDigits: 2 })

  function inspectEvidence(ids: string[]) {
    setSelectedEvidence([...ids])
    setEvidenceOpen(true)
  }
  function refs(ids: string[]) {
    if (!ids.length) return null
    return <button type="button" className="exec-ref" onClick={() => inspectEvidence(ids)}>
      <Icon name="shield" size={14} /><span>{t('exec.viewSources', { n: formatNumber(ids.length) })}</span>
    </button>
  }
  function revoke(url: string) {
    if (objectUrls.current.delete(url)) URL.revokeObjectURL(url)
  }
  function disposeExport(job: ExportJob) {
    job.controller.abort()
    clearInterval(job.poll)
    clearTimeout(job.timeout)
    try {
      if (job.printed) job.popup?.removeEventListener('afterprint', job.printed)
      if (job.popup && !job.popup.closed) job.popup.close()
    } catch { /* A closed or externally navigated preview is no longer usable. */ }
    if (job.url) revoke(job.url)
    if (exportRef.current === job) exportRef.current = null
  }
  function isCurrent(job: ExportJob) {
    return exportRef.current === job && job.scope === currentScope.current && !job.controller.signal.aborted
  }
  function finishExport(job: ExportJob, error: keyof typeof executiveMessages.en | null, status: keyof typeof executiveMessages.en | null = null) {
    if (!isCurrent(job)) return
    disposeExport(job)
    setExportBusy(false)
    setExportError(error)
    setExportStatus(status)
  }
  function cancelExport() {
    if (exportRef.current) finishExport(exportRef.current, null, 'exec.exportCancelled')
  }
  async function exportReport(print: boolean) {
    if (!data || brief !== data || exportRef.current) return
    setExportError(null)
    setExportStatus(null)
    const stamp = brief.run.updated_at
    const snapshotId = brief.snapshot_id
    if (!stamp || !snapshotId) { setExportError('exec.exportStale'); return }
    let popup: Window | null = null
    if (print) {
      // Reserve the preview while this explicit user gesture is still active.
      try {
        popup = window.open('', '_blank')
        if (popup) popup.opener = null
      } catch { popup?.close(); popup = null }
      if (!popup) { setExportError('exec.popupBlocked'); return }
    }
    const job: ExportJob = { controller: new AbortController(), scope: currentScope.current, popup }
    exportRef.current = job
    setExportBusy(true)
    if (popup) job.poll = setInterval(() => {
      if (popup.closed) finishExport(job, null, 'exec.printClosed')
      else job.ready?.()
    }, 400)
    try {
      const result = await api.downloadExecutive(brief.run.id, brief.language, brief.scope.filters, stamp, snapshotId, print ? 'html' : exportFormat, job.controller.signal)
      if (!isCurrent(job)) return
      if (popup?.closed) { finishExport(job, null, 'exec.printClosed'); return }
      const url = URL.createObjectURL(result.blob)
      objectUrls.current.add(url)
      if (!popup) {
        const link = document.createElement('a')
        link.href = url
        link.download = result.name
        try { link.click() } catch (error) { revoke(url); throw error }
        // The browser may consume the blob after the click handler returns.
        setTimeout(() => revoke(url), 1_000)
        finishExport(job, null, 'exec.downloadReady')
        return
      }
      job.url = url
      const loaded = () => popup.location.href === url && popup.document.URL === url && popup.document.readyState === 'complete'
      // Navigation replaces the blank window's global and its load listeners.
      // Poll the actual report document, then enter the font/print path once.
      job.ready = async () => {
        try {
          if (job.printing || !isCurrent(job) || popup.closed || !loaded()) return
          job.printing = true
          await popup.document.fonts?.ready
          if (!isCurrent(job)) return
          if (popup.closed) { finishExport(job, null, 'exec.printClosed'); return }
          if (!loaded()) { finishExport(job, 'exec.printFailed'); return }
          clearTimeout(job.timeout)
          job.printed = () => finishExport(job, null, 'exec.printDone')
          popup.addEventListener('afterprint', job.printed, { once: true })
          popup.focus()
          setExportStatus('exec.printRequested')
          popup.print()
        } catch { finishExport(job, 'exec.printFailed') }
      }
      job.timeout = setTimeout(() => finishExport(job, 'exec.printFailed'), 30_000)
      popup.location.href = url
    } catch (error) {
      const stale = error instanceof Error && 'status' in error && error.status === 409
      finishExport(job, stale ? 'exec.exportStale' : 'exec.exportFailed')
    }
  }

  if (!data) return <section className="card exec-pending" aria-label={t('exec.title')}>
    {failed ? <><p role="alert">{t('exec.failed')}</p><button type="button" className="btn btn--ghost" onClick={() => setRevision((v) => v + 1)}>{t('exec.retry')}</button></>
      : <div role="status" aria-label={t('exec.loading')}><div className="skeleton skeleton--title" /><div className="skeleton skeleton--line" /></div>}
  </section>

  const status = data.readiness.status
  return <div className="exec-overview" dir={isRtl ? 'rtl' : 'ltr'}>
    <section className="exec-hero" aria-labelledby="exec-title">
      <div>
        <h3 id="exec-title">{t('exec.title')}</h3>
        <div className="exec-meta">
          <span className={`exec-badge exec-badge--${status}`}><Icon name={status === 'ready' ? 'shield' : 'alert'} size={15} />{t(`exec.${status}`)}</span>
          <span>{t('exec.engine')}</span>
          {data.run.updated_at ? <time dateTime={data.run.updated_at}>{t('exec.updated')}: <bdi>{new Date(data.run.updated_at).toLocaleString(locale === 'ar' ? 'ar-u-nu-latn' : 'en', { dateStyle: 'medium', timeStyle: 'short' })}</bdi></time> : null}
        </div>
      </div>
      <div className="exec-scope">
        <strong>{formatNumber(data.scope.records)}</strong>
        <span>{t('exec.totalCoverage', { total: formatNumber(data.scope.total_records) })}</span>
        <button type="button" className="btn btn--ghost" onClick={() => setRevision((v) => v + 1)}><Icon name="refresh" size={15} />{t('exec.refresh')}</button>
      </div>
    </section>

    {data.readiness.limitations.length ? <details className="exec-limitations">
      <summary>{t('exec.limits', { n: formatNumber(data.readiness.limitations.length) })}</summary><ul>{data.readiness.limitations.map((text, i) => <li key={i} dir="auto">{text}</li>)}</ul>
    </details> : null}

    {(data.kpis.measures.length > 0 || Object.keys(data.kpis.unavailable).length > 0) ? <section aria-labelledby="exec-kpis">
      <div className="exec-section-head"><h3 id="exec-kpis">{t('exec.kpis')}</h3>{data.kpis.measures.length ? <PolicyButton onClick={() => setPolicyOpen(true)} open={policyOpen} /> : null}</div>
      <details className="exec-about"><summary>{t('exec.about')}</summary><p>{t('exec.kpiScope')}</p><PerformanceLegend /><p>{t('exec.snapshot')}</p></details>
      {policyOpen ? <Suspense fallback={<p role="status">{t('exec.loading')}</p>}><KpiPolicyEditor key={`${runId}:${locale}`} runId={runId} measures={data.kpis.measures} onClose={() => setPolicyOpen(false)} onSaved={() => setRevision((v) => v + 1)} /></Suspense> : null}
      {FAMILIES.map((family) => {
        const items = data.kpis.measures.filter((measure) => (FAMILIES.includes(measure.family as Family) ? measure.family : 'other') === family)
        return items.length ? <section key={family} className="exec-family" data-family={family} aria-labelledby={`exec-family-${family}`}>
          <h4 id={`exec-family-${family}`}><Icon name={FAMILY_ICON[family]} size={16} />{t(`exec.family.${family}`)}</h4>
          <div className="exec-kpis">{items.map((measure) => <Kpi key={measure.key} measure={measure} />)}</div>
        </section> : null
      })}
      {Object.keys(data.kpis.unavailable).length ? <details className="exec-unavailable"><summary>{t('exec.unsupported')}</summary><dl>{Object.entries(data.kpis.unavailable).map(([name, reason]) => <div key={name}><dt><bdi>{name}</bdi></dt><dd dir="auto">{reason}</dd></div>)}</dl></details> : null}
    </section> : null}

    <div className="exec-decision-grid">
      <section className="exec-card exec-agent" aria-labelledby="exec-agent">
        <div className="exec-section-head"><div className="exec-heading"><Icon name="sparkle" size={22} /><h3 id="exec-agent">{t('exec.agent')}</h3></div><span className="exec-badge">{t('exec.engine')}</span></div>
        {brief === data ? <div className="exec-brief" role="region" aria-label={t('exec.prepared')}>
          <p className="exec-headline" dir="auto">{data.headline}</p>
          <h4>{t('exec.questions')}</h4>
          {data.questions.length ? <ol>{data.questions.map((question) => <li key={question.id}><p dir="auto">{question.text}</p>{refs(question.evidence_refs)}</li>)}</ol> : <p>{t('exec.noQuestions')}</p>}
          <div className="exec-export" aria-busy={exportBusy}>
            <div className="field"><label className="field__label" htmlFor="exec-format">{t('exec.format')}</label><select className="field__select" id="exec-format" value={exportFormat} disabled={exportBusy} onChange={(event) => setExportFormat(event.target.value as 'html' | 'docx')}><option value="html">{t('exec.html')}</option><option value="docx">{t('exec.word')}</option></select></div>
            <button type="button" className="btn btn--ghost" disabled={exportBusy} onClick={() => void exportReport(false)}><Icon name="download" size={16} />{t('exec.download')}</button>
            <button type="button" className="btn btn--ghost" disabled={exportBusy} aria-describedby="exec-pdf-help" onClick={() => void exportReport(true)}>{t('exec.print')}</button>
            {exportBusy ? <button type="button" className="btn btn--subtle" onClick={cancelExport}>{t('exec.cancelExport')}</button> : null}
          </div>
          <p className="exec-muted" id="exec-pdf-help">{t('exec.pdfHelp')}</p>
          {exportError ? <div><p role="alert">{t(exportError)}</p>{exportError === 'exec.exportStale' ? <button type="button" className="btn btn--subtle" onClick={() => setRevision((v) => v + 1)}>{t('exec.refresh')}</button> : null}</div> : null}
          <p className="exec-muted" role="status">{exportStatus ? t(exportStatus) : exportBusy ? t('exec.exportBusy') : ''}</p>
        </div> : <button type="button" className="btn btn--primary" onClick={() => setBrief(data)}><Icon name="sparkle" size={16} />{t('exec.prepare')}</button>}
        <p className="exec-boundary"><Icon name="shield" size={16} />{t('exec.human')}</p>
      </section>

      <section className="exec-card" aria-labelledby="exec-attention">
        <div className="exec-section-head"><h3 id="exec-attention">{t('exec.attention')}</h3><span className="exec-count">{formatNumber(data.priorities.length)}</span></div>
        {data.priorities.length ? <ol className="exec-priorities">{data.priorities.map((priority, index) => {
          const drilldown = data.drilldowns.find((item) => item.id === priority.drilldown_id)
          return <li key={priority.id}><span className="exec-priority-number" aria-hidden="true">{formatNumber(index + 1)}</span><div><h4 dir="auto">{priority.title}</h4><p dir="auto">{priority.detail}</p>{refs(priority.evidence_refs)}
            {drilldown && canDrill(drilldown.filters) ? <button type="button" className="btn btn--subtle exec-drill" onClick={() => onDrill(drilldown.filters)}>{drilldown.label || t('exec.drill')}<Icon name="search" size={14} /></button> : null}
          </div></li>
        })}</ol> : <p className="exec-muted">{t('exec.noPriorities')}</p>}
      </section>
    </div>

    <section aria-labelledby="exec-explore"><div className="exec-section-head"><h3 id="exec-explore">{t('exec.explore')}</h3><button type="button" className="btn btn--subtle" onClick={onOpenRun}>{t('exec.openRun')}</button></div>{children}</section>

    <section className="exec-card" aria-labelledby="exec-models">
      <div className="exec-section-head"><h3 id="exec-models">{t('exec.models')}</h3><span className="exec-badge">{t('exec.whole')}</span></div>
      <p className="exec-muted">{t('exec.wholeHelp')}</p>
      {data.models.length ? <div className="evidence__table" role="region" aria-label={t('exec.modelData')} tabIndex={0}><table className="datatable"><thead><tr><th scope="col">{t('exec.model')}</th><th scope="col">{t('exec.verdict')}</th><th scope="col">{t('exec.metric')}</th><th scope="col">{t('exec.holdout')}</th></tr></thead><tbody>{data.models.map((model, index) => <tr key={`${model.role}-${index}`}>
        <th scope="row"><span dir="auto">{model.title || model.target}</span><small className="exec-muted" dir="auto">{model.target}</small></th>
        <td><span className="performance-value" data-performance={modelTone(model)}>{t(modelTone(model) === 'unassessed' ? 'exec.unfitted' : modelTone(model) === 'good' ? 'exec.beats' : 'exec.weak')}</span>{typeof model.details.reason === 'string' ? <small className="exec-muted" dir="auto">{model.details.reason}</small> : null}</td>
        <td>{model.metric && modelTone(model) !== 'unassessed' ? <><bdi>{number(model.metric.model)} / {number(model.metric.baseline)}</bdi><small className="exec-muted"><bdi>{model.metric.name}</bdi></small></> : '—'}</td><td>{number(model.test_records)}</td>
      </tr>)}</tbody></table></div> : <p className="exec-muted">{t('exec.noModels')}</p>}
      {data.findings.length ? <details className="exec-findings"><summary>{t('exec.findings')} · {t('exec.whole')}</summary><ul>{data.findings.map((finding) => <li key={finding.id}><p dir="auto">{finding.text}</p>{refs(finding.evidence_refs)}</li>)}</ul></details> : null}
    </section>

    <details className="exec-card exec-evidence" ref={evidenceRef} open={evidenceOpen} onToggle={(event) => setEvidenceOpen(event.currentTarget.open)}>
      <summary>{t('exec.evidence')} <span className="exec-count">{formatNumber(data.evidence.length)}</span></summary>
      <div className="evidence__table" role="region" aria-label={t('exec.evidence')} tabIndex={0}><table className="datatable"><thead><tr><th scope="col">{t('exec.reference')}</th><th scope="col">{t('exec.value')}</th><th scope="col">{t('exec.method')}</th></tr></thead><tbody>{data.evidence.map((entry) => <tr key={entry.id} data-selected={selectedEvidence.includes(entry.id) || undefined} tabIndex={-1}><th scope="row"><bdi>{entry.id}</bdi><small dir="auto">{entry.label}</small></th><td>{number(entry.value)}</td><td><span dir="auto">{entry.method}</span><small className="exec-muted">{t(entry.scope === 'filtered' ? 'exec.filtered' : 'exec.whole')}</small></td></tr>)}</tbody></table></div>
    </details>
  </div>
}

/** The register names each measure's family, shown as a coloured band.
 * The colour names the family only; good, okay and bad stay with the value. */
const FAMILIES = ['reliability', 'execution', 'cost', 'other'] as const
type Family = typeof FAMILIES[number]
const FAMILY_ICON = { reliability: 'activity', execution: 'check', cost: 'database', other: 'dashboard' } as const

function modelTone(model: RunExecutive['models'][number]) {
  if (model.fitted === false || !model.metric || model.details.verdict === 'not_supported') return 'unassessed'
  if (model.details.verdict === 'weak' || model.beats_baseline === false) return 'bad'
  return model.beats_baseline === true ? 'good' : 'unassessed'
}

function Kpi({ measure }: { measure: KpiMeasure }) {
  const { t, formatNumber } = usePack(executiveMessages)
  const value = measure.value === null ? t('exec.unavailable') : formatNumber(measure.value, { maximumFractionDigits: 2 })
  const unit = measure.value === null ? '' : measure.scale === 'percent' ? '%' : measure.scale === 'hours' ? t('exec.hours') : measure.scale === 'money' ? t('exec.money') : measure.scale
  const tone = performanceTone(measure.value, measure.assessment)
  // A verdict's reason stays on the card, and so does a target held for review;
  // "no target is set" moves into the evidence.
  const verdict = tone === 'good' || tone === 'okay' || tone === 'bad'
    || measure.assessment?.reason_code === 'target_outdated'
  const share = measure.scale === 'percent' && measure.value !== null ? Math.max(0, Math.min(100, measure.value)) : null
  return <article className="exec-kpi" data-source={`kpi.${measure.key}`}>
    <h5 dir="auto">{measure.title}</h5><p className={`exec-kpi-value${measure.value === null ? ' exec-kpi-value--missing' : ''}`}><PerformanceValue tone={tone} reason={verdict ? measure.assessment?.reason : undefined}><bdi>{value}{'\u00a0'}<small>{unit}</small></bdi></PerformanceValue></p>
    {share === null ? null : <svg className="exec-kpi-meter" viewBox="0 0 100 4" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect width="100" height="4" rx="2" /><rect width={share} height="4" rx="2" /></svg>}
    <p className="exec-kpi-covered">{t('exec.covered', { n: formatNumber(measure.records) })}</p>
    {measure.records_unmeasured > 0 ? <p className="exec-kpi-caution">{t('exec.unmeasured', { n: formatNumber(measure.records_unmeasured) })}</p> : null}
    {measure.undefined_reason ? <p className="exec-kpi-caution" dir="auto">{measure.undefined_reason}</p> : null}
    <details><summary>{t('exec.sources')}</summary>{!verdict && measure.assessment?.reason ? <p dir="auto">{measure.assessment.reason}</p> : null}<dl><div><dt>{t('exec.formula')}</dt><dd dir="auto">{measure.formula} · <bdi>{formatNumber(measure.numerator)} / {formatNumber(measure.denominator)}</bdi></dd></div><div><dt>{t('exec.population')}</dt><dd dir="auto">{measure.population_label ?? measure.population}</dd></div><div><dt>{t('exec.missing')}</dt><dd dir="auto">{measure.missing_policy}</dd></div></dl><TargetEvidence measure={measure} />{measure.records_excluded > 0 ? <p>{t('exec.excluded', { n: formatNumber(measure.records_excluded) })}</p> : null}</details>
  </article>
}

function PerformanceLegend() {
  const { t } = usePack(policyMessages)
  return <p className="exec-muted">{t('policy.legend')}</p>
}

function PolicyButton({ onClick, open }: { onClick: () => void; open: boolean }) {
  const { t } = usePack(policyMessages)
  return <button type="button" className="btn btn--ghost" disabled={open} aria-expanded={open} onClick={onClick}>{t('policy.title')}</button>
}

function TargetEvidence({ measure }: { measure: KpiMeasure }) {
  const { t, formatNumber } = usePack(policyMessages)
  const assessment = measure.assessment
  const unit = measure.scale === 'percent' ? '%' : measure.scale === 'hours' ? t('policy.hours') : measure.scale === 'money' ? t('policy.money') : measure.scale
  if (!assessment?.direction) return null
  return <dl><div><dt>{t('policy.direction')}</dt><dd>{t(`policy.${assessment.direction}`)}</dd></div>
    {Object.entries(assessment.thresholds || {}).map(([key, number]) => <div key={key}><dt>{t(`policy.${key}` as 'policy.good_at')}</dt><dd><bdi>{formatNumber(number, { maximumSignificantDigits: 12 })} {unit}</bdi></dd></div>)}
    <div><dt>{t('policy.sourceLabel')}</dt><dd dir="auto">{assessment.source_ref}</dd></div></dl>
}
