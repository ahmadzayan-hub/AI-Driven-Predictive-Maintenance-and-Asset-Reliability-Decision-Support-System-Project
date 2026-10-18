import { useEffect, useRef, useState } from 'react'
import { useI18n } from '../../i18n'
import type { MessageKey } from '../../i18n'
import { Icon } from '../../shared/components/Icon'
import type { IconName } from '../../shared/components/Icon'
import { MiyaarMark } from '../../shared/components/MiyaarMark'
import { StatusBadge } from '../../shared/components/StatusBadge'
import type { ConnectionStatus, SessionState } from '../../shared/types'
import { Composer } from './Composer'
import type { ComposerHandle } from './Composer'
import { MessageBubble } from './MessageBubble'
import './miyaar.css'

export interface Suggestion { label: MessageKey; icon: IconName; insert: MessageKey }
export const SUGGESTIONS: Suggestion[] = [
  { label: 'miyaar.followupLabel', icon: 'shield', insert: 'miyaar.followupPrompt' },
  { label: 'suggestion.help', icon: 'help', insert: 'suggestion.help.insert' },
]
export type WorkspaceAction = 'analyse' | 'assets' | 'report' | 'compare' | 'approvals'
const ACTIONS: { id: WorkspaceAction; icon: IconName; title: MessageKey; description: MessageKey }[] = [
  { id: 'analyse', icon: 'database', title: 'miyaar.analyse', description: 'miyaar.analyseDesc' },
  { id: 'assets', icon: 'activity', title: 'miyaar.assets', description: 'miyaar.assetsDesc' },
  { id: 'report', icon: 'edit', title: 'miyaar.report', description: 'miyaar.reportDesc' },
  { id: 'compare', icon: 'dashboard', title: 'miyaar.compare', description: 'miyaar.compareDesc' },
  { id: 'approvals', icon: 'shield', title: 'miyaar.approvals', description: 'miyaar.approvalsDesc' },
]
const SOURCES: Record<string, MessageKey> = { model: 'miyaar.model', runtime: 'miyaar.runtime', rules: 'miyaar.rules', command: 'miyaar.command' }

interface ChatViewProps {
  session: SessionState
  sending: boolean
  failedText: string | null
  pendingText?: string | null
  requestError?: string | null
  connectionStatus?: ConnectionStatus
  offline: boolean
  userName: string | null
  onSend: (text: string) => void | Promise<boolean>
  onRetry: () => void
  onDismissFailed: () => void
  composerRef: React.RefObject<ComposerHandle | null>
  onOpenRun?: (id: string) => void
  onAction?: (action: WorkspaceAction) => void
}

/** A decorative industrial motif. No metric or status is encoded in the artwork. */
function IndustrialMotif() {
  return <div className="miyaar-hero__motif" aria-hidden="true">
    <svg viewBox="0 0 320 220" fill="none" stroke="currentColor" focusable="false">
      <path d="M0 64h45l30 30h40M320 158h-45l-32-32h-40M25 190h58l32-32M290 25h-50l-30 30" strokeOpacity=".3" />
      <circle cx="160" cy="110" r="87" strokeOpacity=".2" />
      <circle cx="160" cy="110" r="67" strokeDasharray="2 8" strokeOpacity=".6" />
      <circle cx="160" cy="110" r="49" strokeOpacity=".5" />
      {Array.from({ length: 12 }, (_, i) => <path key={i} d="M161 61l15 15-5 14" transform={`rotate(${i * 30} 160 110)`} strokeOpacity=".65" />)}
      <circle cx="160" cy="110" r="23" strokeWidth="2" />
      <path d="M148 116v-12l12 8 12-8v12" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="45" cy="64" r="4" /><circle cx="275" cy="158" r="4" />
    </svg>
  </div>
}

