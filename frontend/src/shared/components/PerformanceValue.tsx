import type { ReactNode } from 'react'
import { usePack } from '../../i18n/pack'
import { performanceMessages } from './performanceMessages'
import './performance.css'

export type PerformanceTone = 'good' | 'okay' | 'bad' | 'unassessed' | 'unavailable'

const performanceTones: PerformanceTone[] = ['bad', 'okay', 'good', 'unassessed', 'unavailable']

export function PerformanceLegend() {
  const { t } = usePack(performanceMessages)
  return <aside className="performance-legend" aria-label={t('performance.legend')}>
    <strong className="performance-legend__title">{t('performance.legend')}</strong>
    <ul>{performanceTones.map((tone) => <li key={tone} data-tone={tone}>
      <span className="performance-value__status">{t(`performance.${tone}`)}</span>
    </li>)}</ul>
    <p>{t('performance.explanation')}</p>
  </aside>
}

/** Only a supplied assessment establishes performance. Sign, magnitude and
 * metric name never establish an outcome; an absent number stays unavailable. */
export function performanceTone(value: number | null | undefined, assessment?: { status?: string } | null): PerformanceTone {
  if (value == null || !Number.isFinite(value)) return 'unavailable'
  const status = assessment?.status
  return status === 'good' || status === 'okay' || status === 'bad' || status === 'unavailable' ? status : 'unassessed'
}

/** Preserve the caller's governed number, unit and locale formatting. */
export function PerformanceValue({ tone, children, status, reason }: {
  tone: PerformanceTone
  children: ReactNode
  status?: string
  reason?: string
}) {
  const { t } = usePack(performanceMessages)
  return <span className="performance-value" data-performance={tone}>
    <span className="performance-value__number">{children}</span>
    <span className="performance-value__status">{status || t(`performance.${tone}`)}</span>
    {reason ? <span className="performance-value__reason" dir="auto">{reason}</span> : null}
  </span>
}
