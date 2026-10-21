import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { usePack } from '../../i18n/pack'
import { ApiError } from '../../shared/api'
import { PerformanceValue, performanceTone } from '../../shared/components/PerformanceValue'
import { Field } from './OperationsView'
import { operationsRequest, requestKey } from './operationsApi'
import type { OperationsOverview } from './types'
import { validationMessages } from './validationMessages'

interface Protocol { name: string; model_version: string; baseline_name: string; trained_through: string; horizon_hours: number; threshold: number; failure_definition: string; cohort_definition: string; registered_at: string }
interface TrialSummary { id: string; revision: number; protocol: Protocol }
interface Fraction { numerator: number; denominator: number; value: number | null; wilson_95: [number, number] | null }
interface Prediction { id: string; asset_id: string; probability: number; baseline_probability: number; predicted_at: string; window_end: string; outcome: { failed: boolean; evidence_reference: string } | null }
interface Trial extends TrialSummary {
  predictions: Prediction[];
  metrics: { registered: number; evaluated: number; pending: number; failure_alert_precision: Fraction; failure_window_recall: Fraction; actionable_alert_precision: Fraction; brier_score: number | null; baseline: { brier_score: number | null }; lead_time_hours: { mean: number | null }; false_alerts_per_asset_month: number | null; calibration: Array<{ lower: number; upper: number; count: number; mean_probability: number | null; observed_failure_rate: number | null }> };
}
type RecordAction = (kind: string, body: object, url: string) => Promise<boolean>
const endpoint = (id: string) => `/api/operations/trials/${encodeURIComponent(id)}`
const iso = (local: string) => new Date(local).toISOString()