export function ChatView({
  session, sending, failedText, pendingText, requestError, connectionStatus,
  offline, userName, onSend, onRetry, onDismissFailed, composerRef, onOpenRun, onAction,
}: ChatViewProps) {
  const { t, formatNumber } = useI18n()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [pinnedToBottom, setPinnedToBottom] = useState(true)
  const [waiting, setWaiting] = useState(false)
  const transcriptLength = session.transcript.length
  const latest = session.transcript.filter((entry) => entry.role === 'agent').at(-1)
  const status = connectionStatus ?? (offline ? 'offline' : session.ended ? 'ended' : sending ? 'working' : 'ready')
  useEffect(() => {
    const container = scrollRef.current
    if (container && pinnedToBottom) container.scrollTop = transcriptLength || sending || failedText ? container.scrollHeight : 0
  }, [transcriptLength, sending, pinnedToBottom, failedText])
  useEffect(() => {
    setWaiting(false)
    if (!sending) return
    const timer = setTimeout(() => setWaiting(true), 8000)
    return () => clearTimeout(timer)
  }, [sending])
  function handleScroll() {
    const container = scrollRef.current
    if (container) setPinnedToBottom(container.scrollHeight - container.scrollTop - container.clientHeight < 48)
  }
  const empty = transcriptLength === 0 && !failedText && !sending
  return <section className="chat" aria-label={t('chat.aria')}>
    <div className="miyaar-toolbar">
      <MiyaarMark />
      <div><strong>{t('assistant.name')}</strong><span>{t('assistant.tagline')}</span></div>
      <span className="miyaar-toolbar__count">{formatNumber(transcriptLength)} · {t('rail.messages')}</span>
    </div>
    <div className="chat__scroll" ref={scrollRef} onScroll={handleScroll}>
      {empty ? <div className="miyaar-welcome">
        <div className="miyaar-hero">
          <div className="miyaar-hero__copy">
            <p className="eyebrow">{t('miyaar.eyebrow')}</p>
            {userName ? <p className="miyaar-hero__name"><bdi>{userName}</bdi></p> : null}
            <h2>{t('miyaar.headline')}</h2>
            <p>{t('miyaar.intro')}</p>
            <div className="miyaar-hero__steps">
              <span><Icon name="database" size={14} />{t('miyaar.step1')}</span>
              <span><Icon name="activity" size={14} />{t('miyaar.step2')}</span>
              <span><Icon name="shield" size={14} />{t('miyaar.step3')}</span>
            </div>
          </div>
          <div className="miyaar-hero__art"><IndustrialMotif /><span>{t('miyaar.art')}</span></div>
        </div>
        <dl className="miyaar-status">
          <div><dt><Icon name="activity" size={16} />{t('miyaar.session')}</dt><dd><StatusBadge status={status} announce={false} /></dd></div>
          <div><dt><Icon name="chat" size={16} />{t('miyaar.mode')}</dt><dd>{t('miyaar.noReply')}</dd></div>
          <div><dt><Icon name="shield" size={16} />{t('miyaar.governance')}</dt><dd>{t('miyaar.review')}</dd></div>
        </dl>
        <h3 className="miyaar-welcome__heading">{t('miyaar.start')}</h3>
        <div className="miyaar-actions">
          {ACTIONS.map((action) => <button key={action.id} type="button" className="miyaar-action"
            onClick={() => onAction?.(action.id)} disabled={!onAction}>
            <span className="miyaar-action__icon"><Icon name={action.icon} size={20} /></span>
            <span><strong>{t(action.title)}</strong><small>{t(action.description)}</small></span>
            <span className="miyaar-action__arrow" aria-hidden="true">↗</span>
          </button>)}
        </div>
        <p className="miyaar-welcome__note"><Icon name="shield" size={15} />{t('miyaar.sourceHint')}</p>
      </div> : <div className="chat__stream" role="log" aria-live="polite" aria-relevant="additions" aria-label={t('chat.aria')}>
        {session.transcript.map((entry) => <MessageBubble key={entry.id} entry={entry} agentName={t('assistant.name')} onOpenRun={onOpenRun} />)}
        {sending ? <>
          {pendingText ? <article className="msg msg--user" aria-label={t('miyaar.pending')}>
            <div className="msg__bubble" dir="auto">{pendingText}</div>
          </article> : null}
          <div className="typing" role="status">
            <MiyaarMark /><span>{t(waiting ? 'miyaar.waiting' : 'chat.typing')}</span>
            <span className="typing__dot" aria-hidden="true" />
          </div>
        </> : null}
        {!sending && latest?.source === 'rules' && latest.action === 'chat' ? <div className="miyaar-notice" role="status">
          <Icon name="help" size={18} /><p>{t('miyaar.fallback')}</p>
        </div> : null}
        {failedText ? <div className="alertbar" role="alert">
          <Icon name="alert" size={16} />
          <div><p>{t('chat.failed')}</p>{requestError ? <p dir="auto">{requestError}</p> : null}</div>
          <button type="button" className="alertbar__retry" onClick={onRetry} disabled={sending}>{t('chat.retry')}</button>
          <button type="button" className="iconbtn" onClick={onDismissFailed} aria-label={t('chat.dismiss')}><Icon name="x" size={14} /></button>
        </div> : null}
        {session.ended ? <div className="alertbar alertbar--info" role="status"><Icon name="power" size={16} /><span>{t('chat.ended')}</span></div> : null}
        {!sending && !session.ended && latest ? <div className="miyaar-followups" aria-label={t('miyaar.followup')}>
          {SUGGESTIONS.map((suggestion) => <button key={suggestion.label} type="button" className="suggestion"
            onClick={() => composerRef.current?.insert(t(suggestion.insert))}>
            <Icon name={suggestion.icon} size={15} />{t(suggestion.label)}
          </button>)}
          {onAction ? <button type="button" className="suggestion" onClick={() => onAction('assets')}><Icon name="activity" size={15} />{t('miyaar.assets')}</button> : null}
          <span className="msg__source">{latest.source && SOURCES[latest.source] ? t(SOURCES[latest.source]) : t('miyaar.sourceHint')}</span>
        </div> : null}
      </div>}
    </div>
    {!pinnedToBottom && !empty ? <button type="button" className="jump" onClick={() => {
      const container = scrollRef.current
      if (container) container.scrollTop = container.scrollHeight
      setPinnedToBottom(true)
    }}><Icon name="arrowDown" size={14} />{t('chat.latest')}</button> : null}
    <Composer draftKey={`${session.session_id}:composer`} ref={composerRef} onSend={onSend}
      busy={sending} disabled={session.ended || offline} offline={offline} />
  </section>
}
