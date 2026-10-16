import { useCallback, useEffect, useRef, useState } from 'react'
import { useI18n } from '../../i18n'
import { api, ApiError, MAX_UPLOAD_BYTES } from '../../shared/api'
import { barGeometry } from '../../shared/charts'
import { Icon } from '../../shared/components/Icon'
import { formatLabel, questionLabel, stateLabel, typeLabel } from '../../shared/labels'
import type {
  ChartSpec,
  DatasetSummary,
  Pipelines,
  RunDetail,
  RunSummary,
  UploadResult,
} from '../../shared/types'

const ACTIVE_STATES = ['queued', 'running']

const SOURCE_LABELS = {
  sample: 'runs.sample',
  stored: 'runs.stored',
  upload: 'runs.upload',
} as const

function BarChart({ chart }: { chart: ChartSpec }) {
  const barWidth = 100 / chart.values.length
  const { zero, bars } = barGeometry(chart.values)
  return (
    <svg viewBox="0 0 100 58" role="img" aria-label={chart.alt} className="runchart__svg">
      {bars.map((bar, index) => (
        <rect
          key={chart.labels[index]}
          x={index * barWidth + barWidth * 0.15}
          y={bar.y}
          width={barWidth * 0.7}
          height={bar.height}
          rx="1"
          fill={bar.negative ? 'var(--highlight)' : 'var(--accent-solid)'}
        />
      ))}
      <line x1="0" y1={zero} x2="100" y2={zero} stroke="var(--border-strong)" strokeWidth="0.5" />
      {chart.labels.map((label, index) => (
        <text
          key={label}
          x={index * barWidth + barWidth / 2}
          y="56"
          textAnchor="middle"
          fontSize="3.4"
          fill="var(--text-faint)"
        >
          {label.length > 9 ? `${label.slice(0, 8)}…` : label}
        </text>
      ))}
    </svg>
  )
}

function LineChart({ chart }: { chart: ChartSpec }) {
  const { t } = useI18n()
  const max = Math.max(...chart.values, 1)
  const min = Math.min(...chart.values, 0)
  const span = max - min || 1
  const xy = chart.values.map((value, index) => ({
    x: (index / Math.max(chart.values.length - 1, 1)) * 96 + 2,
    y: 48 - ((value - min) / span) * 42,
  }))
  const join = (list: { x: number; y: number }[]) => list.map((p) => `${p.x},${p.y}`).join(' ')
  // A projection is drawn dashed from the last measured point onwards, with
  // the boundary marked and named, so nobody reads it as a measurement.
  const from = chart.forecast_from
  const split = from !== undefined && from > 0 && from < xy.length
  const history = split ? xy.slice(0, from) : xy
  const projection = split ? xy.slice(from - 1) : []
  const boundaryX = split ? xy[from - 1].x : 0
  return (
    <svg viewBox="0 0 100 58" role="img" aria-label={chart.alt} className="runchart__svg">
      <polyline points={join(history)} fill="none" stroke="var(--accent-solid)" strokeWidth="1.4" />
      {split ? (
        <>
          <polyline
            points={join(projection)}
            fill="none"
            stroke="var(--accent-solid)"
            strokeWidth="1.4"
            strokeDasharray="2.4 1.6"
          />
          <line
            x1={boundaryX}
            y1="4"
            x2={boundaryX}
            y2="50"
            stroke="var(--text-faint)"
            strokeWidth="0.4"
            strokeDasharray="1 1"
          />
          <text x={boundaryX + 1} y="7" fontSize="3.2" fill="var(--text-faint)">
            {t('runs.forecast')}
          </text>
        </>
      ) : null}
      <line x1="0" y1="50" x2="100" y2="50" stroke="var(--border-strong)" strokeWidth="0.5" />
      <text x="2" y="56" fontSize="3.4" fill="var(--text-faint)">
        {chart.labels[0]}
      </text>
      <text x="98" y="56" fontSize="3.4" textAnchor="end" fill="var(--text-faint)">
        {chart.labels[chart.labels.length - 1]}
      </text>
    </svg>
  )
}

