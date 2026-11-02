import { useEffect, useState } from 'react'
import { api } from '../../shared/api'
import type { RunDetail } from '../../shared/types'
import type { MessageKey } from '../../i18n'
import { usePack } from '../../i18n/pack'
import { jarvisMessages } from '../../i18n/jarvis'
import { stateLabel } from '../../shared/labels'
import { BASE_ROLES, groupedTasks } from '../runs/pipeline'

const LIVE = new Set(['queued', 'running'])
const MARK: Record<string, string> = { succeeded: '✓', failed: '!', skipped: '–', cancelled: '–', running: '•', awaiting_approval: '◆' }

/** The run's real stage states, read from the server and refreshed while it runs. Nothing is simulated. */
export function AgentMap({ runId }: { runId: string }) {
  const { t, formatNumber } = usePack(jarvisMessages)
  const [run, setRun] = useState<RunDetail | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let alive = true; let timer = 0
    const load = () => api.getRun(runId).then((next) => {
      if (!alive) return
      setRun(next); setFailed(false)
      if (LIVE.has(next.state)) timer = window.setTimeout(load, 4000)
    }).catch(() => { if (alive) setFailed(true) })
    void load()
    return () => { alive = false; window.clearTimeout(timer) }
  }, [runId])
  if (!run) return failed ? <p className="agent-map__none">{t('agentMapNone')}</p> : null
  const done = run.tasks.filter((task) => task.state === 'succeeded').length
  return <section className="agent-map" aria-label={t('agentMap')}>
    <header><strong>{t('agentMap')}</strong><span>{stateLabel(t, run.state)} · <bdi>{formatNumber(done)}/{formatNumber(run.tasks.length)}</bdi></span></header>
    <p>{t('hermes')}</p>
    <div className="agent-map__bands">{groupedTasks(run.tasks).filter((group) => group.tasks.length).map(({ band, tasks }) => <div key={band}>
      <h4>{t(`cockpit.band.${band}` as MessageKey)}</h4>
      <ol>{tasks.map((task) => <li key={task.id} data-state={task.state} title={stateLabel(t, task.state)}>
        <span aria-hidden="true">{MARK[task.state] ?? ''}</span>
        <span dir="auto">{(BASE_ROLES as readonly string[]).includes(task.role) ? t(`cockpit.role.${task.role}` as MessageKey) : task.title.split(' — ')[0]}</span>
        <span className="agent-map__state">{stateLabel(t, task.state)}</span>
      </li>)}</ol></div>)}</div>
  </section>
}
