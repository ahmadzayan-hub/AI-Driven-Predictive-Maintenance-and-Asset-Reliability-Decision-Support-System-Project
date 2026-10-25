import { useI18n } from '../i18n'
import type { MessageKey } from '../i18n'
import { Icon } from '../shared/components/Icon'
import type { IconName } from '../shared/components/Icon'
import type { Tab } from './routing'

interface Destination { id: Tab; label: MessageKey; icon: IconName }
export const NEEDS_SESSION: ReadonlySet<Tab> = new Set(['chat', 'memory', 'preferences', 'operations', 'rmd'])
export const WORKFLOW: { label: MessageKey; items: Destination[] }[] = [
  { label: 'nav.sources', items: [{ id: 'datasets', label: 'nav.datasets', icon: 'database' }] },
  { label: 'nav.evidence', items: [
    { id: 'runs', label: 'nav.runs', icon: 'sparkle' },
    { id: 'assets', label: 'nav.assets', icon: 'activity' },
    { id: 'rmd', label: 'nav.rmd', icon: 'search' },
  ] },
  { label: 'nav.priorities', items: [
    { id: 'overview', label: 'nav.overview', icon: 'dashboard' },
    { id: 'approvals', label: 'nav.approvals', icon: 'shield' },
    { id: 'operations', label: 'nav.operations', icon: 'check' },
  ] },
  { label: 'nav.outputs', items: [{ id: 'dashboard', label: 'nav.dashboard', icon: 'chart' }] },
]
const TOOLS: Destination[] = [
  { id: 'memory', label: 'nav.memory', icon: 'memory' },
  { id: 'activity', label: 'nav.activity', icon: 'clock' },
  { id: 'preferences', label: 'nav.preferences', icon: 'settings' },
]

/** Stages are navigation, never a claim that analysis or approval is complete. */
export function WorkflowNav({ tab, demo, onGo }: { tab: Tab; demo: boolean; onGo: (tab: Tab) => void }) {
  const { t } = useI18n()
  const button = (item: Destination) => <button key={item.id} type="button" className="navbtn" data-route={item.id}
    aria-current={tab === item.id ? 'page' : undefined} onClick={() => onGo(item.id)}>
    <Icon name={item.icon} size={18} />{t(item.label)}
  </button>
  return <nav className="sidebar__nav" aria-label={t('nav.main')}>
    {WORKFLOW.map((stage, index) => {
      const items = stage.items.filter(item => !demo || !NEEDS_SESSION.has(item.id))
      const active = items.some(item => item.id === tab)
      return <section key={stage.label} className="workflow-stage" aria-label={t(stage.label)}>
        <button type="button" className="navbtn workflow-stage__entry" data-route={items[0].id} aria-current={active ? 'step' : undefined}
          onClick={() => onGo(items[0].id)}><span aria-hidden="true">{index + 1}</span>{t(stage.label)}</button>
        <div className="workflow-stage__views" hidden={!active || items.length === 1}>{items.map(button)}</div>
      </section>
    })}
    {!demo ? button({ id: 'chat', label: 'nav.assistant', icon: 'chat' }) : null}
    <details className="sidebar__group" open={TOOLS.some(item => item.id === tab)}>
      <summary>{t('nav.tools')}</summary>{TOOLS.filter(item => !demo || !NEEDS_SESSION.has(item.id)).map(button)}
    </details>
  </nav>
}