const TASK_ICON: Record<string, string> = {
  succeeded: '✓',
  failed: '✕',
  skipped: '—',
  cancelled: '—',
  running: '…',
  awaiting_approval: '!',
  pending: '·',
}

/** Arrow-key movement inside the analytics-type tablist. Selection
 *  follows focus, which is the expected behaviour when switching panels
 *  is cheap — here it only swaps already-loaded text. In a right-to-left
 *  layout the tabs run the other way, so the arrows do too (WAI-ARIA). */
function nextTabIndex(key: string, current: number, count: number, rtl: boolean): number | null {
  const forward = rtl ? 'ArrowLeft' : 'ArrowRight'
  const backward = rtl ? 'ArrowRight' : 'ArrowLeft'
  if (key === forward) return (current + 1) % count
  if (key === backward) return (current - 1 + count) % count
  if (key === 'Home') return 0
  if (key === 'End') return count - 1
  return null
}

/** What another view asked the form to start with: the upload fields
 *  open, or a dataset already stored on the server. The view is mounted
 *  afresh on each visit, so the preset seeds its first render. */
export type RunPreset = { kind: 'upload' } | { kind: 'stored'; id: string; name: string }

interface RunsViewProps {
  /** A run to open on arrival — the one the assistant just started. */
  openRunId?: string | null
  openNonce?: number
  preset?: RunPreset | null
}

/** The custom stages a profile includes, by title, for the picker's help. */
function stageTitles(pipelines: Pipelines, profile: string): string[] {
  const roles = profile ? (pipelines.profiles[profile] ?? []) : pipelines.default
  return roles.map((role) => {
    const stage = pipelines.stages.find((s) => s.role === role)
    return stage ? stage.title.split(' — ')[0] : role
  })
}

