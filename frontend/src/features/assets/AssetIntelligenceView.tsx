import { useEffect, useState } from 'react'
import { usePack } from '../../i18n/pack'
import { assetMessages } from './messages'
import { api, ApiError } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import { stateLabel } from '../../shared/labels'
import { PerformanceLegend, PerformanceValue, performanceTone } from '../../shared/components/PerformanceValue'
import type { Pipelines } from '../../shared/types'
import { findAssetEvidence } from './assetEvidence'
import type { AssetEvidence } from './assetEvidence'
import { formatValue, needsDisclosure } from './kpiDisplay'
import type { RunKpis } from '../../shared/types'
import './assets.css'

interface Props {
  /** Absent in the view-only demo, where nothing can be uploaded. */
  onUpload?: () => void
  onOpenRun: (id: string) => void
}

export function AssetIntelligenceView({ onUpload, onOpenRun }: Props) {
  const { t, locale, formatDate, formatTime } = usePack(assetMessages)
  const [evidence, setEvidence] = useState<AssetEvidence | null>(null)
  const [pipelines, setPipelines] = useState<Pipelines | null>(null)
  const [kpiAnswer, setKpiAnswer] = useState<{ key: string; data: RunKpis } | null>(null)
  const [preparedAt, setPreparedAt] = useState('')
  const [kpiState, setKpiState] = useState<{ key: string; loading: boolean; error: string } | null>(null)
  const [kpiReload, setKpiReload] = useState(0)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let alive = true
    const controller = new AbortController()
    setBusy(true)
    setError('')
    setEvidence(null)
    setPreparedAt('')
    Promise.all([api.pipelines(controller.signal), api.assetEvidence(controller.signal)])
      .then(([config, result]) => {
        if (!alive) return
        setPipelines(config)
        setPreparedAt(result.prepared_at)
        setEvidence(findAssetEvidence(result.run ? [result.run] : []))
      })
      .catch((reason) => alive && setError(reason instanceof ApiError ? reason.message : t('assets.unavailable')))
      .finally(() => { if (alive) setBusy(false) })
    return () => { alive = false; controller.abort() }
  }, [reload, t])

  const runId = evidence?.run.id ?? null
  const kpiKey = JSON.stringify([runId, evidence?.run.updated_at, locale, kpiReload])
  const kpis = kpiAnswer?.key === kpiKey ? kpiAnswer.data : null
  useEffect(() => {
    if (!runId) return
    let alive = true
    const controller = new AbortController()
    setKpiState({ key: kpiKey, loading: true, error: '' })
    api.runKpis(runId, locale === 'ar' ? 'ar' : 'en', controller.signal)
      .then((result) => {
        if (!alive) return
        setKpiAnswer({ key: kpiKey, data: result })
        setKpiState({ key: kpiKey, loading: false, error: '' })
      })
      .catch(() => {
        if (!alive) return
        setKpiAnswer(null)
        setKpiState({ key: kpiKey, loading: false, error: t('assets.kpiFailed') })
      })
    return () => { alive = false; controller.abort() }
  }, [runId, locale, kpiKey, t])

  const enabled = Boolean(pipelines?.profiles.maintenance?.includes('rail_asset_manager'))
  return (
    <section className="panel" aria-label={t('assets.title')}>
      <div className="panel__inner panel__inner--wide asset-intelligence">
        <header className="asset-intelligence__header">
          <div>
            <h2>{t('assets.title')}</h2>
            <p>{t('assets.description')}</p>
          </div>
          {onUpload ? <button type="button" className="btn btn--primary" onClick={onUpload}>
            <Icon name="plus" size={17}/>{t('assets.upload')}
          </button> : null}
        </header>
        <div className="asset-intelligence__data">
          <div className="asset-intelligence__datahead">
            <h3>{t('assets.evidence')}</h3>
            <span>{busy ? t('assets.loading') : enabled ? t('assets.profile') : t('assets.profileMissing')}</span>
          </div>
          {error ? <div role="alert"><p>{error}</p><button type="button" className="btn btn--ghost" onClick={() => setReload((n) => n + 1)}>{t('assets.retry')}</button></div> : null}
          {!busy && preparedAt ? <p className="panel__note">{t('assets.checked')} <time dateTime={preparedAt}>{formatDate(preparedAt)} {formatTime(preparedAt)}</time> · {t('assets.scope')}</p> : null}
          {!busy && !error && !evidence ? (
            <div className="asset-intelligence__blank">
              <Icon name="database" size={31}/>
              <h4>{t('assets.empty')}</h4>
              <p>{t('assets.emptyDetail')}</p>
              {onUpload ? <button type="button" className="btn btn--ghost" onClick={onUpload}>{t('assets.upload')}</button> : null}
            </div>
          ) : null}
          {!busy && evidence ? (
            <>
              <dl className="asset-intelligence__source">
                <div><dt>{t('assets.dataset')}</dt><dd dir="auto">{evidence.run.dataset_name}</dd></div>
                <div><dt>{t('assets.runState')}</dt><dd>{stateLabel(t, evidence.run.state)}</dd></div>
                <div><dt>{t('assets.stage')}</dt><dd>{stateLabel(t, evidence.screen.state)}</dd></div>
                <div><dt>{t('assets.updated')}</dt><dd><time dateTime={evidence.run.updated_at}>{formatDate(evidence.run.updated_at)} {formatTime(evidence.run.updated_at)}</time></dd></div>
              </dl>
              {evidence.health ? <p dir="auto">{evidence.health}</p> : null}
              {kpiState?.key === kpiKey && kpiState.loading ? <p role="status">{t('assets.kpiLoading')}</p> : null}
              {kpiState?.key === kpiKey && kpiState.error ? <div role="alert">
                <p>{kpiState.error}</p><button type="button" className="btn btn--ghost" onClick={() => setKpiReload((n) => n + 1)}>{t('assets.kpiRetry')}</button>
              </div> : null}
              {/* Figures first; the screening and model notes that qualify the run follow. */}
              {kpis && kpis.measures.length ? (
                <div className="asset-intelligence__finding">
                  <strong>{t('assets.kpiHeading')}</strong>
                  <PerformanceLegend />
                  <ul className="asset-intelligence__kpis">
                    {kpis.measures.map((measure) => {
                      const shown = formatValue(measure, locale === 'ar' ? 'ar' : 'en')
                      const tone = performanceTone(measure.value, measure.assessment)
                      // A reason explains a verdict; "no target" is said once, below.
                      const verdict = tone === 'good' || tone === 'okay' || tone === 'bad'
                        || measure.assessment?.reason_code === 'target_outdated'
                      return (
                        <li key={measure.key} data-family={measure.family ?? 'other'}>
                          <span dir="auto">{measure.title}</span>
                          <PerformanceValue tone={tone} reason={verdict ? measure.assessment?.reason : undefined}>{shown ?? t('assets.kpiUndefined')}</PerformanceValue>
                          <small dir="auto">
                            {measure.population_label ?? measure.population} · {t('assets.kpiRecords', { records: String(measure.records) })}
                            {needsDisclosure(measure) ? ' · ' + (measure.value === null
                              ? t('assets.kpiNoEvidence')
                              : t('assets.kpiUnmeasured',
                                  { unmeasured: String(measure.records_unmeasured) })) : ''}
                          </small>
                        </li>
                      )
                    })}
                  </ul>
                  {Object.keys(kpis.unavailable).length ? (
                    <p className="asset-intelligence__caution" dir="auto">
                      {t('assets.kpiUnavailable',
                         { measures: Object.keys(kpis.unavailable).join(', ') })}
                    </p>
                  ) : null}
                  <details className="asset-intelligence__about">
                    <summary>{t('assets.about')}</summary>
                    {kpis.measures.some((measure) => performanceTone(measure.value, measure.assessment) === 'unassessed' && measure.assessment?.reason_code !== 'target_outdated') ? <p dir="auto">{t('assets.noTarget')}</p> : null}
                    <p>{t('assets.kpiScope')}</p>
                  </details>
                </div>
              ) : null}
              <div className="asset-intelligence__finding">
                <strong>{t('assets.screening')}</strong>
                <p dir="auto">{evidence.screen.summary || t('assets.notAvailable')}</p>
                <p className="asset-intelligence__caution">{t('assets.disclaimer')}</p>
              </div>
              {evidence.risk ? <div className="asset-intelligence__finding">
                <strong>{t('assets.modelEvidence')}</strong>
                <p dir="auto">{evidence.risk.summary || t('assets.notAvailable')}</p>
              </div> : null}
              {evidence.decisions.map((task) => <div key={task.id} className="asset-intelligence__finding">
                <strong dir="auto">{task.title}</strong>
                {task.claims.map((claim) => <p key={claim.id} dir="auto">{claim.text_ar ?? claim.text}</p>)}
              </div>)}
              <ul className="asset-intelligence__checks">
                {evidence.screen.quality_checks.map((check) => (
                  <li key={check.name}>
                    <span>{check.passed ? t('assets.passed') : t('assets.needsReview')}</span>
                    <span dir="auto">{check.name}: {check.detail}</span>
                  </li>
                ))}
              </ul>
              <button type="button" className="btn btn--primary" onClick={() => onOpenRun(evidence.run.id)}>
                {t('assets.openRun')}
              </button>
            </>
          ) : null}
        </div>
      </div>
    </section>
  )
}
