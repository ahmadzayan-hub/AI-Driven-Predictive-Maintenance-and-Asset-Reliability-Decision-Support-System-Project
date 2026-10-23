import './collaboration.css'
import { useEffect, useId, useRef, useState } from 'react'
import { usePack } from '../../i18n/pack'
import { Icon } from '../../shared/components/Icon'
import type { IconName } from '../../shared/components/Icon'
import { stateLabel } from '../../shared/labels'
import type { Pipelines, RunDetail, RunTask } from '../../shared/types'
import { BANDS, groupedTasks, roleBand } from './pipeline'
import type { RunEvent } from './runEvents'
import { changeFlowZoom, collaborationEvents, finishedTasks, FLOW_ZOOM_MAX, FLOW_ZOOM_MIN, focusTask, groupState, handoffDirection, isWorking } from './collaboration'
import { collaborationMessages } from './collaborationMessages'

const ICONS: IconName[] = ['database', 'activity', 'shield', 'send']
const MARKS: Record<string, string> = { succeeded: '✓', failed: '!', running: '…', awaiting_approval: '!', skipped: '—', cancelled: '—', pending: '·' }
const ROUTES = [
  { outbound: 'M500 218V172Q500 110 430 110H300', inbound: 'M300 110H430Q500 110 500 172V218' },
  { outbound: 'M500 218V172Q500 110 570 110H700', inbound: 'M700 110H570Q500 110 500 172V218' },
  { outbound: 'M500 302V348Q500 410 430 410H300', inbound: 'M300 410H430Q500 410 500 348V302' },
  { outbound: 'M500 302V348Q500 410 570 410H700', inbound: 'M700 410H570Q500 410 500 348V302' },
]
interface Observation { run: RunDetail; events: RunEvent[]; interrupted: boolean }
interface Props extends Observation {
  pipelines: Pipelines | null
  onEvidence: (task: RunTask) => void
}

/** A view of governed stage state, never a simulated conversation.
 * Mount with the run ID as its key: paused snapshots must not cross runs. */
