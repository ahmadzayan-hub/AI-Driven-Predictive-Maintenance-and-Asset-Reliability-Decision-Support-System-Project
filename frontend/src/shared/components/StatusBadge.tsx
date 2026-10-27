import { useI18n } from '../../i18n'
import type { MessageKey } from '../../i18n'
import type { ConnectionStatus } from '../types'

const LABELS: Record<ConnectionStatus, MessageKey> = {
  ready: 'status.ready',
  working: 'status.working',
  offline: 'status.offline',
  error: 'status.error',
  ended: 'status.ended',
}

/** Live session status shown in the header and announced to screen readers. */
export function StatusBadge({ status, announce = true }: { status: ConnectionStatus; announce?: boolean }) {
  const { t } = useI18n()
  return (
    <span className={`badge badge--${status}`} role={announce ? "status" : undefined} aria-live={announce ? "polite" : undefined}>
      <span className="badge__dot" aria-hidden="true" />
      {t('miyaar.session')}: {t(LABELS[status])}
    </span>
  )
}
