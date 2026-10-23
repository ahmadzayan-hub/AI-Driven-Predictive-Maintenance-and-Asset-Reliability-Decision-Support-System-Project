import { definePack, usePack } from '../../i18n/pack'
import { Icon } from '../../shared/components/Icon'

export const decisionActionMessages = definePack({
  agents: 'Inspect agent workflow',
  agentsHelp: 'Follow handoffs, stages and the evidence behind a run',
}, {
  agents: 'استعراض سير عمل الوكلاء',
  agentsHelp: 'تتبّع انتقال العمل بين المراحل والأدلة المرتبطة بالتحليل',
})

interface DecisionActionsProps {
  /** Absent in the view-only demo, where nothing can be uploaded. */
  onUpload?: () => void
  onDashboard: () => void
  onApprovals?: () => void
  /** Only offered when a real run can be inspected. */
  onAgents?: () => void
}

/** A factual, action-first entry point. Never displays fictional
 * asset KPIs or opens a non-existent feature. */
export function DecisionActions({ onUpload, onDashboard, onApprovals, onAgents }: DecisionActionsProps) {
  const { t } = usePack(decisionActionMessages)
  return (
    <section className="decision-actions" aria-label={t('decision.heading')}>
      <div className="decision-actions__grid">
        {onUpload ? (
          <button type="button" onClick={onUpload}>
            <Icon name="database" size={21}/>
            <span><strong>{t('decision.upload')}</strong><small>{t('decision.uploadHelp')}</small></span>
          </button>
        ) : null}
        {onAgents ? (
          <button type="button" onClick={onAgents}>
            <Icon name="activity" size={21}/>
            <span><strong>{t('agents')}</strong><small>{t('agentsHelp')}</small></span>
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