export default function AgentCollaboration({ run, events, interrupted, pipelines, onEvidence }: Props) {
  const { t, isRtl, formatNumber, formatTime } = usePack(collaborationMessages)
  const titleId = useId()
  const markerId = useId().replace(/:/g, '')
  const [held, setHeld] = useState<Observation | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(true)
  const [hidden, setHidden] = useState(document.hidden)
  const [reducedMotion, setReducedMotion] = useState(() => document.documentElement.dataset.motion === 'reduce'
    || Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches))
  const [pulseId, setPulseId] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const viewport = useRef<HTMLDivElement>(null)
  const observation = held ?? { run, events, interrupted }
  const shown = observation.run
  const history = collaborationEvents(shown, observation.events)
  const latest = history.at(-1)
  const latestStage = [...history].reverse().find((event) => event.kind === 'stage.changed')
  const lastObservedEvent = useRef(latestStage?.id)
  const selected = shown.tasks.find((task) => task.id === selectedId) ?? focusTask(shown.tasks)
  const band = roleBand(selected?.role ?? '', pipelines)
  const groups = groupedTasks(shown.tasks, pipelines)
  const selectedIndex = shown.tasks.findIndex((task) => task.id === selected?.id)
  const previous = shown.tasks[selectedIndex - 1]
  const next = shown.tasks[selectedIndex + 1]
  const working = isWorking(shown, observation.interrupted)
  const moving = !held && !hidden && !observation.interrupted && !shown.paused && !reducedMotion
  const latestTask = shown.tasks.find((task) => task.id === latestStage?.subject)
  const observedDirection = handoffDirection(latestStage)
  const activeTask = observedDirection ? latestTask : working ? shown.tasks.find((task) => task.state === 'running') : undefined
  const signalBand = roleBand(activeTask?.role ?? '', pipelines)
  const direction = observedDirection ?? (working ? 'outbound' : null)
  const routeIndex = (index: number) => isRtl ? index ^ 1 : index
  const signalRoute = ROUTES[routeIndex(BANDS.indexOf(signalBand))]

  useEffect(() => {
    const update = () => {
      setHidden(document.hidden)
      if (document.hidden) setPulseId(null)
    }
    document.addEventListener('visibilitychange', update)
    return () => document.removeEventListener('visibilitychange', update)
  }, [])

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    const update = () => {
      const reduced = document.documentElement.dataset.motion === 'reduce' || Boolean(media?.matches)
      setReducedMotion(reduced)
      if (reduced) setPulseId(null)
    }
    const observer = new MutationObserver(update)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-motion'] })
    media?.addEventListener('change', update)
    update()
    return () => { observer.disconnect(); media?.removeEventListener('change', update) }
  }, [])

  useEffect(() => {
    const id = latestStage?.id
    const unseen = Boolean(id && id !== lastObservedEvent.current)
    if (id) lastObservedEvent.current = id
    // Consume observed updates even when motion is suppressed. A held view may
    // discover a new update on resume, but cannot replay one already observed.
    if (!moving) setPulseId(null)
    else if (unseen) setPulseId(observedDirection ? id! : null)
  }, [latestStage?.id, moving, observedDirection])

  useEffect(() => {
    if (!pulseId) return
    // Hidden SVGs (the phone layout) do not dispatch animationend.
    const timeout = window.setTimeout(() => setPulseId((current) => current === pulseId ? null : current), 900)
    return () => window.clearTimeout(timeout)
  }, [pulseId])

  function fit() {
    setZoom(1)
    if (viewport.current) { viewport.current.scrollLeft = 0; viewport.current.scrollTop = 0 }
  }

  function eventText(event: RunEvent): string {
    if (event.kind === 'stage.changed') {
      return `${shown.tasks.find((task) => task.id === event.subject)?.title}: ${stateLabel(t, event.state)}`
    }
    if (event.kind === 'artifact.published') return t('flow.published')
    if (event.kind === 'approval.superseded') return t('flow.reviewReplaced')
    if (event.kind.startsWith('approval.')) {
      const decision = ['approved', 'approved_once'].includes(event.state) ? t('flow.approved')
        : event.state === 'rejected' ? t('flow.rejected') : stateLabel(t, event.state)
      return `${t('flow.approval')}: ${decision}`
    }
    if (event.kind === 'run.paused') return t('flow.runPaused')
    if (event.kind === 'run.resumed') return t('flow.runResumed')
    return `${t('flow.received')}: ${stateLabel(t, event.state)}`
  }

  return <section className="agent-flow card" aria-labelledby={titleId} data-still={!moving} data-working={working}>
    <div className="agent-flow__head">
      <div><p className="eyebrow">{t('flow.workspace')}</p><h3 id={titleId}>{t('flow.title')}</h3></div>
      <button type="button" className="btn btn--ghost" aria-pressed={Boolean(held)}
        onClick={() => { setPulseId(null); setHeld(held ? null : { run, events, interrupted }) }}>
        <Icon name={held ? 'refresh' : 'clock'} size={16} />{held ? t('flow.resume') : t('flow.pause')}
      </button>
    </div>
    <p className="agent-flow__help">{held ? t('flow.paused') : observation.interrupted ? t('flow.interrupted') : t('flow.help')}</p>
    <div className="agent-flow__workspace">
      <div className="agent-flow__map">
        <div className="agent-flow__toolbar">
          <span className="agent-flow__live"><span aria-hidden="true" />{t('flow.live')}</span>
          <div className="agent-flow__zoom" role="group" aria-label={t('flow.controls')}>
            <button type="button" aria-label={t('flow.zoomOut')} disabled={zoom <= FLOW_ZOOM_MIN} onClick={() => setZoom((value) => changeFlowZoom(value, -.1))}><span aria-hidden="true">−</span></button>
            <output aria-label={t('flow.zoom', { n: formatNumber(Math.round(zoom * 100)) })}><bdi dir="ltr">{formatNumber(Math.round(zoom * 100))}%</bdi></output>
            <button type="button" aria-label={t('flow.zoomIn')} disabled={zoom >= FLOW_ZOOM_MAX} onClick={() => setZoom((value) => changeFlowZoom(value, .1))}><Icon name="plus" size={16} /></button>
            <button type="button" className="agent-flow__fit" onClick={fit}>{t('flow.fit')}</button>
          </div>
          <span className="agent-flow__sequence-label">{t('flow.sequence')}</span>
        </div>
        <div className="agent-flow__viewport" ref={viewport}>
          <div className="agent-flow__zoom-surface" style={{ width: `${zoom * 100}%`, minHeight: `${zoom * 520}px` }}>
            <div className="agent-flow__canvas" data-zoom={zoom} style={{ width: `${100 / zoom}%`, transform: `scale(${zoom})`, transformOrigin: isRtl ? 'top right' : 'top left' }}>
              <svg className="agent-flow__routes" viewBox="0 0 1000 520" preserveAspectRatio="none" aria-hidden="true">
                <defs><marker id={markerId} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M1 1L8 5L1 9" /></marker></defs>
                {groups.map(({ band: name, tasks }, index) => <path key={name} className={band === name ? 'agent-flow__route--selected' : undefined}
                  data-connected={Boolean(tasks.length)} d={ROUTES[routeIndex(index)].outbound} markerEnd={`url(#${markerId})`} />)}
                {activeTask && direction ? <path key={latestStage?.id ?? activeTask.id}
                  className={`agent-flow__signal ${moving && pulseId === latestStage?.id ? 'agent-flow__signal--updated' : ''}`}
                  onAnimationEnd={() => setPulseId((current) => current === latestStage?.id ? null : current)}
                  data-direction={direction} pathLength="100" d={signalRoute[direction]} /> : null}
              </svg>
              <div className="agent-flow__coordinator">
                <span className="agent-flow__emblem"><Icon name="command" size={28} /></span>
                <div><strong>Hermes</strong><span>{t('flow.coordinator')}</span></div>
                <span className={`agent-flow__status agent-flow__status--${shown.state}`}>{shown.paused ? t('flow.runPaused') : stateLabel(t, shown.state)}</span>
              </div>
              <div className="agent-flow__groups" role="group" aria-label={t('flow.order')}>
                {groups.map(({ band: name, tasks }, index) => {
                  const state = groupState(tasks)
                  const current = focusTask(tasks)
                  return <button type="button" key={name}
                    className={`agent-flow__group agent-flow__group--${state}`} aria-pressed={band === name}
                    disabled={!tasks.length} onClick={() => { setSelectedId(current?.id ?? null); setExpanded(true) }}>
                    <span className="agent-flow__group-title"><Icon name={ICONS[index]} size={19} /><span>{t(`cockpit.band.${name}`)}</span></span>
                    <span className="agent-flow__group-meta"><span className={`agent-flow__status agent-flow__status--${state}`}>{tasks.length ? stateLabel(t, state) : t('flow.noStages')}</span>
                      <strong><bdi dir="ltr">{formatNumber(finishedTasks(tasks))}<span> / {formatNumber(tasks.length)}</span></bdi></strong></span>
                    <span className="agent-flow__preview" lang={current ? shown.report_language : undefined} dir="auto">{current?.title ?? t('flow.noStages')}</span>
                    <span className="agent-flow__progress" aria-hidden="true"><span style={{ width: `${tasks.length ? 100 * finishedTasks(tasks) / tasks.length : 0}%` }} /></span>
                    <span className="agent-flow__ordinal" aria-hidden="true"><bdi>{formatNumber(index + 1)}</bdi></span>
                  </button>
                })}
              </div>
            </div>
          </div>
        </div>
        <div className="agent-flow__map-footer">
          <p className="agent-flow__caption">{t('flow.count', { done: formatNumber(finishedTasks(shown.tasks)), total: formatNumber(shown.tasks.length) })}</p>
          <div className="agent-flow__legend" role="group" aria-label={t('flow.legend')}>
            {['running', 'awaiting_approval', 'failed'].map((state) => <span key={state} className={`agent-flow__status agent-flow__status--${state}`}>{stateLabel(t, state)}</span>)}
          </div>
        </div>
        <p className="agent-flow__help agent-flow__order-help">{t('flow.orderHelp')}</p>
      </div>
      <details className="agent-flow__detail-panel" open={expanded} onToggle={(event) => setExpanded(event.currentTarget.open)}>
        <summary>{t('flow.details')}</summary>
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
          <div className="agent-flow__inspector-label"><span>{t('flow.inspect')}</span><bdi>{t('flow.position', { n: formatNumber(selectedIndex + 1), total: formatNumber(shown.tasks.length) })}</bdi></div>
          <div className="agent-flow__handoff">
            <button type="button" aria-label={t('flow.previous')} disabled={!previous} onClick={() => { if (previous) setSelectedId(previous.id) }}><span>{t('flow.previous')}</span><p lang={previous ? shown.report_language : undefined} dir="auto">{previous?.title ?? t('flow.first')}</p></button>
            <Icon name="arrowDown" size={18} />
            <div><span>{t('flow.selected')}</span><p lang={shown.report_language} dir="auto"><strong>{selected.title}</strong></p><span className={`agent-flow__status agent-flow__status--${selected.state}`}>{stateLabel(t, selected.state)}</span></div>
            <Icon name="arrowDown" size={18} />
            <button type="button" aria-label={t('flow.next')} disabled={!next} onClick={() => { if (next) setSelectedId(next.id) }}><span>{t('flow.next')}</span><p lang={next ? shown.report_language : undefined} dir="auto">{next?.title ?? t('flow.last')}</p></button>
          </div>
          {selected.state === 'awaiting_approval' ? <p className="agent-flow__review"><Icon name="shield" size={16} />{t('flow.review')}</p> : null}
          <p className="agent-flow__summary" lang={selected.summary ? shown.report_language : undefined} dir="auto">{selected.summary ?? t('flow.noSummary')}</p>
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
    </div>
    {latest ? <p className="agent-flow__latest" key={latest.id}><span><Icon name="activity" size={14} /><span dir="auto">{eventText(latest)}</span></span><span>{t('flow.updated', { time: formatTime(latest.time) })}</span></p>
      : <p className="agent-flow__caption">{t('flow.waiting')}</p>}
  </section>
}
