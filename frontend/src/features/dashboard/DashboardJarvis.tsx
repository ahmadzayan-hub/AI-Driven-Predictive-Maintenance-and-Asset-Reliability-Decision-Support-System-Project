import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { request, api } from '../../shared/api'
import type { SessionState, TableFilter } from '../../shared/types'
import { useReadOnly } from '../../shared/readOnly'
import { usePack } from '../../i18n/pack'
import { jarvisDashboardMessages } from '../../i18n/jarvisDashboard'

const Workspace = lazy(() => import('../chat/JarvisWorkspace').then(module => ({ default: module.JarvisWorkspace })))

/** An explicit session binding to the exact chart scope. Never auto-select another run. */
export function DashboardJarvis({ runId, datasetName, filters, children }: {
  runId: string; datasetName: string; filters: TableFilter[]; children: ReactNode
}) {
  const { t, locale } = usePack(jarvisDashboardMessages)
  const readOnly = useReadOnly()
  const scopeKey = JSON.stringify([runId, filters, locale])
  const [expanded, setExpanded] = useState(false)
  const [binding, setBinding] = useState<{ scope: string; session: SessionState } | null>(null)
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const sessionId = useRef<string | null>(null)
  const generation = useRef(0)
  const inFlight = useRef(false)
  const bound = binding?.scope === scopeKey ? binding.session : null
  useEffect(() => {
    generation.current++; inFlight.current = false
    setBinding(null); setBusy(false); setFailed(false)
  }, [scopeKey])
  useEffect(() => () => { generation.current++ }, [])

  async function connect() {
    if (readOnly || inFlight.current) return
    const token = ++generation.current
    inFlight.current = true; setExpanded(true); setBusy(true); setFailed(false); setBinding(null)
    try {
      const id = sessionId.current ?? (await api.createSession(locale)).session_id
      if (generation.current !== token) return
      sessionId.current = id
      const session = await request<SessionState>(`/api/sessions/${encodeURIComponent(id)}/data-context`, {
        method: 'PUT', body: JSON.stringify({ run_id: runId, filters }),
      })
      if (generation.current === token) setBinding({ scope: scopeKey, session })
    } catch { if (generation.current === token) setFailed(true) }
    finally { if (generation.current === token) { inFlight.current = false; setBusy(false) } }
  }

  return <section className="dash-jarvis" aria-label={t('title')}>
    <header className="dash-jarvis__bar">
      <div><p className="eyebrow">{t('mode')}</p><h3>{t('title')}</h3><p>{t('help')}</p>
        <p className="dash-jarvis__scope">{t('scope')}: <bdi>{datasetName}</bdi> · <bdi>{runId}</bdi></p></div>
      <div className="dash-actions">
        <button type="button" className="btn btn--primary" disabled={readOnly || busy} onClick={() => void connect()}>{busy ? t('connecting') : bound ? t('reconnect') : t('open')}</button>
        {expanded && <button type="button" className="btn btn--ghost" onClick={() => {
          generation.current++; inFlight.current = false; setBusy(false); setExpanded(false); setBinding(null)
        }}>{t('close')}</button>}
      </div>
    </header>
    {readOnly && <p>{t('readonly')}</p>}
    <div className={`dash-jarvis__workspace${expanded ? ' dash-jarvis__workspace--open' : ''}`}>
      <div className="dash-jarvis__analytics">{children}</div>
      {expanded && <aside className="dash-jarvis__assistant" aria-label="Jarvis OS">
        {busy ? <p role="status">{t('connecting')}</p> : failed ? <p role="alert">{t('unavailable')}</p> : bound ?
          <Suspense fallback={<p role="status">{t('loading')}</p>}><Workspace session={bound} embedded /></Suspense> : <p role="status">{t('changed')}</p>}
      </aside>}
    </div>
  </section>
}
