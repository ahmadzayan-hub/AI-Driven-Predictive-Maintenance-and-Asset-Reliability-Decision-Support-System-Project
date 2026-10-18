import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { api, ApiError } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import type { Pipelines } from '../../shared/types'
import { findAssetEvidence } from './assetEvidence'
import type { AssetEvidence } from './assetEvidence'
import './assets.css'

interface Props {
  onUpload: () => void
  onOpenRun: (id: string) => void
}

export function AssetIntelligenceView({ onUpload, onOpenRun }: Props) {
  const { t } = useI18n()
  const [evidence, setEvidence] = useState<AssetEvidence | null>(null)
  const [pipelines, setPipelines] = useState<Pipelines | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let alive = true
    setBusy(true)
    setError('')
    Promise.all([api.pipelines(), api.listRuns()])
      .then(async ([config, list]) => {
        const candidates = [...list.runs]
          .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
          .slice(0, 8)
        const details = await Promise.allSettled(candidates.map((run) => api.getRun(run.id)))
        if (!alive) return
        setPipelines(config)
        setEvidence(findAssetEvidence(details.flatMap((item) =>
          item.status === 'fulfilled' ? [item.value] : [])))
        if (details.length && details.every((item) => item.status === 'rejected')) {
          setError(t('assets.unavailable'))
        }
      })
      .catch((reason) => alive && setError(reason instanceof ApiError ? reason.message : t('assets.unavailable')))
      .finally(() => { if (alive) setBusy(false) })
    return () => { alive = false }
  }, [reload, t])

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
                <div><dt>{t('assets.runState')}</dt><dd>{evidence.run.state}</dd></div>
                <div><dt>{t('assets.stage')}</dt><dd>{evidence.screen.state}</dd></div>
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
