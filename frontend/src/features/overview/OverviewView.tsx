import '../../shared/styles/kpi.css'
import './overview.css'
import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { api, ApiError } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import { stateLabel, typeLabel } from '../../shared/labels'
import type { RunDetail, RunExecutive, RunSummary, Usage } from '../../shared/types'
import type { RunPreset } from '../runs/RunsView'
import { countRuns, latestWithFindings, recentRuns, RUN_PAGE, waitingForApproval } from './summary'
import { CommandCentre } from './CommandCentre'
import { DecisionActions } from './DecisionActions'
import { summarizeRunEvidence } from './evidence'
import { downloadMotionRun } from './motionEvidence'

interface OverviewViewProps {
  onOpenRun: (id: string) => void
  onStart: (preset: RunPreset | null) => void
  onAddDataset?: () => void
  /** False in the view-only demo: no button that would start an analysis. */
  canStart?: boolean
  onApprovals?: () => void
  /** With a run id, opens that run's executive overview; without, the
   *  dashboard as last left. */
  onOpenDashboard?: (runId?: string) => void
  /** The list of analyses. Falls back to the new-analysis form when absent. */
  onSeeAll?: () => void
}

/** Where the workspace stands, on one screen: the figures, the latest
 *  findings, what is waiting at the approval gate, and the newest runs.
 *  Everything comes from existing endpoints; nothing is computed here
 *  that the server did not already say. */
