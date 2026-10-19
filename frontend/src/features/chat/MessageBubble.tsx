import { useState } from 'react'
import { useI18n } from '../../i18n'
import { MiyaarMark } from '../../shared/components/MiyaarMark'
import { Icon } from '../../shared/components/Icon'
import type { TranscriptEntry } from '../../shared/types'
import { ResultCard, ToolCards } from './ResultCard'
import { VoicePlayback } from './VoicePlayback'

interface MessageBubbleProps {
  entry: TranscriptEntry
  agentName: string
  onOpenRun?: (id: string) => void
}

export function MessageBubble({ entry, onOpenRun }: MessageBubbleProps) {
  const { t, plural, formatTime } = useI18n()
  const [copied, setCopied] = useState(false)
  const isAgent = entry.role === 'agent'

  async function copy() {
    try {
      await navigator.clipboard.writeText(entry.text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // Clipboard unavailable (permissions/insecure context) — leave silently.
    }
  }

  return (
    <article className={`msg msg--${entry.role}`} aria-label={isAgent ? t('msg.agent') : t('msg.you')}>
      {isAgent ? (
        <div className="msg__head">
          <MiyaarMark />
          <span className="msg__author" dir="auto">
            {t('assistant.name')}
          </span>
          <time dateTime={entry.time}>{formatTime(entry.time)}</time>
        </div>
      ) : null}
      {/* Each bubble orients by its own content: an English reply in an
          Arabic interface, or an Arabic question in an English one, reads
          in its own direction rather than the page's. */}
      <div className="msg__bubble" dir="auto">
        {entry.text}
      </div>
      {isAgent ? <><ResultCard entry={entry} onOpenRun={onOpenRun} /><ToolCards entry={entry} /></> : null}
      <div className="msg__meta">
        {isAgent ? (
          <>
            <button type="button" className="msg__copy" onClick={copy}>
              <Icon name={copied ? 'check' : 'copy'} size={13} />
              {copied ? t('msg.copied') : t('msg.copy')}
            </button>
            <VoicePlayback text={entry.text} />
            {/* Honest about who understood: a model's phrasing is
                labelled as such, the way a report names its narrator. */}
            {entry.source === 'rules' || entry.source === 'command' ? <span className="msg__source">{t(entry.source === 'rules' ? 'miyaar.rules' : 'miyaar.command')}</span> : null}
            {entry.source === 'model' ? (
              <span className="msg__source">
                {t('msg.viaModel', { provider: entry.provider ?? 'model' })}
              </span>
            ) : null}
            {/* An agent runtime's reply carries what it called: the tools'
                own texts are in the bubble verbatim; this says who drove
                them and how many calls it took. */}
            {entry.source === 'runtime' ? (
              <span className="msg__source">
                {t('msg.viaRuntime', { name: entry.provider ?? 'runtime' })} ·{' '}
                {plural('msg.toolCalls', entry.steps?.length ?? 0)}
              </span>
            ) : null}
          </>
        ) : (
          <time dateTime={entry.time}>{formatTime(entry.time)}</time>
        )}
      </div>
    </article>
  )
}

