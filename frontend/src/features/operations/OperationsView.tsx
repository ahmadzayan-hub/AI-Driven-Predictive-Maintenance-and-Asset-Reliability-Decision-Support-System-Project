import { cloneElement, lazy, Suspense, useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, ReactElement } from 'react'
import { usePack } from '../../i18n/pack'
import { hasWorkSource } from '../../shared/sourceHandoff'
import type { RunDetail } from '../../shared/types'
import { api, ApiError } from '../../shared/api'
import { Icon } from '../../shared/components/Icon'
import { PerformanceLegend, PerformanceValue } from '../../shared/components/PerformanceValue'
import { messages } from './messages'
import { operationsApi, requestKey } from './operationsApi'
import { RegistryPanel, TeamPanel } from './RegistryPanel'
import { WorkOrdersPanel } from './WorkOrdersPanel'
import type { OperationsOverview, Organization, Readiness } from './types'
import './operations.css'
const ValidationPanel = lazy(() => import('./ValidationPanel').then((module) => ({ default: module.ValidationPanel })))

export type Mutate = (kind: string, body: object, action: (key: string) => Promise<unknown>) => Promise<boolean>
export function Field({ label, children }: { label: string; children: ReactElement<{ id?: string }> }) {
  const generated = useId()
  const id = children.props.id ?? generated
  return <div className="operations__field"><label htmlFor={id}>{label}</label>{cloneElement(children, { id })}</div>
}

function errorKey(error: unknown, loading = false) {
  if (error instanceof ApiError) {
    if (error.status === 409) return 'conflict'
    if (error.status === 403) return 'forbidden'
    if (error.status === 400 || error.status === 422) return 'invalid'
  }
  return loading ? 'loadFailed' : 'failed'
}

