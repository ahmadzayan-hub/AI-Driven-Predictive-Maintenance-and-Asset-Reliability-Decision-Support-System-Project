import { useEffect, useRef, useState, type FormEvent } from 'react'
import { usePack } from '../../i18n/pack'
import { api, ApiError } from '../../shared/api'
import type { KpiMeasure, KpiPolicy, KpiRule } from '../../shared/types'
import { policyMessages } from './policyMessages'
import './policy.css'

const bounds = (direction: KpiRule['direction']) => direction === 'range'
  ? ['good_min', 'good_max', 'okay_min', 'okay_max'] as const
  : ['good_at', 'okay_at'] as const

export default function KpiPolicyEditor({ runId, measures, onSaved, onClose }: {
  runId: string; measures: KpiMeasure[]; onSaved: () => void; onClose: () => void
}) {
  const { t, locale } = usePack(policyMessages)
  const [policy, setPolicy] = useState<KpiPolicy | null>(null)
  const [writable, setWritable] = useState(false)
  const [metric, setMetric] = useState(measures[0]?.key || '')
  const [direction, setDirection] = useState<KpiRule['direction']>('higher')
  const [values, setValues] = useState<Record<string, string>>({})
  const [source, setSource] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<'failed' | 'invalid' | 'conflict' | null>(null)
  const [reload, setReload] = useState(0)
  const active = useRef<AbortController | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => { heading.current?.focus() }, [])
  useEffect(() => {
    const controller = new AbortController()
    let current = true
    setPolicy(null); setError(null); setWritable(false)
    Promise.all([api.kpiPolicy(runId, locale, controller.signal), api.identity()])
      .then(([result, identity]) => {
        if (current) { setPolicy(result); setWritable(identity.principal.permissions.includes('write')) }
      }).catch(() => { if (current) setError('failed') })
    return () => { current = false; controller.abort(); active.current?.abort() }
  }, [runId, locale, reload])
  useEffect(() => {
    const rule = policy?.rules[metric]
    setDirection(rule?.direction || 'higher')
    setSource(rule?.source_ref || '')
    setValues(rule ? Object.fromEntries(bounds(rule.direction).map((key) => [key, String(rule[key])])) : {})
  }, [metric, policy])
  const measure = measures.find((item) => item.key === metric)
  const fields = bounds(direction)
  const unit = measure?.scale === 'percent' ? '%' : measure?.scale || ''
  async function save(remove = false) {
    if (!policy || !measure || !writable || busy || error === 'conflict') return
    const numeric = Object.fromEntries(fields.map((key) => [key, values[key]?.trim() ? Number(values[key]) : NaN]))
    const ordered = direction === 'higher' ? numeric.good_at >= numeric.okay_at : direction === 'lower'
      ? numeric.good_at <= numeric.okay_at : numeric.okay_min <= numeric.good_min && numeric.good_min <= numeric.good_max && numeric.good_max <= numeric.okay_max
    if (!remove && (!ordered || !Object.values(numeric).every(Number.isFinite) || !source.trim())) { setError('invalid'); return }
    const rules = { ...policy.rules }
    if (remove) delete rules[metric]
    else rules[metric] = { direction, scale: measure.scale, source_ref: source.trim(), ...numeric }
    const controller = new AbortController()
    active.current = controller
    setBusy(true); setError(null)
    try {
      await api.saveKpiPolicy(runId, { revision: policy.revision, rules }, locale, controller.signal)
      if (!controller.signal.aborted) onSaved()
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof ApiError && err.status === 409 ? 'conflict' : 'failed')
    } finally { if (!controller.signal.aborted) setBusy(false) }
  }
  function submit(event: FormEvent) { event.preventDefault(); void save() }
  return <section className="exec-card policy-editor" aria-labelledby="policy-title" aria-busy={busy}>
    <div className="exec-section-head"><h3 id="policy-title" tabIndex={-1} ref={heading}>{t('policy.title')}</h3><button type="button" className="btn btn--ghost" disabled={busy} onClick={onClose}>{t('policy.cancel')}</button></div>
    <p className="exec-muted">{t('policy.help')}</p>
    {error ? <p role="alert">{t(`policy.${error}`)}</p> : null}
    {!policy || error === 'conflict' ? <button type="button" className="btn btn--ghost" onClick={() => setReload((v) => v + 1)}>{t('policy.reload')}</button> : null}
    {!policy && !error ? <p role="status">{t('policy.loading')}</p> : null}
    {policy ? <form onSubmit={submit}>
      {!writable ? <p>{t('policy.readonly')}</p> : null}
      <fieldset disabled={busy || !writable || error === 'conflict'}>
        <div className="policy-fields">
          <div className="field"><label className="field__label" htmlFor="policy-metric">{t('policy.metric')}</label><select className="field__select" id="policy-metric" value={metric} onChange={(e) => { setMetric(e.target.value); setError(null) }}>{measures.map((item) => <option key={item.key} value={item.key}>{item.title}</option>)}</select></div>
          <div className="field"><label className="field__label" htmlFor="policy-direction">{t('policy.direction')}</label><select className="field__select" id="policy-direction" value={direction} onChange={(e) => { setDirection(e.target.value as KpiRule['direction']); setValues({}); setError(null) }}>{(['higher', 'lower', 'range'] as const).map((value) => <option key={value} value={value}>{t(`policy.${value}`)}</option>)}</select></div>
          {fields.map((name) => <div className="field" key={name}><label className="field__label" htmlFor={`policy-${name}`}>{t(`policy.${name}`)}</label><input className="field__input" id={`policy-${name}`} type="number" step="any" required dir="ltr" value={values[name] || ''} onChange={(e) => setValues({ ...values, [name]: e.target.value })} aria-describedby="policy-scale policy-boundaries" /></div>)}
        </div>
        <p className="exec-muted" id="policy-scale">{t('policy.scale', { unit })}</p>
        <p className="exec-muted" id="policy-boundaries">{t(`policy.${direction}Help`)}</p>
        <div className="field"><label className="field__label" htmlFor="policy-source">{t('policy.source')}</label><input className="field__input" id="policy-source" required maxLength={240} value={source} onChange={(e) => setSource(e.target.value)} dir="auto" /></div>
        <div className="policy-actions"><button type="submit" className="btn btn--primary">{t('policy.save')}</button>{policy.rules[metric] ? <button type="button" className="btn btn--ghost" onClick={() => void save(true)}>{t('policy.remove')}</button> : null}</div>
      </fieldset>
    </form> : null}
  </section>
}
