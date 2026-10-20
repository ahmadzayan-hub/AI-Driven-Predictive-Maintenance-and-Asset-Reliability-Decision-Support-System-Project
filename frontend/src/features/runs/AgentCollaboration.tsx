import './collaboration.css'
import { useEffect, useId, useRef, useState } from 'react'
import { usePack } from '../../i18n/pack'
import { Icon } from '../../shared/components/Icon'
import type { IconName } from '../../shared/components/Icon'
import { stateLabel } from '../../shared/labels'
import type { Pipelines, RunDetail, RunTask } from '../../shared/types'
import { BANDS, groupedTasks, roleBand } from './pipeline'
import type { RunEvent } from './runEvents'
import { collaborationEvents, finishedTasks, focusTask, groupState, isWorking } from './collaboration'
import { collaborationMessages } from './collaborationMessages'

const ICONS: IconName[] = ['database', 'activity', 'shield', 'send']
const MARKS: Record<string, string> = { succeeded: '✓', failed: '!', running: '…', awaiting_approval: '!', skipped: '—', cancelled: '—', pending: '·' }
interface Observation { run: RunDetail; events: RunEvent[]; interrupted: boolean }
interface Props extends Observation {
  pipelines: Pipelines | null
  onEvidence: (task: RunTask) => void
}

/** A view of governed stage state, never a simulated conversation.
 *  Mount with the run ID as its key: paused snapshots must not cross runs. */
