import { pickMeasures } from '../../shared/pickMeasures'
export { pickMeasures } from '../../shared/pickMeasures'
import { usePack } from '../../i18n/pack'
import { Icon } from '../../shared/components/Icon'
import { PerformanceValue, hasVerdict, performanceTone } from '../../shared/components/PerformanceValue'
import { formatMoney } from '../../shared/format'
import { modelTone } from '../../shared/modelTone'
import type { RunExecutive, RunSummary } from '../../shared/types'
import { formatValue } from '../assets/kpiDisplay'
import { commandMessages } from './commandMessages'

interface CommandCentreProps {
  run: RunSummary
  brief: RunExecutive | null
  failed: boolean
  onOpenDashboard?: (runId: string) => void
}

/** Literal source lead only: never synthesize, clip a sentence or drop the full text. */
export function recommendationLead(text: string, fallback: string): string {
  if (text.length <= 180) return text
  return text.match(/^(.{20,180}?[.!?؟。])(?:\s|$)/u)?.[1] ?? fallback
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
  const recommendation = brief.findings.find((f) => f.id === 'cl_recommendation' || f.kind === 'recommendation')
  const assumption = brief.findings.find((f) => f.stage === 'prescriptive' && f.kind === 'assumption' && f !== recommendation)
  const quality = brief.findings.find((f) => f.stage === 'quality')
  const failedChecks = brief.evidence.find((e) => e.id === 'executive.validation.failed_checks')?.value
  const fullRecommendation = brief.advisory?.recommendation ?? brief.headline
  const lead = recommendationLead(fullRecommendation, t('command.action'))
  const limitations = brief.readiness.limitations

  return (
    <section className="command" aria-label={t('command.aria')}>
      <div className="card command__hero">
        <div className="command__hero-body">
          <span className="command__eyebrow">{t('command.eyebrow')} · <span dir="auto">{run.dataset_name}</span></span>
          <p className="command__headline" dir="auto">{lead}</p>
          {lead !== fullRecommendation && <details className="command__limits"><summary>{t('command.fullRecommendation')}</summary><p dir="auto">{fullRecommendation}</p></details>}
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
        <section className="card command__performance" aria-labelledby="command-kpis">
          <h3 className="card__title" id="command-kpis">{t('command.kpis')}</h3>
          {measures.length ? <dl className="command__kpis">{measures.map((m) => {
            // Money carries the mapping's currency code when the owner stated
            // one; otherwise it says so, and never assumes a currency.
            const stated = m.scale === 'money' && m.value !== null && Number.isFinite(m.value) && brief.currency ? brief.currency : null
            const value = stated ? formatMoney(m.value as number, stated, locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : formatValue(m, locale)
            const unit = m.scale === 'hours' ? ` ${t('command.hours')}` : m.scale === 'money' && !stated ? ` ${t('command.currency')}` : ''
            const tone = performanceTone(m.value, m.assessment)
            const verdict = hasVerdict(tone)
            return <div key={m.key} data-source={`kpi.${m.key}`}>
              <dt dir="auto">{m.title}</dt>
              <dd><PerformanceValue tone={tone} reason={verdict ? m.assessment?.reason : undefined}><bdi>{value ?? '-'}{value === null ? '' : <small>{unit}</small>}</bdi></PerformanceValue></dd>
            </div>
          })}</dl> : <p className="card__empty">{t('command.kpisNone')}</p>}
          <p className="card__meta">{t('command.context')}</p>
          {unavailable ? <p className="card__meta">{t('command.unavailable', { n: formatNumber(unavailable) })}</p> : null}
        </section>

        <section className="card" aria-labelledby="command-decisions">
          <h3 className="card__title" id="command-decisions">{t('command.decisions')} <span className="command__count">{formatNumber(decisions.length)}</span></h3>
          {decisions.length ? <ol className="command__list">{decisions.slice(0, 4).map((d, i) => (
            <li key={d.id}><span className="command__n" aria-hidden="true">{formatNumber(i + 1)}</span>
              <div><details><summary><strong dir="auto">{d.title}</strong></summary><p dir="auto">{d.detail}</p>
                {d.owner ? <p className="command__owner">{t('command.owner')}: <span dir="auto">{d.owner}</span> · {t('command.gate')}: <span dir="auto">{d.gate}</span></p> : null}</details></div>
            </li>))}</ol> : <p className="card__empty">{t('command.decisionsNone')}</p>}
        </section>

        <section className="card" aria-labelledby="command-quality">
          <h3 className="card__title" id="command-quality">{t('command.quality')}</h3>
          {quality ? <p dir="auto">{quality.text}</p> : <p className="card__empty">{t('command.qualityNone')}</p>}
          {typeof failedChecks === 'number' && failedChecks > 0 ? <p className="command__caution">{t('command.failedChecks', { n: formatNumber(failedChecks) })}</p> : null}
          {limitations.length ? <details className="command__limits"><summary>{t('command.limitations', { n: formatNumber(limitations.length) })}</summary>
            <ul>{limitations.map((text) => <li key={text} dir="auto">{text}</li>)}</ul></details> : null}
        </section>

        <details className="card command__detail" aria-labelledby="command-models">
          <summary><h3 className="card__title" id="command-models">{t('command.models')}</h3></summary>
          {brief.models.length ? <ul className="command__models">{brief.models.slice(0, 4).map((model, i) => {
            const tone = modelTone(model)
            return <li key={`${model.role}-${i}`}><span dir="auto">{model.target}</span>
              <span className="performance-value" data-performance={tone}><span className="performance-value__status">{t(`command.model.${tone}`)}</span></span></li>
          })}</ul> : <p className="card__empty">{t('command.modelsNone')}</p>}
          {brief.advisory?.prediction ? <p className="card__meta" dir="auto">{brief.advisory.prediction}</p> : null}
        </details>

        <details className="card command__detail" aria-labelledby="command-action">
          <summary><h3 className="card__title" id="command-action">{t('command.action')}</h3></summary>
          {recommendation ? <>
            <p className="command__action" dir="auto">{recommendation.text}</p>
            {assumption ? <p className="card__meta" dir="auto">{assumption.text}</p> : null}
            <p className="command__boundary"><Icon name="shield" size={14} />{t('command.actionNote')}</p>
          </> : <p className="card__empty">{t('command.actionNone')}</p>}
        </details>

        <details className="card command__detail" aria-labelledby="command-questions">
          <summary><h3 className="card__title" id="command-questions">{t('command.questions')}</h3></summary>
          {brief.questions.length ? <ul className="command__questions">{brief.questions.slice(0, 3).map((q) => <li key={q.id} dir="auto">{q.text}</li>)}</ul> : null}
          {onOpenDashboard ? <button type="button" className="evidence-link" onClick={() => onOpenDashboard(run.id)}>{t('command.evidenceLink')}</button> : null}
        </details>
      </div>
    </section>
  )
}