export function RunsView({ openRunId = null, openNonce = 0, preset = null }: RunsViewProps) {
  const { t, tx, plural, isRtl, locale, formatNumber, formatDate } = useI18n()
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [run, setRun] = useState<RunDetail | null>(null)
  // Where the data comes from (ADR 0024). A stored dataset and an
  // uploaded file are both analysed by reference: the run sends an id.
  const [source, setSource] = useState<'sample' | 'stored' | 'upload'>(() =>
    preset?.kind === 'stored' ? 'stored' : preset?.kind === 'upload' ? 'upload' : 'sample',
  )
  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null)
  const [storedId, setStoredId] = useState(() => (preset?.kind === 'stored' ? preset.id : ''))
  const [goal, setGoal] = useState(() =>
    preset?.kind === 'stored' ? t('runs.goalStored', { name: preset.name }) : t('runs.goalDefault'),
  )
  // The goal the form last wrote itself. A goal the person typed is
  // never replaced when they pick another dataset.
  const autoGoal = useRef(goal)
  const [uploaded, setUploaded] = useState<UploadResult | null>(null)
  const [uploading, setUploading] = useState<string | null>(null)
  const [csvDraft, setCsvDraft] = useState('')
  // Stepping stops for two different reasons: the user paused the run
  // (durable, server-side, also obeyed by a background worker) or a
  // request failed (local to this tab, cleared on the next action).
  const [stoppedByError, setStoppedByError] = useState(false)
  // Which analytics type's report is on screen. Descriptive is the floor
  // of the maturity ladder, so it opens first.
  const [openReport, setOpenReport] = useState('descriptive')
  const [busy, setBusy] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [throttled, setThrottled] = useState(false)
  // Custom stages and profiles (ADR 0020). The picker exists only when
  // an operator configured profiles; a default install shows nothing.
  const [pipelines, setPipelines] = useState<Pipelines | null>(null)
  const [profile, setProfile] = useState('')
  const advancing = useRef(false)

  const refreshList = useCallback(async () => {
    try {
      const result = await api.listRuns()
      setRuns(result.runs)
    } catch {
      /* list refresh is best-effort; the create/open flows surface errors */
    }
  }, [])

  useEffect(() => {
    void refreshList()
  }, [refreshList])

  useEffect(() => {
    let cancelled = false
    api
      .listDatasets()
      .then((result) => !cancelled && setDatasets(result.datasets))
      .catch(() => !cancelled && setDatasets([]))
    return () => {
      cancelled = true
    }
  }, [])

  function suggestGoal(name: string | null) {
    if (goal !== autoGoal.current) return
    const next = name ? t('runs.goalStored', { name }) : t('runs.goalDefault')
    autoGoal.current = next
    setGoal(next)
  }

  async function uploadFile(file: File) {
    setErrorMessage(null)
    setUploaded(null)
    if (file.size > MAX_UPLOAD_BYTES) {
      setErrorMessage(
        t('runs.tooBig', {
          name: file.name,
          size: formatNumber(file.size / 1_000_000, { maximumFractionDigits: 1 }),
          limit: formatNumber(MAX_UPLOAD_BYTES / 1_000_000),
        }),
      )
      return
    }
    setUploading(file.name)
    try {
      const result = await api.uploadDataset(file, locale)
      setUploaded(result)
      setCsvDraft('')
      suggestGoal(result.dataset.name)
      setDatasets((list) =>
        list && !list.some((d) => d.id === result.dataset.id) ? [result.dataset, ...list] : list,
      )
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : t('runs.uploadFailed'))
    } finally {
      setUploading(null)
    }
  }

  useEffect(() => {
    let cancelled = false
    api
      .pipelines()
      .then((result) => !cancelled && setPipelines(result))
      .catch(() => {
        /* an older server without the endpoint: no picker */
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!openRunId) return
    let cancelled = false
    setBusy(true)
    api
      .getRun(openRunId)
      .then((detail) => {
        if (cancelled) return
        setRun(detail)
        setStoppedByError(false)
      })
      .catch((error) => {
        if (cancelled) return
        setErrorMessage(error instanceof ApiError ? error.message : t('runs.actionFailed'))
      })
      .finally(() => {
        if (!cancelled) setBusy(false)
      })
    return () => {
      cancelled = true
    }
    // `t` changes only with the locale; the run to open is the key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openRunId, openNonce])

  // Bounded client-driven stepping: one task per tick while the run is
  // active and auto-run is on. Pausing simply stops advancing — the run
  // state is durable on the server either way.
  useEffect(() => {
    if (!run || run.paused || stoppedByError || !ACTIVE_STATES.includes(run.state)) return
    const timer = setTimeout(async () => {
      if (advancing.current) return
      advancing.current = true
      try {
        setRun(await api.advanceRun(run.id))
        setErrorMessage(null)
        setThrottled(false)
      } catch (error) {
        if (error instanceof ApiError && error.status === 429) {
          // Throttled: keep the run active and let the next tick retry
          // instead of abandoning a half-finished pipeline.
          setErrorMessage(t('runs.slowing'))
          setThrottled(true)
        } else {
          setErrorMessage(error instanceof ApiError ? error.message : t('runs.advanceFailed'))
          setStoppedByError(true)
        }
      } finally {
        advancing.current = false
      }
    }, throttled ? 1500 : 350)
    return () => clearTimeout(timer)
  }, [run, stoppedByError, throttled, t])

  async function createRun(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setErrorMessage(null)
    try {
      const datasetId =
        source === 'stored' ? storedId || undefined : source === 'upload' ? uploaded?.dataset.id : undefined
      const pasted = source === 'upload' && !uploaded && csvDraft.trim()
      const detail = await api.createRun(
        goal.trim(),
        pasted ? csvDraft : undefined,
        pasted ? t('runs.pastedName') : undefined,
        profile || undefined,
        // The report is written in the reader's language, and stays in it:
        // switching the interface later does not rewrite an approved artifact.
        locale,
        datasetId,
      )
      setRun(detail)
      setStoppedByError(false)
      void refreshList()
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : t('runs.startFailed'))
    } finally {
      setBusy(false)
    }
  }

  async function act(action: () => Promise<RunDetail>) {
    setBusy(true)
    setErrorMessage(null)
    try {
      setRun(await action())
      void refreshList()
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : t('runs.actionFailed'))
    } finally {
      setBusy(false)
    }
  }

  function moveTabFocus(event: React.KeyboardEvent, types: string[]) {
    const target = nextTabIndex(event.key, types.indexOf(openReport), types.length, isRtl)
    if (target === null) return
    event.preventDefault()
    const type = types[target]
    setOpenReport(type)
    document.getElementById(`reporttab-${type}`)?.focus()
  }

  const pendingApproval = run?.approvals.find((a) => a.state === 'pending')

  /** One line per stored dataset: what it is called, how big, what it was. */
  function datasetLine(d: DatasetSummary) {
    const parts = [d.name]
    if (d.row_count != null) parts.push(plural('runs.rows', d.row_count))
    if (d.source_format) parts.push(formatLabel(t, d.source_format))
    parts.push(formatDate(d.created_at))
    return parts.join(' · ')
  }

  // Until the list arrives, a preset from the Datasets view is the one
  // choice, so the picker never flashes empty.
  const storedChoices = datasets
    ? datasets.map((d) => ({ id: d.id, label: datasetLine(d) }))
    : preset?.kind === 'stored'
      ? [{ id: preset.id, label: preset.name }]
      : []

  if (!run) {
    return (
      <section className="panel" aria-label={t('runs.aria')}>
        <div className="panel__inner">
          <div className="panel__header">
            <div>
              <h2 className="panel__title">{t('runs.title')}</h2>
              <p className="panel__desc">{t('runs.desc')}</p>
            </div>
          </div>

          <div className="card">
            <form onSubmit={createRun}>
              <div className="field">
                <label className="field__label" htmlFor="run-goal">
                  {t('runs.goal')}
                </label>
                <input
                  id="run-goal"
                  className="field__input"
                  dir="auto"
                  value={goal}
                  maxLength={500}
                  onChange={(event) => setGoal(event.target.value)}
                  disabled={busy}
                />
              </div>
              <div className="field">
                <span className="field__label" id="dataset-label">
                  {t('runs.dataset')}
                </span>
                <div className="segmented" role="group" aria-labelledby="dataset-label">
                  {(['sample', 'stored', 'upload'] as const).map((option) => (
                    <button
                      key={option}
                      type="button"
                      className="segmented__option"
                      aria-pressed={source === option}
                      onClick={() => {
                        setSource(option)
                        if (option === 'sample') suggestGoal(null)
                        if (option === 'stored') {
                          const chosen = datasets?.find((d) => d.id === storedId)
                          if (chosen) suggestGoal(chosen.name)
                        }
                      }}
                    >
                      {t(SOURCE_LABELS[option])}
                    </button>
                  ))}
                </div>
              </div>
              {source === 'stored' ? (
                <div className="field">
                  <label className="field__label" htmlFor="run-stored">
                    {t('runs.storedLabel')}
                  </label>
                  {datasets && datasets.length === 0 && !storedId ? (
                    <p className="field__help">{t('runs.storedNone')}</p>
                  ) : (
                    <>
                      <select
                        id="run-stored"
                        className="field__select"
                        value={storedId}
                        disabled={busy}
                        onChange={(event) => {
                          setStoredId(event.target.value)
                          const chosen = datasets?.find((d) => d.id === event.target.value)
                          suggestGoal(chosen ? chosen.name : null)
                        }}
                      >
                        {storedId ? null : <option value="">{t('runs.storedPick')}</option>}
                        {storedChoices.map((choice) => (
                          <option key={choice.id} value={choice.id}>
                            {choice.label}
                          </option>
                        ))}
                      </select>
                      <span className="field__help">{t('runs.storedHelp')}</span>
                    </>
                  )}
                </div>
              ) : null}
              {source === 'upload' ? (
                <>
                  <div className="field">
                    <label className="field__label" htmlFor="run-file">
                      {t('runs.chooseFile')}
                    </label>
                    <span className="field__help">{t('runs.fileHelp')}</span>
                    <input
                      id="run-file"
                      className="field__input"
                      type="file"
                      accept=".csv,.tsv,.txt,.xlsx,.json,.jsonl,.ndjson"
                      disabled={busy || uploading !== null}
                      onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (file) void uploadFile(file)
                      }}
                    />
                    <p className="privacy-note" role="status" aria-live="polite">
                      {uploading ? (
                        <>
                          <span className="spinner" aria-hidden="true" />
                          {t('runs.uploading', { name: uploading })}
                        </>
                      ) : uploaded ? (
                        <>
                          <Icon name="check" size={14} />
                          <span dir="auto">{uploaded.dataset.name}</span> ·{' '}
                          {plural('runs.rows', uploaded.dataset.row_count ?? uploaded.preview.length)} ·{' '}
                          {formatLabel(t, uploaded.dataset.source_format)}
                          {uploaded.created ? null : <> · {t('runs.alreadyStored')}</>}
                        </>
                      ) : null}
                    </p>
                    {uploaded && uploaded.warnings.length > 0 ? (
                      <ul className="warnings">
                        {uploaded.warnings.map((warning) => (
                          <li key={warning} dir="auto">
                            {warning}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  <div className="field">
                    <label className="field__label" htmlFor="run-csv">
                      {t('runs.paste')}
                    </label>
                    {/* CSV is a left-to-right format whatever the interface language. */}
                    <textarea
                      id="run-csv"
                      className="field__input runform__textarea"
                      dir="ltr"
                      rows={6}
                      value={csvDraft}
                      onChange={(event) => {
                        setCsvDraft(event.target.value)
                        // Pasted text replaces a file chosen before it.
                        setUploaded(null)
                      }}
                      placeholder={'team,quarter,sales\nA,Q1,100\nB,Q1,90'}
                      disabled={busy}
                    />
                  </div>
                </>
              ) : null}
              {pipelines && Object.keys(pipelines.profiles).length > 0 ? (
                <div className="field">
                  <label className="field__label" htmlFor="run-profile">
                    {t('runs.profile')}
                  </label>
                  <span className="field__help">
                    {t('runs.profileHelp')}{' '}
                    {stageTitles(pipelines, profile).length > 0
                      ? t('runs.profileStages', { list: stageTitles(pipelines, profile).join(', ') })
                      : t('runs.profileNone')}
                  </span>
                  <select
                    id="run-profile"
                    className="field__select"
                    value={profile}
                    onChange={(event) => setProfile(event.target.value)}
                    disabled={busy}
                  >
                    <option value="">{t('runs.profileDefault')}</option>
                    {Object.keys(pipelines.profiles)
                      .filter((name) => name !== 'default')
                      .map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                  </select>
                </div>
              ) : null}
              <div className="field">
                <button type="submit" className="btn btn--primary" disabled={busy || !goal.trim()}>
                  {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="sparkle" size={16} />}
                  {t('runs.start')}
                </button>
              </div>
            </form>
            <p
              className={`statusline ${errorMessage ? 'statusline--error' : ''}`}
              role="status"
              aria-live="polite"
              dir="auto"
            >
              {errorMessage ?? ''}
            </p>
          </div>

          {runs.length > 0 ? (
            <div className="card">
              <h3 className="card__title">{t('runs.previous')}</h3>
              <ul className="controls__list">
                {runs.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className="controlrow"
                      onClick={() => void act(() => api.getRun(item.id))}
                    >
                      <Icon name="clock" size={17} />
                      <span>
                        <span className="controlrow__label" dir="auto">
                          {item.goal}
                        </span>
                        <span className="controlrow__help">
                          <span dir="auto">{item.dataset_name}</span> · {stateLabel(t, item.state)}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </section>
    )
  }

  const reportLang = run.report_language === 'ar' ? 'ar' : 'en'
  const reportDir = reportLang === 'ar' ? 'rtl' : 'ltr'

  return (
    <section className="panel" aria-label={t('runs.detailAria')}>
      <div className="panel__inner panel__inner--split">
        <div className="panel__column">
          <div className="panel__header">
            <div>
              <h2 className="panel__title" dir="auto">
                {run.goal}
              </h2>
              <p className="panel__desc">
                <span dir="auto">{run.dataset_name}</span> · {t('runs.state')}{' '}
                <strong>{stateLabel(t, run.state)}</strong>
                {run.error ? (
                  <>
                    {' — '}
                    <span dir="auto">{run.error}</span>
                  </>
                ) : null}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              {ACTIVE_STATES.includes(run.state) ? (
                <>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={busy}
                    onClick={() => {
                      setStoppedByError(false)
                      void act(() => (run.paused ? api.resumeRun(run.id) : api.pauseRun(run.id)))
                    }}
                  >
                    {run.paused ? t('runs.resume') : t('runs.pause')}
                  </button>
                  <button
                    type="button"
                    className="btn btn--subtle"
                    onClick={() => void act(() => api.cancelRun(run.id))}
                    disabled={busy}
                  >
                    {t('runs.cancel')}
                  </button>
                </>
              ) : null}
              <button type="button" className="btn btn--ghost" onClick={() => setRun(null)}>
                {t('runs.all')}
              </button>
            </div>
          </div>

          {pendingApproval ? (
            <div className="card approvalcard" role="region" aria-label={t('runs.approval')}>
              <h3 className="card__title">
                <Icon name="alert" size={16} /> {t('runs.approval')}
              </h3>
              <dl>
                <div className="rail__row">
                  <dt>{t('runs.action')}</dt>
                  <dd dir="auto" style={{ maxWidth: '70%', whiteSpace: 'normal', textAlign: 'end' }}>
                    {pendingApproval.action}
                  </dd>
                </div>
                <div className="rail__row">
                  <dt>{t('runs.target')}</dt>
                  <dd dir="ltr" style={{ maxWidth: '70%', whiteSpace: 'normal', textAlign: 'end' }}>
                    {pendingApproval.target}
                  </dd>
                </div>
                <div className="rail__row">
                  <dt>{t('runs.risk')}</dt>
                  <dd dir="auto">
                    {pendingApproval.risk === 'high' ? t('runs.riskHigh') : pendingApproval.risk}
                  </dd>
                </div>
                <div className="rail__row">
                  <dt>{t('runs.impact')}</dt>
                  <dd dir="auto" style={{ maxWidth: '70%', whiteSpace: 'normal', textAlign: 'end' }}>
                    {pendingApproval.impact}
                  </dd>
                </div>
                <div className="rail__row">
                  <dt>{t('runs.reversibility')}</dt>
                  <dd dir="auto" style={{ maxWidth: '70%', whiteSpace: 'normal', textAlign: 'end' }}>
                    {pendingApproval.reversibility}
                  </dd>
                </div>
              </dl>
              <div className="dialog__actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  disabled={busy}
                  onClick={() => void act(() => api.decideApproval(run.id, pendingApproval.id, 'reject'))}
                >
                  {t('runs.reject')}
                </button>
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={busy}
                  onClick={() => void act(() => api.decideApproval(run.id, pendingApproval.id, 'approve'))}
                >
                  {t('runs.approve')}
                </button>
              </div>
            </div>
          ) : null}

          {run.charts.length > 0 ? (
            <div className="card">
              <h3 className="card__title">{t('runs.charts')}</h3>
              {/* A chart's axis runs left to right in either language;
                  the labels come from the data and are shown as written. */}
              {run.charts.map((chart) => (
                <figure key={chart.id} className="runchart" dir="ltr">
                  <figcaption className="field__label" dir="auto">
                    {chart.title}
                  </figcaption>
                  {chart.type === 'bar' ? <BarChart chart={chart} /> : <LineChart chart={chart} />}
                  {/* The same numbers as a table: nobody has to read a
                      value off a bar, and a screen reader gets every one. */}
                  <details className="runchart__data" dir={isRtl ? 'rtl' : 'ltr'}>
                    <summary>{t('runs.chartData')}</summary>
                    <table className="datatable">
                      <thead>
                        <tr>
                          <th scope="col">{t('runs.chartLabel')}</th>
                          <th scope="col">{t('runs.chartValue')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {chart.labels.map((label, index) => (
                          <tr key={label}>
                            <th scope="row" dir="auto">
                              {label}
                              {chart.forecast_from !== undefined && index >= chart.forecast_from
                                ? ` (${t('runs.forecast')})`
                                : ''}
                            </th>
                            <td>{formatNumber(chart.values[index])}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </details>
                </figure>
              ))}
            </div>
          ) : null}

          {run.reports.length ? (
            <div className="card">
              <h3 className="card__title">{t('runs.reports')}</h3>
              <div
                className="reporttabs"
                role="tablist"
                aria-label={t('runs.reportSection')}
                onKeyDown={(event) => moveTabFocus(event, run.reports.map((s) => s.type))}
              >
                {run.reports.map((section) => (
                  <button
                    key={section.type}
                    type="button"
                    role="tab"
                    id={`reporttab-${section.type}`}
                    aria-selected={openReport === section.type}
                    aria-controls={`reportpanel-${section.type}`}
                    // Roving tabindex: one stop for the whole tablist, then
                    // the arrow keys move within it (WAI-ARIA tabs pattern).
                    tabIndex={openReport === section.type ? 0 : -1}
                    className={`reporttab ${openReport === section.type ? 'reporttab--on' : ''}`}
                    onClick={() => setOpenReport(section.type)}
                  >
                    <span className="reporttab__name">{typeLabel(t, section.type, section.title)}</span>
                    <span className="reporttab__q">
                      {questionLabel(t, section.type, section.question)}
                    </span>
                  </button>
                ))}
              </div>
              {run.reports
                .filter((section) => section.type === openReport)
                .map((section) => (
                  <div
                    key={section.type}
                    role="tabpanel"
                    id={`reportpanel-${section.type}`}
                    aria-labelledby={`reporttab-${section.type}`}
                  >
                    {section.headline ? (
                      <p className="reporthead" dir="auto">
                        {section.headline}
                      </p>
                    ) : null}
                    {/* The <pre> is what scrolls, so the tab stop belongs
                        here rather than on the panel around it. The block
                        carries the report's own language, which is the
                        run's, not the interface's (ADR 0022), so a screen
                        reader and the bidi algorithm read it correctly. */}
                    <pre
                      className="runreport"
                      tabIndex={0}
                      role="region"
                      lang={reportLang}
                      dir={reportDir}
                      aria-label={t('runs.reportText', { type: typeLabel(t, section.type, section.title) })}
                    >
                      {section.content}
                    </pre>
                  </div>
                ))}
            </div>
          ) : null}

          {run.report ? (
            <div className="card">
              <h3 className="card__title">
                {t('runs.comprehensive', { version: run.report.version })}
                {run.report.published_path ? t('runs.published') : ''}
              </h3>
              {run.report.published_path ? (
                <p className="privacy-note">
                  <Icon name="check" size={14} /> <span dir="ltr">{run.report.published_path}</span>
                </p>
              ) : null}
              <pre
                className="runreport runreport--full"
                tabIndex={0}
                role="region"
                lang={reportLang}
                dir={reportDir}
                aria-label={t('runs.comprehensiveText')}
              >
                {run.report.content}
              </pre>
            </div>
          ) : null}

          <p
            className={`statusline ${errorMessage ? 'statusline--error' : ''}`}
            role="status"
            aria-live="polite"
            dir="auto"
          >
            {errorMessage ?? ''}
          </p>
        </div>

        <div className="panel__column panel__column--side">
          <div className="card">
            <h3 className="card__title">{t('runs.pipeline')}</h3>
            <p className="controlrow__help">
              {tx('runs.pipelineDesc', { hermes: <strong>Hermes</strong> })}
            </p>
            <ul className="runtasks" aria-live="polite">
              {run.tasks.map((task) => (
                <li key={task.id} className={`runtask runtask--${task.state}`}>
                  <span className="runtask__mark" aria-hidden="true">
                    {TASK_ICON[task.state] ?? '·'}
                  </span>
                  <span>
                    <span className="controlrow__label" dir="auto">
                      {task.title}
                    </span>
                    {task.summary ? (
                      <span className="controlrow__help" dir="auto">
                        {task.summary}
                      </span>
                    ) : (
                      <span className="controlrow__help">{stateLabel(t, task.state)}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
