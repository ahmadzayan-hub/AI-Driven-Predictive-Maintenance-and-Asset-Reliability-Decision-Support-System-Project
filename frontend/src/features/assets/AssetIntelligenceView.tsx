import { useEffect, useState } from 'react'
import { usePack } from '../../i18n/pack'
import { assetMessages } from './messages'
import { api, ApiError } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import { stateLabel } from '../../shared/labels'
import { PerformanceValue, performanceTone } from '../../shared/components/PerformanceValue'
import type { Pipelines } from '../../shared/types'
import { loadAssetEvidence } from './assetEvidence'
import type { AssetEvidence } from './assetEvidence'
import { formatValue, needsDisclosure } from './kpiDisplay'
import type { RunKpis } from '../../shared/types'
import './assets.css'

interface Props {
  onUpload: () => void
  onOpenRun: (id: string) => void
}

export function AssetIntelligenceView({ onUpload, onOpenRun }: Props) {
  const { t, locale } = usePack(assetMessages)
  const [evidence, setEvidence] = useState<AssetEvidence | null>(null)
  const [pipelines, setPipelines] = useState<Pipelines | null>(null)
  const [kpiAnswer, setKpiAnswer] = useState<{ key: string; data: RunKpis } | null>(null)
  const [searchCapped, setSearchCapped] = useState(false)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let alive = true
    setBusy(true)
    setError('')
    setEvidence(null)
    Promise.all([api.pipelines(), api.listRuns()])
      .then(async ([config, list]) => {
        const result = await loadAssetEvidence(list.runs, api.getRun, () => !alive)
        if (!alive) return
        setPipelines(config)
        setSearchCapped(list.runs.length >= 50)
        setEvidence(result.evidence)
        if (result.incomplete) {
          setError(t('assets.unavailable'))
        }
      })
      .catch((reason) => alive && setError(reason instanceof ApiError ? reason.message : t('assets.unavailable')))
      .finally(() => { if (alive) setBusy(false) })
    return () => { alive = false }
  }, [reload, t])

  const runId = evidence?.run.id ?? null
  const kpiKey = JSON.stringify([runId, evidence?.run.updated_at, locale])
  const kpis = kpiAnswer?.key === kpiKey ? kpiAnswer.data : null
  useEffect(() => {
    if (!runId) return
    let alive = true
    api.runKpis(runId, locale === 'ar' ? 'ar' : 'en')
      .then((result) => { if (alive) setKpiAnswer({ key: kpiKey, data: result }) })
      .catch(() => { if (alive) setKpiAnswer(null) })
    return () => { alive = false }
  }, [runId, locale, kpiKey])

  const enabled = Boolean(pipelines?.profiles.maintenance?.includes('rail_asset_manager'))
  return (
    <section className="panel" aria-label={t('assets.title')}>
      <div className="panel__inner panel__inner--wide asset-intelligence">
        <header className="asset-intelligence__header">
          <div>
            <p className="asset-intelligence__eyebrow">{t('assets.kicker')}</p>
            <h2>{t('assets.title')}</h2>
            <p>{t('assets.description')}</p>
          </div>
          <button type="button" className="btn btn--primary" onClick={onUpload}>
            <Icon name="plus" size={17}/>{t('assets.upload')}
          </button>
        </header>
        <div className="asset-intelligence__capabilities">
          {(['criticality', 'reliability', 'obsolescence'] as const).map((capability) => (
            <div key={capability} className="asset-intelligence__capability">
              <Icon name={capability === 'criticality' ? 'shield' : capability === 'reliability' ? 'activity' : 'clock'} size={21}/>
              <h3>{t('assets.' + capability as 'assets.criticality' | 'assets.reliability' | 'assets.obsolescence')}</h3>
              <p>{t('assets.' + capability + 'Sub' as 'assets.criticalitySub' | 'assets.reliabilitySub' | 'assets.obsolescenceSub')}</p>
            </div>
          ))}
        </div>
        <div className="asset-intelligence__data">
          <div className="asset-intelligence__datahead">
            <h3>{t('assets.evidence')}</h3>
            <span>{busy ? t('assets.loading') : enabled ? t('assets.profile') : t('assets.profileMissing')}</span>
          </div>
          {error ? <div role="alert"><p>{error}</p><button type="button" className="btn btn--ghost" onClick={() => setReload((n) => n + 1)}>{t('assets.retry')}</button></div> : null}
          {searchCapped ? <p className="panel__note">{t('assets.searchScope')}</p> : null}
          {!busy && !error && !evidence ? (
            <div className="asset-intelligence__blank">
              <Icon name="database" size={31}/>
              <h4>{t('assets.empty')}</h4>
              <p>{t('assets.emptyDetail')}</p>
              <button type="button" className="btn btn--ghost" onClick={onUpload}>{t('assets.upload')}</button>
            </div>
          ) : null}
          {!busy && evidence ? (
            <>
              <dl className="asset-intelligence__source">
                <div><dt>{t('assets.dataset')}</dt><dd dir="auto">{evidence.run.dataset_name}</dd></div>
                <div><dt>{t('assets.runState')}</dt><dd>{stateLabel(t, evidence.run.state)}</dd></div>
                <div><dt>{t('assets.stage')}</dt><dd>{stateLabel(t, evidence.screen.state)}</dd></div>
              </dl>
              <div className="asset-intelligence__finding">
                <strong>{t('assets.screening')}</strong>
                <p dir="auto">{evidence.screen.summary || t('assets.notAvailable')}</p>
                <p className="asset-intelligence__caution">{t('assets.disclaimer')}</p>
              </div>
              {evidence.risk ? <div className="asset-intelligence__finding">
                <strong>{t('assets.modelEvidence')}</strong>
                <p dir="auto">{evidence.risk.summary || t('assets.notAvailable')}</p>
              </div> : null}
              <ul className="asset-intelligence__checks">
                {evidence.screen.quality_checks.map((check) => (
                  <li key={check.name}>
                    <span>{check.passed ? t('assets.passed') : t('assets.needsReview')}</span>
                    <span dir="auto">{check.name}: {check.detail}</span>
                  </li>
                ))}
              </ul>
              {kpis && kpis.measures.length ? (
                <div className="asset-intelligence__finding">
                  <strong>{t('assets.kpiHeading')}</strong>
                  <ul className="asset-intelligence__checks">
                    {kpis.measures.map((measure) => {
                      const shown = formatValue(measure, locale === 'ar' ? 'ar' : 'en')
                      return (
                        <li key={measure.key}>
                          <PerformanceValue tone={performanceTone(measure.value, measure.assessment)} reason={measure.assessment?.reason}>{shown ?? t('assets.kpiUndefined')}</PerformanceValue>
                          <span dir="auto">
                            {measure.title} · {measure.population} ·{' '}
                            {t('assets.kpiRecords', { records: String(measure.records) })}
                            {needsDisclosure(measure) ? ' · ' + (measure.value === null
                              ? t('assets.kpiNoEvidence')
                              : t('assets.kpiUnmeasured',
                                  { unmeasured: String(measure.records_unmeasured) })) : ''}
                          </span>
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
                  <p className="asset-intelligence__caution">{t('assets.kpiScope')}</p>
                </div>
              ) : null}
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