export function OperationsView({ onOpenRun, sourceRunId, onClearSource }: { onOpenRun: (id: string) => void; sourceRunId?: string; onClearSource?: () => void }) {
  const { t } = usePack(messages)
  const [source, setSource] = useState<RunDetail | null>(null)
  const [sourceError, setSourceError] = useState(false)
  useEffect(() => {
    let alive = true
    setSource(null); setSourceError(false)
    if (sourceRunId) api.getRun(sourceRunId).then(run => {
      if (!alive) return
      if (run.id === sourceRunId && hasWorkSource(run)) setSource(run)
      else setSourceError(true)
    }).catch(() => { if (alive) setSourceError(true) })
    return () => { alive = false }
  }, [sourceRunId])
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [selected, setSelected] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ReturnType<typeof errorKey> | null>(null)
  const [creating, setCreating] = useState(false)
  const [setupOpen, setSetupOpen] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const key = useRef(requestKey())
  useEffect(() => {
    let alive = true
    setLoading(true)
    operationsApi.organizations().then(({ organizations: items }) => {
      if (!alive) return
      setOrganizations(items)
      if (!items.length) setSetupOpen(true)
      setSelected((current) => items.some((item) => item.id === current) ? current : items[0]?.id ?? '')
      setError(null)
    }).catch((reason: unknown) => { if (alive) setError(errorKey(reason, true)) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [attempt])

  async function create(event: FormEvent) {
    event.preventDefault()
    setCreating(true); setError(null)
    try {
      const organization = await operationsApi.createOrganization(name.trim(), key.current(name.trim()))
      setOrganizations((items) => [...items.filter((item) => item.id !== organization.id), organization])
      setSelected(organization.id); setName(''); setSetupOpen(false); key.current = requestKey()
    } catch (reason) { setError(errorKey(reason)) }
    finally { setCreating(false) }
  }

  return <section className="operations view" aria-labelledby="operations-title">
    <header className="operations__heading">
      <div><h2 id="operations-title">{t('title')}</h2></div>
      <span className="operations__emblem"><Icon name="activity" size={28} /></span>
    </header>
    {sourceRunId && <div className="operations__card">
      {source ? <><strong dir="auto">{source.goal}</strong><p>{t('sourceScope')}</p><p>{t('run')}: <bdi>{source.id}</bdi> · {t('sourceDataset')}: <bdi>{source.dataset_id}</bdi></p></> : <p role={sourceError ? 'alert' : 'status'}>{t(sourceError ? 'sourceFailed' : 'loading')}</p>}
      <button type="button" className="btn btn--ghost" onClick={onClearSource}>{t('clearSource')}</button>
    </div>}
    <div className="operations__workspace">
      {organizations.length > 0 && <Field label={t('organization')}><select value={selected} onChange={(event) => setSelected(event.target.value)} disabled={creating || loading}>
        {organizations.map((organization) => <option value={organization.id} key={organization.id}>{organization.name}</option>)}
      </select></Field>}
      <details className="operations__setup" open={setupOpen} onToggle={(event) => setSetupOpen(event.currentTarget.open)}>
        <summary>{t('createOrganization')}</summary>
        <form onSubmit={(event) => void create(event)}>
          <Field label={t('organizationName')}><input value={name} onChange={(event) => setName(event.target.value)} required maxLength={120} disabled={creating} /></Field>
          <button className="btn btn--primary" disabled={creating || loading}>{creating ? t('saving') : t('createOrganization')}</button>
        </form>
      </details>
    </div>
    {loading && <p role="status">{t('loading')}</p>}
    {error && <div className="operations__error" role="alert"><p>{t(error)}</p><button className="btn btn--ghost" onClick={() => setAttempt((value) => value + 1)} disabled={loading}>{t('refresh')}</button></div>}
    {!selected && !loading && !error && <div className="operations__empty operations__empty--workspace">
      <Icon name="database" size={32} /><h3>{t('emptyOrganization')}</h3><p>{t('workspaceEmptyHelp')}</p>
      <ol className="operations__steps"><li>{t('setupRegistry')}</li><li>{t('setupEvidence')}</li><li>{t('setupOutcome')}</li></ol>
    </div>}
    {selected && (!sourceRunId || source?.id === sourceRunId) && <OperationsWorkspace key={`${selected}:${sourceRunId ?? ''}`} organizationId={selected} sourceRunId={sourceRunId ? source?.id : undefined} onOpenRun={onOpenRun} />}
  </section>
}

function OperationsWorkspace({ organizationId, onOpenRun, sourceRunId }: { organizationId: string; onOpenRun: (id: string) => void; sourceRunId?: string }) {
  const { t, formatNumber } = usePack(messages)
  const [data, setData] = useState<OperationsOverview | null>(null)
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<'saved' | null>(null)
  const [error, setError] = useState<ReturnType<typeof errorKey> | null>(null)
  const [serverMessage, setServerMessage] = useState('')
  const [tab, setTab] = useState<'orders' | 'registry' | 'team' | 'validation'>('orders')
  const [validationVisited, setValidationVisited] = useState(false)
  const alive = useRef(true)
  const readGeneration = useRef(0)
  const keys = useRef(new Map<string, ReturnType<typeof requestKey>>())
  const alert = useRef<HTMLDivElement>(null)
  const registry = useRef<HTMLDivElement>(null)
  const [registryFocus, setRegistryFocus] = useState(0)
  const refresh = useCallback(async () => {
    const current = ++readGeneration.current
    setLoading(true)
    try {
      const [overviewResult, readinessResult] = await Promise.allSettled([operationsApi.overview(organizationId), operationsApi.readiness(organizationId)])
      if (overviewResult.status === 'rejected') throw overviewResult.reason
      if (alive.current && current === readGeneration.current) { setData(overviewResult.value); setReadiness(readinessResult.status === 'fulfilled' ? readinessResult.value : null); setError(null); setServerMessage('') }
      return true
    } catch (reason) {
      if (alive.current && current === readGeneration.current) {
        setError(errorKey(reason, true)); setServerMessage(reason instanceof ApiError && reason.status ? reason.message : '')
        if (reason instanceof ApiError && [401, 403, 404].includes(reason.status)) setData(null)
      }
      return false
    }
    finally { if (alive.current && current === readGeneration.current) setLoading(false) }
  }, [organizationId])
  useEffect(() => {
    alive.current = true
    void refresh()
    return () => { alive.current = false; readGeneration.current++ }
  }, [refresh])
  useEffect(() => { if (error) alert.current?.focus() }, [error])
  useEffect(() => { if (registryFocus) registry.current?.focus() }, [registryFocus])

  const mutate: Mutate = async (kind, body, action) => {
    if (busy) return false
    setBusy(true); setError(null); setMessage(null); setServerMessage('')
    if (!keys.current.has(kind)) keys.current.set(kind, requestKey())
    try {
      await action(keys.current.get(kind)!(body))
      keys.current.delete(kind)
      if (alive.current) { setMessage('saved'); await refresh() }
      return true
    } catch (reason) { if (alive.current) { setError(errorKey(reason)); setServerMessage(reason instanceof ApiError && reason.status ? reason.message : '') }; return false }
    finally { if (alive.current) setBusy(false) }
  }

  async function exportRecords() {
    setBusy(true); setError(null)
    try {
      const payload = await operationsApi.export(organizationId)
      if (!alive.current) return
      const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a')
      link.href = url; link.download = `maintenance-operations-${organizationId}.json`; link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (reason) { if (alive.current) setError(errorKey(reason, true)) }
    finally { if (alive.current) setBusy(false) }
  }

  return <div className="operations__body" aria-busy={loading || busy}>
    <div className="operations__toolbar">
      <p className="operations__connection" role="status"><span className={`operations__dot ${loading || busy ? 'operations__dot--busy' : ''}`} aria-hidden="true" />{busy ? t('saving') : loading ? t('loading') : error ? t('loadFailed') : t('connected')}</p>
      <button className="btn btn--ghost" onClick={() => void refresh()} disabled={loading || busy}><Icon name="refresh" size={16} />{t('refresh')}</button>
    </div>
    {error && <div className="operations__error" role="alert" tabIndex={-1} ref={alert}><p>{t(error)}</p>{serverMessage && <p dir="auto">{serverMessage}</p>}</div>}
    {message && <p role="status">{t(message)}</p>}
    {data && <>
      <section className="operations__overview" aria-label={t('overviewTitle')}>
        <div className="operations__overview-heading"><div><p className="operations__eyebrow">{t('overviewTitle')}</p><h3 dir="auto">{data.organization.name}</h3><p className="operations__muted">{t('overviewHelp')}</p></div>
          <button type="button" className="btn btn--ghost" aria-controls="operations-registry-panel" onClick={() => { setTab('registry'); setRegistryFocus((value) => value + 1) }}><Icon name="database" size={17} />{t('browseRegistry')}</button>
        </div>
        <dl className="operations__coverage" aria-label={t('registrySummary')}>
          <div><dt>{t('registeredAssets')}</dt><dd><bdi>{formatNumber(data.assets.length)}</bdi></dd></div>
          <div><dt>{t('registeredSites')}</dt><dd><bdi>{formatNumber(data.sites.length)}</bdi></dd></div>
          <div><dt>{t('recordedOrders')}</dt><dd><bdi>{formatNumber(data.work_order_count)}</bdi></dd></div>
        </dl>
      </section>
      {readiness?.execution.mode === 'worker' && !readiness.execution.ready && <p className="operations__error" role="status">{t('workerMissing')}</p>}
      <details className="operations__card"><summary>{t('readiness')}</summary>
        <p>{!readiness ? t('readinessUnknown') : readiness.execution.mode === 'client' ? t('clientMode') : readiness.execution.ready ? t('workerReady') : t('workerMissing')}</p>
        {readiness && <ul>{readiness.checks.map((check) => <li key={check.id}>{t(check.id)}: {t(check.observed ? 'observed' : 'notObserved')}</li>)}</ul>}
        <p>{t('readinessLimits')}</p>
      </details>
      {data.work_orders_truncated && <p>{t('truncated', { shown: data.work_orders.length, total: data.work_order_count })}</p>}
      <PerformanceLegend />
      <div className="operations__summary" role="group" aria-label={t('summaryTitle')}>
        <div><span>{t('waiting')}</span><PerformanceValue tone="unassessed"><strong><bdi>{formatNumber(data.work_orders.filter((order) => order.status === 'draft').length)}</bdi></strong></PerformanceValue></div>
        <div><span>{t('active')}</span><PerformanceValue tone="unassessed"><strong><bdi>{formatNumber(data.work_orders.filter((order) => order.status === 'authorized' || order.status === 'in_progress').length)}</bdi></strong></PerformanceValue></div>
        <div><span>{t('closed')}</span><PerformanceValue tone="unassessed"><strong><bdi>{formatNumber(data.work_orders.filter((order) => order.status === 'completed').length)}</bdi></strong></PerformanceValue></div>
      </div>
      <p className="operations__summary-help">{t('summaryHelp')}</p>
      <nav className="operations__tabs" aria-label={t('title')}>
        {(['orders', 'registry', 'team', 'validation'] as const).map((item) => <button type="button" key={item} aria-current={tab === item ? 'page' : undefined} onClick={() => { setTab(item); if (item === 'validation') setValidationVisited(true) }}>{t(item)}</button>)}
      </nav>
      {!data.permissions.write && <p>{t('readOnly')}</p>}
      {/* Keep unsaved forms in this open workspace when switching sections. */}
      <div hidden={tab !== 'orders'}><WorkOrdersPanel sourceRunId={sourceRunId} data={data} busy={busy || loading} mutate={mutate} onOpenRun={onOpenRun} /></div>
      <div id="operations-registry-panel" ref={registry} tabIndex={-1} hidden={tab !== 'registry'}><RegistryPanel data={data} busy={busy || loading} mutate={mutate} onOpenRun={onOpenRun} /></div>
      <div hidden={tab !== 'team'}><TeamPanel data={data} busy={busy || loading} mutate={mutate} /></div>
      {validationVisited && <div hidden={tab !== 'validation'}><Suspense fallback={<p role="status">{t('loading')}</p>}><ValidationPanel data={data} /></Suspense></div>}
      <footer className="operations__footer"><p>{t('draftHelp')}</p><button className="btn btn--ghost" disabled={loading || busy} onClick={() => void exportRecords()}>{t('export')}</button><p>{t('exportHelp')}</p></footer>
    </>}
  </div>
}
