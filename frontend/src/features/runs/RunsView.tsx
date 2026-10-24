import '../../shared/styles/analytics.css'
import './report-theme.css'
import './report-document.css'
import { ReportDocument } from './ReportDocument'
import { lazy, Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useReadOnly } from '../../shared/readOnly'
import { useSessionDraft } from '../../shared/useSessionDraft'
import { formatNumberIn, translate } from '../../i18n'
import type { Locale } from '../../i18n'
import { api, ApiError, MAX_UPLOAD_BYTES, UPLOAD_ACCEPT } from '../../shared/api'
import { usePack } from '../../i18n/pack'
import { intakeMessages } from '../datasets/intakeMessages'
import { decisionMessages } from './messages'
import { WorkbookSheetPicker } from '../datasets/WorkbookSheetPicker'
import { MappingPanel } from '../datasets/MappingPanel'
import { barGeometry, valueScale } from '../../shared/charts'
import { Icon } from '../../shared/components/Icon'
import { languageLabel, formatLabel, questionLabel, stateLabel, typeLabel } from '../../shared/labels'
import type {
  ChartSpec,
  DatasetSummary,
  JoinSpec,
  Pipelines,
  RunAssumptions,
  RunDetail,
  RunSummary,
  RunTask,
  UploadResult,
} from '../../shared/types'

import { ApprovalCard } from './ApprovalCard'
import { DecisionInputs } from './DecisionInputs'
import { DecisionRecordCard } from './DecisionRecordCard'
import { CreationAttempt } from './creationAttempt'
import { EvidencePanel } from './EvidencePanel'
import { JoinBuilder } from './JoinBuilder'
import { ModelCards } from './ModelCards'
import { PlanPreview, RunTimeline } from './RunTimeline'
import { runStore, useRun } from './runStore'
import { UploadPreview } from '../datasets/UploadPreview'
import { workflowMessages } from './workflowMessages'

const AgentCollaboration = lazy(() => import('./AgentCollaboration'))

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

