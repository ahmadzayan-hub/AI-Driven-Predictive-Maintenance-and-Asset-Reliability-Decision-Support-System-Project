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
import { DataChatContext } from './DataChatContext'

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

/** A decorative AI-core motif: rings, an orbit and streams around the
 *  mark. No metric, status or activity is encoded in the artwork. */
function CoreMotif() {
  return <div className="miyaar-hero__motif miyaar-core" aria-hidden="true">
    <svg viewBox="0 0 320 220" fill="none" stroke="currentColor" focusable="false">
      {Array.from({ length: 16 }, (_, i) => <path key={i} d="M160 110 L160 8" strokeOpacity={i % 2 ? '.12' : '.22'} transform={`rotate(${i * 22.5} 160 110)`} />)}
      <circle cx="160" cy="110" r="96" strokeOpacity=".18" />
      <circle cx="160" cy="110" r="74" strokeDasharray="3 9" strokeOpacity=".55" className="miyaar-core__orbit" />
      <circle cx="160" cy="110" r="52" strokeOpacity=".4" />
      <circle cx="160" cy="110" r="34" strokeWidth="2" />
      <path d="M146 118v-16l14 10 14-10v16" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="234" cy="110" r="4" fill="currentColor" /><circle cx="86" cy="110" r="4" fill="currentColor" />
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
  return <div className="assistant-workspace">
    <aside className="assistant-context" aria-label={session.data_chat_labels?.title ?? t('miyaar.workspace')}>
      <div className="assistant-context__state"><strong>{t('miyaar.session')}</strong><StatusBadge status={status} announce={false} /></div>
      {session.assistant_status && <p className="miyaar-notice" role="status" dir="auto">{session.assistant_status.message}</p>}
      <DataChatContext key={session.session_id} session={session} disabled={session.ended || offline || sending} />
      <p className="assistant-context__boundary"><Icon name="shield" size={18} />{t('miyaar.review')}</p>
    </aside>
    <section className="chat" aria-label={t('chat.aria')}>
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
          <div className="miyaar-hero__art"><CoreMotif /><span>{t('miyaar.art')}</span></div>
        </div>
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
    <Composer sessionId={session.session_id} draftKey={`${session.session_id}:composer`} ref={composerRef} onSend={onSend}
      busy={sending} disabled={session.ended || offline} offline={offline} />
  </section></div>
}
