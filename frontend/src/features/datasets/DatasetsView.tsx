import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { api, ApiError } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import { formatBytes } from '../../shared/format'
import type { DatasetSummary, Usage } from '../../shared/types'

/** The most datasets GET /api/datasets returns. */
const DATASET_PAGE = 50

interface DatasetsViewProps {
  onAnalyse: (dataset: DatasetSummary) => void
  onAdd: () => void
}

/** The datasets stored for this owner. Datasets are content-addressed on
 *  the server, so analysing one again sends nothing: the run refers to
 *  the stored copy by its id. */
export function DatasetsView({ onAnalyse, onAdd }: DatasetsViewProps) {
  const { t, formatNumber, formatDate } = useI18n()
  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const [usage, setUsage] = useState<Usage | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setFailed(null)
    setDatasets(null)
    api
      .listDatasets()
      .then((result) => !cancelled && setDatasets(result.datasets))
      .catch((error) => {
        if (!cancelled) {
          setFailed(error instanceof ApiError ? error.message : t('datasets.failed'))
        }
      })
    api
      .usage()
      .then((result) => !cancelled && setUsage(result))
      .catch(() => {
        /* the allowance line is a courtesy; the list stands without it */
      })
    return () => {
      cancelled = true
    }
    // `t` changes only with the locale; a retry is the key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt])

  return (
    <section className="panel" aria-label={t('datasets.aria')}>
      <div className="panel__inner">
        <div className="panel__header">
          <div>
            <h2 className="panel__title">{t('datasets.title')}</h2>
            <p className="panel__desc">{t('datasets.desc')}</p>
          </div>
          <button type="button" className="btn btn--ghost" onClick={onAdd}>
            <Icon name="plus" size={16} />
            {t('datasets.add')}
          </button>
        </div>

        {usage ? (
          <p className="panel__note">
            {t('datasets.usage', {
              used: formatNumber(usage.datasets.used),
              limit: formatNumber(usage.datasets.limit),
              bytes: formatBytes(usage.dataset_bytes.used, formatNumber),
              bytesLimit: formatBytes(usage.dataset_bytes.limit, formatNumber),
            })}
          </p>
        ) : null}

        {failed ? (
          <div className="card">
            <p className="statusline statusline--error" role="alert" dir="auto">
              {failed}
            </p>
            <button type="button" className="btn btn--ghost" onClick={() => setAttempt((n) => n + 1)}>
              <Icon name="refresh" size={16} />
              {t('common.tryAgain')}
            </button>
          </div>
        ) : !datasets ? (
          <div className="card" role="status" aria-label={t('datasets.loading')}>
            <div className="skeleton skeleton--line" />
            <div className="skeleton skeleton--line" />
            <div className="skeleton skeleton--line skeleton--short" />
          </div>
        ) : datasets.length === 0 ? (
          <div className="card empty">
            <div className="empty__icon">
              <Icon name="database" size={32} />
            </div>
            <h3 className="empty__title">{t('datasets.emptyTitle')}</h3>
            <p className="empty__text">{t('datasets.emptyText')}</p>
            <div className="empty__actions">
              <button type="button" className="btn btn--primary" onClick={onAdd}>
                {t('datasets.add')}
              </button>
            </div>
          </div>
        ) : (
          <div className="card">
            <h3 className="card__title">{t('datasets.listTitle')}</h3>
            <ul className="datasets">
              {datasets.map((dataset) => (
                <li key={dataset.id} className="dataset">
                  <span className="dataset__icon">
                    <Icon name="database" size={18} />
                  </span>
                  <span className="dataset__body">
                    <span className="dataset__name" dir="auto">
                      {dataset.name}
                    </span>
                    <span className="dataset__meta">
                      <span className="dataset__figure">
                        {formatBytes(dataset.byte_size, formatNumber)}
                      </span>
                      {' · '}
                      {t('datasets.added', { date: formatDate(dataset.created_at) })}
                      {' · '}
                      <span className="dataset__hash">
                        {t('datasets.fingerprint', { hash: dataset.sha256.slice(0, 8) })}
                      </span>
                    </span>
                  </span>
                  <button
                    type="button"
                    className="btn btn--ghost dataset__action"
                    aria-label={t('datasets.analyseAria', { name: dataset.name })}
                    onClick={() => onAnalyse(dataset)}
                  >
                    {t('datasets.analyse')}
                  </button>
                </li>
              ))}
            </ul>
            {datasets.length >= DATASET_PAGE ? (
              <p className="panel__note">
                {t('datasets.capped', { n: formatNumber(DATASET_PAGE) })}
              </p>
            ) : null}
          </div>
        )}
      </div>
    </section>
  )
}