function LineChart({ chart, language }: { chart: ChartSpec; language: Locale }) {
  const scale = valueScale(chart.values, 6, 48)
  const compact = (value: number) => formatNumberIn(language, value, { notation: 'compact' })
  const xy = chart.values.map((value, index) => ({
    x: (index / Math.max(chart.values.length - 1, 1)) * 90 + 8,
    y: scale.y(value),
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
            {translate('runs.forecast', undefined, language)}
          </text>
        </>
      ) : null}
      <line x1="8" y1={scale.zero} x2="100" y2={scale.zero} stroke="var(--border-strong)" strokeWidth="0.5" />
      <text x="7" y={scale.y(scale.max) + 1} fontSize="3" textAnchor="end" fill="var(--text-faint)">
        {compact(scale.max)}
      </text>
      {scale.min !== scale.max ? (
        <text x="7" y={scale.y(scale.min) + 1} fontSize="3" textAnchor="end" fill="var(--text-faint)">
          {compact(scale.min)}
        </text>
      ) : null}
      <text x="8" y="56" fontSize="3.4" fill="var(--text-faint)">
        {chart.labels[0]}
      </text>
      <text x="98" y="56" fontSize="3.4" textAnchor="end" fill="var(--text-faint)">
        {chart.labels[chart.labels.length - 1]}
      </text>
    </svg>
  )
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
export type RunPreset = ({ kind: 'upload' } | { kind: 'stored'; id: string; name: string }) & { profile?: 'maintenance' | 'models' }

interface RunsViewProps {
  draftScope?: string
  /** A run to open on arrival — the one the assistant just started. */
  openRunId?: string | null
  openNonce?: number
  preset?: RunPreset | null
  onRunSelected?: (id: string | null) => void
  /** Open this run's dashboard (ADR 0032). */
  onOpenDashboard?: (id: string) => void
}

/** The custom stages a profile includes, by title, for the picker's help. */
// A profile's key is an identifier, not a label. Every shipped one gets a
// translated name; an operator's own profile falls back to its key, which
// is better than hiding it.
const PROFILE_LABELS: Record<string, 'runs.profileModels' | 'runs.profileMaintenance' | 'runs.profileSpecialists'> = {
  models: 'runs.profileModels',
  maintenance: 'runs.profileMaintenance',
  specialist_evidence: 'runs.profileSpecialists',
}

function stageTitles(pipelines: Pipelines, profile: string, locale: string): string[] {
  const roles = profile ? (pipelines.profiles[profile] ?? []) : pipelines.default
  return roles.map((role) => {
    const stage = pipelines.stages.find((s) => s.role === role)
    return stage ? ((locale === 'ar' && stage.title_ar) || stage.title).split(' — ')[0] : role
  })
}

export function RunsView({ openRunId = null, openNonce = 0, preset = null, onRunSelected, onOpenDashboard, draftScope = 'session' }: RunsViewProps) {
  const readOnly = useReadOnly()
  const { t, plural, isRtl, locale, formatNumber, formatDate, formatTime } = usePack(intakeMessages)
  const { t: tDecision } = usePack(decisionMessages)
  const { t: tWorkflow } = usePack(workflowMessages)
  const visible = useRef(true)
  useLayoutEffect(() => { visible.current = true; return () => { visible.current = false } }, [])
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [runsState, setRunsState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [datasetsState, setDatasetsState] = useState<'loading' | 'ready' | 'error'>('loading')
  const runsRequest = useRef(0)
  const listingDatasets = useRef(false)
  const [selectedId, setSelectedId] = useState<string | null>(openRunId)
  const snapshot = useRun(selectedId, true)
  const run = snapshot.detail
  const setRun = useCallback((detail: RunDetail | null) => {
    if (!visible.current) return
    if (detail) runStore.receive(detail)
    setSelectedId(detail?.id ?? null)
    onRunSelected?.(detail?.id ?? null)
  }, [onRunSelected])
  const [evidenceTask, setEvidenceTask] = useState<RunTask | null>(null)
  const fullReportRef = useRef<HTMLDivElement | null>(null)
  const closeEvidence = useCallback(() => setEvidenceTask(null), [])
  const starting = useRef(false)
  const creationAttempt = useRef<CreationAttempt | null>(null)
  if (!creationAttempt.current) creationAttempt.current = new CreationAttempt()
  // Where the data comes from (ADR 0024). A stored dataset and an
  // uploaded file are both analysed by reference: the run sends an id.
  const [source, setSource] = useState<'sample' | 'stored' | 'upload'>(() =>
    preset?.kind === 'stored' ? 'stored' : preset?.kind === 'upload' ? 'upload' : 'sample',
  )
  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null)
  const [storedId, setStoredId] = useState(() => (preset?.kind === 'stored' ? preset.id : ''))
  const suggestedGoal = preset?.kind === 'stored' ? t('runs.goalStored', { name: preset.name }) : preset?.kind === 'upload' ? t('intake.goal') : t('runs.goalDefault')
  const questionContext = preset?.kind === 'stored' ? preset.id : preset?.kind ?? 'sample'
  const [goal, setGoal] = useSessionDraft(`${draftScope}:analysis-question:${questionContext}`, () => suggestedGoal)
  const [chosenLanguage, setChosenLanguage] = useState<'en' | 'ar' | null>(null)
  const reportLanguage = chosenLanguage ?? locale
  // The goal the form last wrote itself. A goal the person typed is
  // never replaced when they pick another dataset.
  const autoGoal = useRef(suggestedGoal)
  const [uploaded, setUploaded] = useState<UploadResult | null>(null)
  const [uploading, setUploading] = useState<string | null>(null)
  const sourceFile = useRef<File | null>(null)
  const [mappingId, setMappingId] = useState<string | null>(null)
  const [csvDraft, setCsvDraft] = useState('')
  // Stepping stops for two different reasons: the user paused the run
  // (durable, server-side, also obeyed by a background worker) or a
  // request failed (local to this tab, cleared on the next action).
  // Which analytics type's report is on screen. Descriptive is the floor
  // of the maturity ladder, so it opens first.
  const [preferredReport, setOpenReport] = useState('descriptive')
  const openReport = run?.reports.some((section) => section.type === preferredReport)
    ? preferredReport : run?.reports[0]?.type ?? ''
  const [localBusy, setBusy] = useState(false)
  const busy = localBusy || snapshot.pending
  const [localError, setErrorMessage] = useState<string | null>(null)
  const errorMessage = localError ?? snapshot.error?.message ?? null
  // Custom stages and profiles (ADR 0020). The picker exists only when
  // an operator configured profiles; a default install shows nothing.
  const [pipelines, setPipelines] = useState<Pipelines | null>(null)
  const [profile, setProfile] = useState<string>(preset?.profile ?? '')
  // Other stored datasets joined onto the main one (ADR 0030).
  const [downloading, setDownloading] = useState(false)
  const [joins, setJoins] = useState<JoinSpec[]>([])
  const [breakdown, setBreakdown] = useState('')
  // The decision inputs the run states (slice three, A2): undefined when
  // nothing is stated, null while the form cannot be read as numbers.
  const [assumptions, setAssumptions] = useState<RunAssumptions | null | undefined>(undefined)
  const changeJoins = useCallback((next: JoinSpec[], nextBreakdown: string) => {
    setJoins(next)
    setBreakdown(nextBreakdown)
  }, [])

  const refreshList = useCallback(async () => {
    // A mutation may request a newer list while the initial GET is pending.
    // Only the latest request may replace the history or its freshness state.
    const request = ++runsRequest.current
    setRunsState('loading')
    try {
      const result = await api.listRuns()
      if (!visible.current || request !== runsRequest.current) return
      setRuns(result.runs)
      setRunsState('ready')
    } catch {
      // A failed read is not an empty history. Keep any last known rows.
      if (visible.current && request === runsRequest.current) setRunsState('error')
    }
  }, [])

  const refreshDatasets = useCallback(async () => {
    if (listingDatasets.current) return
    listingDatasets.current = true
    setDatasetsState('loading')
    try {
      const result = await api.listDatasets()
      if (!visible.current) return
      setDatasets(result.datasets)
      setDatasetsState('ready')
    } catch {
      // Retain the selected dataset and the person's question for retry.
      if (visible.current) setDatasetsState('error')
    } finally { listingDatasets.current = false }
  }, [])

  useEffect(() => { void refreshList() }, [refreshList])
  useEffect(() => { void refreshDatasets() }, [refreshDatasets])

  function suggestGoal(name: string | null) {
    if (goal !== autoGoal.current) return
    const next = name ? t('runs.goalStored', { name }) : t('runs.goalDefault')
    autoGoal.current = next
    setGoal(next)
  }

  async function uploadFile(file: File, sheet?: string) {
    setErrorMessage(null)
    setUploaded(null)
    setCsvDraft('')
    setMappingId(null)
    sourceFile.current = file
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
      const result = await api.uploadDataset(file, locale, sheet)
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
    if (openRunId) {
      setSelectedId(openRunId)
      setErrorMessage(null)
    }
  }, [openRunId, openNonce])

  useEffect(() => { setOpenReport('descriptive'); setEvidenceTask(null) }, [selectedId])

  async function createRun(event: React.FormEvent) {
    event.preventDefault()
    await startRun()
  }

  async function startRun() {
    if (starting.current) return
    if (uploading) { setErrorMessage(t('intake.wait')); return }
    if ((source === 'stored' && !storedId) || (source === 'upload' && !uploaded && !csvDraft.trim())) {
      setErrorMessage(t('intake.required'))
      return
    }
    if (!goal.trim()) return
    if (assumptions === null) { setErrorMessage(tDecision('decision.invalid')); return }
    starting.current = true
    setBusy(true)
    setErrorMessage(null)
    try {
      const datasetId = primaryId ?? undefined
      const pasted = source === 'upload' && !uploaded && csvDraft.trim()
      const idempotencyKey = await creationAttempt.current!.forRequest(draftScope, JSON.stringify([
        goal.trim(), pasted ? csvDraft : null, pasted ? t('runs.pastedName') : null,
        profile || null, reportLanguage, datasetId ?? null,
        datasetId && joins.length ? { joins, breakdown } : null, assumptions ?? null,
      ]))
      if (!visible.current) return
      const detail = await api.createRun(
        goal.trim(),
        pasted ? csvDraft : undefined,
        pasted ? t('runs.pastedName') : undefined,
        profile || undefined,
        // The report is written in the chosen language, and stays in it:
        // switching the interface later does not rewrite an approved artifact.
        reportLanguage,
        datasetId,
        datasetId && joins.length ? { joins, breakdown } : undefined,
        assumptions ?? undefined,
        idempotencyKey,
      )
      creationAttempt.current!.complete(draftScope)
      setRun(detail)
      void refreshList()
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : t('runs.startFailed'))
    } finally {
      starting.current = false
      setBusy(false)
    }
  }

  // The dataset a run starts from, when it is a stored one: joins need it.
  const primaryId =
    source === 'stored' ? storedId || null : source === 'upload' ? uploaded?.dataset.id ?? null : null

  /** Save the run's cleaned (and merged) table as CSV (ADR 0031). */
  async function downloadTable(id: string) {
    setDownloading(true)
    setErrorMessage(null)
    try {
      const { blob, name } = await api.downloadTable(id, locale)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = name
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : t('runs.downloadFailed'))
    } finally {
      setDownloading(false)
    }
  }

  async function act(action: () => Promise<RunDetail>) {
    setBusy(true)
    setErrorMessage(null)
    try {
      const detail = selectedId ? await runStore.mutate(selectedId, action) : await action()
      if (detail) setRun(detail)
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


  /** One line per stored dataset: what it is called, how big, what it was. */
  function datasetLine(d: DatasetSummary) {
    const parts = [d.name]
    if (d.row_count != null) parts.push(plural('runs.rows', d.row_count))
    if (d.source_format) parts.push(formatLabel(t, d.source_format))
    // A mapped dataset runs by its saved mapping (ADR 0025), so say so.
    if (d.mapped) parts.push(t('mapping.mapped'))
    parts.push(formatDate(d.created_at))
    return parts.join(' · ')
  }

  // Until the list arrives, a preset from the Datasets view is the one
  // choice, so the picker never flashes empty.
  const storedChoices = datasets
    ? [
        ...(preset?.kind === 'stored' && storedId === preset.id && !datasets.some((d) => d.id === preset.id)
          ? [{ id: preset.id, label: preset.name }] : []),
        ...datasets.map((d) => ({ id: d.id, label: datasetLine(d) })),
      ]
    : preset?.kind === 'stored'
      ? [{ id: preset.id, label: preset.name }]
      : []

  if (selectedId && !run) {
    return <section className="panel" aria-label={t('runs.detailAria')}><div className="panel__inner">
      {errorMessage ? <p role="alert" className="statusline statusline--error" dir="auto">{errorMessage}</p> : <div role="status" aria-label={t('cockpit.loading')} className="card"><span className="visually-hidden">{t('cockpit.loading')}</span><div className="skeleton skeleton--title" /><div className="skeleton skeleton--line" /></div>}
      <div className="dialog__actions"><button type="button" className="btn btn--ghost" onClick={() => void runStore.retry(selectedId)}>{t('common.tryAgain')}</button><button type="button" className="btn btn--ghost" onClick={() => setRun(null)}>{t('runs.all')}</button></div>
    </div></section>
  }

  if (!run) {
    return (
      <section className="panel" aria-label={t('runs.aria')}>
        <div className="panel__inner">
          <div className="panel__header">
            <div>
              <h2 className="panel__title">{t('runs.title')}</h2>
            </div>
          </div>

          {readOnly ? <p className="panel__note" role="note">{t('demo.note')}</p> : <div className="card">
            <form onSubmit={createRun}>
              <ol className="run-steps">
                {(['intake.step1', 'intake.step2', 'intake.step3', 'intake.step4'] as const).map((key) => <li key={key}>{t(key)}</li>)}
              </ol>
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
                <label className="field__label" htmlFor="run-language">{t('intake.reportLanguage')}</label>
                <select id="run-language" className="field__select" value={reportLanguage}
                  aria-describedby="run-language-help" disabled={busy}
                  onChange={(event) => setChosenLanguage(event.target.value === 'ar' ? 'ar' : 'en')}>
                  <option value="ar" lang="ar">العربية</option>
                  <option value="en" lang="en">English</option>
                </select>
                <p className="field__help" id="run-language-help">{t('intake.reportLanguageHelp')}</p>
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
                      disabled={busy || uploading !== null}
                      onClick={() => {
                        setSource(option)
                        setMappingId(null)
                        setErrorMessage(null)
                        if (option === 'sample') suggestGoal(null)
                        if (option === 'upload' && goal === autoGoal.current) {
                          const next = uploaded ? t('runs.goalStored', { name: uploaded.dataset.name }) : t('intake.goal')
                          autoGoal.current = next
                          setGoal(next)
                        }
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
                  {datasetsState === 'loading' ? <p role="status">{tWorkflow('workflow.datasetsLoading')}</p> : null}
                  {datasetsState === 'error' ? <div>
                    <p role="alert" className="statusline statusline--error">{tWorkflow('workflow.datasetsFailed')}</p>
                    <button type="button" className="btn btn--ghost" onClick={() => void refreshDatasets()}>{tWorkflow('workflow.retryDatasets')}</button>
                  </div> : null}
                  {datasetsState === 'ready' && datasets && datasets.length === 0 && !storedId ? (
                    <p className="field__help">{t('runs.storedNone')}</p>
                  ) : (
                    <>
                      <select
                        id="run-stored"
                        className="field__select"
                        value={storedId}
                        disabled={busy}
                        onChange={(event) => {
                          setMappingId(null)
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
                      accept={UPLOAD_ACCEPT}
                      disabled={busy || uploading !== null}
                      onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (file) void uploadFile(file)
                        event.target.value = ''
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
                  {uploaded && sourceFile.current && <WorkbookSheetPicker result={uploaded} onSelect={(sheet) => { if (sourceFile.current) void uploadFile(sourceFile.current, sheet) }} />}
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
                        setMappingId(null)
                      }}
                      placeholder={'team,quarter,sales\nA,Q1,100\nB,Q1,90'}
                      disabled={busy || uploading !== null}
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
                    {t(pipelines.explicit_plans?.[profile] ? 'runs.profileExplicitHelp' : 'runs.profileHelp')}{' '}
                    {!pipelines.explicit_plans?.[profile] && (stageTitles(pipelines, profile, locale).length > 0
                      ? t('runs.profileStages', { list: stageTitles(pipelines, profile, locale).join(', ') })
                      : t('runs.profileNone'))}
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
                          {PROFILE_LABELS[name] ? t(PROFILE_LABELS[name]) : name}
                        </option>
                      ))}
                  </select>
                </div>
              ) : null}
              {uploaded ? <UploadPreview result={uploaded} /> : null}
              {primaryId && !mappingId && <div className="field"><button className="btn btn--ghost" type="button" disabled={busy || uploading !== null} onClick={() => setMappingId(primaryId)}>{t('intake.columns')}</button></div>}
              {mappingId && <MappingPanel key={mappingId} datasetId={mappingId} focusOnOpen onClose={() => setMappingId(null)} onChanged={(dataset) => {
                setDatasets((list) => list?.map((item) => item.id === dataset.id ? dataset : item) ?? null)
                setUploaded((previous) => previous?.dataset.id === dataset.id ? { ...previous, dataset } : previous)
              }} onAnalyse={() => { setMappingId(null); void startRun() }} />}
              {source !== 'sample' ? (
                <JoinBuilder
                  primaryId={primaryId}
                  datasets={datasets}
                  disabled={busy}
                  joins={joins}
                  breakdown={breakdown}
                  onChange={changeJoins}
                />
              ) : null}
              <DecisionInputs disabled={busy} onChange={setAssumptions} />
              <PlanPreview pipelines={pipelines} profile={profile} joined={joins.length > 0} />
              <details className="run-more">
                <summary>{t('intake.more')}</summary>
                <p className="panel__note">{t('intake.models')}</p>
                <p className="panel__note">{t('intake.limits')}</p>
              </details>
              <div className="field">
                <button type="submit" className="btn btn--primary" disabled={busy || uploading !== null || !goal.trim() || (source === 'stored' && !storedId) || (source === 'upload' && !uploaded && !csvDraft.trim())}>
                  {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="sparkle" size={16} />}
                  {t('runs.start')}
                </button>
              </div>
            </form>
            <p
              className={`statusline ${errorMessage ? 'statusline--error' : ''}`}
              role={errorMessage ? 'alert' : 'status'}
              aria-live="polite"
              dir="auto"
            >
              {errorMessage ?? ''}
            </p>
          </div>}

          {readOnly && errorMessage ? <p role="alert" className="statusline statusline--error" dir="auto">{errorMessage}</p> : null}
          <section className="card" aria-label={t('runs.previous')}>
              <h3 className="card__title">{t('runs.previous')}</h3>
              {runsState === 'loading' ? <p role="status">{tWorkflow('workflow.runsLoading')}</p> : null}
              {runsState === 'error' ? <div>
                <p role="alert" className="statusline statusline--error">{tWorkflow('workflow.runsFailed')}</p>
                <button type="button" className="btn btn--ghost" onClick={() => void refreshList()}>{tWorkflow('workflow.retryRuns')}</button>
              </div> : null}
              {runsState === 'ready' && runs.length === 0 ? <p role="status">{tWorkflow('workflow.runsEmpty')}</p> : null}
              <ul className="controls__list" aria-busy={runsState === 'loading'}>
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
          </section>
        </div>
      </section>
    )
  }

  const reportLang = run.report_language === 'ar' ? 'ar' : 'en'
  const reportDir = reportLang === 'ar' ? 'rtl' : 'ltr'
  // The table the run analyses exists once cleaning, and any merge, is done.
  const tableTask = run.tasks.find((task) => task.role === 'merge') ?? run.tasks.find((task) => task.role === 'cleaner')
  const tableReady = tableTask?.state === 'succeeded'

  return (
    <section className="panel cockpit" aria-label={t('runs.detailAria')}>
      <div className="panel__inner panel__inner--split">
        <div className="panel__column">
          <div className="panel__header cockpit__header">
            <div>
              <p className="eyebrow">{t('cockpit.workspace')}</p>
              <h2 className="panel__title" dir="auto">
                {run.goal}
              </h2>
              {run.reports[0]?.headline ? <p className="cockpit__finding" dir={run.report_language === 'ar' ? 'rtl' : 'ltr'} lang={run.report_language}>{run.reports[0].headline}</p> : null}
              <p className="panel__desc">
                <span dir="auto">{run.dataset_name}</span> · {languageLabel(t, reportLang)} · {t('runs.state')}{' '}
                <strong>{stateLabel(t, run.paused && ACTIVE_STATES.includes(run.state) ? 'paused' : run.state)}</strong>
                {run.error ? (
                  <>
                    {' — '}
                    <span dir="auto">{run.error}</span>
                  </>
                ) : null}
              </p>
              <p className="card__meta"><time dateTime={snapshot.receivedAt ?? run.updated_at}>{t('cockpit.lastObserved', { time: `${formatDate(snapshot.receivedAt ?? run.updated_at)} ${formatTime(snapshot.receivedAt ?? run.updated_at)}` })}</time></p>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
              {run.report?.published_path ? <button type="button" className="btn btn--primary" onClick={() => { fullReportRef.current?.focus(); fullReportRef.current?.scrollIntoView({ block: 'center' }) }}>{t('cockpit.readPublished')}</button> : null}
              {ACTIVE_STATES.includes(run.state) && !readOnly ? (
                <>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    disabled={busy}
                    onClick={() => {
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
              {tableReady && onOpenDashboard ? (
                <button type="button" className="btn btn--ghost" onClick={() => onOpenDashboard(run.id)}>
                  <Icon name="dashboard" size={16} />
                  {t('runs.openDashboard')}
                </button>
              ) : null}
              {tableReady ? (
                <button type="button" className="btn btn--ghost" disabled={downloading} onClick={() => void downloadTable(run.id)}>
                  {downloading ? <span className="spinner" aria-hidden="true" /> : <Icon name="download" size={16} />}
                  {t('runs.download')}
                </button>
              ) : null}
              <button type="button" className="btn btn--ghost" onClick={() => setRun(null)}>
                {t('runs.all')}
              </button>
            </div>
          </div>

          <p className="cockpit__continuity"><Icon name="shield" size={14} />{t('cockpit.keepOpen')}</p>
          {reportLang !== locale ? <p className="report-language-note">{t('intake.reportLanguageFixed', { language: languageLabel(t, reportLang) })}</p> : null}
          <p className="visually-hidden" role="status" aria-live="polite">{(() => {
            const event = [...snapshot.events].reverse().find((item) => item.kind === 'stage.changed')
            const task = run.tasks.find((item) => item.id === event?.subject)
            return task ? `${task.title}: ${stateLabel(t, task.state)}` : stateLabel(t, run.state)
          })()}</p>
          <ApprovalCard detail={run} onDecision={(detail) => { setRun(detail); void refreshList() }} />
          {run.decision ? <DecisionRecordCard decision={run.decision} language={reportLang} /> : null}
          <Suspense fallback={null}><AgentCollaboration key={run.id} run={run} events={snapshot.events}
            interrupted={snapshot.interrupted} pipelines={pipelines} onEvidence={setEvidenceTask} /></Suspense>
          {run.reports.length ? <section className="finding-grid report-theme" aria-label={t('overview.findings')}>
            {run.reports.filter((section) => ['descriptive', 'diagnostic', 'predictive', 'prescriptive'].includes(section.type)).map((section) => {
              const task = run.tasks.find((item) => item.role === section.type)
              return <article className="finding-card" key={section.type}>
                <p className="eyebrow">{typeLabel(t, section.type, section.title)}</p>
                <h3>{questionLabel(t, section.type, section.question)}</h3>
                <p className="finding-card__headline" lang={reportLang} dir={reportDir}>{section.headline}</p>
                {task ? <button type="button" className="evidence-link" aria-label={t('cockpit.whyFor', { type: typeLabel(t, section.type, section.title) })} onClick={(event) => {
                  // Safari does not focus a button on pointer activation.
                  // Give the dialog a reliable invoking control to restore.
                  event.currentTarget.focus({ preventScroll: true })
                  setEvidenceTask(task)
                }}>{t('cockpit.why')}<Icon name="search" size={14} /></button> : null}
              </article>
            })}
          </section> : null}
          {run.tasks.find((task) => task.role === 'validator')?.quality_checks.length ? <div className="assurance-strip"><Icon name="shield" size={16} /><span>{t('cockpit.checks')}: {run.tasks.find((task) => task.role === 'validator')!.quality_checks.every((check) => check.passed) ? t('cockpit.passed') : t('cockpit.notPassed')}</span><span>{run.report?.published_path ? t('cockpit.published') : t('cockpit.unpublished')}</span></div> : null}

          {run.charts.length > 0 ? (
            <div className="card report-theme report-sheet" lang={reportLang}>
              <h3 className="card__title" lang={locale}>{t('runs.charts')}</h3>
              {/* A chart's axis runs left to right in either language;
                  the labels come from the data and are shown as written. */}
              {run.charts.map((chart) => (
                <figure key={chart.id} className="runchart" dir="ltr" lang={reportLang}>
                  <figcaption className="field__label" dir="auto">
                    {chart.title}
                  </figcaption>
                  {chart.type === 'bar' ? <BarChart chart={chart} /> : <LineChart chart={chart} language={reportLang} />}
                  {/* The same numbers as a table: nobody has to read a
                      value off a bar, and a screen reader gets every one. */}
                  <details className="runchart__data" dir={reportDir}>
                    <summary lang={locale} dir={isRtl ? 'rtl' : 'ltr'}>{t('runs.chartData')}</summary>
                    <table className="datatable">
                      <thead>
                        <tr>
                          <th scope="col">{translate('runs.chartLabel', undefined, reportLang)}</th>
                          <th scope="col">{translate('runs.chartValue', undefined, reportLang)}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {chart.labels.map((label, index) => (
                          <tr key={label}>
                            <th scope="row" dir="auto">
                              {label}
                              {chart.forecast_from !== undefined && index >= chart.forecast_from
                                ? ` (${translate('runs.forecast', undefined, reportLang)})`
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

          <ModelCards models={run.models ?? []} language={reportLang} />

          {run.reports.length ? (
            <div className="card report-theme report-sheet">
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
                      <p className="reporthead" dir={reportDir} lang={reportLang}>
                        {section.headline}
                      </p>
                    ) : null}
                    <ReportDocument content={section.content} language={reportLang}
                      label={t('runs.reportText', { type: typeLabel(t, section.type, section.title) })} />
                  </div>
                ))}
            </div>
          ) : null}

          {run.report ? (
            <div className="card report-theme report-sheet">
              <h3 className="card__title">
                {t('runs.comprehensive', { version: run.report.version })}
                {run.report.published_path ? t('runs.published') : ''}
              </h3>
              {run.report.published_path ? (
                <p className="privacy-note">
                  <Icon name="check" size={14} /> <span dir="ltr">{run.report.published_path}</span>
                </p>
              ) : null}
              <ReportDocument ref={fullReportRef} className="runreport--full" content={run.report.content}
                language={reportLang} label={t('runs.comprehensiveText')} />
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

        <div className="panel__column panel__column--side"><RunTimeline run={run} pipelines={pipelines} onEvidence={setEvidenceTask} /></div>
      </div>
      {snapshot.interrupted ? <div className="cockpit__recovery"><p role="alert" dir="auto">{errorMessage}</p><button type="button" className="btn btn--ghost" onClick={() => { setErrorMessage(null); void runStore.retry(run.id) }}>{t('common.tryAgain')}</button></div> : null}
      {evidenceTask ? <EvidencePanel run={run} task={evidenceTask} onClose={closeEvidence} /> : null}
    </section>
  )
}
