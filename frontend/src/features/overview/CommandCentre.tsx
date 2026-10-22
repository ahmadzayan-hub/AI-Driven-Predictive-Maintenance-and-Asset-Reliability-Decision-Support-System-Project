import { usePack } from '../../i18n/pack'
import { Icon } from '../../shared/components/Icon'
import { PerformanceValue, performanceTone } from '../../shared/components/PerformanceValue'
import { formatMoney } from '../../shared/format'
import { modelTone } from '../../shared/modelTone'
import type { KpiMeasure, RunExecutive, RunSummary } from '../../shared/types'
import { formatValue } from '../assets/kpiDisplay'
import { commandMessages } from './commandMessages'

interface CommandCentreProps {
  run: RunSummary
  brief: RunExecutive | null
  failed: boolean
  onOpenDashboard?: (runId: string) => void
}

const MAX_KPIS = 6
const FAMILY_ORDER = ['reliability', 'execution', 'cost']

/** The measures worth a tile: every one with a verdict first, then the
 *  first of each family, so a reader sees reliability, work and cost
 *  even when no target is set. Never more than six. */
export function pickMeasures(measures: KpiMeasure[]): KpiMeasure[] {
  const assessed = measures.filter((m) => ['good', 'okay', 'bad'].includes(m.assessment?.status ?? ''))
  const chosen = [...assessed]
  for (const family of FAMILY_ORDER) {
    const first = measures.find((m) => m.family === family && !chosen.includes(m))
    if (first) chosen.push(first)
  }
  for (const measure of measures) {
    if (chosen.length >= MAX_KPIS) break
    if (!chosen.includes(measure)) chosen.push(measure)
  }
  return chosen.slice(0, MAX_KPIS)
}

/** The decision brief of the latest analysis, on one screen: what to
 *  decide, how the fleet performs, whether a model can be trusted, what is
 *  recommended, how good and fresh the data is, and what to ask before
 *  approving. Every figure is the server's; nothing is computed here. */