export function OverviewView({ onOpenRun, onStart, onAddDataset, onApprovals, onOpenDashboard, onSeeAll, canStart = true }: OverviewViewProps) {
  const { t, tx, locale, formatNumber, formatDate } = useI18n()
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  const [usage, setUsage] = useState<Usage | null>(null)
  const [usageFailed, setUsageFailed] = useState(false)
  const [latest, setLatest] = useState<RunDetail | null>(null)
  const [latestFailed, setLatestFailed] = useState(false)
  const [brief, setBrief] = useState<RunExecutive | null>(null)
  const [briefFailed, setBriefFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [motionError, setMotionError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setFailed(null)
    setRuns(null)
    setLatest(null)
    setLatestFailed(false)
    setBrief(null)
    setBriefFailed(false)
    setUsageFailed(false)
    api
      .listRuns()
      .then(async (result) => {
        if (cancelled) return
        setRuns(result.runs)
        const source = latestWithFindings(result.runs)
        if (!source) return
        // The decision brief and the run detail are independent reads:
        // one failing never hides the other.
        api.runExecutive(source.id, locale)
          .then((executive) => !cancelled && setBrief(executive))
          .catch(() => !cancelled && setBriefFailed(true))
        try {
          const detail = await api.getRun(source.id)
          if (!cancelled) setLatest(detail)
        } catch {
          if (!cancelled) setLatestFailed(true)
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setFailed(error instanceof ApiError ? error.message : t('overview.failed'))
        }
      })
    api
      .usage()
      .then((result) => !cancelled && setUsage(result))
      .catch(() => !cancelled && setUsageFailed(true))
    return () => {
      cancelled = true
    }
    // A retry or a language change re-reads; `t` follows the locale.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, locale])

  const orderedRuns = recentRuns(runs ?? [], RUN_PAGE)
  const agentRun = orderedRuns.find((run) => run.state === 'running' || run.state === 'queued') ?? orderedRuns[0]
  const actions = onOpenDashboard ? (
    <DecisionActions
      onUpload={canStart ? onAddDataset : undefined}
      onDashboard={() => onOpenDashboard()}
      onApprovals={onApprovals}
      onAgents={agentRun ? () => onOpenRun(agentRun.id) : undefined}
    />
  ) : null

  const header = (
    <div className="panel__header">
      <div>
        <h2 className="panel__title">{t('overview.title')}</h2>
        <p className="panel__desc">{t('overview.desc')}</p>
      </div>
      {canStart ? <button type="button" className="btn btn--primary" onClick={() => onStart({ kind: 'upload' })}>
        <Icon name="plus" size={16} />
        {t('overview.start')}
      </button> : null}
    </div>
  )

  if (failed) {
    return (
      <section className="panel" aria-label={t('overview.aria')}>
        <div className="panel__inner panel__inner--wide">
          {header}
        {actions}
          <div className="card">
            <p className="statusline statusline--error" role="alert" dir="auto">
              {failed}
            </p>
            <button type="button" className="btn btn--ghost" onClick={() => setAttempt((n) => n + 1)}>
              <Icon name="refresh" size={16} />
              {t('common.tryAgain')}
            </button>
          </div>
        </div>
      </section>
    )
  }

  if (!runs) {
    return (
      <section className="panel" aria-label={t('overview.aria')}>
        <div className="panel__inner panel__inner--wide">
          {header}
          {actions}
          <div className="kpis" role="status" aria-label={t('overview.loading')}><span className="visually-hidden">{t('overview.loading')}</span>
            {[0, 1, 2, 3].map((n) => (
              <div key={n} className="kpi">
                <div className="skeleton skeleton--line" />
                <div className="skeleton skeleton--title" />
              </div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  if (runs.length === 0) {
    return (
      <section className="panel" aria-label={t('overview.aria')}>
        <div className="panel__inner panel__inner--wide">
          {header}
          {actions}
          <div className="card empty">
            <img className="overview__onboarding-art" src="/artwork/asset-reliability-hero.svg" alt="" width={800} height={206} loading="lazy" />
            <div className="empty__icon">
              <img src="/artwork/asset-intelligence-icon.svg" alt="" width={32} height={32} />
            </div>
            <h3 className="empty__title">{t('overview.emptyTitle')}</h3>
            <p className="empty__text">{t('overview.emptyText')}</p>
            {canStart ? <div className="empty__actions">
              <button type="button" className="btn btn--primary" onClick={() => onStart(null)}>
                {t('overview.trySample')}
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => onStart({ kind: 'upload' })}
              >
                {t('overview.addDataset')}
              </button>
            </div> : null}
          </div>
        </div>
      </section>
    )
  }

  const counts = countRuns(runs)
  const waiting = waitingForApproval(runs)
  const recent = recentRuns(runs)
  const source = latestWithFindings(runs)
  const findings = latest ? latest.reports.filter((report) => (report.headline ?? '').trim()) : []
  const reportLang = latest?.report_language === 'ar' ? 'ar' : 'en'
  // A run's independent validator is evidence about that run, not a claim
  // that every model is accurate or operationally approved.
  const evidence = summarizeRunEvidence(latest)

  const tiles = [
    {
      key: 'finished',
      hue: 'teal',
      label: t('overview.finished'),
      value: counts.finished,
      sub: counts.active > 0 ? t('overview.inProgress', { n: formatNumber(counts.active) }) : '',
      attention: false,
    },
    {
      key: 'waiting',
      hue: 'teal',
      label: t('overview.waitingTile'),
      value: counts.waiting,
      sub: '',
      attention: counts.waiting > 0,
    },
    {
      key: 'datasets',
      hue: 'violet',
      label: t('usage.datasets'),
      value: usage?.datasets.used,
      sub: usage
        ? t('overview.ofLimit', { limit: formatNumber(usage.datasets.limit) })
        : usageFailed
          ? t('usage.unavailable')
          : '',
      attention: false,
    },
    {
      key: 'today',
      hue: 'magenta',
      label: t('usage.runs'),
      value: usage?.runs_today.used,
      sub: usage
        ? t('overview.ofLimit', { limit: formatNumber(usage.runs_today.limit) })
        : usageFailed
          ? t('usage.unavailable')
          : '',
      attention: false,
    },
  ]

  return (
    <section className="panel" aria-label={t('overview.aria')}>
      <div className="panel__inner panel__inner--wide">
        {header}

        {source ? <CommandCentre run={source} brief={brief} failed={briefFailed} onOpenDashboard={onOpenDashboard} /> : null}

        {/* Counts are counts: a status reads only where a target exists. */}
        <dl className="kpis">
          {tiles.map((tile) => (
            <div key={tile.key} data-hue={tile.hue} className={`kpi ${tile.attention ? 'kpi--attention' : ''}`}>
              <dt className="kpi__label">{tile.label}</dt>
              <dd className="kpi__value"><bdi>{tile.value === undefined ? '—' : formatNumber(tile.value)}</bdi></dd>
              {tile.sub ? <dd className="kpi__sub">{tile.sub}</dd> : null}
            </div>
          ))}
        </dl>
        {counts.capped ? (
          <p className="panel__note">{t('overview.capped', { n: formatNumber(RUN_PAGE) })}</p>
        ) : null}

        <section className="card overview__evidence" aria-label={t('overview.evidenceHeading')}>
          <div className="overview__evidence-head">
            <Icon name="shield" size={22} />
            <div>
              <h3 className="card__title">{t('overview.evidenceHeading')}</h3>
              <p className="card__meta">{latest
                ? t('overview.evidenceStages', {
                    done: formatNumber(evidence.completed),
                    total: formatNumber(evidence.total),
                  })
                : t('overview.evidenceMissing')}</p>
            </div>
          </div>
          <div className="overview__evidence-state">
            <strong>{!latest ? t('overview.evidenceUnavailable')
              : evidence.status === 'passed' ? t('overview.evidencePassed')
                : t('overview.evidencePending')}</strong>
            <p>{t('overview.evidenceScope')}</p>
          </div>
          {latest ? (
            <>
              <button type="button" className="btn btn--ghost" onClick={() => onOpenRun(latest.id)}>
                {t('overview.openAnalysis')}
              </button>
              <a
                href="/motion-studio/index.html"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn--ghost"
              >
                {reportLang === 'ar' ? 'فتح محرر الموشن' : 'Open Motion Studio'}
              </a>
              <button
                type="button"
                className="btn btn--ghost"
                disabled={evidence.status !== 'passed' || !latest.report?.id || !latest.reports.some((r) => r.headline?.trim())}
                title={evidence.status === 'passed'
                  ? (reportLang === 'ar' ? 'تنزيل مسودة موشن من تحليل موثق، لا يعني الموافقة للنشر'
                    : 'Download a source-linked motion draft, not publication approval')
                  : (reportLang === 'ar' ? 'يتطلب تحليلًا اجتاز فحوص الأدلة'
                    : 'Requires a run that passed evidence checks')}
                onClick={() => {
                  try {
                    setMotionError(null)
                    api.motionStoryboard(latest.id)
                      .then(downloadMotionRun)
                      .catch(() => setMotionError(reportLang === 'ar'
                        ? 'تعذّر إنشاء مسودة الفيديو: راجع حالة الأدلة وصلاحياتك.'
                        : 'Motion draft could not be prepared. Check the evidence status and your permissions.'))
                  } catch {
                    setMotionError(reportLang === 'ar' ? 'تعذّر إنشاء المسودة.' : 'Could not prepare the draft.')
                  }
                }}
              >
                {reportLang === 'ar' ? 'مسودة فيديو تحليلي' : 'Motion draft'}
              </button>
              {motionError ? <p role="alert" className="statusline statusline--error" dir="auto" lang={reportLang}>{motionError}</p> : null}
            </>
          ) : null}
        </section>

        {actions}
        <div className="overview__grid">
          <div className="card">
            <h3 className="card__title">{t('overview.findings')}</h3>
            {latest ? (
              <>
                <p className="card__meta">
                  {tx('overview.findingsFrom', {
                    goal: <span dir="auto">{latest.goal}</span>,
                    state: <strong>{stateLabel(t, latest.state)}</strong>,
                  })}
                </p>
                {findings.length > 0 ? (
                  <ul className="findings">
                    {findings.map((report) => (
                      <li key={report.type} className="finding" data-type={report.type}>
                        <span className="finding__type">
                          {typeLabel(t, report.type, report.title)}
                        </span>
                        <span
                          className="finding__text"
                          lang={reportLang}
                          dir={reportLang === 'ar' ? 'rtl' : 'ltr'}
                        >
                          {report.headline}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="card__empty">{t('overview.findingsNone')}</p>
                )}
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => onOpenRun(latest.id)}
                >
                  {t('overview.openAnalysis')}
                </button>
              </>
            ) : latestFailed ? (
              <p className="card__empty">{t('overview.findingsFailed')}</p>
            ) : counts.finished + counts.waiting === 0 ? (
              <p className="card__empty">{t('overview.findingsNone')}</p>
            ) : (
              <>
                <div className="skeleton skeleton--line" />
                <div className="skeleton skeleton--line skeleton--short" />
              </>
            )}
          </div>

          <div className="card">
            <h3 className="card__title">{t('overview.waiting')}</h3>
            {onApprovals ? <button type="button" className="evidence-link" onClick={onApprovals}>{t('approvals.openInbox')}</button> : null}
            {waiting.length === 0 ? (
              <p className="card__empty">{t('overview.waitingNone')}</p>
            ) : (
              <ul className="controls__list">
                {waiting.map((run) => (
                  <li key={run.id}>
                    <button type="button" className="controlrow" onClick={() => onOpenRun(run.id)}>
                      <Icon name="shield" size={17} />
                      <span className="controlrow__body">
                        <span className="controlrow__label" dir="auto">
                          {run.goal}
                        </span>
                        <span className="controlrow__help">
                          <span dir="auto">{run.dataset_name}</span> ·{' '}
                          {t('overview.waitingSince', { date: formatDate(run.updated_at) })}
                        </span>
                      </span>
                      <span className="controlrow__action">{t('overview.review')}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="card">
          <h3 className="card__title">{t('overview.recent')}</h3>
          <ul className="controls__list">
            {recent.map((run) => (
              <li key={run.id}>
                <button type="button" className="controlrow" onClick={() => onOpenRun(run.id)}>
                  <Icon name="clock" size={17} />
                  <span className="controlrow__body">
                    <span className="controlrow__label" dir="auto">
                      {run.goal}
                    </span>
                    <span className="controlrow__help">
                      <span dir="auto">{run.dataset_name}</span> · {stateLabel(t, run.state)} ·{' '}
                      {formatDate(run.updated_at)}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="btn btn--subtle" onClick={() => (onSeeAll ? onSeeAll() : onStart(null))}>
            {t('overview.seeAll')}
          </button>
        </div>
      </div>
    </section>
  )
}

