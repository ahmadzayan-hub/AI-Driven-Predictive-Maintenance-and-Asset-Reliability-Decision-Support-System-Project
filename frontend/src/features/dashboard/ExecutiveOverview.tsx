import { useEffect, useRef, useState, type ReactNode } from 'react'
import { usePack } from '../../i18n/pack'
import { api } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import type { KpiMeasure, RunExecutive, TableFilter } from '../../shared/types'
import { executiveMessages } from './executiveMessages'
import './executive.css'

interface Props {
  runId: string
  filters: TableFilter[]
  onOpenRun: () => void
  onDrill: (filters: TableFilter[]) => void
  canDrill: (filters: TableFilter[]) => boolean
  children: ReactNode
}

/** Each response belongs to one exact run, language and filter scope.
 * No cross-user/module cache; changing scope aborts and hides old figures. */
export function ExecutiveOverview({ runId, filters, onOpenRun, onDrill, canDrill, children }: Props) {
  const { t, locale, isRtl, formatNumber } = usePack(executiveMessages)
  const key = JSON.stringify([runId, locale, filters])
  const [revision, setRevision] = useState(0)
  const [answer, setAnswer] = useState<{ key: string; data: RunExecutive | null; failed: boolean }>({ key: '', data: null, failed: false })
  const [brief, setBrief] = useState<RunExecutive | null>(null)
  const [evidenceOpen, setEvidenceOpen] = useState(false)
  const [selectedEvidence, setSelectedEvidence] = useState<string[]>([])
  const evidenceRef = useRef<HTMLDetailsElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    let current = true
    setAnswer({ key, data: null, failed: false })
    setEvidenceOpen(false)
    setSelectedEvidence([])
    api.runExecutive(runId, locale, filters, controller.signal)
      .then((data) => { if (current) setAnswer({ key, data, failed: false }) })
      .catch(() => { if (current) setAnswer({ key, data: null, failed: true }) })
    return () => { current = false; controller.abort() }
    // The serialized key includes the complete request, independent of prop identity.
  }, [key, revision]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!evidenceOpen || !selectedEvidence.length) return
    const row = evidenceRef.current?.querySelector<HTMLTableRowElement>('tr[data-selected="true"]')
    row?.scrollIntoView?.({ block: 'nearest', behavior: 'instant' })
    if (row) row.focus()
    else evidenceRef.current?.querySelector('summary')?.focus()
  }, [evidenceOpen, selectedEvidence])

  const data = answer.key === key ? answer.data : null
  const failed = answer.key === key && answer.failed
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
  function download() {
    if (!data) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `miyaar-executive-${runId.replace(/[^a-zA-Z0-9_-]/g, '_')}-${locale}.json`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  if (!data) return <section className="card exec-pending" aria-label={t('exec.title')}>
    {failed ? <><p role="alert">{t('exec.failed')}</p><button type="button" className="btn btn--ghost" onClick={() => setRevision((v) => v + 1)}>{t('exec.retry')}</button></>
      : <div role="status" aria-label={t('exec.loading')}><div className="skeleton skeleton--title" /><div className="skeleton skeleton--line" /></div>}
  </section>

  const status = data.readiness.status
  return <div className="exec-overview" dir={isRtl ? 'rtl' : 'ltr'}>
    <section className="exec-hero" aria-labelledby="exec-title">
      <div>
        <p className="eyebrow">{t('exec.eyebrow')}</p>
        <h3 id="exec-title">{t('exec.title')}</h3>
        <div className="exec-meta">
          <span className={`exec-badge exec-badge--${status}`}><Icon name={status === 'ready' ? 'shield' : 'alert'} size={15} />{t(`exec.${status}`)}</span>
          <span>{t('exec.engine')}</span>
          {data.run.updated_at ? <time dateTime={data.run.updated_at}>{t('exec.updated')}: <bdi>{new Date(data.run.updated_at).toLocaleString(locale === 'ar' ? 'ar-u-nu-latn' : 'en', { dateStyle: 'medium', timeStyle: 'short' })}</bdi></time> : null}
        </div>
      </div>
      <div className="exec-scope">
        <span className="eyebrow">{t('exec.scope')}</span>
        <strong>{formatNumber(data.scope.records)}</strong>
        <span>{t('exec.totalCoverage', { total: formatNumber(data.scope.total_records) })}</span>
        <button type="button" className="btn btn--ghost" onClick={() => setRevision((v) => v + 1)}><Icon name="refresh" size={15} />{t('exec.refresh')}</button>
      </div>
    </section>

    {data.readiness.limitations.length ? <details className="exec-limitations">
      <summary>{t('exec.limits', { n: formatNumber(data.readiness.limitations.length) })}</summary><ul>{data.readiness.limitations.map((text, i) => <li key={i} dir="auto">{text}</li>)}</ul>
    </details> : null}

    {(data.kpis.measures.length > 0 || Object.keys(data.kpis.unavailable).length > 0) ? <section aria-labelledby="exec-kpis">
      <div className="exec-section-head"><h3 id="exec-kpis">{t('exec.kpis')}</h3><p>{t('exec.kpiScope')}</p></div>
      <div className="exec-kpis">{data.kpis.measures.map((measure) => <Kpi key={measure.key} measure={measure} />)}</div>
      {Object.keys(data.kpis.unavailable).length ? <details className="exec-unavailable"><summary>{t('exec.unsupported')}</summary><dl>{Object.entries(data.kpis.unavailable).map(([name, reason]) => <div key={name}><dt><bdi>{name}</bdi></dt><dd dir="auto">{reason}</dd></div>)}</dl></details> : null}
    </section> : null}

    <div className="exec-decision-grid">
      <section className="exec-card exec-agent" aria-labelledby="exec-agent">
        <div className="exec-section-head"><div className="exec-heading"><Icon name="sparkle" size={22} /><h3 id="exec-agent">{t('exec.agent')}</h3></div><span className="exec-badge">{t('exec.engine')}</span></div>
        <p className="exec-muted">{t('exec.agentHelp')}</p>
        {brief === data ? <div className="exec-brief" role="region" aria-label={t('exec.prepared')}>
          <p className="exec-headline" dir="auto">{data.headline}</p>
          <h4>{t('exec.questions')}</h4>
          {data.questions.length ? <ol>{data.questions.map((question) => <li key={question.id}><p dir="auto">{question.text}</p>{refs(question.evidence_refs)}</li>)}</ol> : <p>{t('exec.noQuestions')}</p>}
          <button type="button" className="btn btn--ghost" onClick={download}><Icon name="download" size={16} />{t('exec.download')}</button>
        </div> : <button type="button" className="btn btn--primary" onClick={() => setBrief(data)}><Icon name="sparkle" size={16} />{t('exec.prepare')}</button>}
        <p className="exec-boundary"><Icon name="shield" size={16} />{t('exec.human')}</p>
      </section>

      <section className="exec-card" aria-labelledby="exec-attention">
        <div className="exec-section-head"><h3 id="exec-attention">{t('exec.attention')}</h3><span className="exec-count">{formatNumber(data.priorities.length)}</span></div>
        <p className="exec-muted">{t('exec.attentionHelp')}</p>
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
        <td>{t(model.fitted === false || !model.metric ? 'exec.unfitted' : model.beats_baseline && model.details.verdict !== 'weak' ? 'exec.beats' : 'exec.weak')}{typeof model.details.reason === 'string' ? <small className="exec-muted" dir="auto">{model.details.reason}</small> : null}</td>
        <td>{model.metric ? <><bdi>{number(model.metric.model)} / {number(model.metric.baseline)}</bdi><small className="exec-muted"><bdi>{model.metric.name}</bdi></small></> : '—'}</td><td>{number(model.test_records)}</td>
      </tr>)}</tbody></table></div> : <p className="exec-muted">{t('exec.noModels')}</p>}
      {data.findings.length ? <details className="exec-findings"><summary>{t('exec.findings')} · {t('exec.whole')}</summary><ul>{data.findings.map((finding) => <li key={finding.id}><p dir="auto">{finding.text}</p>{refs(finding.evidence_refs)}</li>)}</ul></details> : null}
    </section>

    <details className="exec-card exec-evidence" ref={evidenceRef} open={evidenceOpen} onToggle={(event) => setEvidenceOpen(event.currentTarget.open)}>
      <summary>{t('exec.evidence')} <span className="exec-count">{formatNumber(data.evidence.length)}</span></summary>
      <div className="evidence__table" role="region" aria-label={t('exec.evidence')} tabIndex={0}><table className="datatable"><thead><tr><th scope="col">{t('exec.reference')}</th><th scope="col">{t('exec.value')}</th><th scope="col">{t('exec.method')}</th></tr></thead><tbody>{data.evidence.map((entry) => <tr key={entry.id} data-selected={selectedEvidence.includes(entry.id) || undefined} tabIndex={-1}><th scope="row"><bdi>{entry.id}</bdi><small dir="auto">{entry.label}</small></th><td>{number(entry.value)}</td><td><span dir="auto">{entry.method}</span><small className="exec-muted">{t(entry.scope === 'filtered' ? 'exec.filtered' : 'exec.whole')}</small></td></tr>)}</tbody></table></div>
    </details>
    <p className="exec-footnote">{t('exec.snapshot')}</p>
  </div>
}