export function CommandCentre({ run, brief, failed, onOpenDashboard }: CommandCentreProps) {
  const { t, locale, formatNumber, formatDate } = usePack(commandMessages)
  const open = onOpenDashboard ? (
    <button type="button" className="btn btn--ghost" onClick={() => onOpenDashboard(run.id)}>
      <Icon name="chart" size={16} />{t('command.openExecutive')}
    </button>
  ) : null

  if (!brief) {
    return (
      <section className="card command command--pending" aria-label={t('command.aria')}>
        {failed
          ? <p className="card__empty" role="alert">{t('command.failed')}</p>
          : <p role="status"><span className="skeleton skeleton--line" />{t('command.loading')}</p>}
        {failed ? open : null}
      </section>
    )
  }

  const decisions = brief.advisory?.decisions?.length
    ? brief.advisory.decisions.map((d) => ({ id: d.id, title: d.title, detail: d.action, owner: d.owner, gate: d.gate }))
    : brief.priorities.map((p) => ({ id: p.id, title: p.title, detail: p.detail, owner: '', gate: '' }))
  const measures = pickMeasures(brief.kpis.measures)
  const unavailable = Object.keys(brief.kpis.unavailable).length
  const recommendation = brief.findings.find((f) => f.kind === 'recommendation')
  const assumption = brief.findings.find((f) => f.stage === 'prescriptive' && f.kind === 'assumption')
  const quality = brief.findings.find((f) => f.stage === 'quality')
  const failedChecks = brief.evidence.find((e) => e.id === 'executive.validation.failed_checks')?.value
  const limitations = brief.readiness.limitations

  return (
    <section className="command" aria-label={t('command.aria')}>
      <div className="card command__hero">
        <div className="command__hero-body">
          <span className="command__eyebrow">{t('command.eyebrow')} · <span dir="auto">{run.dataset_name}</span></span>
          <p className="command__headline" dir="auto">{brief.advisory?.recommendation ?? brief.headline}</p>
          <p className="command__meta">
            <span className="performance-value" data-performance={brief.readiness.status === 'ready' ? 'good' : brief.readiness.status === 'limited' ? 'okay' : 'unavailable'}>
              <span className="performance-value__status">{t(`command.readiness.${brief.readiness.status}`)}</span>
            </span>
            {' · '}{t('command.asOf', { date: formatDate(brief.run.updated_at ?? run.updated_at) })}
            {' · '}{t('command.scope', { records: formatNumber(brief.scope.records), measures: formatNumber(brief.kpis.measures.length) })}
          </p>
        </div>
        {open}
      </div>

      <div className="command__grid">
        <section className="card" aria-labelledby="command-decisions">
          <h3 className="card__title" id="command-decisions">{t('command.decisions')} <span className="command__count">{formatNumber(decisions.length)}</span></h3>
          {decisions.length ? <ol className="command__list">{decisions.slice(0, 4).map((d, i) => (
            <li key={d.id}><span className="command__n" aria-hidden="true">{formatNumber(i + 1)}</span>
              <div><strong dir="auto">{d.title}</strong><p dir="auto">{d.detail}</p>
                {d.owner ? <p className="command__owner">{t('command.owner')}: <span dir="auto">{d.owner}</span> · {t('command.gate')}: <span dir="auto">{d.gate}</span></p> : null}</div>
            </li>))}</ol> : <p className="card__empty">{t('command.decisionsNone')}</p>}
        </section>

        <section className="card" aria-labelledby="command-kpis">
          <h3 className="card__title" id="command-kpis">{t('command.kpis')}</h3>
          {measures.length ? <dl className="command__kpis">{measures.map((m) => {
            // Money carries the mapping's currency code when the owner stated
            // one; otherwise it says so, and never assumes a currency.
            const stated = m.scale === 'money' && m.value !== null && Number.isFinite(m.value) && brief.currency ? brief.currency : null
            const value = stated ? formatMoney(m.value as number, stated, locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : formatValue(m, locale)
            const unit = m.scale === 'hours' ? ` ${t('command.hours')}` : m.scale === 'money' && !stated ? ` ${t('command.currency')}` : ''
            const tone = performanceTone(m.value, m.assessment)
            const verdict = tone === 'good' || tone === 'okay' || tone === 'bad'
            return <div key={m.key} data-source={`kpi.${m.key}`}>
              <dt dir="auto">{m.title}</dt>
              <dd><PerformanceValue tone={tone} reason={verdict ? m.assessment?.reason : undefined}><bdi>{value === null ? '—' : value}{value === null ? '' : unit}</bdi></PerformanceValue></dd>
            </div>
          })}</dl> : <p className="card__empty">{t('command.kpisNone')}</p>}
          {unavailable ? <p className="card__meta">{t('command.unavailable', { n: formatNumber(unavailable) })}</p> : null}
        </section>

        <section className="card" aria-labelledby="command-models">
          <h3 className="card__title" id="command-models">{t('command.models')}</h3>
          {brief.models.length ? <ul className="command__models">{brief.models.slice(0, 4).map((model, i) => {
            const tone = modelTone(model)
            return <li key={`${model.role}-${i}`}><span dir="auto">{model.target}</span>
              <span className="performance-value" data-performance={tone}><span className="performance-value__status">{t(`command.model.${tone}`)}</span></span></li>
          })}</ul> : <p className="card__empty">{t('command.modelsNone')}</p>}
          {brief.advisory?.prediction ? <p className="card__meta" dir="auto">{brief.advisory.prediction}</p> : null}
        </section>

        <section className="card" aria-labelledby="command-action">
          <h3 className="card__title" id="command-action">{t('command.action')}</h3>
          {recommendation ? <>
            <p className="command__action" dir="auto">{recommendation.text}</p>
            {assumption ? <p className="card__meta" dir="auto">{assumption.text}</p> : null}
            <p className="command__boundary"><Icon name="shield" size={14} />{t('command.actionNote')}</p>
          </> : <p className="card__empty">{t('command.actionNone')}</p>}
        </section>

        <section className="card" aria-labelledby="command-quality">
          <h3 className="card__title" id="command-quality">{t('command.quality')}</h3>
          {quality ? <p dir="auto">{quality.text}</p> : <p className="card__empty">{t('command.qualityNone')}</p>}
          <p className="card__meta">{t('command.asOf', { date: formatDate(brief.run.updated_at ?? run.updated_at) })}</p>
          {typeof failedChecks === 'number' && failedChecks > 0 ? <p className="command__caution">{t('command.failedChecks', { n: formatNumber(failedChecks) })}</p> : null}
          {limitations.length ? <details className="command__limits"><summary>{t('command.limitations', { n: formatNumber(limitations.length) })}</summary>
            <ul>{limitations.map((text) => <li key={text} dir="auto">{text}</li>)}</ul></details> : null}
        </section>

        <section className="card" aria-labelledby="command-questions">
          <h3 className="card__title" id="command-questions">{t('command.questions')}</h3>
          {brief.questions.length ? <ul className="command__questions">{brief.questions.slice(0, 3).map((q) => <li key={q.id} dir="auto">{q.text}</li>)}</ul> : null}
          {onOpenDashboard ? <button type="button" className="evidence-link" onClick={() => onOpenDashboard(run.id)}>{t('command.evidenceLink')}</button> : null}
        </section>
      </div>
    </section>
  )
}