export function ValidationPanel({ data }: { data: OperationsOverview }) {
  const { t } = usePack(validationMessages)
  const [trials, setTrials] = useState<TrialSummary[]>([]), [selected, setSelected] = useState('')
  const [trial, setTrial] = useState<Trial | null>(null), [busy, setBusy] = useState(false)
  const [error, setError] = useState(''), [loading, setLoading] = useState(true), [saved, setSaved] = useState(false)
  const keys = useRef(new Map<string, ReturnType<typeof requestKey>>()), live = useRef(true), generation = useRef(0)
  const base = `/api/operations/organizations/${encodeURIComponent(data.organization.id)}/trials`
  const readList = useCallback(async () => {
    const result = await operationsRequest<{ trials: TrialSummary[] }>(base)
    if (live.current) { setTrials(result.trials); setSelected((id) => result.trials.some((item) => item.id === id) ? id : result.trials[0]?.id ?? '') }
  }, [base])
  useEffect(() => {
    live.current = true
    setLoading(true)
    void readList().catch((reason: unknown) => { if (live.current) setError(reason instanceof ApiError ? reason.message : t('error')) }).finally(() => { if (live.current) setLoading(false) })
    return () => { live.current = false; generation.current++ }
  }, [readList, t])
  useEffect(() => {
    const current = ++generation.current
    setTrial(null)
    if (!selected) return
    setLoading(true)
    void operationsRequest<Trial>(endpoint(selected)).then((result) => { if (live.current && current === generation.current) setTrial(result) })
      .catch((reason: unknown) => { if (live.current && current === generation.current) setError(reason instanceof ApiError ? reason.message : t('error')) })
      .finally(() => { if (live.current && current === generation.current) setLoading(false) })
  }, [selected, t])
  async function refresh() {
    setLoading(true); setError('')
    const id = selected, current = generation.current
    try {
      await readList()
      if (id) {
        const result = await operationsRequest<Trial>(endpoint(id))
        if (live.current && current === generation.current) setTrial(result)
      }
    } catch (reason) { if (live.current) setError(reason instanceof ApiError ? reason.message : t('error')) }
    finally { if (live.current) setLoading(false) }
  }
  const record: RecordAction = async (kind, body, url) => {
    setBusy(true); setError(''); setSaved(false)
    if (!keys.current.has(kind)) keys.current.set(kind, requestKey())
    const requestId = keys.current.get(kind)!(body)
    try {
      const result = await operationsRequest<Trial>(url, { method: 'POST', body: JSON.stringify({ ...body, ...(!kind.startsWith('outcome') ? { request_id: requestId } : {}) }) })
      keys.current.delete(kind)
      if (live.current) { setSelected(result.id); setTrial(result); setSaved(true); await readList() }
      return true
    } catch (reason) { if (live.current) setError(reason instanceof ApiError ? reason.message : t('error')); return false }
    finally { if (live.current) setBusy(false) }
  }
  function download() {
    if (!trial) return
    const url = URL.createObjectURL(new Blob([JSON.stringify(trial, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `validation-${trial.id}.json`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <section className="operations__validation" aria-label={t('title')}>
    <div className="operations__toolbar"><p>{t('intro')}</p><button className="btn btn--ghost" disabled={busy || loading} onClick={() => void refresh()}>{t('refresh')}</button></div>
    {loading && <p role="status">{t('loading')}</p>}
    {error && <div className="operations__error" role="alert"><p>{t('error')}</p><p dir="auto">{error}</p></div>}
    {saved && <p role="status">{t('saved')}</p>}
    {data.permissions.manage && <details className="operations__card"><summary>{t('create')}</summary><ProtocolForm busy={busy || loading} record={record} url={base} /></details>}
    {!trials.length && !loading && <p>{t('empty')}</p>}
    {trials.length > 0 && <Field label={t('protocol')}><select value={selected} onChange={(event) => setSelected(event.target.value)} disabled={busy}>{trials.map((item) => <option key={item.id} value={item.id}>{item.protocol.name} · {item.protocol.model_version}</option>)}</select></Field>}
    {trial && <div key={trial.id}>
      <details className="operations__card"><summary>{t('protocol')}</summary><p dir="auto">{trial.protocol.failure_definition}</p><p dir="auto">{trial.protocol.cohort_definition}</p><p>{t('horizon')}: {trial.protocol.horizon_hours} · {t('threshold')}: {trial.protocol.threshold}</p><p dir="auto">{t('baseline')}: {trial.protocol.baseline_name}</p><p>{t('immutable')}</p></details>
      <TrialMetrics trial={trial} />
      {data.permissions.write && <details className="operations__card"><summary>{t('prediction')}</summary><PredictionForm trial={trial} data={data} busy={busy || loading} record={record} /></details>}
      {data.permissions.authorize && <details className="operations__card"><summary>{t('adjudicate')}</summary><OutcomeForm trial={trial} data={data} busy={busy || loading} record={record} /></details>}
      <details className="operations__card"><summary>{t('pendingList')}</summary><ul>{trial.predictions.map((prediction) => <li key={prediction.id}><span dir="auto">{data.assets.find((asset) => asset.id === prediction.asset_id)?.name ?? prediction.asset_id}</span> · {prediction.probability} · {t('ends')}: <bdi>{prediction.window_end}</bdi> · {t(prediction.outcome ? 'completed' : 'waiting')}</li>)}</ul></details>
      <button className="btn btn--ghost" onClick={download}>{t('export')}</button>
    </div>}
  </section>
}

function ProtocolForm({ busy, record, url }: { busy: boolean; record: RecordAction; url: string }) {
  const { t } = usePack(validationMessages)
  const [draft, setDraft] = useState({ name: '', model_version: '', baseline_name: '', trained_through: '', horizon_hours: '', threshold: '', failure_definition: '', cohort_definition: '' })
  async function submit(event: FormEvent) {
    event.preventDefault()
    const body = { ...draft, trained_through: iso(draft.trained_through), horizon_hours: Number(draft.horizon_hours), threshold: Number(draft.threshold) }
    if (await record('protocol', body, url)) setDraft({ name: '', model_version: '', baseline_name: '', trained_through: '', horizon_hours: '', threshold: '', failure_definition: '', cohort_definition: '' })
  }
  const fields = [['name', 'name'], ['model_version', 'model'], ['baseline_name', 'baseline'], ['trained_through', 'trained'], ['horizon_hours', 'horizon'], ['threshold', 'threshold'], ['failure_definition', 'failure'], ['cohort_definition', 'cohort']] as const
  return <form onSubmit={(event) => void submit(event)}><p>{t('immutable')}</p><fieldset disabled={busy}><div className="operations__forms">
    {fields.map(([key, label]) => <Field key={key} label={t(label)}><input required maxLength={key.endsWith('definition') ? 1000 : 200} type={key === 'trained_through' ? 'datetime-local' : key === 'horizon_hours' || key === 'threshold' ? 'number' : 'text'} min={key === 'horizon_hours' ? 1 : key === 'threshold' ? 0 : undefined} max={key === 'horizon_hours' ? 8760 : key === 'threshold' ? 1 : undefined} step={key === 'horizon_hours' || key === 'threshold' ? 'any' : undefined} value={draft[key]} onChange={(event) => setDraft((value) => ({ ...value, [key]: event.target.value }))} /></Field>)}
    </div><button className="btn btn--primary">{t('create')}</button></fieldset></form>
}

function PredictionForm({ trial, data, busy, record }: { trial: Trial; data: OperationsOverview; busy: boolean; record: RecordAction }) {
  const { t } = usePack(validationMessages)
  const [asset, setAsset] = useState(''), [probability, setProbability] = useState(''), [baseline, setBaseline] = useState('')
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (await record('prediction', { revision: trial.revision, asset_id: asset, probability: Number(probability), baseline_probability: Number(baseline) }, `${endpoint(trial.id)}/predictions`)) { setProbability(''); setBaseline('') }
  }
  return <form onSubmit={(event) => void submit(event)}><p>{t('predictionHelp')}</p><fieldset disabled={busy}>
    <Field label={t('asset')}><select value={asset} onChange={(event) => setAsset(event.target.value)} required><option value="">{t('choose')}</option>{data.assets.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></Field>
    <div className="operations__forms"><Field label={t('probability')}><input type="number" min="0" max="1" step="any" required value={probability} onChange={(event) => setProbability(event.target.value)} /></Field><Field label={t('baselineProbability')}><input type="number" min="0" max="1" step="any" required value={baseline} onChange={(event) => setBaseline(event.target.value)} /></Field></div>
    <button className="btn btn--primary">{t('prediction')}</button>
  </fieldset></form>
}

function OutcomeForm({ trial, data, busy, record }: { trial: Trial; data: OperationsOverview; busy: boolean; record: RecordAction }) {
  const { t } = usePack(validationMessages)
  const [prediction, setPrediction] = useState(''), [failed, setFailed] = useState(''), [actionable, setActionable] = useState('')
  const [failureAt, setFailureAt] = useState(''), [through, setThrough] = useState(''), [evidence, setEvidence] = useState(''), [confirmed, setConfirmed] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!confirmed) return
    const body = { revision: trial.revision, failed: failed === 'yes', actionable: actionable ? actionable === 'yes' : null, failure_at: failed === 'yes' ? iso(failureAt) : null, observed_through: iso(through), evidence_reference: evidence.trim() }
    if (await record(`outcome-${prediction}`, body, `${endpoint(trial.id)}/predictions/${encodeURIComponent(prediction)}/outcome`)) { setPrediction(''); setFailed(''); setEvidence(''); setConfirmed(false) }
  }
  return <form onSubmit={(event) => void submit(event)}><p>{t('outcomeHelp')}</p><fieldset disabled={busy}>
    <Field label={t('window')}><select required value={prediction} onChange={(event) => { setPrediction(event.target.value); setConfirmed(false) }}><option value="">{t('choose')}</option>{trial.predictions.filter((item) => !item.outcome).map((item) => <option key={item.id} value={item.id}>{data.assets.find((asset) => asset.id === item.asset_id)?.name} · {item.window_end}</option>)}</select></Field>
    <div className="operations__forms"><Field label={t('failed')}><select required value={failed} onChange={(event) => setFailed(event.target.value)}><option value="">{t('choose')}</option><option value="yes">{t('yes')}</option><option value="no">{t('no')}</option></select></Field><Field label={t('actionability')}><select value={actionable} onChange={(event) => setActionable(event.target.value)}><option value="">{t('unknown')}</option><option value="yes">{t('yes')}</option><option value="no">{t('no')}</option></select></Field></div>
    {failed === 'yes' && <Field label={t('failureAt')}><input type="datetime-local" required value={failureAt} onChange={(event) => setFailureAt(event.target.value)} /></Field>}
    <Field label={t('through')}><input type="datetime-local" required value={through} onChange={(event) => setThrough(event.target.value)} /></Field>
    <Field label={t('evidence')}><input required maxLength={500} value={evidence} onChange={(event) => setEvidence(event.target.value)} /></Field>
    <label className="operations__acknowledge"><input type="checkbox" required checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />{t('final')}</label>
    <button className="btn btn--primary" disabled={!confirmed}>{t('adjudicate')}</button>
  </fieldset></form>
}

function TrialMetrics({ trial }: { trial: Trial }) {
  const { t, formatNumber } = usePack(validationMessages)
  const metric = trial.metrics
  const number = (value: number | null) => <PerformanceValue tone={performanceTone(value)}><bdi>{value === null ? t('unmeasured') : formatNumber(value, { maximumFractionDigits: 3 })}</bdi></PerformanceValue>
  const fraction = (value: Fraction) => <><PerformanceValue tone={performanceTone(value.value)}><bdi>{value.value === null ? t('unmeasured') : formatNumber(value.value, { style: 'percent', maximumFractionDigits: 1 })}</bdi></PerformanceValue> <bdi>({value.numerator}/{value.denominator})</bdi>{value.wilson_95 && <small> · {t('uncertainty')}: {value.wilson_95.map((bound) => formatNumber(bound, { style: 'percent', maximumFractionDigits: 1 })).join(' – ')}</small>}</>
  return <section className="operations__card"><h3>{t('metrics')}</h3><p>{t('scope')}</p><dl className="operations__evidence">
    <div><dt>{t('registered')}</dt><dd>{number(metric.registered)}</dd></div><div><dt>{t('evaluated')}</dt><dd>{number(metric.evaluated)}</dd></div><div><dt>{t('pending')}</dt><dd>{number(metric.pending)}</dd></div>
    <div><dt>{t('precision')}</dt><dd>{fraction(metric.failure_alert_precision)}</dd></div><div><dt>{t('recall')}</dt><dd>{fraction(metric.failure_window_recall)}</dd></div><div><dt>{t('actionable')}</dt><dd>{fraction(metric.actionable_alert_precision)}</dd></div>
    <div><dt>{t('brier')}</dt><dd>{number(metric.brier_score)}</dd></div><div><dt>{t('baselineBrier')}</dt><dd>{number(metric.baseline.brier_score)}</dd></div><div><dt>{t('lead')}</dt><dd>{number(metric.lead_time_hours.mean)}</dd></div><div><dt>{t('falseAlerts')}</dt><dd>{number(metric.false_alerts_per_asset_month)}</dd></div>
  </dl><details><summary>{t('calibration')}</summary><div className="operations__table"><table><caption>{t('calibration')}</caption><thead><tr>{(['range', 'count', 'predicted', 'observed'] as const).map((key) => <th scope="col" key={key}>{t(key)}</th>)}</tr></thead><tbody>{metric.calibration.map((bin) => <tr key={bin.lower}><th scope="row"><bdi>{bin.lower}–{bin.upper}</bdi></th><td>{bin.count}</td><td>{number(bin.mean_probability)}</td><td>{number(bin.observed_failure_rate)}</td></tr>)}</tbody></table></div></details></section>
}