export default function AgentCollaboration({ run, events, interrupted, pipelines, onEvidence }: Props) {
  const { t, isRtl, formatNumber, formatTime } = usePack(collaborationMessages)
  const titleId = useId()
  const [held, setHeld] = useState<Observation | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [hidden, setHidden] = useState(document.hidden)
  const observation = held ?? { run, events, interrupted }
  const shown = observation.run
  const history = collaborationEvents(shown, observation.events)
  const latest = history.at(-1)
  const latestStage = [...history].reverse().find((event) => event.kind === 'stage.changed')
  const initialEvent = useRef(latestStage?.id)
  const selected = shown.tasks.find((task) => task.id === selectedId) ?? focusTask(shown.tasks)
  const band = roleBand(selected?.role ?? '', pipelines)
  const groups = groupedTasks(shown.tasks, pipelines)
  const selectedIndex = shown.tasks.findIndex((task) => task.id === selected?.id)
  const working = isWorking(shown, observation.interrupted)
  const moving = !held && !hidden && !observation.interrupted && !shown.paused
  const latestTask = shown.tasks.find((task) => task.id === latestStage?.subject)
  const activeTask = working ? shown.tasks.find((task) => task.state === 'running') : latestTask
  const signalBand = roleBand(activeTask?.role ?? '', pipelines)
  const signalX = 50 + 100 * (isRtl ? 3 - BANDS.indexOf(signalBand) : BANDS.indexOf(signalBand))
  const newlyObserved = Boolean(latestStage && latestStage.id !== initialEvent.current)

  useEffect(() => {
    const update = () => setHidden(document.hidden)
    document.addEventListener('visibilitychange', update)
    return () => document.removeEventListener('visibilitychange', update)
  }, [])

  function eventText(event: RunEvent): string {
    if (event.kind === 'stage.changed') {
      return `${shown.tasks.find((task) => task.id === event.subject)?.title}: ${stateLabel(t, event.state)}`
    }
    if (event.kind === 'artifact.published') return t('flow.published')
    if (event.kind.startsWith('approval.')) {
      const decision = event.state === 'approved' ? t('flow.approved')
        : event.state === 'rejected' ? t('flow.rejected') : stateLabel(t, event.state)
      return `${t('flow.approval')}: ${decision}`
    }
    if (event.kind === 'run.paused') return t('flow.runPaused')
    if (event.kind === 'run.resumed') return t('flow.runResumed')
    return `${t('flow.received')}: ${stateLabel(t, event.state)}`
  }

  return <section className="agent-flow card" aria-labelledby={titleId} data-still={!moving} data-working={working}>
    <div className="agent-flow__head">
      <div><p className="eyebrow">{t('flow.live')}</p><h3 id={titleId}>{t('flow.title')}</h3></div>
      <button type="button" className="btn btn--ghost" aria-pressed={Boolean(held)}
        onClick={() => setHeld(held ? null : { run, events, interrupted })}>
        {held ? t('flow.resume') : t('flow.pause')}
      </button>
    </div>
    <p className="agent-flow__help">{held ? t('flow.paused') : observation.interrupted ? t('flow.interrupted') : t('flow.help')}</p>
    <div className="agent-flow__coordinator">
      <span className="agent-flow__emblem"><Icon name="command" size={23} /></span>
      <div><strong>Hermes</strong><span>{t('flow.coordinator')}</span></div>
      <span className="agent-flow__status">{shown.paused ? t('flow.runPaused') : stateLabel(t, shown.state)}</span>
    </div>
    <svg className="agent-flow__routes" viewBox="0 0 400 36" preserveAspectRatio="none" aria-hidden="true">
      <path d="M200 0V18M50 18H350M50 18V36M150 18V36M250 18V36M350 18V36" />
      {working || newlyObserved ? <path key={latestStage?.id} className={`agent-flow__signal ${newlyObserved ? 'agent-flow__signal--updated' : ''}`}
        d={`M200 0V18H${signalX}V36`} /> : null}
    </svg>
    <div className="agent-flow__groups" role="group" aria-label={t('flow.order')}>
      {groups.map(({ band: name, tasks }, index) => <button type="button" key={name}
        className={`agent-flow__group agent-flow__group--${groupState(tasks)}`} aria-pressed={band === name}
        disabled={!tasks.length} onClick={() => { setSelectedId(focusTask(tasks)?.id ?? null); setExpanded(true) }}>
        <span className="agent-flow__group-title"><Icon name={ICONS[index]} size={18} />{t(`cockpit.band.${name}`)}</span>
        <strong><bdi dir="ltr">{formatNumber(finishedTasks(tasks))}<span> / {formatNumber(tasks.length)}</span></bdi></strong>
        <span>{tasks.length ? stateLabel(t, groupState(tasks)) : t('flow.noStages')}</span>
      </button>)}
    </div>
    <p className="agent-flow__caption">{t('flow.count', { done: formatNumber(finishedTasks(shown.tasks)), total: formatNumber(shown.tasks.length) })}</p>
    <details open={expanded} onToggle={(event) => setExpanded(event.currentTarget.open)}>
      <summary>{t('flow.details')}</summary>
      <p className="agent-flow__help">{t('flow.orderHelp')}</p>
      <div className="agent-flow__stage-head">
        <h4>{t(`cockpit.band.${band}`)}</h4>
        <button type="button" className="evidence-link" onClick={() => setSelectedId(null)}>{t('flow.follow')}</button>
      </div>
      <div className="agent-flow__stages" role="group" aria-label={t('flow.stages')}>
        {groups.find((group) => group.band === band)?.tasks.map((task) => <button type="button" key={task.id}
          className={`agent-flow__stage agent-flow__stage--${task.state}`} aria-pressed={task.id === selected?.id}
          onClick={() => setSelectedId(task.id)}>
          <span className="agent-flow__mark" aria-hidden="true">{MARKS[task.state] ?? '·'}</span>
          <span lang={shown.report_language} dir="auto">{task.title}</span>
          <span className="agent-flow__task-state">{stateLabel(t, task.state)}</span>
        </button>)}
      </div>
      {selected ? <div className="agent-flow__inspector">
        <div className="agent-flow__handoff">
          <div><span>{t('flow.previous')}</span><p lang={shown.tasks[selectedIndex - 1] ? shown.report_language : undefined} dir="auto">{shown.tasks[selectedIndex - 1]?.title ?? t('flow.first')}</p></div>
          <Icon name="arrowDown" size={18} />
          <div><span>{t('flow.selected')}</span><p lang={shown.report_language} dir="auto"><strong>{selected.title}</strong></p></div>
          <Icon name="arrowDown" size={18} />
          <div><span>{t('flow.next')}</span><p lang={shown.tasks[selectedIndex + 1] ? shown.report_language : undefined} dir="auto">{shown.tasks[selectedIndex + 1]?.title ?? t('flow.last')}</p></div>
        </div>
        <p lang={selected.summary ? shown.report_language : undefined} dir="auto">{selected.summary ?? t('flow.noSummary')}</p>
        <div className="agent-flow__evidence">
          <span>{t('flow.checks', { n: formatNumber(selected.quality_checks.length) })}</span>
          <span>{t('flow.claims', { n: formatNumber(selected.claims.length) })}</span>
          {selected.claims.length || selected.quality_checks.length ? <button type="button" className="evidence-link"
            onClick={() => { const current = run.tasks.find((task) => task.id === selected.id); if (current) onEvidence(current) }}>
            {t('flow.evidence')}<Icon name="search" size={14} />
          </button> : null}
        </div>
      </div> : null}
      <details className="agent-flow__activity">
        <summary>{t('flow.history')}</summary>
        <p className="agent-flow__help">{t('flow.historyHelp')}</p>
        {history.length ? <p className="agent-flow__caption">{t('flow.historyCount', { n: formatNumber(Math.min(12, history.length)), total: formatNumber(history.length) })}</p> : null}
        {history.length ? <ol>{history.slice(-12).reverse().map((event) => <li key={event.id}>
          <time dateTime={event.time}>{formatTime(event.time)}</time>
          {event.kind === 'stage.changed'
            ? <button type="button" className="evidence-link" onClick={() => setSelectedId(event.subject)} dir="auto">{eventText(event)}</button>
            : <span dir="auto">{eventText(event)}</span>}
        </li>)}</ol> : <p>{t('flow.empty')}</p>}
      </details>
    </details>
    {latest ? <p className="agent-flow__latest" key={latest.id}><span dir="auto">{eventText(latest)}</span><span>{t('flow.updated', { time: formatTime(latest.time) })}</span></p> : null}
  </section>
}
