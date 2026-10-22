/** The run's decision record (slice three, A13): the recommendation, the
 *  inputs each option was scored on and whether each was stated or
 *  assumed, the range the ranking survives, and who decided. Every figure
 *  is the report's own calculation; nothing is computed here. */
import { usePack } from '../../i18n/pack'
import type { DecisionRecord } from '../../shared/types'
import { decisionMessages } from './messages'
import './decision.css'

export function DecisionRecordCard({ decision, language }: { decision: DecisionRecord; language: 'en' | 'ar' }) {
  const { t, formatNumber, formatDate } = usePack(decisionMessages)
  const percent = (n: number) => formatNumber(n, { style: 'percent', maximumFractionDigits: 1 })
  const amount = (n: number) => formatNumber(n, { maximumFractionDigits: 2 })
  const impact = decision.expected_impact
  const uncertainty = decision.uncertainty
  const flip = uncertainty?.flip_points.find((point) => point.flip_at_uplift !== null && point.inside_range)
  const gate = decision.approval
  // The gate records "approved_once" for a one-time publication; any
  // approved state reads as approved here, any rejected one as rejected.
  const stateLabel = gate?.state.startsWith('approved') ? t('decision.state.approved')
    : gate?.state.startsWith('rejected') ? t('decision.state.rejected') : gate?.state ?? ''
  return (
    <section className="card decision-record" aria-labelledby="decision-record-title">
      <p className="eyebrow">{t('decision.id')}: <span dir="ltr" lang="en">{decision.decision_id}</span></p>
      <h3 className="card__title" id="decision-record-title">{t('decision.recordTitle')}</h3>
      <p className="field__help">{t('decision.recordIntro')}</p>
      <dl className="decision-record__facts">
        <dt>{t('decision.recommended')}</dt>
        <dd>
          {decision.recommended_action
            ? <strong dir="auto" lang={language}>{decision.recommended_action}</strong>
            : t('decision.none')}
          <span className="decision-record__basis">{t(`decision.basis.${decision.recommendation_basis}`)}</span>
        </dd>
        <dt>{t('decision.scope')}</dt>
        <dd dir="auto">{decision.scope}</dd>
        <dt>{t('decision.impact')}</dt>
        <dd>
          {t('decision.impactRange', {
            low: amount(impact.low), high: amount(impact.high), measure: decision.risk.measure,
            rangeLow: percent(impact.uplift_range[0]), rangeHigh: percent(impact.uplift_range[1]),
          })}
          <span className={`decision-record__tag decision-record__tag--${impact.label}`}>
            {impact.label === 'stated' ? t('decision.impactStated') : t('decision.impactIllustrative')}
          </span>
        </dd>
      </dl>
      {decision.alternatives.length ? (
        <table className="decision-record__table">
          <caption>{t('decision.options')}</caption>
          <thead><tr>
            <th scope="col">{t('decision.option')}</th>
            <th scope="col">{t('decision.improvement')}</th>
            <th scope="col">{t('decision.costCol')}</th>
            <th scope="col">{t('decision.gain')}</th>
          </tr></thead>
          <tbody>
            {decision.alternatives.map((option) => (
              <tr key={option.key} className={option.key === decision.decision_id.split(':').pop() ? 'decision-record__winner' : undefined}>
                <th scope="row" dir="auto" lang={language}>{option.title}</th>
                <td>{percent(option.uplift)} <small className={`decision-record__tag decision-record__tag--${option.uplift_source}`}>{t(`decision.${option.uplift_source}`)}</small></td>
                <td>{option.cost === null ? <small className="decision-record__tag">{t('decision.costNotStated')}</small> : amount(option.cost)}</td>
                <td>{amount(option.expected_gain)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {uncertainty ? (
        <p className={`decision-record__verdict decision-record__verdict--${uncertainty.stable_within_ranges ? 'stable' : 'close'}`}>
          {uncertainty.stable_within_ranges
            ? t('decision.stable')
            : flip
              ? t('decision.unstable', { target: flip.target, pct: percent(flip.flip_at_uplift as number) })
              : t('decision.unstableNoFlip')}
        </p>
      ) : null}
      <p className="decision-record__gate">
        <strong>{t('decision.gate')}:</strong>{' '}
        {gate
          ? gate.decided_by
            ? t('decision.decided', { state: stateLabel, who: gate.decided_by, when: gate.decided_at ? formatDate(gate.decided_at) : '' })
            : t('decision.decidedAnon', { state: stateLabel, when: gate.decided_at ? formatDate(gate.decided_at) : '' })
          : t('decision.pending')}
      </p>
    </section>
  )
}