function Kpi({ measure }: { measure: KpiMeasure }) {
  const { t, formatNumber } = usePack(executiveMessages)
  const value = measure.value === null ? t('exec.unavailable') : formatNumber(measure.value, { maximumFractionDigits: 2 })
  const unit = measure.value === null ? '' : measure.scale === 'percent' ? '%' : measure.scale === 'hours' ? t('exec.hours') : measure.scale === 'money' ? t('exec.money') : measure.scale
  return <article className="exec-kpi" data-source={`kpi.${measure.key}`}>
    <h4 dir="auto">{measure.title}</h4><p className={`exec-kpi-value${measure.value === null ? ' exec-kpi-value--missing' : ''}`}><bdi>{value}</bdi> <small>{unit}</small></p>
    <p>{t('exec.covered', { n: formatNumber(measure.records) })}</p>
    {measure.records_unmeasured > 0 ? <p className="exec-kpi-caution">{t('exec.unmeasured', { n: formatNumber(measure.records_unmeasured) })}</p> : null}
    {measure.undefined_reason ? <p className="exec-kpi-caution" dir="auto">{measure.undefined_reason}</p> : null}
    <details><summary>{t('exec.sources')}</summary><dl><div><dt>{t('exec.formula')}</dt><dd dir="auto">{measure.formula} · <bdi>{formatNumber(measure.numerator)} / {formatNumber(measure.denominator)}</bdi></dd></div><div><dt>{t('exec.population')}</dt><dd dir="auto">{measure.population}</dd></div><div><dt>{t('exec.missing')}</dt><dd dir="auto">{measure.missing_policy}</dd></div></dl>{measure.records_excluded > 0 ? <p>{t('exec.excluded', { n: formatNumber(measure.records_excluded) })}</p> : null}</details>
  </article>
}
