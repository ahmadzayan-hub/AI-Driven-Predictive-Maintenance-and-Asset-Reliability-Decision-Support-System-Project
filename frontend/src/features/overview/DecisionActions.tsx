import { useI18n } from '../../i18n'
import { Icon } from '../../shared/components/Icon'

interface DecisionActionsProps {
  /** Absent in the view-only demo, where nothing can be uploaded. */
  onUpload?: () => void
  onDashboard: () => void
  onApprovals?: () => void
}

/** A factual, action-first entry point. Never displays fictional
 * asset KPIs or opens a non-existent feature. */
export function DecisionActions({ onUpload, onDashboard, onApprovals }: DecisionActionsProps) {
  const { t } = useI18n()
  return (
    <section className="decision-actions" aria-labelledby="decision-actions-title">
      <div className="decision-actions__intro">
        <span className="decision-actions__eyebrow">{t('decision.eyebrow')}</span>
        <h3 id="decision-actions-title">{t('decision.heading')}</h3>
        <p>{t('decision.subtitle')}</p>
      </div>
      <div className="decision-actions__grid">
        {onUpload ? (
          <button type="button" onClick={onUpload}>
            <Icon name="database" size={21}/>
            <span><strong>{t('decision.upload')}</strong><small>{t('decision.uploadHelp')}</small></span>
          </button>
        ) : null}
        <button type="button" onClick={onDashboard}>
          <Icon name="dashboard" size={21}/>
          <span><strong>{t('decision.dashboard')}</strong><small>{t('decision.dashboardHelp')}</small></span>
        </button>
        {onApprovals ? (
          <button type="button" onClick={onApprovals}>
            <Icon name="shield" size={21}/>
            <span><strong>{t('decision.approvals')}</strong><small>{t('decision.approvalsHelp')}</small></span>
          </button>
        ) : null}
      </div>
    </section>
  )
}
